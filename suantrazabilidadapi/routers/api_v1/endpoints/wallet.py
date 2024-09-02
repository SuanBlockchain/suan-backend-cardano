import binascii
from typing import Union

from fastapi import APIRouter, HTTPException
from pycardano import *

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.generic import Constants, is_valid_hex_string
from suantrazabilidadapi.utils.plataforma import CardanoApi, Plataforma

router = APIRouter()


@router.get(
    "/get-wallets/",
    status_code=200,
    summary="Get all the wallets registered in Plataforma",
    response_description="Wallet details",
)
async def getWallets():
    """Get all the wallets registered in Plataforma"""
    try:
        r = Plataforma().listWallets()
        if r["data"].get("data", None) is not None:
            wallet_list = r["data"]["data"]["listWallets"]["items"]
            if wallet_list == []:
                final_response = {
                    "success": True,
                    "msg": "No wallets present in the table",
                    "data": r["data"],
                }
            else:
                final_response = {
                    "success": True,
                    "msg": "List of wallets",
                    "data": wallet_list,
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


@router.get(
    "/get-wallet/{command_name}",
    status_code=200,
    summary="Get the wallet with specific id or address as registered in Plataforma",
    response_description="Wallet details",
)
async def getWallet(command_name: pydantic_schemas.walletCommandName, query_param: str):
    """Get the wallet with specific id as registered in Plataforma"""
    try:
        if command_name == "id":
            # Validate the id
            if not is_valid_hex_string(query_param):
                raise TypeError()

            r = Plataforma().getWallet(command_name, query_param)

            if r["data"].get("data", None) is not None:
                walletInfo = r["data"]["data"]["getWallet"]

                if walletInfo is None:
                    final_response = {
                        "success": True,
                        "msg": f"Wallet with id: {query_param} does not exist in DynamoDB",
                        "data": r["data"],
                    }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Wallet info",
                        "data": walletInfo,
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

        elif command_name == "address":
            # Validate the address
            Address.decode(query_param)._infer_address_type()

            r = Plataforma().getWallet(command_name, query_param)

            if r["data"].get("data", None) is not None:
                walletInfo = r["data"]["data"]["listWallets"]

                if walletInfo["items"] == []:
                    final_response = {
                        "success": True,
                        "msg": f"Wallet with address: {query_param} does not exist in DynamoDB",
                        "data": r["data"],
                    }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Wallet info",
                        "data": walletInfo,
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
    except TypeError as e:
        msg = f"Input parameter not valid for address type or id type"
        raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        msg = f"Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg)


@router.get(
    "/generate-words/",
    status_code=200,
    summary="Generate mnemonics with different word extensions",
    response_description="Response with mnemonics",
    # response_model=List[str],
)
async def generateWords(size: pydantic_schemas.Words):
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
        mnemonic_words = wallet.words
        ########################
        """2. Generate new wallet"""
        ########################
        hdwallet = HDWallet.from_mnemonic(mnemonic_words)

        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

        payment_verification_key = PaymentVerificationKey.from_primitive(
            child_hdwallet.public_key
        )
        staking_verification_key = StakeVerificationKey.from_primitive(
            child_hdwallet.public_key
        )

        pkh = payment_verification_key.hash()
        address = Address(
            payment_part=pkh,
            staking_part=staking_verification_key.hash(),
            network=Network.TESTNET,
        )
        stake_address = Address(
            payment_part=None,
            staking_part=staking_verification_key.hash(),
            network=Network.TESTNET,
        )

        wallet_id = binascii.hexlify(pkh.payload).decode("utf-8")

        seed = binascii.hexlify(hdwallet._seed).decode("utf-8")

        ########################
        """3. Store wallet info"""
        ########################
        # Check if wallet Id already exists in database
        r = Plataforma().getWallet("id", wallet_id)
        if r["success"] == True:
            if r["data"]["data"]["getWallet"] is None:
                # It means that wallet does not exist in database, so update database if save_flag is True
                if save_flag:
                    # Hash passphrase
                    variables = {
                        "id": wallet_id,
                        "seed": seed,
                        "userID": userID,
                        "address": str(address),
                        "stake_address": str(stake_address),
                    }
                    responseWallet = Plataforma().createWallet(variables)
                    if responseWallet["success"] == True:
                        final_response = {
                            "success": True,
                            "msg": f"Wallet created",
                            "data": {
                                "wallet_id": wallet_id,
                                "address": str(address),
                                "stake_address": str(stake_address),
                            },
                        }
                    else:
                        final_response = {
                            "success": False,
                            "msg": f"Problems creating the wallet",
                            "data": responseWallet["error"],
                        }
                else:
                    final_response = {
                        "success": True,
                        "msg": f"Wallet created but not stored in Database",
                        "data": {
                            "wallet_id": wallet_id,
                            "seed": seed,
                            "address": str(address),
                            "stake_address": str(stake_address),
                        },
                    }

            else:
                final_response = {
                    "success": False,
                    "msg": f"Wallet with id: {wallet_id} already exists in DynamoDB",
                    "data": r["data"],
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


@router.get(
    "/query-address/",
    status_code=201,
    summary="Given an address or a list of address obtain the details",
    response_description="Get address info - balance, associated stake address (if any) and UTxO set for given addresses",
)
async def queryAddress(address: str):
    """Get address info - balance, associated stake address (if any) and UTxO set for given addresses \n"""
    try:
        return CardanoApi().getAddressInfo(address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/address-tx/",
    status_code=200,
    summary="Get a list of all transactions made using this address",
    response_description="List of transactions for given address",
)
async def addressTxs(
    address: str,
    from_block: str = None,
    to_block: str = None,
    page_number: int = 1,
    limit: int = 10,
) -> list[dict]:

    try:
        return CardanoApi().getAddressTxs(
            address, from_block, to_block, page_number, limit
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/address-utxo/",
    status_code=200,
    summary="Get a list of all UTxOs currently present in the provided address",
    response_description="List of UtxOs for given address",
)
async def addressUtxos(
    address: str, page_number: int = 1, limit: int = 10
) -> list[dict]:
    """Get a list of all UTxOs currently present in the provided address \n

    Args:
        address (str): Bech32 address
        page_number (int, optional): The page number for listing the results. Defaults to 1.
        limit (int, optional): The number of results displayed on one page. Defaults to 10.
        all (bool, optional): Will collect all pages into one return. Defaults to False.

    Raises:
        HTTPException: Reflects endpoint down

    Returns:
        _type_: list of utxos
    """
    try:
        addressUtxos = CardanoApi().getAddressUtxos(address, page_number, limit)
        return addressUtxos
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/address-details/",
    status_code=200,
    summary="",
    response_description="",
)
async def addressDetails(address: str) -> dict:

    try:
        addressDetails = CardanoApi().getAddressDetails(address)
        return addressDetails
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/asset-info/",
    status_code=200,
    summary="Get the information for all assets under the same policy",
    response_description="Array of detailed information of assets under the same policy",
)
async def accountUtxos(policy_id: str):
    """Array of detailed information of assets under the same policy \n"""
    try:
        asset_info = CardanoApi().assetInfo(policy_id)

        return asset_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
