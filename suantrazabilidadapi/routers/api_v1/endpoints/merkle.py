import binascii
import os
from typing import Union
import logging

from fastapi import APIRouter, HTTPException
from pymerkle import DynamoDBTree, verify_inclusion
from pycardano import (
    HDWallet,
    ExtendedSigningKey,
    Address,
    PaymentVerificationKey,
    TransactionBuilder,
    ScriptPubkey,
    ScriptAll,
    MultiAsset,
    ScriptHash,
    AssetName,
    min_lovelace,
    TransactionOutput,
    Value,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,

)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.exception import ResponseDynamoDBException, ResponseFindingUtxo
from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.utils.plataforma import CardanoApi, Plataforma
from suantrazabilidadapi.utils.response import Response

router = APIRouter()

async def admin_call():
    env = os.getenv("env")
    command_name = "getWalletAdmin"
    graphql_variables = {"isAdmin": True}

    listWallet_response = Plataforma().getWallet(command_name, graphql_variables)

    final_response = Response().handle_listWallets_response(listWallets_response=listWallet_response)

    if not final_response.get("data", None):
        raise ResponseDynamoDBException(
            f"Could not find the core wallet for the environment: {env}"
        )

    return final_response

@router.post(
    "/merkle-tree/",
    status_code=201,
    summary="Include the information provided in the merkle tree table and submit the digest to the blockchain as part of a metadata transaction",
    response_description="Blockchain transaction id confirmation",
)
async def merkleTree(action: pydantic_schemas.OracleAction, project_id: str, body: dict = {}, onchain: bool = True) -> dict:
    """Include result in merkle tree and submit information to the blockchain as part of a metadata transaction \n"""
    env = os.getenv("env")
    opts = { "app_name": project_id, "env": env + ("-onchain" if onchain else "-local") }
    try:
        #TODO: In future, explore the possibility to use datum instead of metadata
        tree = DynamoDBTree(aws_access_key_id=Constants.AWS_ACCESS_KEY_ID, aws_secret_access_key=Constants.AWS_SECRET_ACCESS_KEY, region_name=Constants.REGION_NAME, **opts)
        hash = tree.hash_hex(body)

        #TODO: I need to allow more time for the table to be created for the first time, otherwise the insertion will fail
        index = tree.get_index_by_digest_hex(hash)
        if index:
            raise ValueError(f"Data already stored in merkle tree with index: {index}") 
        
        index = tree.append_entry(body)

        root = tree.get_state()

        tx_id = None

        if onchain:

            final_response = await admin_call()
            coreWalletInfo = final_response["data"]["items"][0]

            # Get core wallet params
            seed = coreWalletInfo["seed"]
            hdwallet = HDWallet.from_seed(seed)
            child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

            core_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)
            core_address = Address.from_primitive(coreWalletInfo["address"])

            core_vkey = PaymentVerificationKey.from_primitive(
                            child_hdwallet.public_key
                        )

            chain_context = CardanoNetwork().get_chain_context()

            # Create a transaction builder
            builder = TransactionBuilder(chain_context)

            # Add core address as the input address
            builder.add_input_address(core_address)

            ########################
            """Create the native script and policy from the pubkey"""
            ########################
            pub_key_policy = ScriptPubkey(core_vkey.hash())
            policy = ScriptAll([pub_key_policy])
            # Calculate policy ID, which is the hash of the policy
            policy_id = policy.hash()
            native_scripts = [policy]

            # Set native script
            builder.native_scripts = native_scripts
            merkle_token_name = tree.table_name
            tokenName = bytes(merkle_token_name, encoding="utf-8")
            ########################
            """Define NFT"""
            ########################
            my_nft = MultiAsset.from_primitive(
                {
                    policy_id.payload: {
                        tokenName: 1,
                    }
                }
            )
            #TODO: Move this section to a common function; this section is also used in the oracleDatum endpoint
            if action == "Create":
                builder.mint = my_nft
                # Set native script
                builder.native_scripts = native_scripts
                msg = f"{merkle_token_name} minted to store merkle root for project {project_id}"
            else:
                merkle_utxo = None
                for utxo in chain_context.utxos(core_address):

                    def f1(pi: ScriptHash, an: AssetName, a: int) -> bool:
                        return pi == policy_id and an.payload == tokenName and a == 1

                    if utxo.output.amount.multi_asset.count(f1):
                        merkle_utxo = utxo

                        builder.add_input(merkle_utxo)

                # Check if merkle_utxo exists and is found
                if not merkle_utxo:
                    raise ResponseFindingUtxo(
                        f"Utxo for oracle token name {merkle_token_name} could not be found in {core_address}"
                    )

            min_val = min_lovelace(
                chain_context,
                output=TransactionOutput(core_address, Value(0, my_nft)),
            )
            builder.add_output(
                TransactionOutput(core_address, Value(min_val, my_nft))
            )

            # TODO: Move this section to a common function; this section is used in several endpoints
            ########################
            """Create metadata"""
            ########################
            metadata = {
                721: {
                    policy_id.payload.hex(): {
                        merkle_token_name: {
                            "name": f"MerkleTree token for project {project_id}",
                            "image": "ipfs://QmVjGABVnLpKHfs8VnLzfvCRZrjryxVe2N57bVW8Zx5ggq",
                            "mediaType": "image/png",
                            "description": f"MerkleTree token for project {project_id}",
                            "files": [{
                                "name": "Merkle Tree root certificate",
                                "mediaType": "image/png",
                                "src": "ipfs://QmVjGABVnLpKHfs8VnLzfvCRZrjryxVe2N57bVW8Zx5ggq"
                            }],
                            "url": f"https://{env}.marketplace.suan.global", #TODO: idea is to provide a link to the table results or the report in png format
                            "root_digest": root.hex()
                            }
                        },
                    }
                }
            # Place metadata in AuxiliaryData, the format acceptable by a transaction.
            auxiliary_data = AuxiliaryData(
                AlonzoMetadata(metadata=Metadata(metadata))
            )
            # Set transaction metadata
            builder.auxiliary_data = auxiliary_data


            signed_tx = builder.build_and_sign(
                [core_skey], change_address=core_address
            )

            # Submit signed transaction to the network
            tx_id = signed_tx.transaction_body.hash().hex()
            chain_context.submit_tx(signed_tx)
            

        final_response = {
            "success": True,
            "onchain": onchain,
            "msg": f"Root for merkle tree implementation for project {project_id} updated. Root: {root}",
            "project_id": project_id,
            "index": index,
            "data_hash": hash,
            "tx_id": tx_id,
        }
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    

