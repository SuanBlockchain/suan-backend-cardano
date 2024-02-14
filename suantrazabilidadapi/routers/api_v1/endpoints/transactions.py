from fastapi import APIRouter, HTTPException
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.plataforma import Plataforma, CardanoApi

import os
import pathlib
from typing import Union

from pycardano import *
from blockfrost import ApiUrls

class Constants:
    NETWORK = Network.TESTNET
    BLOCK_FROST_PROJECT_ID = os.getenv('block_frost_project_id')
    PROJECT_ROOT = "suantrazabilidadapi"
    ROOT = pathlib.Path(PROJECT_ROOT)
    KEY_DIR = ROOT / f'.priv/wallets'
    ENCODING_LENGHT_MAPPING = {12: 128, 15: 160, 18: 192, 21: 224, 24:256}


chain_context = BlockFrostChainContext(
    project_id=Constants.BLOCK_FROST_PROJECT_ID,
    base_url=ApiUrls.preview.value,
)

"""Preparation"""
# Define the root directory where images and keys will be stored.
PROJECT_ROOT = "suantrazabilidadapi"
root = Constants.ROOT

# Create the directory if it doesn't exist
root.mkdir(parents=True, exist_ok=True)

# mainWalletName = "SuanMasterSigningKeys#"
key_dir = Constants.KEY_DIR
key_dir.mkdir(exist_ok=True)

def load_or_create_key_pair(base_dir, base_name):
    skey_path = base_dir / f"{base_name}.skey"
    vkey_path = base_dir / f"{base_name}.vkey"

    if skey_path.exists():
        skey = PaymentSigningKey.load(str(skey_path))
        PaymentSigningKey.from_primitive()
        vkey = PaymentVerificationKey.from_signing_key(skey)
    else:
        key_pair = PaymentKeyPair.generate()
        key_pair.signing_key.save(str(skey_path))
        key_pair.verification_key.save(str(vkey_path))
        skey = key_pair.signing_key
        vkey = key_pair.verification_key
    return skey, vkey

router = APIRouter()

@router.post(
    "/build-tx/",
    status_code=201,
    summary="Build the transaction off-chain for validation before signing",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)

async def buildTx(send: pydantic_schemas.BuildTx) -> dict:
    try:

        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet(send.wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                final_response = {
                    "success": True,
                    "msg": f'Wallet with id: {send.wallet_id} does not exist in DynamoDB',
                    "data": r["data"]
                }
            else:
                ########################
                """2. Build transaction"""
                ########################
                # Create a transaction builder
                builder = TransactionBuilder(chain_context)

                # Add user own address as the input address
                builder.add_input_address(walletInfo["address"])

                must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
                # Since an InvalidHereAfter
                builder.ttl = must_before_slot.after

                if send.metadata != {}:
                    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(send.metadata)))
                    # Set transaction metadata
                    builder.auxiliary_data = auxiliary_data
                addresses = send.addresses
                # multi_asset = []
                for address in addresses:
                    multi_asset = MultiAsset()
                    if address.multiAsset:
                        for item in address.multiAsset:
                            for policy_id, tokens in item.items():
                                my_asset = Asset()
                                for name, quantity in tokens.items():
                                    my_asset.data.update({AssetName(name.encode()): quantity})

                                multi_asset[ScriptHash(bytes.fromhex(policy_id))] = my_asset
                                
                    multi_asset_value = Value(0, multi_asset)

                    # Calculate the minimum amount of lovelace that need to be transfered in the utxo  
                    min_val = min_lovelace(
                        chain_context, output=TransactionOutput(address.address, multi_asset_value)
                    )
                    if address.lovelace <= min_val:
                        builder.add_output(TransactionOutput(address.address, Value(min_val, multi_asset)))
                    else:
                        # builder.add_output(TransactionOutput.from_primitive([address.address, address.lovelace]))
                        builder.add_output(TransactionOutput(address.address, Value(address.lovelace, multi_asset)))

                build_body = builder.build(change_address=walletInfo["address"])

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f'{utxo.to_cbor_hex()[6:70]}#{utxo.index}'
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f'Tx Build',
                    "build_tx": format_body,
                    "cbor": str(build_body.to_cbor_hex()),
                    "utxos_info": utxo_list_info
                }
        else:

            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sign-submit/", status_code=201, summary="Sign and submit transaction in cborhex format", response_description="Response with transaction submission confirmation")

async def signSubmit(signSubmit: pydantic_schemas.SignSubmit) -> dict:
    try:

        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet(signSubmit.wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                final_response = {
                    "success": True,
                    "msg": f'Wallet with id: {signSubmit.wallet_id} does not exist in DynamoDB',
                    "data": r["data"]
                }
            else:
                ########################
                """2. Build transaction"""
                ########################
                seed = walletInfo["seed"] 
                hdwallet = HDWallet.from_seed(seed)
                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                spend_vk = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

                cbor_hex = signSubmit.cbor
                tx_body = TransactionBody.from_cbor(cbor_hex)


                signature = payment_skey.sign(tx_body.hash())
                vk_witnesses = [VerificationKeyWitness(spend_vk, signature)]
                signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

                chain_context.submit_tx(signed_tx.to_cbor())
                tx_id = tx_body.hash().hex()
                final_response = {
                    "success": True,
                    "msg": "Tx submitted to the blockchain",
                    "tx_id": tx_id
                }

        else:
            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/tx-status/",
    status_code=201,
    summary="Get the number of block confirmations for a given transaction hash list",
    response_description="Array of transaction confirmation counts",
    # response_model=List[str],
)

async def txStatus(tx_hashes: Union[str, list[str]]) -> list:
    try:
         return CardanoApi().txStatus(tx_hashes)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))