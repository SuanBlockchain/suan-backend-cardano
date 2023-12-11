from fastapi import APIRouter, HTTPException
from cardanopythonlib import keys, base
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.plataforma import Plataforma

import json
import os
import pathlib
import binascii
from passlib.context import CryptContext

from pycardano import *
from blockfrost import ApiUrls

class Constants:
    NETWORK = Network.TESTNET
    BLOCK_FROST_PROJECT_ID = "previewp0ZkXTGqxYc7wcjUllmcPQPpZmUAGCCU"
    PROJECT_ROOT = "suantrazabilidadapi"
    ROOT = pathlib.Path(PROJECT_ROOT)
    KEY_DIR = ROOT / f'.priv/wallets'
    ENCODING_LENGHT_MAPPING = {12: 128, 15: 160, 18: 192, 21: 224, 24:256}

# Copy your BlockFrost project ID below. Go to https://blockfrost.io/ for more information.

NETWORK = Constants.NETWORK

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def remove_file(path: str, name: str) -> None:
    if os.path.exists(path+name):
        os.remove(path+name)

# Load payment keys or create them if they don't exist
def load_or_create_key_pair(base_dir, base_name):
    skey_path = base_dir / f"{base_name}.skey"
    vkey_path = base_dir / f"{base_name}.vkey"

    if skey_path.exists():
        skey = PaymentSigningKey.load(str(skey_path))
        vkey = PaymentVerificationKey.from_signing_key(skey)
    else:
        key_pair = PaymentKeyPair.generate()
        key_pair.signing_key.save(str(skey_path))
        key_pair.verification_key.save(str(vkey_path))
        skey = key_pair.signing_key
        vkey = key_pair.verification_key
    return skey, vkey

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

router = APIRouter()

@router.post(
    "/create-wallet/",
    status_code=200,
    summary="Create wallet, fund wallet with NFT token to access Sandbox marketplace",
    response_description="Response with mnemonics and cardano cli keys",
    # response_model=List[str],
)

