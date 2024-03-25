from typing import List, Optional, Any
import unittest
from functools import cache
from pathlib import Path
from copy import deepcopy
import pycardano as py
from opshin.builder import build, PlutusContract
from opshin.prelude import Address, PubKeyCredential, NoStakingCredential, TxOutRef, TxId
import logging
import binascii


import sys
sys.path.append('./')
from utils.mock import MockChainContext, MockUser
from tests.utils.helpers import build_mintProjectToken, build_inversionista, find_utxos_with_tokens, min_value
# import pydantic_schemas
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas


@cache
def setup_context(script: Optional[str] = None):
    context = MockChainContext()
    # enable opshin validator debugging
    # context.opshin_scripts[plutus_script] = inversionista.validator
    return context, setup_user(context), setup_user(context), setup_user(context)



def buildContract(script_path: Path, token_policy_id: str, token_name: str) -> tuple[py.ScriptHash, py.Address]:

    token_bytes = bytes(token_name, 'utf-8')
    nft_policy_id_bytes = bytes.fromhex(token_policy_id)
    plutus_script = build(script_path, nft_policy_id_bytes, token_bytes)
    script_hash = py.plutus_script_hash(plutus_script)
    script_address = py.Address(script_hash, network=py.Network.TESTNET)

    return (script_hash, script_address)

def build_datum(pkh: str, price: int) -> pydantic_schemas.DatumProjectParams:

    datum = pydantic_schemas.DatumProjectParams(
        beneficiary=Address(
            payment_credential=PubKeyCredential(bytes.fromhex(pkh)),
            staking_credential=NoStakingCredential()
        ),
        price= price
    )
    return datum


def build_multiAsset(policy_id: str, tokenName: str, quantity: int) -> py.MultiAsset:
    multi_asset = py.MultiAsset()
    my_asset = py.Asset()
    my_asset.data.update({py.AssetName(bytes(tokenName, encoding="utf-8")): quantity})
    multi_asset[py.ScriptHash(bytes.fromhex(policy_id))] = my_asset

    return multi_asset

def setup_user(context: MockChainContext):
    user = MockUser(context)
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

    logging.info("Contract created:")
    logging.info(f"testnet address: {testnet_address}")
    logging.info(f"policyId: {policy_id}")

    return plutus_contract

# def test_create_contract_mintProjectToken(contract_dir: Path, context: MockChainContext, master: MockUser, tokenName: str) -> tuple[PlutusContract, py.UTxO]:
#     utxo_to_spend = None
#     for utxo in context.utxos(master.address):
#         if utxo.output.amount.coin > 3_000_000:
#             utxo_to_spend = utxo
#             break
#     assert utxo_to_spend is not None, "UTxO not found to spend!"
#     tn_bytes = bytes(tokenName, encoding="utf-8")
#     oref = TxOutRef(
#         id=TxId(bytes(utxo_to_spend.input.transaction_id)),
#         idx=utxo_to_spend.input.index,
#     )
#     pkh = bytes(master.address.payment_part)
#     logging.info("Create contract with following parameters:")
#     logging.info(f"oref : {oref.id.to_cbor_hex()} and idx: {oref.idx}")
#     logging.info(f"pkh : {pkh}")
#     logging.info(f"token : {tokenName}")

#     contract = build(contract_dir, oref, pkh, tn_bytes)

#     # Build the contract
#     plutus_contract = PlutusContract(contract)

#     assert isinstance(plutus_contract, PlutusContract), "Not a plutus script contract"

#     cbor_hex = plutus_contract.cbor_hex
#     mainnet_address = plutus_contract.mainnet_addr
#     testnet_address = plutus_contract.testnet_addr
#     policy_id = plutus_contract.policy_id

#     logging.info("Contract created:")
#     logging.info(f"testnet address: {testnet_address}")
#     logging.info(f"policyId: {policy_id}")

    # return plutus_contract, utxo_to_spend

# def test_create_contract_inversionista(contract_dir: Path, mint_policy_id: str, tokenName: str) -> tuple[PlutusContract, py.UTxO]:
    
#     tn_bytes = bytes(tokenName, encoding="utf-8")
#     logging.info("Create contract with following parameters:")
#     logging.info(f"Parent policy id from token mint contract : {mint_policy_id}")
#     logging.info(f"token : {tokenName}")
    
#     contract = build(contract_dir, bytes.fromhex(mint_policy_id), tn_bytes)

#     # Build the contract
#     plutus_contract = PlutusContract(contract)

#     assert isinstance(plutus_contract, PlutusContract), "Not a plutus script contract"
    
