import os
import pathlib
from pycardano import Network


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

def is_valid_hex_string(s: str) -> bool:
    try:
        int(s, 16)
        return len(s) % 2 == 0  # Check if the length is even (each byte is represented by two characters)
    except ValueError:
        return False
    
def remove_file(path: str, name: str) -> None:
    if os.path.exists(path+name):
        os.remove(path+name)