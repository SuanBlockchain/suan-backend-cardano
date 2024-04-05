import os
import pathlib
from pycardano import Network
import importlib
from pycardano import Transaction

import logging
import json
from typing import Final

# from suantrazabilidadapi.core.config import config

class Constants:
    KEY_DIR: str = ".priv/wallets"
    CONTRACTS_DIR: str = ".priv/contracts"
    PROJECT_ROOT = pathlib.Path("suantrazabilidadapi")
    ENCODING_LENGHT_MAPPING: dict[str, int] = {"12": 128, "15": 160, "18": 192, "21": 224, "24":256}
    NETWORK_NAME: str = os.getenv("cardano_net", "preview")
    if NETWORK_NAME == "mainnet":
        NETWORK = Network.MAINNET
    else:
        NETWORK = Network.TESTNET
    
    HEADERS = {'Content-Type': 'application/json'}
    KOIOS_API = importlib.import_module("koios_api")
    REGION_NAME = "us-east-1"

def is_valid_hex_string(s: str) -> bool:
    try:
        int(s, 16)
        return len(s) % 2 == 0  # Check if the length is even (each byte is represented by two characters)
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