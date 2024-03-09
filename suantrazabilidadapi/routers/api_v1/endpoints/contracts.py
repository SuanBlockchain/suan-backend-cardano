from opshin.prelude import *
from pycardano import *
from opshin.builder import build, PlutusContract
from fastapi import APIRouter, HTTPException
import subprocess
from typing import Optional
import logging
import os
import shutil

from suantrazabilidadapi.utils.blockchain import Keys, Contracts
from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.utils.plataforma import Plataforma
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas


router = APIRouter()


@dataclass()
class ReferenceParams(PlutusData):
    CONSTR_ID = 0
    tokenName: TokenName
    pkh: PubKeyHash

@router.post("/get-pkh/", status_code=201,
summary="From address or wallet name obtain pkh. If wallet name is provided, it has to exist locally",
    response_description="script hash",)

async def getPkh(wallets: Union[str, list[str]]) -> dict:
    """From address or wallet name obtain pkh. If wallet name is provided, it has to exist locally\n
    """
   
    try:
        pkh_dict = {}
        if isinstance(wallets, str):
            wallet = wallets
            pkh = Keys().getPkh(wallets)
        else:
            for wallet in wallets: 
                pkh = Keys().getPkh(wallet)
        
        pkh_dict[wallet] = pkh

        return pkh_dict

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/get-scripts/", status_code=200,
summary="Get all the scripts registered in Plataforma",
    response_description="Script details",)

