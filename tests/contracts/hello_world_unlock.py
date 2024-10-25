import json
from dataclasses import dataclass
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(project_root)
from suantrazabilidadapi.pycardano1 import (
    Address,
    BlockFrostChainContext,
    Network,
    PaymentSigningKey,
    PaymentVerificationKey,
    PlutusData,
    PlutusV3Script,
    Redeemer,
    ScriptHash,
    TransactionBuilder,
    TransactionOutput,
    UTxO,
)
from pycardano.hash import (
    VerificationKeyHash,
    TransactionId,
)


def read_validator() -> dict:
    with open("suantrazabilidadapi/.priv/suancontracts/plutus.json", "r") as f:
        validator = json.load(f)
    script_bytes = PlutusV3Script(
        bytes.fromhex(validator["validators"][0]["compiledCode"])
    )
    script_hash = ScriptHash(bytes.fromhex(validator["validators"][0]["hash"]))
    return {
        "type": "PlutusV3",
        "script_bytes": script_bytes,
        "script_hash": script_hash,
    }

@dataclass
class HelloWorldDatum(PlutusData):
    """Dummy class stream"""
    CONSTR_ID = 0
    owner: bytes

def unlock(
    utxo: UTxO,
    from_script: PlutusV3Script,
    redeemer: Redeemer,
    signing_key: PaymentSigningKey,
    owner: VerificationKeyHash,
    context: BlockFrostChainContext,
) -> TransactionId:
    # read addresses
    with open("./suantrazabilidadapi/.priv/wallets/me.addr", "r") as f:
        input_address = Address.from_primitive(f.read())

    # build transaction
    builder = TransactionBuilder(context=context)

    builder.add_script_input(
        utxo=utxo,
        script=from_script,
        redeemer=redeemer,
    )
    builder.add_input_address(input_address)
    builder.add_output(
        TransactionOutput(
            address=input_address,
            amount=utxo.output.amount.coin,
        )
    )
    builder.required_signers = [owner]
    signed_tx = builder.build_and_sign(
        signing_keys=[signing_key],
        change_address=input_address,
    )

    # submit transaction
    return context.submit_tx(signed_tx)


def get_utxo_from_str(tx_id: str, contract_address: Address) -> UTxO:
    for utxo in context.utxos(str(contract_address)):
        if str(utxo.input.transaction_id) == tx_id:
            return utxo
    raise Exception(f"UTxO not found for transaction {tx_id}")


@dataclass
class HelloWorldRedeemer(PlutusData):
    """dummy"""
    CONSTR_ID = 0
    msg: bytes


context = BlockFrostChainContext(
    project_id="previewp0ZkXTGqxYc7wcjUllmcPQPpZmUAGCCU",
    base_url="https://cardano-preview.blockfrost.io/api/",
)

signing_key = PaymentSigningKey.load("./suantrazabilidadapi/.priv/wallets/me.sk")

validator = read_validator()

contract_address = Address(payment_part=validator["script_hash"], network=Network.TESTNET)

# get utxo to spend
tx_id = "0b4596cde5200e484e9601f3c0648bf16e3df32e31b25f6a2dc168646e78b91a"
utxo = get_utxo_from_str(tx_id, Address(
    payment_part=validator["script_hash"],
    network=Network.TESTNET,
))

# build redeemer
redeemer = Redeemer(data=HelloWorldRedeemer(msg=b"Hello, World!"))

# execute transaction
tx_hash = unlock(
    utxo=utxo,
    from_script=validator["script_bytes"],
    redeemer=redeemer,
    signing_key=signing_key,
    owner=PaymentVerificationKey.from_signing_key(signing_key).hash(),
    context=context,
)

print(
    f"2 tADA unlocked from the contract\n\tTx ID: {tx_hash}\n\tRedeemer: {redeemer.to_cbor_hex()}"
)
