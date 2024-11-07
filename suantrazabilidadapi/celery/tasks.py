import logging
import json
import os
import sys
import time
from typing import Any
from collections import defaultdict
import asyncio
import redis
from redis.commands.search.query import Query
from celery import shared_task
from celery.utils.log import get_task_logger
from kombu.exceptions import EncodeError

from pycardano.exception import TransactionFailedException
from pycardano import (
    Address,
    AlonzoMetadata,
    AuxiliaryData,
    ExtendedSigningKey,
    HDWallet,
    Metadata,
    MultiAsset,
    PaymentVerificationKey,
    ScriptAll,
    ScriptPubkey,
    TransactionBuilder,
    TransactionOutput,
    Value,
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(project_root)

from suantrazabilidadapi.utils.blockchain import CardanoNetwork  # pylint: disable=wrong-import-position
from suantrazabilidadapi.utils.generic import Constants  # pylint: disable=wrong-import-position
from suantrazabilidadapi.utils.plataforma import Plataforma  # pylint: disable=wrong-import-position
from suantrazabilidadapi.celery.main import redis_config  # pylint: disable=wrong-import-position

# from redis import asyncio as aioredis


logger = get_task_logger("tasks")

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
rdb = redis.Redis.from_url(redis_url, decode_responses=True)
# rdb = aioredis.from_url(redis_url, decode_responses=True)


def set_ttl(task_key: Any, ttl_seconds: int):
    # Check if a TTL is already set
    current_ttl = rdb.ttl(task_key)
    # If TTL is -1, it means the key has no expiration set
    if current_ttl == -1:
        # Set the TTL if it's not already set
        rdb.expire(task_key, ttl_seconds)
    else:
        logging.info(f"TTL is already set for key {task_key} and will not be overwritten.")


@shared_task(name="send_push_notification")
def send_push_notification(device_token: str):
    logger.info("starting background task")
    time.sleep(10)  # simulates slow network call to firebase/sns
    response = f"Successfully sent push notification to: {device_token}\n"
    return response


@shared_task(name="access-token-task")
def get_access_token_sync():
    # Wrapper to run the async function within a Celery task
    try:
        return asyncio.run(get_access_token())
    except Exception as e:
        logging.error(f"Failed to run get_access_token: {e}")
        raise EncodeError(f"Error running async function: {str(e)}") from e


async def get_access_token():
    # TODO: Make sure that the same address cannot claim twice by checking from the wallet table in dynamoDB or There must be a way to derive from the stake key when it already has the token, but also when requesting more than one in the same transaction

    index_name = "idx:AccessToken"
    token_string = "SandboxSuanAccess1"
    tasks_impacted = []
    # Set the TTL (in seconds)
    ttl_seconds = 20
    task_key = ""

    query = Query("@status:pending")
    await redis_config(index_name)

    try:
        # Get all keys that start with 'celery-task-meta-'
        task_keys = rdb.keys("celery-task-meta-*")
        # Update the TTL for each task
        for task_key in task_keys:

            task_data = rdb.get(task_key)
            if task_data:
                # Parse the task data from JSON
                task_data_json = json.loads(task_data)
                # Check if 'processed_addresses' is 0
                result = task_data_json.get("result", {})
                if result and not isinstance(result, str):
                    if result.get("processed_addresses", -1) == 0:
                        # Update the TTL (e.g., 10 minutes)
                        rdb.expire(task_key, ttl_seconds)

                else:
                    rdb.expire(task_key, ttl_seconds)

        result = rdb.ft(index_name).search(query)
        # Group documents by wallet_id
        grouped_by_wallet = defaultdict(list)
        for doc in result.docs:
            # Parse the JSON string to a dictionary
            data = json.loads(doc.json)
            wallet_id = data.get("wallet_id")

            # Group documents by wallet_id
            if wallet_id:
                grouped_by_wallet[wallet_id].append({"id": doc.id, "data": data})

        # Process each batch based on wallet_id
        wallet_ids = {}
        for wallet_id, tasks in grouped_by_wallet.items():
            logging.info(f"Processing batch for wallet_id: {wallet_id}")
            chain_context = CardanoNetwork().get_chain_context()
            builder = None
            graphql_variables = {"walletId": wallet_id}
            r = Plataforma().getWallet("getWalletById", graphql_variables)
            if r["data"].get("data", None) is not None:
                walletInfo = r["data"]["data"]["getWallet"]
                if walletInfo is None:
                    data["status"] = "failure"
                else:
                    # Create a transaction builder
                    builder = TransactionBuilder(chain_context)
                    ########################
                    """1. Obtain the payment sk and vk from the walletInfo"""
                    ########################
                    seed = walletInfo["seed"]
                    hdwallet = HDWallet.from_seed(seed)
                    child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                    payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                    payment_vk = PaymentVerificationKey.from_primitive(
                        child_hdwallet.public_key
                    )

                    master_address = Address.from_primitive(walletInfo["address"])
                    # Add our own address as the input address
                    builder.add_input_address(master_address)

                    ########################
                    """2. Create the native script and policy from the pubkey"""
                    ########################
                    pub_key_policy = ScriptPubkey(payment_vk.hash())
                    policy = ScriptAll([pub_key_policy])
                    # Calculate policy ID, which is the hash of the policy
                    policy_id = policy.hash()
                    with open(Constants().PROJECT_ROOT / "policy.id", "a+", encoding="utf-8") as f:
                        f.truncate(0)
                        f.write(str(policy_id))
                    # Create the final native script that will be attached to the transaction
                    native_scripts = [policy]

                    # Set native script
                    builder.native_scripts = native_scripts

                    destinAddress_list = []
                    for task in tasks:
                        task_data = task["data"]
                        destinAddress = task_data.get("destinAddress")
                        token_string = task_data.get("token_string")

                        ########################
                        """3. Define the Asset"""
                        ########################
                        my_nft_alternative = MultiAsset.from_primitive(
                            {
                                policy_id.payload: {
                                    bytes(token_string, encoding="utf-8"): 1,
                                }
                            }
                        )

                        ########################
                        """5. Build the transaction"""
                        ########################
                        builder.add_output(
                            TransactionOutput(
                                destinAddress, Value(50000000, my_nft_alternative)
                            )
                        )

                        # Update the document with success Status in Redis using the correct id (UUID)
                        task_data["status"] = "success"
                        rdb.json().set(task["id"], "$", task_data)

                        destinAddress_list.append(destinAddress)
                        tasks_impacted.append(task["id"])

                    # Set nft we want to mint and more important the quantity as per number of output addresses
                    builder.mint = MultiAsset.from_primitive(
                        {
                            policy_id.payload: {
                                bytes(token_string, encoding="utf-8"): len(tasks)
                            }
                        }
                    )

                    ########################
                    """4. Create metadata"""
                    ########################
                    metadata = {
                        721: {
                            policy_id.payload.hex(): {
                                bytes(token_string, encoding="utf-8"): {
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
                    # Set transaction metadata
                    builder.auxiliary_data = auxiliary_data

                    logging.info(
                        f"Batch processing for wallet_id: {wallet_id} completed."
                    )

                    signed_tx = builder.build_and_sign(
                        [payment_skey], change_address=master_address
                    )
                    tx_id = signed_tx.transaction_body.hash().hex()
                    logger.info(f"Transaction ID: {tx_id}")

                    wallet_ids[wallet_id] = {
                        "tx_id": tx_id,
                        "destinAddresses": destinAddress_list,
                    }

                    chain_context.submit_tx(signed_tx)

        logging.info("All pending tasks processed and grouped by wallet_id.")

        return {
            "processed_addresses": len(wallet_ids),
            "transactions": wallet_ids,
        }

    except TypeError as e:
        # Log and update impacted tasks on TypeError
        return handle_exception(task_key, e, "Possible non NoneType error")
    except TransactionFailedException as e:
        return handle_exception(task_key, e, "Invalid transaction")
    except Exception as e:
        # Log and update impacted tasks on any other exception
        return handle_exception(task_key, e, "General exception raised")

# @shared_task(name="multiple-contract-buy")
# def multiple_contract_buy():


def handle_exception(task, exception, log_message):
    """
    Function to handle exceptions, log them, and update impacted tasks.
    """
    task_data = rdb.json().get(task)
    if task_data:
        task_data["status"] = "failure"
        rdb.json().set(task, "$", task_data)

    logging.error(f"{log_message}: {str(exception)}")
    return {
        "status": "error",
        "task_errors": task,
        "msg": f"{log_message}: {str(exception)}",
    }


# if __name__ == "__main__":
#     # Run the get_access_token function within an asyncio event loop
#     try:
#         response = asyncio.run(get_access_token())
#         logger.debug(f"Access token: {response}")
#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#     logger.info(response)
