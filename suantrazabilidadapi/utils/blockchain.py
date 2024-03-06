from pycardano import *
from dataclasses import dataclass
import os
from blockfrost import ApiUrls
from pathlib import PosixPath

from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.utils.generic import Constants

cardano = config(section="cardano")

@dataclass()
class Keys(Constants):
    def __post_init__(self):
        self.FULL_KEY_DIR = self.PROJECT_ROOT.joinpath(self.KEY_DIR)
    
    def load_or_create_key_pair(self, wallet_name: str, **kwargs):
        """Load payment keys or create them if they don't exist"""
        path = self.FULL_KEY_DIR / f"{wallet_name}"

        path.mkdir(parents=True, exist_ok=True)

        # skey_path = path / f"{wallet_name}.skey"
        skey_path = path.joinpath(f"{wallet_name}.skey")
        vkey_path = path.joinpath(f"{wallet_name}.vkey")

        if skey_path.exists():
            skey = PaymentSigningKey.load(str(skey_path))
            vkey = PaymentVerificationKey.from_signing_key(skey)
        else:
            if kwargs.get("localKeys", None) is not None:
                if "words" in kwargs["localKeys"].keys():
                    skey = kwargs["localKeys"].get("skey", None)
                    if skey is not None:
                        key_pair = PaymentKeyPair.from_signing_key(kwargs["localKeys"].get("skey"))
                    else:
                        raise ValueError("skey in optional paramaters must be provided if words are provided")
                    #Save mnemonics as words were provided

                    mnemonics_path = path / f"{wallet_name}.mnemonics"
                    # mnemonics_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(mnemonics_path, 'w') as file:
                        file.write(kwargs["localKeys"]["words"])
            
            key_pair = PaymentKeyPair.generate()
            
            key_pair.signing_key.save(str(skey_path))
            key_pair.verification_key.save(str(vkey_path))
            skey = key_pair.signing_key
            vkey = key_pair.verification_key
        return skey, vkey

@dataclass()
class CardanoNetwork(Constants):

    def __post_init__(self):
        self.NETWORK_NAME: str = os.getenv("cardano_net", "preview")
        if self.NETWORK_NAME == "mainnet":
            self.NETWORK = Network.MAINNET
        else:
            self.NETWORK = Network.TESTNET

    def get_chain_context(self) -> ChainContext:
        chain_backend = os.getenv("CHAIN_BACKEND", "blockfrost")
        if chain_backend == "blockfrost":
            if self.NETWORK_NAME == "preview":
                self.BASE_URL = ApiUrls.preview.value
                self.BLOCK_FROST_PROJECT_ID = os.getenv('block_frost_project_id')
            return BlockFrostChainContext(self.BLOCK_FROST_PROJECT_ID, base_url=self.BASE_URL)

        # elif chain_backend == "ogmios":
        #     return OgmiosChainContext(ws_url=ogmios_url, network=network)
        # elif chain_backend == "kupo":
        #     return OgmiosChainContext(ws_url=ogmios_url, network=network, kupo_url=kupo_url)
        else:
            raise ValueError(f"Chain backend not found: {chain_backend}")
        
@dataclass()
class Contracts(Constants):

    def __post_init__(self):
        pass

    def get_contract(self, script_path: PosixPath):
        # Load script info about a contract built with opshin
        with open(script_path) as f:
            cbor_hex = f.read()

        cbor = bytes.fromhex(cbor_hex)

        plutus_script = PlutusV2Script(cbor)
        script_hash = plutus_script_hash(plutus_script)
        script_address = Address(script_hash, network=self.NETWORK)
        return plutus_script, script_hash, script_address

