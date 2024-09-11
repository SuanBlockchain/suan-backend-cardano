import binascii
import logging
from typing import Optional

from cbor2 import loads
from fastapi import APIRouter, HTTPException
from pycardano import (
    Address,
    AssetName,
    Datum,
    HDWallet,
    InvalidHereAfter,
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
import redis
from redis.commands.search.query import Query
import uuid

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork, Keys
from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.utils.plataforma import Helpers, Plataforma


router = APIRouter()


@router.get(
    "/send-access-token/",
    status_code=201,
    summary="Get the token to access Suan Marketplace",
    response_description="Confirmation of token sent to provided address",
    # response_model=List[str],
)
async def sendAccessToken(
    wallet_id: str,
    destinAddress: str,
    marketplace_id: str,
    save_flag: bool = False,
):
    try:
        # TODO: change the redis connectio to a more generic form

        # Set generic variables
        scriptName = "NativeAccessToken"
        scriptCategory = "PlutusV2"
        script_type = "native"

        r = Plataforma().getWallet("id", wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                raise ValueError(
                    f"Wallet with id: {wallet_id} does not exist in DynamoDB"
                )
            else:
                ########################
                """1. Obtain the payment sk and vk from the walletInfo"""
                ########################
                seed = walletInfo["seed"]
                hdwallet = HDWallet.from_seed(seed)
                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                payment_vk = PaymentVerificationKey.from_primitive(
                    child_hdwallet.public_key
                )
                pub_key_policy = ScriptPubkey(payment_vk.hash())
                policy = ScriptAll([pub_key_policy])
                # Calculate policy ID, which is the hash of the policy
                policy_id = policy.hash()
                policy_id_str = binascii.hexlify(policy_id.payload).decode("utf-8")

                ########################
                """2. Create the request in redis cache to be processed by the scheduler"""
                ########################
                import os

                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                rdb = redis.Redis.from_url(redis_url, decode_responses=True)
                # rdb = redis.Redis(decode_responses=True)
                token_string = "SandboxSuanAccess1"

                record = {
                    "status": "pending",
                    "destinAddress": destinAddress,
                    "wallet_id": wallet_id,
                    "token_string": token_string,
                }
                index_name = "idx:AccessToken"
                key = str(uuid.uuid4())
                rdb.json().set("AccessToken:" + key, "$", record)
                query = Query("@status:pending")
                result = rdb.ft(index_name).search(query)

                logging.info(result)

                ########################
                """3. Save the script if save_flag is true"""
                ########################
                if save_flag:
                    variables = {
                        "id": policy_id_str,
                        "name": scriptName,
                        "MainnetAddr": "na",
                        "testnetAddr": "na",
                        "cbor": "na",
                        "pbk": wallet_id,
                        "script_category": scriptCategory,
                        "script_type": script_type,
                        "Active": True,
                        "token_name": token_string,
                        "marketplaceID": marketplace_id,
                    }
                    responseScript = Plataforma().createContract(variables)
                    # TODO: if script exists don't try to write it in dynamoDB
                    if responseScript["success"] == True:
                        if (
                            responseScript["data"]["data"] is not None
                            and responseScript["data"].get("errors", None) is None
                        ):
                            final_response = {
                                "success": True,
                                "msg": "Token scheduled to be sent soon",
                                "policy_id": policy_id_str,
                                "tokenName": token_string,
                            }
                        else:
                            final_response = {
                                "success": False,
                                "msg": "Token scheduled to be sent soon but problems creating the script in dynamoDB",
                                "data": responseScript["data"]["errors"],
                                "policy_id": policy_id_str,
                                "tokenName": token_string,
                            }
                    else:
                        final_response = {
                            "success": False,
                            "msg": "Token scheduled to be sent soon but problems creating the script in dynamoDB",
                            "data": responseScript["error"],
                            "policy_id": policy_id_str,
                            "tokenName": token_string,
                        }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Token scheduled to be sent soon but script not saved in dynamoDB",
                        "policy_id": policy_id_str,
                        "tokenName": token_string,
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
        if multiAsset:
            amount = Value(addressDestin.lovelace, multiAsset)
        else:
            amount = Value(addressDestin.lovelace)

        datum = None
        if addressDestin.datum:
            datum = Datum(addressDestin.datum)
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


# from suantrazabilidad import celery_app


# @router.get("/status/{task_id}")
# async def task_status(task_id: str):
#     task = celery_app.AsyncResult(task_id)
#     if task.state == "SUCCESS":
#         return {"status": "done", "result": task.result}
#     elif task.state == "PENDING":
#         return {"status": "pending"}
#     else:
#         return {"status": "failed"}
