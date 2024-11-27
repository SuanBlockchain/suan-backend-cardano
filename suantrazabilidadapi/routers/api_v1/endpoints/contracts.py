import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from opshin.builder import PlutusContract, build
from opshin.prelude import TxId, TxOutRef
from pycardano import (
    Address,
    HDWallet,
    PaymentVerificationKey
)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.generic import (
    Constants,
    is_valid_hex_string,
    recursion_limit,
)
from suantrazabilidadapi.utils.plataforma import Helpers, Plataforma
from suantrazabilidadapi.utils.response import Response
from suantrazabilidadapi.utils.exception import ResponseProcessingError, ResponseDynamoDBException, ResponseTypeError

router = APIRouter()


@router.get(
    "/get-scripts/",
    status_code=200,
    summary="Get all the scripts registered in Plataforma",
    response_description="Script details",
)
async def getScripts():
    """Get all the scripts registered in Plataforma"""
    try:
        r = Plataforma().listScripts()
        final_response = Response().handle_listGeneric_response(operation_name="listScripts", listGeneric_response=r)

        return final_response

    except ResponseDynamoDBException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/get-script/{script_type}",
    status_code=200,
    summary="Read script created",
    response_description="script details",
)
async def getScript(
    script_type: pydantic_schemas.contractCommandName, query_param: str
) -> dict:
    try:
        final_response = {}
        if script_type == "id":
            # Validate the id
            if not is_valid_hex_string(query_param):
                raise ResponseTypeError("Not valid id format")

            command_name = "getScriptById"

            graphql_variables = {script_type: query_param}

            r = Plataforma().getScript(command_name, graphql_variables)
            final_response = Response().handle_getGeneric_response(operation_name="getScript", getGeneric_response=r)

        
        return final_response
    
    except ResponseTypeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get(
    "/create-contract/{script_type}",
    status_code=200,
    summary="From parameters build and create the smart contract",
    response_description="script details",
)
async def createContract(
    script_type: pydantic_schemas.ScriptType,
    name: str,
    wallet_id: str,
    tokenName: str = "",
    save_flag: bool = True,
    parent_policy_id: str = "",
    project_id: Optional[str] = None,
    oracle_wallet_id: str = "",
) -> dict:
    """From parameters build a smart contract"""
    try:
        # TODO: Verify that the wallet is admin. For now, the wallet_id is only used as beneficiary
        scriptCategory = "PlutusV2"

        graphql_variables = {"walletId": wallet_id}
        r = Plataforma().getWallet("getWalletById", graphql_variables)
        final_response = Response().handle_getGeneric_response(operation_name="getWallet", getGeneric_response=r)
        
        if not final_response["success"]:
            raise ValueError( f"Wallet with id: {wallet_id} does not exist in DynamoDB")

        walletInfo = final_response["data"]

            # Get payment address
        payment_address = Address.from_primitive(walletInfo["address"])
        pkh = bytes(payment_address.payment_part)

        tn_bytes = bytes(tokenName, encoding="utf-8")

        #######################
        # Handle to decide the contract to build
        #######################
        utxo_to_spend = None
        if script_type == "mintSuanCO2":
            script_path = Constants.PROJECT_ROOT.joinpath(
                Constants.CONTRACTS_DIR
            ).joinpath(f"{script_type.value}.py")
            contract = build(script_path, pkh, tn_bytes)

        elif script_type == "mintProjectToken":
            if tokenName == "":
                raise ValueError("Token name is required for this script type")
            
            chain_context = CardanoNetwork().get_chain_context()
            for utxo in chain_context.utxos(payment_address):
                if (
                    utxo.output.amount.coin
                    > 3000000
                ):
                    utxo_to_spend = utxo
                    break
            assert utxo_to_spend is not None, "UTxO not found to spend!"
            oref = TxOutRef(
                id=TxId(utxo_to_spend.input.transaction_id.payload),
                idx=utxo_to_spend.input.index,
            )

            logging.info(
                f"oref found to build the script: {oref.id.tx_id.hex()} and idx: {oref.idx}"
            )

            script_path = Constants.PROJECT_ROOT.joinpath(
                Constants.CONTRACTS_DIR
            ).joinpath(f"{script_type.value}.py")
            contract = build(script_path, oref, pkh, tn_bytes)

        elif script_type == "spendSwap":
            script_path = Constants.PROJECT_ROOT.joinpath(
                Constants.CONTRACTS_DIR
            ).joinpath(f"{script_type.value}.py")

            command_name = "getWalletById"

            graphql_variables = {"walletId": oracle_wallet_id}

            # Check first that the core wallet to pay fees exists
            r = Plataforma().getWallet(command_name, graphql_variables)
            final_response = Response().handle_getGeneric_response(operation_name="getWallet", getGeneric_response=r)

            if not final_response["success"]:
                raise ValueError( f"Wallet with id: {oracle_wallet_id} does not exist in DynamoDB")

            oracleWallet = final_response["data"]

            seed = oracleWallet["seed"]
            hdwallet = HDWallet.from_seed(seed)
            child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

            oracle_vkey = PaymentVerificationKey.from_primitive(
                child_hdwallet.public_key
            )
            oracle_policy_id = Helpers().build_oraclePolicyId(oracle_vkey)
            recursion_limit(2000)
            contract = build(script_path, bytes.fromhex(oracle_policy_id))

        elif script_type == "spendProject":
            script_path = Constants.PROJECT_ROOT.joinpath(
                Constants.CONTRACTS_DIR
            ).joinpath(f"{script_type.value}.py")

            command_name = "getWalletById"

            graphql_variables = {"walletId": oracle_wallet_id}

            # Check first that the core wallet to pay fees exists
            r = Plataforma().getWallet(command_name, graphql_variables)
            final_response = Response().handle_getGeneric_response(operation_name="getWallet", getGeneric_response=r)

            if not final_response["success"]:
                raise ValueError( f"Wallet with id: {oracle_wallet_id} does not exist in DynamoDB")

            oracleWallet = final_response["data"]

            seed = oracleWallet["seed"]
            hdwallet = HDWallet.from_seed(seed)
            child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

            oracle_vkey = PaymentVerificationKey.from_primitive(
                child_hdwallet.public_key
            )

            oracle_policy_id = Helpers().build_oraclePolicyId(oracle_vkey)

            print(bytes.fromhex(oracle_policy_id))
            print(oracle_policy_id)
            recursion_limit(2000)
            contract = build(
                script_path,
                bytes.fromhex(oracle_policy_id),
                bytes.fromhex(parent_policy_id),
                tn_bytes,
            )

        # Build the contract
        plutus_contract = PlutusContract(contract)

        cbor_hex = plutus_contract.cbor_hex
        mainnet_address = plutus_contract.mainnet_addr
        testnet_address = plutus_contract.testnet_addr
        policy_id = plutus_contract.policy_id

        logging.info(
            f"Build contract with policyID: {policy_id} and testnet address: {testnet_address}"
        )

        ##################

        if save_flag:
            command_name = "getScriptById"

            graphql_variables = {"id": policy_id}

            r = Plataforma().getScript(command_name, graphql_variables)
            # final_response = Response().handle_getScript_response(getScript_response=r)
            final_response = Response().handle_getGeneric_response(operation_name="getScript", getGeneric_response=r)

            if final_response["success"]:
                raise ValueError("Script already exists in database")


            # Build the variables and store in DynamoDB
            variables = {
                "id": policy_id,
                "name": name,
                "MainnetAddr": mainnet_address.encode(),
                "testnetAddr": testnet_address.encode(),
                "cbor": cbor_hex,
                "pbk": wallet_id,
                "script_category": scriptCategory,
                "script_type": script_type,
                "Active": True,
                "token_name": tokenName,
                "scriptParentID": (
                    parent_policy_id if parent_policy_id != "" else policy_id
                ),
            }

            variables["productID"] = project_id if project_id else None

            responseScript = Plataforma().createContract(variables)
            responseCreateContract = Response().handle_createContract_response(responseScript)
            if not responseCreateContract["connection"] or not responseCreateContract.get("success", None):
                raise ResponseDynamoDBException(responseCreateContract["data"])

            final_response = {
                "success": True,
                "msg": "Script created",
                "data": {
                    "id": policy_id,
                    "utxo_to_spend": (
                        {
                            "transaction_id": oref.id.tx_id.hex(),
                            "index": oref.idx,
                        }
                        if utxo_to_spend
                        else ""
                    ),
                    "mainnet_address": mainnet_address.encode(),
                    "testnet_address": testnet_address.encode(),
                },
            }
        else:
            final_response = {
                "success": True,
                "msg": "Script created but not stored in Database",
                "data": {
                    "id": policy_id,
                    "mainnet_address": mainnet_address.encode(),
                    "testnet_address": testnet_address.encode(),
                    "cbor": cbor_hex,
                },
            }

        return final_response

    except ResponseDynamoDBException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ResponseProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get(
    "/save-contracts/",
    status_code=201,
    summary="Save all the contracts to S3 available locally in the system",
    response_description="script details",
)
async def saveContracts() -> dict:
    """Save all the contracts to S3 which are available locally in the system"""
    contracts_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR)
    result = Plataforma().upload_folder(contracts_path)
    return result


@router.get(
    "/list-contracts/",
    status_code=201,
    summary="List all the contracts available in S3",
    response_description="script details",
)
async def listContracts() -> list:
    """List all the contracts available in S3"""
    result = Plataforma().list_files("public/contracts")
    return result