async def getScripts():
    """Get all the scripts registered in Plataforma
    """
    try:
        r = Plataforma().listScripts()
        if r["data"].get("data", None) is not None:
            script_list = r["data"]["data"]["listScripts"]["items"]
            if script_list == []:
                final_response = {
                    "success": True,
                    "msg": 'No wallets present in the table',
                    "data": r["data"]
                }
            else:
                final_response = {
                    "success": True,
                    "msg": 'List of wallets',
                    "data": script_list
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

@router.post("/get-contract/{script_type}", status_code=201,
summary="Read created contract",
    response_description="script details")

async def getScript(command_name: pydantic_schemas.contractCommandName, query_param: str) -> dict:

    if command_name == "id":

        r = Plataforma().getScript(command_name, query_param)

        if r["data"].get("data", None) is not None:
            contractInfo = r["data"]["data"]["getScript"]
                
            if contractInfo is None:
                final_response = {
                    "success": True,
                    "msg": f'Contract with id: {query_param} does not exist in DynamoDB',
                    "data": r["data"]
                }
            else:
                final_response = {
                    "success": True,
                    "msg": 'Contract info',
                    "data": contractInfo
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


@router.post("/create-contract/{script_type}", status_code=201,
summary="From parameters build and create the smart contract",
    response_description="script details")

async def createContract(scriptType: pydantic_schemas.ScriptType, pkh: str, tokenName: str = "", save_flag: bool = True, project_id: Optional[str] = None) -> dict:

    """From parameters build a smart contract
    """
    try:

        if scriptType == "mintSuanCO2":
            script_name = "suanco2"
            script_fullName = f"{script_name}.py"
            scriptCategory = "PlutusV2"
            
            # Build parameters to build the SUANCO2 contract
            params_string2 = ReferenceParams(bytes(tokenName.encode("utf-8")), bytes(pkh.encode("utf-8")))

        # Get the location of the contract
        script_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath(script_fullName)
        
        # Build the contract
        contract = build(script_path, params_string2)
        plutus_contract = PlutusContract(contract)

        cbor_hex = plutus_contract.cbor_hex
        mainnet_address = plutus_contract.mainnet_addr
        testnet_address = plutus_contract.testnet_addr
        policy_id = plutus_contract.policy_id

        r = Plataforma().getScript("id", policy_id)
        if r["success"] == True:
            if r["data"]["data"]["getScript"] is None:
                # It means that the Script does not exist in database, so update database if save_flag is True
                if save_flag:
                    # Build the variables and store in DynamoDB
                    variables = {
                        "id": policy_id,
                        "name": script_name,
                        "MainnetAddr": mainnet_address.encode(),
                        "testnetAddr": testnet_address.encode(),
                        "cbor": cbor_hex,
                        "pkh": pkh,
                        "script_category": scriptCategory,
                        "script_type": scriptType,
                        "Active": True,
                        "token_name": tokenName

                    }
                    responseScript = Plataforma().createContract(variables)
                    if responseScript["success"] == True:
                        if responseScript["data"]["data"] is not None:
                            final_response = {"success": True, "msg": f'Script created', "data": {
                                "id": policy_id,
                            }}
                        else: 
                            final_response = {"success": False, "msg": f'Problems creating the cript with id: {policy_id} in dynamoDB'}
                    else:
                         final_response = {"success": False, "msg": f'Problems creating the script', "data": responseScript["error"]}
                else:
                    final_response = {"success": True, "msg": f'Script created but not stored in Database', "data": {
                            "id": policy_id,
                            "mainnet_address": mainnet_address.encode(),
                            "testnet_address": testnet_address.encode(),
                            "cbor": cbor_hex,
                    }}
            else:
                final_response = {
                    "success": True,
                    "msg": f'Script with id: {policy_id} already exists in DynamoDB',
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

@router.get("/save-contracts/", status_code=201,
summary="Save all the contracts to S3 available locally in the system",
    response_description="script details",)

async def saveContracts() -> dict:
    """Save all the contracts to S3 which are available locally in the system
    """
    contracts_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR)
    result = Plataforma().upload_folder(contracts_path)
    return result

@router.get("/list-contracts/", status_code=201,
summary="List all the contracts available in S3",
    response_description="script details",)

async def listContracts() -> list:
    """List all the contracts available in S3
    """
    result = Plataforma().list_files("public/contracts")
    return result










# @click.command()
# @click.argument("wallet_name")
# @click.argument("token_name")
# @click.option( "--amount", type=int, default=1)
# @click.option(
#     "--script",
#     type=click.Choice(["free", "nft", "signed"]),
#     default="nft",
# # )
# def main(wallet_name: str, token_name: str, amount: int, script: str):
#     # Load chain context
#     context = get_chain_context()

#     # Get payment address
#     payment_address = get_address(wallet_name)

#     # Get input utxo
#     utxo_to_spend = None
#     for utxo in context.utxos(payment_address):
#         if utxo.output.amount.coin > 3000000:
#             utxo_to_spend = utxo
#             break
#     assert utxo_to_spend is not None, "UTxO not found to spend!"

#     tn_bytes = bytes(token_name, encoding="utf-8")
#     signatures = []
#     if script == "nft":
#         # Build script
#         script_path = lecture_dir.joinpath("nft.py")
#         oref = TxOutRef(
#             id=TxId(bytes(utxo_to_spend.input.transaction_id)),
#             idx=utxo_to_spend.input.index,
#         )
#         plutus_script = build(script_path, oref, tn_bytes)
#     elif script == "signed":
#         # Build script
#         script_path = lecture_dir.joinpath("signed.py")
#         pkh = bytes(get_address(wallet_name).payment_part)
#         signatures.append(VerificationKeyHash(pkh))
#         plutus_script = build(script_path, pkh)
#     else:
#         cbor_path = assets_dir.joinpath(script, "script.cbor")
#         with open(cbor_path, "r") as f:
#             cbor_hex = f.read()
#         cbor = bytes.fromhex(cbor_hex)
#         plutus_script = PlutusV2Script(cbor)

#     # Load script info
#     script_hash = plutus_script_hash(plutus_script)

#     # Build the transaction
#     builder = TransactionBuilder(context)
#     builder.add_minting_script(script=plutus_script, redeemer=Redeemer(0))
#     builder.mint = MultiAsset.from_primitive({bytes(script_hash): {tn_bytes: amount}})
#     if amount > 0:
#         builder.add_input(utxo_to_spend)
#         builder.add_output(
#             TransactionOutput(
#                 payment_address, amount=Value(coin=2000000, multi_asset=builder.mint)
#             )
#         )
#     else:
#         assert script != "nft", "lecture nft script doesn't allow burning"
#         burn_utxo = None

#         def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
#             return pi == script_hash and an.payload == tn_bytes and a >= -amount

#         for utxo in context.utxos(payment_address):
#             if utxo.output.amount.multi_asset.count(f):
#                 burn_utxo = utxo
#         builder.add_input(burn_utxo)
#         assert burn_utxo, "UTxO containing token not found!"

#     builder.required_signers = signatures

#     # Sign the transaction
#     payment_vkey, payment_skey, payment_address = get_signing_info(wallet_name)
#     signed_tx = builder.build_and_sign(
#         signing_keys=[payment_skey],
#         change_address=payment_address,
#     )

#     # Submit the transaction
#     context.submit_tx(signed_tx)

#     print(f"transaction id: {signed_tx.id}")
#     print(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{signed_tx.id}")
