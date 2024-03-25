from opshin.builder import build, PlutusContract
from pathlib import Path
from opshin.prelude import *
from typing import Optional

import logging
import pycardano as py

from utils.mock import MockChainContext, MockUser



def build_mintProjectToken(contract_dir: Path, context: MockChainContext, master: MockUser, tokenName: str) -> tuple[py.PlutusV2Script, py.UTxO]:
    utxo_to_spend = None
    for utxo in context.utxos(master.address):
        if utxo.output.amount.coin > 3_000_000:
            utxo_to_spend = utxo
            break
    assert utxo_to_spend is not None, "UTxO not found to spend!"
    tn_bytes = bytes(tokenName, encoding="utf-8")
    oref = TxOutRef(
        id=TxId(bytes(utxo_to_spend.input.transaction_id)),
        idx=utxo_to_spend.input.index,
    )
    pkh = bytes(master.address.payment_part)
    logging.info("Create contract with following parameters:")
    logging.info(f"oref : {oref.id.to_cbor_hex()} and idx: {oref.idx}")
    logging.info(f"pkh : {pkh}")
    logging.info(f"token : {tokenName}")

    contract = build(contract_dir, oref, pkh, tn_bytes)

    return contract, utxo_to_spend

def build_inversionista(contract_dir: Path, parent_mint_policyID: str, tokenName: str) -> py.PlutusV2Script:
    tn_bytes = bytes(tokenName, encoding="utf-8")
    logging.info("Create contract with following parameters:")
    logging.info(f"Parent policy id from token mint contract : {parent_mint_policyID}")
    logging.info(f"token : {tokenName}")
    
    return build(contract_dir, bytes.fromhex(parent_mint_policyID), tn_bytes)

def find_utxos_with_tokens(context: MockChainContext, address: py.Address, multi_asset: py.MultiAsset) ->Union[list[py.UTxO], py.UTxO]:
    #TODO: fix this part of the function
    tokens_bytes = { bytes(tokenName, encoding="utf-8"): q for tokenName, q in multi_asset.items() }
    #If burn, insert the utxo that contains the asset
    for tn_bytes, amount in tokens_bytes.items():
        candidate_utxo = None
        candidate_utxo_list = []
        for utxo in context.utxos(address.encode()):
            def f(pi: py.ScriptHash, an: py.AssetName, a: int) -> bool:
                return pi == py.script_hash and an.payload == tn_bytes and a >= -amount
            if utxo.output.amount.multi_asset.count(f):
                candidate_utxo = utxo

        if not candidate_utxo:
            q = 0
            for utxo in context.utxos(address.encode()):
                def f1(pi: py.ScriptHash, an: py.AssetName, a: int) -> bool:
                    return pi == py.script_hash and an.payload == tn_bytes
                if utxo.output.amount.multi_asset.count(f1):
                    candidate_utxo_list.append(utxo)
                    union_multiasset = utxo.output.amount.multi_asset.data
                    for asset in union_multiasset.values():
                        q += int(list(asset.data.values())[0])
            
            if q < amount:
                raise ValueError("UTxO containing token to burn not found!")
    
    if candidate_utxo_list == []:
        return candidate_utxo   
    else:
        candidate_utxo_list

def min_value(context: MockChainContext, address: py.Address, multi_asset: py.MultiAsset, datum: Optional[py.Datum] = None) -> int:
    return py.min_lovelace(
        context, output=py.TransactionOutput(address, py.Value(0, multi_asset), datum=datum)
    )