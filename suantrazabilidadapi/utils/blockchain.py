from pycardano import *
from dataclasses import dataclass
import os
from blockfrost import ApiUrls
import logging

from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.utils.generic import Constants

cardano = config(section="cardano")

@dataclass()
class Keys(Constants):
    def __post_init__(self):
        self.FULL_KEY_DIR = self.PROJECT_ROOT.joinpath(self.KEY_DIR)
    
    def load_or_create_key_pair(self, wallet_name: str, **kwargs) -> tuple[str, ExtendedSigningKey, PaymentVerificationKey, Address, str]:
        """Load payment keys or create them if they don't exist"""
        path = self.FULL_KEY_DIR / f"{wallet_name}"

        path.mkdir(parents=True, exist_ok=True)

        # skey_path = path / f"{wallet_name}.skey"
        skey_path = path.joinpath(f"{wallet_name}.skey")
        vkey_path = path.joinpath(f"{wallet_name}.vkey")

        mnemonics_path = path.joinpath(f"{wallet_name}.mnemonics")
        address_path = path.joinpath(f"{wallet_name}.address")
        pkh_path = path.joinpath(f"{wallet_name}.pkh")

        skey = None
        vkey = None

        if skey_path.exists():
            # skey = PaymentSigningKey.load(str(skey_path))
            skey = ExtendedSigningKey.load(str(skey_path))
            vkey = PaymentVerificationKey.from_signing_key(skey)

            with open(mnemonics_path, 'r') as file:
                mnemonics =file.readline()
            with open(address_path, 'r') as file:
                address =file.readline()
            with open(pkh_path, 'r') as file:
                pkh =file.readline()


        else:
            if kwargs.get("localKeys", None) is not None:
                logging.info(f"Generate Key pair and store them locally")
                mnemonic_words = kwargs["localKeys"].get("mnemonic_words", None)

                hdwallet = HDWallet.from_mnemonic(mnemonic_words)

                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                vkey = PaymentVerificationKey.from_primitive(child_hdwallet.public_key)
                # staking_verification_key = StakeVerificationKey.from_primitive(child_hdwallet.public_key)

                pkh = vkey.hash()

                # address = Address(payment_part=pkh, staking_part=staking_verification_key.hash(), network=Network.TESTNET)
                address = Address(payment_part=pkh, network=Network.TESTNET)
                # stake_address = Address(payment_part=None, staking_part=staking_verification_key.hash(), network=Network.TESTNET)

                # key_pair = PaymentKeyPair.from_signing_key(skey)

                #Save mnemonics as words were provided

                # mnemonics_path.parent.mkdir(parents=True, exist_ok=True)
                with open(mnemonics_path, 'w') as file:
                    file.write(mnemonic_words)

                skey.save(str(skey_path))
                vkey.save(str(vkey_path))

                with open(address_path, 'w') as file:
                    file.write(str(address))

                with open(pkh_path, 'w') as file:
                    file.write(str(pkh))
            else:
                logging.info(f"Only generate key pair but not stored locally")
                mnemonics = "Mnemonics not generated"
                key_pair = PaymentKeyPair.generate()
                
                skey = key_pair.signing_key
                vkey = key_pair.verification_key

                pkh = vkey.hash()
                address = Address(payment_part=pkh, network=Network.TESTNET)
                
        return mnemonics, skey, vkey, address, pkh

    def getPkh(self, address: str) -> str:
        if address.startswith("addr"):
            pkh = Address.decode(address).payment_part.to_cbor_hex()[4:]
        else:
            raise ValueError("address does not have the correct format")
        # else:
        #     # Look for the wallet name stored in .priv/wallets folder
        #     vkey = Keys().load_or_create_key_pair(wallet)[1]
        #     if vkey is not None:
        #         pkh: VerificationKeyHash = vkey.hash().to_cbor_hex()[4:]
        #     else:
        #         pkh = "wallet not found"
        return pkh
    
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

    def get_contract(self, cbor_hex: str):
        # Load script info about a contract built with opshin
        cbor = bytes.fromhex(cbor_hex)
        plutusScript = PlutusV2Script(cbor)

        return plutusScript

