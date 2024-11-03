import sys
import json
import logging
import os
import pathlib
from typing import Final

from dotenv import load_dotenv
from blockfrost import ApiUrls, BlockFrostApi
from pycardano import Network, Transaction
from suantrazabilidadapi.core.config import config

plataformaSecrets = config(section="plataforma")
security = config(section="security")
optional = config(section="optional")
# environment = security["env"]
load_dotenv()


class Constants:
    """Class to define constants for the project"""
    KEY_DIR: str = ".priv/wallets"
    CONTRACTS_DIR: str = ".priv/contracts"
    PROJECT_ROOT = pathlib.Path("suantrazabilidadapi")
    ENCODING_LENGHT_MAPPING: dict[str, int] = {
        "12": 128,
        "15": 160,
        "18": 192,
        "21": 224,
        "24": 256,
    }
    NETWORK_NAME: str = os.getenv("cardano_net", "preview")
    if NETWORK_NAME == "mainnet":
        NETWORK = Network.MAINNET
    else:
        NETWORK = Network.TESTNET

    HEADERS = {"Content-Type": "application/json"}
    ORACLE_WALLET_NAME = "SuanOracle"
    # ORACLE_POLICY_ID = "b11a367d61a2b8f6a77049a809d7b93c6d44c140678d69276ab77c12"
    ORACLE_TOKEN_NAME = "SuanOracle"
    BASE_URL = ApiUrls.preview.value
    BLOCK_FROST_PROJECT_ID = plataformaSecrets["block_frost_project_id"]
    BLOCKFROST_API = BlockFrostApi(project_id=BLOCK_FROST_PROJECT_ID, base_url=BASE_URL)
    COPILOT_SERVICE_DISCOVERY_ENDPOINT = os.getenv("COPILOT_SERVICE_DISCOVERY_ENDPOINT")
    OGMIOS_SERVICE_NAME = "ogmiosbackend"
    if not COPILOT_SERVICE_DISCOVERY_ENDPOINT:
        OGMIOS_URL = "localhost"
    else:
        OGMIOS_URL = f"{OGMIOS_SERVICE_NAME}.{COPILOT_SERVICE_DISCOVERY_ENDPOINT}"
    OGMIOS_PORT = 1337
    S3_BUCKET_NAME = os.getenv("s3_bucket_name")
    S3_BUCKET_NAME_HIERARCHY = os.getenv("s3_bucket_name_hierarchy")
    AWS_ACCESS_KEY_ID = os.getenv("aws_access_key_id")
    AWS_SECRET_ACCESS_KEY = os.getenv("aws_secret_access_key")
    ENVIRONMENT_NAME = os.getenv("env")


def is_valid_hex_string(s: str) -> bool:
    try:
        int(s, 16)
        return (
            len(s) % 2 == 0
        )  # Check if the length is even (each byte is represented by two characters)
    except ValueError:
        return False


def remove_file(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


# Transaction template.
tx_template: Final[dict] = {
    "type": "Witnessed Tx BabbageEra",
    "description": "Ledger Cddl Format",
    "cborHex": "",
}


def save_transaction(trans: Transaction, file: str):
    """Save transaction helper function saves a Tx object to file."""
    logging.info(
        "saving Tx to: %s , inspect with: 'cardano-cli transaction view --tx-file %s'",
        file,
        file,
    )
    tx = tx_template.copy()
    tx["cborHex"] = trans.to_cbor().hex()
    with open(file, "w", encoding="utf-8") as tf:
        tf.write(json.dumps(tx, indent=4))


def recursion_limit(limit: int = 2000):

    # Check if the new limit is greater than the current one
    if limit > sys.getrecursionlimit():
        # Set the new recursion limit
        sys.setrecursionlimit(limit)
        print("Recursion limit updated successfully.")
    else:
        print("New limit must be greater than the current limit.")