#     utxo_to_spend = None
#     for utxo in context.utxos(master.address):
#         if utxo.output.amount.coin > 3_000_000:
#             utxo_to_spend = utxo
#             break
#     assert utxo_to_spend is not None, "UTxO not found to spend!"
#     tn_bytes = bytes(tokenName, encoding="utf-8")
#     oref = TxOutRef(
#         id=TxId(bytes(utxo_to_spend.input.transaction_id)),
#         idx=utxo_to_spend.input.index,
#     )
#     pkh = bytes(master.address.payment_part)
#     logging.info("Create contract with following parameters:")
#     logging.info(f"oref : {oref.id.to_cbor_hex()} and idx: {oref.idx}")
#     logging.info(f"pkh : {pkh}")
#     logging.info(f"token : {tokenName}")

#     contract = build(contract_dir, oref, pkh, tn_bytes)

#     # Build the contract
#     plutus_contract = PlutusContract(contract)

#     assert isinstance(plutus_contract, PlutusContract), "Not a plutus script contract"

#     cbor_hex = plutus_contract.cbor_hex
#     mainnet_address = plutus_contract.mainnet_addr
#     testnet_address = plutus_contract.testnet_addr
#     policy_id = plutus_contract.policy_id

#     logging.info("Contract created:")
#     logging.info(f"mainnet address: {mainnet_address}")
#     logging.info(f"testnet address: {testnet_address}")
#     logging.info(f"policyId: {policy_id}")

#     return plutus_contract, utxo_to_spend

def test_mint_lock(
        plutus_contract: PlutusContract, 
        utxo_to_spend: py.UTxO, 
        context: MockChainContext, 
        master: MockUser, 
        tokenName: str,
        tokenQ: int,
        price: int,
        beneficiary: MockUser, 
        destin: Optional[py.Address] = None) -> MockChainContext:

    tx_builder = py.TransactionBuilder(context)
    tx_builder.add_input(utxo_to_spend)

    signatures = []
    signatures.append(py.VerificationKeyHash(bytes(master.address.payment_part)))

    redeemer = pydantic_schemas.RedeemerMint()
    tx_builder.add_minting_script(script=plutus_contract.contract, redeemer=py.Redeemer(redeemer))
    multi_asset = build_multiAsset(plutus_contract.policy_id, tokenName, tokenQ)
    tx_builder.mint = multi_asset
    tx_builder.required_signers = signatures

    must_before_slot = py.InvalidHereAfter(context.last_block_slot + 10000)
    # Since an InvalidHereAfter
    tx_builder.ttl = must_before_slot.after
    pkh = binascii.hexlify(beneficiary.pkh.payload).decode('utf-8')
    datum = build_datum(pkh, price)


    min_val = min_value(context, master.address, multi_asset, datum)
    # min_val = py.min_lovelace(
    #     context, output=py.TransactionOutput(master.address, py.Value(0, multi_asset), datum=datum)
    # )
    if not destin:
        tx_builder.add_output(py.TransactionOutput(master.address, py.Value(min_val, multi_asset), datum=datum))
        assert master.balance().multi_asset == multi_asset, "Multi asset not found in expected utxo"
    else:
        spected_tx_output = py.TransactionOutput(destin, py.Value(min_val, multi_asset), datum=datum)
        tx_builder.add_output(spected_tx_output, datum=datum)

    tx = tx_builder.build_and_sign([master.signing_key], change_address=master.address)
    context.submit_tx(tx)
    new_context = context
    utxos_at_spend = context._utxos(destin.encode())
    assert utxos_at_spend[0].output == spected_tx_output, "Problems creating the transaction"

    return new_context

def test_unlock(
        plutus_contract: PlutusContract, 
        context: MockChainContext, 
        buyer: MockUser,
        tokenName: str, 
        buyQ: int,
        price: int,
        beneficiary: MockUser) -> MockChainContext:
    
    tx_builder = py.TransactionBuilder(context)
    # MultiAsset to trade
    multi_asset = build_multiAsset(plutus_contract.policy_id, tokenName, buyQ)

    # Build Transaction Output to buyer
    datum = None
    min_val = min_value(context, buyer.address, multi_asset=py.MultiAsset(), datum=datum)
    tx_builder.add_output(py.TransactionOutput(buyer.address, py.Value(min_val, multi_asset), datum=datum))
    
    # Build Transaction Output to beneficiary
    # same min val can be taken
    tx_builder.add_output(py.TransactionOutput(beneficiary.address, py.Value(price, multi_asset), datum=datum))
    
    # Build Transaction Output to contract
    pkh = binascii.hexlify(beneficiary.pkh.payload).decode('utf-8')
    datum = build_datum(pkh, price)
    min_val = min_value(context, plutus_contract.testnet_addr, multi_asset=multi_asset, datum=datum)
    tx_builder.add_output(py.TransactionOutput(buyer.address, py.Value(min_val, multi_asset), datum=datum))

    # Build redeemer
    redeemer = pydantic_schemas.RedeemerBuy()
    # Find the utxo at the contract
    spend_utxo = find_utxos_with_tokens(context, plutus_contract.testnet_addr, multi_asset=multi_asset)
    tx_builder.add_script_input(
        spend_utxo,
        plutus_contract.contract,
        redeemer=py.Redeemer(redeemer),
        )
    
    tx = tx_builder.build_and_sign([buyer.signing_key], change_address=buyer.address)
    context.submit_tx(tx)
    new_context = context
    utxos_at_spend = context._utxos(plutus_contract.testnet_addr.encode())
    # assert utxos_at_spend[0].output == spected_tx_output, "Problems creating the transaction"

    return new_context