@router.post(
    "/verify-inclusion/",
    status_code=201,
    summary="Verify the inclusion of a data in the merkle tree",
    response_description="Verification result",
)
async def verifyInclusion(project_id: str, index: Union[int, None] = None, body: dict = {}, onchain: bool = False) -> dict:
    """ Index is optional. If provided it will search for this record in local DB; otherwise it will verify inclusion iteratively across all existing records until finalize verification\n"""
    env = os.getenv("env")
    opts = { "app_name": project_id, "env": env + ("onchain" if onchain else "local") }
    try:
        tree = DynamoDBTree(aws_access_key_id=Constants.AWS_ACCESS_KEY_ID, aws_secret_access_key=Constants.AWS_SECRET_ACCESS_KEY, region_name=Constants.REGION_NAME, **opts)
        
        if onchain:
            ########################
            """Derive the policyid from the core wallet"""
            ########################
            final_response = await admin_call()

            coreWalletInfo = final_response["data"]["items"][0]
            seed = coreWalletInfo["seed"]
            hdwallet = HDWallet.from_seed(seed)
            child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
            core_vkey = PaymentVerificationKey.from_primitive(
                    child_hdwallet.public_key
                )
            pub_key_policy = ScriptPubkey(core_vkey.hash())
            policy = ScriptAll([pub_key_policy])
            # Calculate policy ID, which is the hash of the policy
            policy_id = policy.hash()
            # Concatenate the policy_id with the token name
            asset_name = policy_id.payload.hex() + binascii.hexlify(bytes(tree.table_name, 'utf-8')).decode('utf-8')
            cardanoApi = CardanoApi()
            asset_info = cardanoApi.specificAssetInfo(asset_name)

            blockchain_root = asset_info.get("onchain_metadata", {}).get("root_digest", None)
            if not blockchain_root:
                raise ValueError(f"Could not find the root digest for the asset {asset_name}")

            blockchain_root = binascii.unhexlify(blockchain_root)
            root = blockchain_root
        else:
            root = tree.get_state()

        hash = tree.hash_hex(body)

        base = binascii.unhexlify(hash)

        size = tree.get_size()

        # Generate proof
        inclusion = False
        if not index:
            for i in range(size):
                proof = tree.prove_inclusion(i + 1)
                inclusion = verify_inclusion(base, root, proof)
                if inclusion:
                    break
        else:
            proof = tree.prove_inclusion(index)
            inclusion = verify_inclusion(base, root, proof)

        logging.info(inclusion)

        if inclusion:
            final_response = {
                "msg": "Verification of inclusion succesful",
                "project_id": project_id,
                "data_hash": hash,
                "inclusion": inclusion,
                "proof": proof.serialize(),
            }
        else:
            final_response = {
                "msg": "Verification of inclusion failed",
                "project_id": project_id,
                "data_hash": hash,
                "inclusion": inclusion,
                "proof": proof.serialize(),
            }
        return final_response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e