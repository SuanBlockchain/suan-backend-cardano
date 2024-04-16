from opshin.builder import build, PlutusContract
from pathlib import Path
from opshin.prelude import *
from typing import Optional, Final

import logging
import pycardano as py
import json

from utils.mock import MockChainContext, MockUser

# Transaction template.
tx_template: Final[dict] = {
    "type": "Witnessed Tx BabbageEra",
    "description": "Ledger Cddl Format",
    "cborHex": "",
}

def build_mintProjectToken(contract_dir: Path, context: MockChainContext, master: MockUser, tokenName: str) -> tuple[py.PlutusV2Script, py.UTxO]:
    utxo_to_spend = None
    for utxo in context.utxos(master.address):
        if utxo.output.amount.coin > 3_000_000:
            utxo_to_spend = utxo
            break
    assert utxo_to_spend is not None, "UTxO not found to spend!"
    tn_bytes = bytes(tokenName, encoding="utf-8")
    oref = TxOutRef(
        id=TxId(utxo_to_spend.input.transaction_id.payload),
        idx=utxo_to_spend.input.index,
    )
    pkh = bytes(master.address.payment_part)
    logging.info("Create contract with following parameters:")
    logging.info(f"oref : {oref.id.tx_id.hex()} and idx: {oref.idx}")
    logging.info(f"pkh : {pkh}")
    logging.info(f"token : {tokenName}")

    contract = build(contract_dir, oref, pkh, tn_bytes)

    return contract, utxo_to_spend

def build_spend(contract_dir: Path, parent_mint_policyID: str, tokenName: str) -> py.PlutusV2Script:
# def build_inversionista(contract_dir: Path) -> py.PlutusV2Script:
    tn_bytes = bytes(tokenName, encoding="utf-8")
    logging.info("Create contract with following parameters:")
    logging.info(f"Parent policy id from token mint contract : {parent_mint_policyID}")
    logging.info(f"token : {tokenName}")
    
    # return build(contract_dir)
    return build(contract_dir, bytes.fromhex(parent_mint_policyID), tn_bytes)

def find_utxos_with_tokens(context: MockChainContext, address: py.Address, multi_asset: py.MultiAsset) -> py.UTxO:
    for policy_id, asset in multi_asset.data.items():
        for tn_bytes, amount in asset.data.items():

            for utxo in context.utxos(address.encode()):
                def f(pi: py.ScriptHash, an: py.AssetName, a: int) -> bool:
                    return pi == policy_id and an.payload == tn_bytes.payload and a >= amount
                if utxo.output.amount.multi_asset.count(f):
                    candidate_utxo = utxo
                    break
            
            assert isinstance(candidate_utxo, py.UTxO), "Not enough tokens found in Utxo"
    
    return candidate_utxo

def min_value(context: MockChainContext, address: py.Address, multi_asset: py.MultiAsset, datum: Optional[py.Datum] = None) -> int:
    return py.min_lovelace(
        context, output=py.TransactionOutput(address, py.Value(0, multi_asset), datum=datum)
    )

def save_transaction(trans: py.Transaction, file: str):
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