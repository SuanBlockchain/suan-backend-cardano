from fastapi import APIRouter, HTTPException
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.plataforma import Plataforma, CardanoApi

import os
import pathlib
import binascii
from typing import Union

from pycardano import *

class Constants:
    NETWORK = Network.TESTNET
    PROJECT_ROOT = "suantrazabilidadapi"
    ROOT = pathlib.Path(PROJECT_ROOT)
    KEY_DIR = ROOT / f'.priv/wallets'
    ENCODING_LENGHT_MAPPING = {"12": 128, "15": 160, "18": 192, "21": 224, "24":256}


# Create the directory if it doesn't exist
Constants.ROOT.mkdir(parents=True, exist_ok=True)

key_dir = Constants.KEY_DIR
key_dir.mkdir(exist_ok=True)

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

router = APIRouter()

@router.get("/get-wallets/", status_code=200,
summary="Get all the wallets registered in Plataforma",
    response_description="Wallet details",)

async def getWallets():
    """Get all the wallets registered in Plataforma
    """
    try:
        r = Plataforma().listWallets()
        if r["data"].get("data", None) is not None:
            wallet_list = r["data"]["data"]["listWallets"]["items"]
            if wallet_list == []:
                final_response = {
                    "success": True,
                    "msg": 'No wallets present in the table',
                    "data": r["data"]
                }
            else:
                final_response = {
                    "success": True,
                    "msg": 'List of wallets',
                    "data": wallet_list
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

@router.get("/get-wallet-by-id/", status_code=200,
summary="Get the wallet with specific id as registered in Plataforma",
    response_description="Wallet details",)

async def getWalletById(wallet_id: str):
    """Get the wallet with specific id as registered in Plataforma
    """
    try:
        r = Plataforma().getWallet(wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                final_response = {
                    "success": True,
                    "msg": f'Wallet with id: {wallet_id} does not exist in DynamoDB',
                    "data": r["data"]
                }
            else:
                final_response = {
                    "success": True,
                    "msg": 'Wallet info',
                    "data": walletInfo
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
    "/generate-words/",
    status_code=201,
    summary="Generate mnemonics with different word extensions",
    response_description="Response with mnemonics",
    # response_model=List[str],
)

async def generateWords(size: pydantic_schemas.Words, ):
    try:
        strength = Constants.ENCODING_LENGHT_MAPPING.get(size, None)
        if strength is None:
            strength = 256
        
        return HDWallet.generate_mnemonic(strength=strength)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/create-wallet/",
    status_code=201,
    summary="Create wallet for internal use in Marketplace",
    response_description="Response with wallet id",
    # response_model=List[str],
)

async def createWallet(wallet: pydantic_schemas.Wallet):
    try:
        
        ########################
        """1. Get wallet info"""
        ########################
        
        save_flag = wallet.save_flag
        userID = wallet.userID
        # passphrase = wallet.passphrase
        mnemonic_words = wallet.words
        ########################
        """2. Generate new wallet"""
        ########################
        hdwallet = HDWallet.from_mnemonic(mnemonic_words)

        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

        payment_verification_key = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)
        staking_verification_key = StakeVerificationKey.from_primitive(child_hdwallet.public_key)

        address = Address(payment_part=payment_verification_key.hash(), staking_part=staking_verification_key.hash(), network=Network.TESTNET)
        stake_address = Address(payment_part=None, staking_part=staking_verification_key.hash(), network=Network.TESTNET)

        wallet_id = payment_verification_key.hash()

        wallet_id = binascii.hexlify(wallet_id.payload).decode('utf-8')

        seed = binascii.hexlify(hdwallet._seed).decode('utf-8')

        ########################
        """3. Store wallet info"""
        ########################
        # Check if wallet Id already exists in database
        r = Plataforma().getWallet(wallet_id)
        if r["success"] == True:
            if r["data"]["data"]["getWallet"] is None:
                # It means that wallet does not exist in database, so update database if save_flag is True
                # hashed_passphrase = get_password_hash(passphrase)
                if save_flag:
                    # Hash passphrase
                    variables = {
                        "id": wallet_id,
                        "seed": seed,
                        "userID": userID,
                        "address": str(address),
                        "stake_address": str(stake_address)
                    }
                    responseWallet = Plataforma().createWallet(variables)
                    if responseWallet["success"] == True:
                        final_response = {"success": True, "msg": f'Wallet created', "data": {
                            "wallet_id": wallet_id,
                            "address": str(address),
                            "stake_address": str(stake_address)
                        }}
                    else:
                        final_response = {"success": False, "msg": f'Problems creating the wallet', "data": responseWallet["error"]}
                else:
                    final_response = {"success": True, "msg": f'Wallet created but not stored in Database', "data": {
                            "wallet_id": wallet_id,
                            "address": str(address),
                            "stake_address": str(stake_address)
                    }}

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

@router.post("/query-address/", status_code=201,
summary="Given an address or a list of address obtain the details",
    response_description="Get address info - balance, associated stake address (if any) and UTxO set for given addresses",)

async def queryAddress(address: Union[str, list[str]] ):
    """Get address info - balance, associated stake address (if any) and UTxO set for given addresses \n
    """
    try:
        return CardanoApi().getAddressInfo(address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/account-tx/", status_code=201,
    summary="Get a list of all Txs for a given stake address (account)",
    response_description="Get a list of all Txs for a given stake address (account)")

async def accountTx(stake: str, after_block_height: int = 0):
    """Get a list of all Txs for a given stake address (account) \n
    """
    try:
        accountTxs = CardanoApi().getAccountTxs(stake, after_block_height)



        return accountTxs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))