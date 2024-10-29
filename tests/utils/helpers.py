import json
import logging
import time
import os
from pathlib import Path
from typing import Final, Optional

import pycardano as py
from opshin.builder import PlutusContract, build
from opshin.prelude import *
from tests.utils.mock import MockChainContext, MockUser

from suantrazabilidadapi.utils.generic import recursion_limit
from suantrazabilidadapi.utils.plataforma import CardanoApi

# Transaction template.
tx_template: Final[dict] = {
    "type": "Witnessed Tx BabbageEra",
    "description": "Ledger Cddl Format",
    "cborHex": "",
}


def build_mintProjectToken(
    contract_dir: Path, context: MockChainContext, master: MockUser, tokenName: str
) -> tuple[py.PlutusV2Script, py.UTxO]:
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


def build_spend(
    contract_dir: Path, oracle_policy_id: str, parent_mint_policyID: str, tokenName: str
) -> py.PlutusV2Script:
    tn_bytes = bytes(tokenName, encoding="utf-8")
    logging.info("Create contract with following parameters:")
    logging.info(f"Parent policy id from token mint contract : {parent_mint_policyID}")
    logging.info(f"token : {tokenName}")

    recursion_limit(2000)

    return build(
        contract_dir,
        bytes.fromhex(oracle_policy_id),
        bytes.fromhex(parent_mint_policyID),
        tn_bytes,
    )


def build_mintSwapToken(
    contract_dir: Path, context: MockChainContext, master: MockUser, tokenName: str
) -> tuple[py.PlutusV2Script, py.UTxO]:
    pkh = bytes(master.address.payment_part)
    tn_bytes = bytes(tokenName, encoding="utf-8")

    logging.info("Create contract with following parameters:")
    logging.info(f"pkh : {pkh}")
    logging.info(f"token : {tokenName}")

    contract = build(contract_dir, pkh, tn_bytes)

    return contract


def build_swap(contract_dir: Path, oracle_policy_id: str) -> py.PlutusV2Script:
    # tn_bytes = bytes(tokenName, encoding="utf-8")
    logging.info("Create contract with following parameters:")
    logging.info(f"Parent policy id from token mint contract : {oracle_policy_id}")
    # logging.info(f"token : {tokenName}")
    recursion_limit(2000)
    return build(contract_dir, bytes.fromhex(oracle_policy_id))


def build_mintSuanCO2(
    contract_dir: Path,
    context: MockChainContext,
    master: MockUser,
) -> tuple[py.PlutusV2Script, py.UTxO]:
    utxo_to_spend = None
    for utxo in context.utxos(master.address):
        if utxo.output.amount.coin > 3_000_000:
            utxo_to_spend = utxo
            break
    assert utxo_to_spend is not None, "UTxO not found to spend!"
    oref = TxOutRef(
        id=TxId(utxo_to_spend.input.transaction_id.payload),
        idx=utxo_to_spend.input.index,
    )
    pkh = bytes(master.address.payment_part)
    logging.info("Create contract with following parameters:")
    logging.info(f"oref : {oref.id.tx_id.hex()} and idx: {oref.idx}")
    logging.info(f"pkh : {pkh}")

    contract = build(contract_dir, oref, pkh)

    return contract, utxo_to_spend


def mock_find_utxos(
    context: MockChainContext, address: py.Address, multi_asset: Union[py.MultiAsset, None], tx_id: Union[str, None]= None
) -> Union[py.UTxO, None]:

    candidate_utxo = None
    if not tx_id and not multi_asset:
        raise Exception("you must provide either tx_id or multi_asset to find a candidate utxo")
    if tx_id:
        candidate_utxo = next((utxo for utxo in context.utxos(str(address.encode())) if str(utxo.input.transaction_id) == tx_id), None)
        return candidate_utxo
    if multi_asset:
        for policy_id, asset in multi_asset.data.items():
            for tn_bytes, amount in asset.data.items():
                for utxo in context.utxos(address.encode()):
                    # TODO: correct here to find multiple utxos to fullfill quantity requirement
                    def f(pi: py.ScriptHash, an: py.AssetName, a: int) -> bool:
                        return (
                            pi == policy_id
                            and an.payload == tn_bytes.payload
                            and a >= amount
                        )

                    if utxo.output.amount.multi_asset.count(f):
                        candidate_utxo = utxo
                        break

                assert isinstance(
                    candidate_utxo, py.UTxO
                ), "Not enough tokens found in Utxo"

    return candidate_utxo


def min_value(
    context: MockChainContext,
    address: py.Address,
    multi_asset: py.MultiAsset,
    datum: Optional[py.Datum] = None,
) -> int:
    return py.min_lovelace(
        context,
        output=py.TransactionOutput(address, py.Value(0, multi_asset), datum=datum),
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
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", encoding="utf-8") as tf:
        tf.write(json.dumps(tx, indent=4))


def setup_user(context: MockChainContext, walletName: Optional[str] = ""):
    user = MockUser(context, walletName)
    user.fund(100000000)  # 100 ADA
    return user


def setup_users(context: MockChainContext) -> List[MockUser]:
    users = []
    for _ in range(3):
        u = MockUser(context)
        u.fund(10_000_000)  # 10 ADA
        users.append(u)
    return users


def create_contract(contract: py.PlutusV2Script) -> PlutusContract:
    # Build the contract
    plutus_contract = PlutusContract(contract)

    assert isinstance(plutus_contract, PlutusContract), "Not a plutus script contract"

    cbor_hex = plutus_contract.cbor_hex
    mainnet_address = plutus_contract.mainnet_addr
    testnet_address = plutus_contract.testnet_addr
    policy_id = plutus_contract.policy_id

    logging.info(f"testnet address: {testnet_address}")
    logging.info(f"policyId: {policy_id}")

    return plutus_contract


def build_multiAsset(policy_id: str, tokenName: str, quantity: int) -> py.MultiAsset:
    multi_asset = py.MultiAsset()
    my_asset = py.Asset()
    my_asset.data.update({py.AssetName(bytes(tokenName, encoding="utf-8")): quantity})
    multi_asset[py.ScriptHash(bytes.fromhex(policy_id))] = my_asset

    return multi_asset


# def monitor_transaction(transaction_id: str) -> bool:
#     # Wait to confirm the transaction in the blockchain
#     confirmation = False
#     while not confirmation:  # type: ignore
#         status = CardanoApi().txStatus(transaction_id)[0]["num_confirmations"]
#         if status:
#             if status >= 1:
#                 confirmation = True
#             else:
#                 print(f"Transaction {transaction_id} not yet confirmed")
#                 time.sleep(5)
#         else:
#             print(f"Transaction {transaction_id} not yet confirmed")
#             time.sleep(10)

#     print(f"transaction succesfully submitted with Hash: {transaction_id}")

#     return confirmation