async def createWallet(wallet: pydantic_schemas.WalletCreate):
    try:
        
        ########################
        """1. Get wallet info"""
        ########################
        size = wallet.size
        save_flag = wallet.save_flag
        userID = wallet.userID
        passphrase = wallet.passphrase

        strength = Constants.ENCODING_LENGHT_MAPPING.get(size, None)
        if strength is None:
            strength = 256

        ########################
        """2. Generate new wallet"""
        ########################
        mnemonic_words = HDWallet.generate_mnemonic(strength=strength)
        hdwallet = HDWallet.from_mnemonic(mnemonic_words, passphrase=passphrase)

        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

        payment_verification_key = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)
        wallet_id = payment_verification_key.hash()

        wallet_id = binascii.hexlify(wallet_id.payload).decode('utf-8')

        seed = binascii.hexlify(hdwallet._seed).decode('utf-8')

        ########################
        """3. Store wallet info"""
        ########################
        # Check if wallet Id already exists in database
        r = Plataforma().getWallets(wallet_id)
        if r["success"] == True:
            if r["data"]["data"]["getWallet"] is None:
                # It means that wallet does not exist in database, so update database if save_flag is True
                if save_flag:
                    # Hash passphrase
                    hashed_passphrase = get_password_hash(passphrase)
                    variables = {
                        "id": wallet_id,
                        "isAdmin": wallet.isAdmin,
                        "isSelected": wallet.isSelected,
                        "name": wallet.walletName,
                        "password": hashed_passphrase,
                        "seed": seed,
                        "status": wallet.status,
                        "userID": userID
                    }
                    responseWallet = Plataforma().createWallet(variables)
                    if responseWallet["success"] == True:
                        final_response = {"success": True, "msg": f'Wallet created', "data": {"mnemonic": mnemonic_words, "wallet_id": wallet_id}}
                    else:
                        final_response = {"success": False, "msg": f'Problems created the wallet', "data": responseWallet["error"]}
                else:
                    final_response = {"success": True, "msg": f'Wallet created but not stored in Database', "data": {"mnemonic": mnemonic_words, "wallet_id": wallet_id}}

            else:
                final_response = {
                    "success": True,
                    "msg": f'Wallet with id: {wallet_id} already exists in DynamoDB',
                    "data": r["data"]
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


@router.get(
    "/mylib-create-wallet/",
    status_code=200,
    summary="Create wallet, fund wallet with NFT token to access Sandbox marketplace",
    response_description="Response with mnemonics and cardano cli keys",
    # response_model=List[str],
)

async def mylibCreateWallet():
    try:
        wallet = keys.Keys()
        allKeys = wallet.deriveAllKeys("temp",24, False)
        payment_addr = allKeys["payment_addr"]

        node = base.Node()
        
        mainWalletName = "SuanMasterSigningKeys#"
        with open(f'{node.KEYS_FILE_PATH}/{mainWalletName}/{mainWalletName}.json', 'r') as file:
            walletContent = json.load(file)

        hash_verification_key = walletContent["hash_verification_key"]

        tokenName = "SandboxSuanAccess1"
        type = "all"
        hashes = [hash_verification_key]
        slot = node.query_tip_exec()["slot"] + 20000
        parameters = {
            "type": type,
            "hashes": hashes,
            "purpose": "mint"
        }
        multisig_script, policyID = node.create_simple_script(parameters)
        script_file_path = node.MINT_FOLDER

        address_destin_tokens = [
            {
                "address": payment_addr,
                "tokens": [
                    {
                        "name": tokenName,
                        "amount": 1,
                        "policyID": policyID
                    }
                ]
            }
        ]

        mint = {
            "action": "mint",
            "tokens": [
                {"name": tokenName, "amount": 1, "policyID": policyID},
            ],
        }
        tx_file_path = node.TRANSACTION_PATH_FILE

        metadata = {"1337": {"Title": "Token NFT SandBox", "description": "NFT con acceso a marketplace en Sandbox" }}
        params = {
            "address_origin": walletContent["payment_addr"],
            "metadata": metadata,
            "address_destin": address_destin_tokens,
            "mint": mint,
        }
        response = node.build_tx_components(params)
        file_exists = os.path.exists(tx_file_path + "/tx.draft")

        remove_file(script_file_path, "/" + policyID + ".script")
        remove_file(script_file_path, "/" + policyID + ".policyid")
        remove_file(tx_file_path, "/tx_metadata.json")
        remove_file(tx_file_path, "/tx.draft")

        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

# @router.get(
#     "/create-wallet/",
#     status_code=200,
#     summary="Create wallet, fund wallet with NFT token to access Sandbox marketplace",
#     response_description="Response with mnemonics and cardano cli keys",
#     # response_model=List[str],
# )

# async def createWallet():
#     try:

#         ########################
#         """1. Generate new wallet"""
#         ########################
#         mnemonic_words = HDWallet.generate_mnemonic()
#         hdwallet = HDWallet.from_mnemonic(mnemonic_words)

#         child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

#         payment_verification_key = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)

#         destination_address = Address(payment_part=payment_verification_key.hash(), network=Network.TESTNET)
#         # print(destination_address)
#         ########################
#         """2. Obtain the MasterKey to pay and mint"""
#         ########################
#         payment_skey, payment_vkey = load_or_create_key_pair(key_dir, "payment")
#         address = Address(payment_vkey.hash(), network=NETWORK)
#         print(address)

#         ########################
#         """3. Create the script and policy"""
#         ########################
#         # A policy that requires a signature from the policy key we generated above
#         pub_key_policy = ScriptPubkey(payment_vkey.hash())

#         # A time policy that disallows token minting after 10000 seconds from last block
#         # must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)

#         # Combine two policies using ScriptAll policy
#         policy = ScriptAll([pub_key_policy])

#         # Calculate policy ID, which is the hash of the policy
#         policy_id = policy.hash()
#         print(policy_id)
#         print(f"Policy ID: {policy_id}")
#         with open(root / "policy.id", "a+") as f:
#             f.truncate(0)
#             f.write(str(policy_id))

#         # Create the final native script that will be attached to the transaction
#         native_scripts = [policy]

#         ########################
#         """Define NFT"""
#         ########################

#         tokenName = b"SandboxSuanAccess1"
#         my_nft_alternative = MultiAsset.from_primitive(
#             {
#                 policy_id.payload: {
#                     tokenName: 1,  
#                 }
#             }
#         )

#         ########################
#         """Create metadata"""
#         ########################
#         metadata = {
#             721: {  
#                 policy_id.payload.hex(): {
#                     tokenName: {
#                         "description": "NFT con acceso a marketplace en Sandbox",
#                         "name": "Token NFT SandBox",
#                     },
#                 }
#             }
#         }

#         # Place metadata in AuxiliaryData, the format acceptable by a transaction.
#         auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))

#         """Build transaction"""

#         # Create a transaction builder
#         builder = TransactionBuilder(chain_context)

#         # Add our own address as the input address
#         builder.add_input_address(address)

#         # Since an InvalidHereAfter rule is included in the policy, we must specify time to live (ttl) for this transaction
#         # builder.ttl = must_before_slot.after

#         # Set nft we want to mint
#         builder.mint = my_nft_alternative

#         # Set native script
#         builder.native_scripts = native_scripts

#         # Set transaction metadata
#         builder.auxiliary_data = auxiliary_data

#         # Calculate the minimum amount of lovelace that need to hold the NFT we are going to mint
#         min_val = min_lovelace(
#             chain_context, output=TransactionOutput(destination_address, Value(0, my_nft_alternative))
#         )

#         # Send the NFT to our own address + 500 ADA
#         builder.add_output(TransactionOutput(destination_address, Value(min_val, my_nft_alternative)))
#         builder.add_output(TransactionOutput(destination_address, Value(500000000)))

#         # Create final signed transaction
#         signed_tx = builder.build_and_sign([payment_skey], change_address=address)
#         print(signed_tx)

#         # Submit signed transaction to the network
#         chain_context.submit_tx(signed_tx)

#         ####################################################

#         return {"mnemonic": mnemonic_words}
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))