# def unlock(context: MockChainContext, u1: MockUser, u3: MockUser, redeemer):
#     scriptUtxo = context.utxos(script_address)[0]
#     tx_builder = py.TransactionBuilder(context)

#     # burn_utxo = None
#     # def f(pi: py.ScriptHash, an: py.AssetName, a: int) -> bool:
#     #     return pi == py.ScriptHash(bytes.fromhex("2fa3f8b68cd8f4bb95ebc0e24ee5ee7629081e094cab8319caf0453f")) and an.payload == token_name and a >= 1
#     # for utxo in context.utxos(u3.address):
#     #     if utxo.output.amount.multi_asset.count(f):
#     #         burn_utxo = utxo
#     # assert burn_utxo, "UTxO containing token not found!"
#     # tx_builder.reference_inputs.add(burn_utxo)
#     # nft_multiasset = py.MultiAsset.from_primitive({bytes.fromhex("2fa3f8b68cd8f4bb95ebc0e24ee5ee7629081e094cab8319caf0453f"): {token_name: 1}})
#     # reference_input = py.UTxO(
#     #     py.TransactionInput(
#     #         transaction_id=py.TransactionId(bytes.fromhex("a841120bcfa9b59477338fd4a540e35eb758725bfaa194b0b9fc101d1b4a2edf")),
#     #         index = 0
#     #     ),
#     #     py.TransactionOutput(
#     #         address=py.Address.from_primitive("addr_test1wzkfdtd5k5t3ggcsz22yj6r5cwtxa8x9vzs0qyz00x9y2ngra8aqg"),
#     #         amount=py.Value(0, nft_multiasset),
#     #         datum=datum
#     #     ),
#     # )
#     # tx_builder.reference_inputs.add(reference_input)
#     tx_builder.add_input_address(u1.address)
#     tx_builder.add_script_input(
#         scriptUtxo,
#         redeemer=py.Redeemer(inversionista.Buy()),
#         script=plutus_script
#     )
#     destionation_address = py.Address(py.VerificationKeyHash(bytes.fromhex("96be4512d3162d6752a86a19ec8ea28d497aceafad8cd6fc3152cad6")), network=py.Network.TESTNET)
#     tx_builder.add_output(
#         py.TransactionOutput(destionation_address, amount=10000000)
#     )
#     tx_builder.add_output(
#         py.TransactionOutput(destionation_address, amount=2000000)
#     )
#     # tx_builder.validity_start = context.last_block_slot
#     # tx_builder.ttl = tx_builder.validity_start + 1
#     # tx_builder.required_signers()
#     signatures = []
#     signatures.append(py.VerificationKeyHash(bytes.fromhex("96be4512d3162d6752a86a19ec8ea28d497aceafad8cd6fc3152cad6")))
#     tx_builder.required_signers = signatures

#     tx = tx_builder.build_and_sign([u1.signing_key], change_address=u1.address)
#     # context.submit_tx(tx)
#     return context



def test_inversionista():

    ROOT = Path(__file__).resolve().parent.parent
    # 1. Create the context and fund test wallets
    context, master, beneficiary, buyer = deepcopy(setup_context())
    
    # 2. Build the mint contract
    contract_dir = ROOT.joinpath("suantrazabilidadapi/.priv/contracts/project.py")
    tokenName = "PROJECTTOKEN"
    tokenQ = 100_000_000
    price = 2_000_000
    buyQ = 250_000

    (plutus_contract, utxo_to_spend) = build_mintProjectToken(contract_dir, context, master, tokenName)

    mint_contract = create_contract(plutus_contract)

    parent_mint_policyID = mint_contract.policy_id

    # 2. Build the spend project contract
    contracts_dir = ROOT.joinpath("suantrazabilidadapi/.priv/contracts/inversionista.py")
    plutus_contract = build_inversionista(contract_dir, parent_mint_policyID, tokenName)

    spend_contract = create_contract(plutus_contract)

    spend_address = spend_contract.testnet_addr

    context = test_mint_lock(mint_contract, utxo_to_spend, context, master, tokenName, tokenQ, price, beneficiary, spend_address)

    context = test_unlock(spend_contract, context, buyer, tokenName, buyQ, price, beneficiary)



    context.wait(1000)

    # context = unlock(context, u1, u3, inversionista.Buy())


if __name__ == "__main__":
    # test_gift_contract()
    test_inversionista()

# def test_negative():
#     deadline_slot = 1000
#     redeemer_data = -1
#     context, u1, u2 = deepcopy(setup_context())
#     context = lock(context, u1, deadline_slot)
#     context.wait(1000)
#     unlock(context, u2, redeemer_data)


