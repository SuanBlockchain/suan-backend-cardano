from fastapi import APIRouter, HTTPException
# from cardanopythonlib import keys, base
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.plataforma import Plataforma

import os
import pathlib
import binascii
from passlib.context import CryptContext

from pycardano import *

class Constants:
    NETWORK = Network.TESTNET
    BLOCK_FROST_PROJECT_ID = os.getenv('block_frost_project_id')
    PROJECT_ROOT = "suantrazabilidadapi"
    ROOT = pathlib.Path(PROJECT_ROOT)
    KEY_DIR = ROOT / f'.priv/wallets'
    ENCODING_LENGHT_MAPPING = {12: 128, 15: 160, 18: 192, 21: 224, 24:256}

# Copy your BlockFrost project ID below. Go to https://blockfrost.io/ for more information.


"""Preparation"""
# Define the root directory where images and keys will be stored.
# chain_context = BlockFrostChainContext(
#     project_id=Constants.BLOCK_FROST_PROJECT_ID,
#     base_url=ApiUrls.preview.value,
# )

# Create the directory if it doesn't exist
Constants.ROOT.mkdir(parents=True, exist_ok=True)

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
    status_code=201,
    summary="Create wallet for internal use in Marketplace",
    response_description="Response with mnemonics and wallet id",
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
        destination_address = Address(payment_part=payment_verification_key.hash(), network=Network.TESTNET)
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
                        "userID": userID,
                        # "address": destination_address,
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


@router.post("/query-wallet/{command_name}/", status_code=201,
summary="query data depending on the input command",
    response_description="Response from the wallet",)

async def queryWallet(command_name: pydantic_schemas.SourceName, address: list[str]):
    """Returns the info as per command name requested \n
    **command_name**: Choose the option to retreive wallet info.
    addr_test1vqkge7txl2vdw26efyv7cytjl8l6n8678kz09agc0r34pdss0xtmp
    """

    try:
        if command_name == "balance":
            responseAddress = Plataforma().getAddressInfo(address)

            return responseAddress

     
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))