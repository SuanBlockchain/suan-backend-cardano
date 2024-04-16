
from pycardano import HDWallet

from suantrazabilidadapi.utils.blockchain import Keys


def create_wallets(
    wallet_name: str
):

    mnemonic_words = HDWallet.generate_mnemonic(strength=256)

    localKeys = {"mnemonic_words": mnemonic_words}

    skey, vkey = Keys().load_or_create_key_pair(wallet_name, localKeys=localKeys)


if __name__ == "__main__":

    options = [
        "suanco",
    ]
    # options = [
    #     "propiteario",
    #     "inversionista",
    #     "administrador",
    #     "buffer",
    #     "comunidad",
    #     "BioC"
    # ]
    for name in options:
        # wallet_name = "propietario"
        create_wallets(name)