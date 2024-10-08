from fastapi import APIRouter, HTTPException
from pycardano import (
    Address,
    HDWallet,
)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.generic import Constants, is_valid_hex_string
from suantrazabilidadapi.utils.plataforma import CardanoApi, Plataforma
from suantrazabilidadapi.utils.response import Response
from suantrazabilidadapi.utils.exception import ResponseTypeError, ResponseProcessingError

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
        final_response = Response().handle_listWallets_response(r)

        return final_response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/get-wallet/{command_name}",
    status_code=200,
    summary="Get the wallet with specific id or address as registered in Plataforma",
    response_description="Wallet details",
)
async def getWallet(command_name: pydantic_schemas.walletCommandName, query_param: str):
    """Get the wallet with specific id as registered in Plataforma"""
    try:
        final_response = {}
        if command_name == "id":
            # Validate the id
            if not is_valid_hex_string(query_param):
                raise ResponseTypeError("Not valid id format")

            getWallet_response = Plataforma().getWallet(command_name, query_param)

            final_response = Response().handle_getWallet_response(getWallet_response=getWallet_response)

        elif command_name == "address":
            # Validate the address
            Address.decode(query_param)._infer_address_type()  # pylint: disable=protected-access

            listWallet_response = Plataforma().getWallet(command_name, query_param)

            final_response = Response().handle_listWallets_response(listWallets_response=listWallet_response)

        else:
            raise Exception("Error. Please review your id or address provided")

        return final_response

    except ResponseTypeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


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

    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


@router.post(
    "/create-wallet/",
    status_code=201,
    summary="Create wallet for internal use in Marketplace",
    response_description="Response with wallet id",
    # response_model=List[str],
)
async def createWallet(mnemonic_words: str, wallet_type: pydantic_schemas.walletType, userID: str = "", save_flag: bool = True):
    try:

        ########################
        """Generate new wallet"""
        ########################

        wallet_info = Plataforma().generateWallet(mnemonic_words)
        wallet_id = wallet_info[0]
        seed = wallet_info[1]
        # skey = wallet_info[2]
        # vkey = wallet_info[3]
        address = wallet_info[4]
        stake_address = wallet_info[5]

        ########################
        """3. Store wallet info"""
        ########################
        # Check if wallet Id already exists in database
        r = Plataforma().getWallet("id", wallet_id)
        wallet_response = Response().handle_getWallet_response(r)
        if wallet_response["success"]:
            if wallet_response.get("data", None):
                raise ResponseProcessingError("Not possible to create wallet, wallet already exists in Dynamo")
            if save_flag:

                variables = {
                    "id": wallet_id,
                    "seed": seed,
                    "address": str(address),
                    "stake_address": str(stake_address),
                }
                if wallet_type == "user":
                    variables["userID"] = userID
                else:
                    variables["claimed_token"] = False
                    variables["isAdmin"] = False
                    variables["isSelected"] = False
                    variables["name"] = wallet_type
                    variables["status"] = "active"

                responseWallet = Plataforma().createWallet(variables, wallet_type)
                final_response = Response().handle_createWallet_response(responseWallet)
                final_response["wallet_id"] = wallet_id
                final_response["address"] = str(address)
                final_response["stake_address"] = str(stake_address)
            else:
                final_response = {
                    "success": True,
                    "msg": "Wallet created but not stored in Database",
                    "data": {
                        "wallet_id": wallet_id,
                        "seed": seed,
                        "address": str(address),
                        "stake_address": str(stake_address),
                    },
                }

        return final_response

    except ResponseProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


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

    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


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

    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


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
        utxos = CardanoApi().getAddressUtxos(address, page_number, limit)
        return utxos

    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get(
    "/address-details/",
    status_code=200,
    summary="",
    response_description="",
)
async def addressDetails(address: str) -> dict:

    try:
        details = CardanoApi().getAddressDetails(address)
        return details

    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


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

    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e
