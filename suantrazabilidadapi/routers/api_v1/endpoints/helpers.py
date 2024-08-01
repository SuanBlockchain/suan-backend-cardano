import logging
from typing import Optional, Union

from cbor2 import loads
from fastapi import APIRouter, HTTPException, Depends
from pycardano import (
    Address,
    AlonzoMetadata,
    AssetName,
    AuxiliaryData,
    Datum,
    ExtendedSigningKey,
    HDWallet,
    InvalidHereAfter,
    Metadata,
    MultiAsset,
    PaymentVerificationKey,
    ScriptAll,
    ScriptHash,
    ScriptPubkey,
    TransactionBuilder,
    TransactionOutput,
    Value,
    min_lovelace,
)

# from sqlalchemy.orm import Session

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork, Keys
from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.utils.plataforma import CardanoApi, Helpers, Plataforma

# from suantrazabilidadapi.db.dblib import get_db
# from suantrazabilidadapi.db.models import dbmodels

router = APIRouter()


# @router.post(
#     "/tx-status/",
#     status_code=201,
#     summary="Get the number of block confirmations for a given transaction hash list",
#     response_description="Array of transaction confirmation counts",
#     # response_model=List[str],
# )
# async def txStatus(tx_hashes: Union[str, list[str]]) -> list:
#     try:
#         return CardanoApi().txStatus(tx_hashes)

#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/send-access-token/",
    status_code=201,
    summary="Get the token to access Suan Marketplace",
    response_description="Confirmation of token sent to provided address",
    # response_model=List[str],
)
async def sendAccessToken(wallet_id: str, destinAddress: str):
    try:
        ########################
        """1. Obtain the MasterKey to pay and mint"""
        ########################

        # db_wallet = db.query(dbmodels.TokenAccess).filter(dbmodels.TokenAccess.requester == destinAddress).first()

        r = Plataforma().getWallet("id", wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                raise ValueError(
                    f"Wallet with id: {wallet_id} does not exist in DynamoDB"
                )
            else:
                seed = walletInfo["seed"]
                hdwallet = HDWallet.from_seed(seed)
                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                payment_vk = PaymentVerificationKey.from_primitive(
                    child_hdwallet.public_key
                )

                master_address = Address.from_primitive(walletInfo["address"])
                ########################
                """3. Create the script and policy"""
                ########################
                # A policy that requires a signature from the policy key we generated above
                pub_key_policy = ScriptPubkey(payment_vk.hash())  # type: ignore
                # A time policy that disallows token minting after 10000 seconds from last block
                # must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
                # Combine two policies using ScriptAll policy
                policy = ScriptAll([pub_key_policy])
                # Calculate policy ID, which is the hash of the policy
                policy_id = policy.hash()
                print(f"Policy ID: {policy_id}")
                with open(Constants().PROJECT_ROOT / "policy.id", "a+") as f:
                    f.truncate(0)
                    f.write(str(policy_id))
                # Create the final native script that will be attached to the transaction
                native_scripts = [policy]
                ########################
                """Define NFT"""
                ########################
                tokenName = b"SandboxSuanAccess1"
                my_nft_alternative = MultiAsset.from_primitive(
                    {
                        policy_id.payload: {
                            tokenName: 1,
                        }
                    }
                )
                ########################
                """Create metadata"""
                ########################
                metadata = {
                    721: {
                        policy_id.payload.hex(): {
                            tokenName: {
                                "description": "NFT con acceso a marketplace en Sandbox",
                                "name": "Token NFT SandBox",
                            },
                        }
                    }
                }
                # Place metadata in AuxiliaryData, the format acceptable by a transaction.
                auxiliary_data = AuxiliaryData(
                    AlonzoMetadata(metadata=Metadata(metadata))
                )
                """Build transaction"""
                chain_context = CardanoNetwork().get_chain_context()
                # Create a transaction builder
                builder = TransactionBuilder(chain_context)
                # Add our own address as the input address
                builder.add_input_address(master_address)
                # Since an InvalidHereAfter rule is included in the policy, we must specify time to live (ttl) for this transaction
                # builder.ttl = must_before_slot.after
                # Set nft we want to mint
                builder.mint = my_nft_alternative
                # Set native script
                builder.native_scripts = native_scripts
                # Set transaction metadata
                builder.auxiliary_data = auxiliary_data
                # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
                min_val = min_lovelace(
                    chain_context,
                    output=TransactionOutput(
                        destinAddress, Value(0, my_nft_alternative)
                    ),
                )
                # Send the NFT to our own address + 500 ADA
                builder.add_output(
                    TransactionOutput(destinAddress, Value(min_val, my_nft_alternative))
                )
                builder.add_output(TransactionOutput(destinAddress, Value(50000000)))
                # Create final signed transaction
                signed_tx = builder.build_and_sign(
                    [payment_skey], change_address=master_address
                )
                # Submit signed transaction to the network
                tx_id = signed_tx.transaction_body.hash().hex()
                chain_context.submit_tx(signed_tx)
                ####################################################
                final_response = {
                    "success": True,
                    "msg": "Tx submitted to the blockchain",
                    "tx_id": tx_id,
                }
        else:
            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"],
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"],
                }

        return final_response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/min-lovelace/",
    status_code=201,
    summary="Given utxo output details, obtain calculated min ADA required",
    response_description="Min Ada required for the utxo in lovelace",
)
async def minLovelace(addressDestin: pydantic_schemas.AddressDestin) -> int:
    """Min Ada required for the utxo in lovelace \n"""
    try:
        address = addressDestin.address

        # Get Multiassets
        multiAsset = None
        if addressDestin.multiAsset:
            for multiasset in addressDestin.multiAsset:
                policy_id = multiasset.policyid
                tokens = multiasset.tokens
                multiAsset = Helpers().build_multiAsset(
                    policy_id=policy_id, tq_dict=tokens
                )
        # Create Value type
        amount = Value(addressDestin.lovelace, multiAsset)

        if addressDestin.datum:
            datum = Datum(addressDestin.datum)
        else:
            datum = None
        # if not datum_hash:
        #     datum_hash = None
        # if not datum:
        #     datum = None
        # if not script:
        #     script = None

        output = TransactionOutput(address=address, amount=amount, datum=datum)

        chain_context = CardanoNetwork().get_chain_context()
        min_val = min_lovelace(chain_context, output)

        return min_val
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tx-fee/",
    status_code=200,
    summary="Deserialized a transaction provided in cbor format to get the fee",
    response_description="Fee in lovelace",
)
async def getFeeFromCbor(txcbor: str) -> int:
    """Deserialized a transaction provided in cbor format to get the fee \n"""
    try:
        payload = bytes.fromhex(txcbor)
        value = loads(payload)
        if isinstance(value, list):
            fee = value[0][2]
        else:
            fee = value[2]

        return fee

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/oracle-datum/{action}",
    status_code=201,
    summary="Build and upload inline datum",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def oracleDatum(
    action: pydantic_schemas.OracleAction,
    oracle_data: pydantic_schemas.Oracle,
    oracle_wallet_name: Optional[str] = "SuanOracle",
    # token_name: Optional[str] = "SuanOracle",
) -> dict:
    try:
        oracle_walletInfo = Keys().load_or_create_key_pair(oracle_wallet_name)

        chain_context = CardanoNetwork().get_chain_context()

        # Create a transaction builder
        builder = TransactionBuilder(chain_context)

        # Add user own address as the input address
        oracle_address = Address.from_primitive(oracle_walletInfo[3])
        builder.add_input_address(oracle_address)
        must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
        builder.ttl = must_before_slot.after

        ########################
        """3. Create the script and policy"""
        ########################
        # A policy that requires a signature from the policy key we generated above
        pub_key_policy = ScriptPubkey(oracle_walletInfo[2].hash())
        # Combine two policies using ScriptAll policy
        policy = ScriptAll([pub_key_policy])
        # Calculate policy ID, which is the hash of the policy
        policy_id = policy.hash()
        print(f"Policy ID: {policy_id}")
        with open(Constants().PROJECT_ROOT / "policy.id", "a+") as f:
            f.truncate(0)
            f.write(str(policy_id))
        # Create the final native script that will be attached to the transaction
        native_scripts = [policy]

        tokenName = b"SuanOracle"
        # tokenName = bytes(token_name, encoding="utf-8")
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

        if action == "Create":
            builder.mint = my_nft
            # Set native script
            builder.native_scripts = native_scripts
            msg = f"{tokenName} minted to store oracle data info in datum for Suan"
        else:
            nft_utxo = None
            for utxo in chain_context.utxos(oracle_address):

                def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
                    return pi == policy_id and an.payload == tokenName and a == 1

                if utxo.output.amount.multi_asset.count(f):
                    nft_utxo = utxo

                    builder.add_input(nft_utxo)

            msg = "Oracle datum updated"
        # Build the inline datum
        precision = 14
        value_dict = {}
        for data in oracle_data.data:
            # policy_id = data.policy_id
            token_feed = pydantic_schemas.TokenFeed(
                tokenName=bytes(data.token, encoding="utf-8"), price=data.price
            )
            value_dict[bytes.fromhex(data.policy_id)] = token_feed

        datum = pydantic_schemas.DatumOracle(
            value_dict=value_dict,
            identifier=bytes.fromhex(oracle_walletInfo[4]),
            validity=oracle_data.validity,
        )
        min_val = min_lovelace(
            chain_context,
            output=TransactionOutput(oracle_address, Value(0, my_nft), datum=datum),
        )
        builder.add_output(
            TransactionOutput(oracle_address, Value(min_val, my_nft), datum=datum)
        )

        signed_tx = builder.build_and_sign(
            [oracle_walletInfo[1]], change_address=oracle_address
        )

        # Submit signed transaction to the network
        tx_id = signed_tx.transaction_body.hash().hex()
        chain_context.submit_tx(signed_tx)

        logging.info(f"transaction id: {tx_id}")
        logging.info(f"https://preview.cardanoscan.io/transaction/{tx_id}")

        ####################################################
        final_response = {
            "success": True,
            "msg": msg,
            "tx_id": tx_id,
            "cardanoScan": f"https://preview.cardanoscan.io/transaction/{tx_id}",
        }

        return final_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
