from typing import List, Optional, Union
import unittest
from functools import cache
from pathlib import Path
from copy import deepcopy
import pycardano as py
from opshin.builder import build, PlutusContract, load
from opshin.prelude import Address, PubKeyCredential, NoStakingCredential, TxOutRef, TxId
import logging
import binascii
import json
import os


import sys
sys.path.append('./')
from utils.mock import MockChainContext, MockUser
from tests.utils.helpers import build_mintProjectToken, build_inversionista, find_utxos_with_tokens, min_value, save_transaction
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
# import inversionista


@cache
def setup_context():
    context = MockChainContext()
    # enable opshin validator debugging
    # context.opshin_scripts[py.PlutusV2Script] = inversionista.validator
    return context, setup_user(context), setup_user(context), setup_user(context)



def buildContract(script_path: Path, token_policy_id: str, token_name: str) -> tuple[py.ScriptHash, py.Address]:

    token_bytes = bytes(token_name, 'utf-8')
    nft_policy_id_bytes = bytes.fromhex(token_policy_id)
    plutus_script = build(script_path, nft_policy_id_bytes, token_bytes)
    script_hash = py.plutus_script_hash(plutus_script)
    script_address = py.Address(script_hash, network=py.Network.TESTNET)

    return (script_hash, script_address)

def build_datum(pkh: str) -> pydantic_schemas.DatumProjectParams:

    datum = pydantic_schemas.DatumProjectParams(
        # oracle_policy_id=bytes.fromhex(oracle_policy_id),
        beneficiary=bytes.fromhex(pkh)
    )
    return datum


def build_multiAsset(policy_id: str, tokenName: str, quantity: int) -> py.MultiAsset:
    multi_asset = py.MultiAsset()
    my_asset = py.Asset()
    my_asset.data.update({py.AssetName(bytes(tokenName, encoding="utf-8")): quantity})
    multi_asset[py.ScriptHash(bytes.fromhex(policy_id))] = my_asset

    return multi_asset

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

def test_mint_lock(
        contract_info: dict,
        tokenName: str,
        tokenQ: int) -> MockChainContext:


    mint_contract = contract_info["mint_contract"]
    context = contract_info["context"]
    administrador = contract_info["administrador"]
    spend_address = contract_info["spend_address"]
    parent_mint_policyID = contract_info["parent_mint_policyID"]
    utxo_to_spend = contract_info["utxo_to_spend"]

    tx_builder = py.TransactionBuilder(context)

    tx_builder.add_input(utxo_to_spend)

    signatures = []

    redeemer = pydantic_schemas.RedeemerMint()
    signatures.append(py.VerificationKeyHash(bytes(administrador.address.payment_part)))

    tx_builder.add_minting_script(script=mint_contract.contract, redeemer=py.Redeemer(redeemer))
    multi_asset = build_multiAsset(parent_mint_policyID, tokenName, tokenQ)
    tx_builder.mint = multi_asset
    tx_builder.required_signers = signatures

    must_before_slot = py.InvalidHereAfter(context.last_block_slot + 10000)
    # Since an InvalidHereAfter
    tx_builder.ttl = must_before_slot.after
    pkh = binascii.hexlify(administrador.pkh.payload).decode('utf-8')
    datum = build_datum(pkh)


    min_val = min_value(context, administrador.address, multi_asset, datum)
    
    spected_tx_output = py.TransactionOutput(spend_address, py.Value(min_val, multi_asset), datum=datum)
    tx_builder.add_output(spected_tx_output)

    tx = tx_builder.build_and_sign([administrador.signing_key], change_address=administrador.address)
    new_context = context
    if isinstance(context, MockChainContext):
        context.submit_tx(tx)
        utxos_at_spend = context._utxos(spend_address.encode())
        assert utxos_at_spend[0].output == spected_tx_output, "Problems creating the transaction"
    else:
        #TODO: Check what to do with the result of the evaluation
        result = context.evaluate_tx(tx)
        context.submit_tx(tx)

        logging.info(f"New tokens created and locked at: {spend_address}")

    return new_context

def test_unlock(
    contract_info: dict,
    tokenName: str, 
    buyQ: int,
    redeemer: str) -> py.Transaction:

    context = contract_info["context"]
    administrador = contract_info["administrador"]
    spend_address = contract_info["spend_address"]
    spend_contract = contract_info["spend_contract"]
    parent_mint_policyID = contract_info["parent_mint_policyID"]
    propietario = contract_info["propietario"]
    
    tx_builder = py.TransactionBuilder(context)
    # MultiAsset to trade
    multi_asset_buy = build_multiAsset(parent_mint_policyID, tokenName, buyQ)

    # Build redeemer
    if redeemer == "buy":
        redeemer = pydantic_schemas.RedeemerBuy()
    else:
        redeemer = pydantic_schemas.RedeemerUnlist()
    # Find the utxo at the contract
    spend_utxo = find_utxos_with_tokens(context, spend_address, multi_asset=multi_asset_buy)

    oracle_asset = build_multiAsset("f74904d005a134a622ab52ddcf4bd206a5d5ac6ea19de7587bb8ebb2", "SuanOracle", 1)
    oracle_address = py.Address.from_primitive("addr_test1qzjawhpa7860arp70znfdmsudqldsegvscvxamcn2rrkjc996awrmu05l6xru79xjmhpc6p7mpjsepscdmh3x5x8d9sqg8lag7")
    oracle_utxo = find_utxos_with_tokens(context, oracle_address, multi_asset=oracle_asset)
    tx_builder.reference_inputs.add(oracle_utxo)
    # Build Transaction Output to contract
    pkh = binascii.hexlify(administrador.pkh.payload).decode('utf-8')
    pkh = "96be4512d3162d6752a86a19ec8ea28d497aceafad8cd6fc3152cad6"
    datum = build_datum(pkh)
    tx_builder.add_script_input(
        spend_utxo,
        spend_contract.contract,
        redeemer=py.Redeemer(redeemer)
        )

    # Add input address to pay fees. This is the buyer address
    tx_builder.add_input_address(propietario.address)
    
    # Build Transaction Output to buyer
    min_val = min_value(context, propietario.address, multi_asset=multi_asset_buy)
    tx_builder.add_output(py.TransactionOutput(propietario.address, py.Value(min_val, multi_asset_buy)))
    
    # Build Transaction Output to beneficiary
    # tx_builder.add_output(py.TransactionOutput(administrador.address, py.Value(20_000_000)))
    tx_builder.add_output(py.TransactionOutput("addr_test1qzttu3gj6vtz6e6j4p4pnmyw52x5j7kw47kce4hux9fv445khez395ck94n492r2r8kgag5df9avatad3nt0cv2jettqxfwfwv", py.Value(20_000_000)))
    
    # Calculate the change of tokens back to the contract
    balance = spend_utxo.output.amount.multi_asset.data.get(py.ScriptHash(bytes.fromhex(parent_mint_policyID)), {b"": 0}).get(py.AssetName(bytes(tokenName, encoding="utf-8")), {b"":0})
    new_token_balance = balance - buyQ
    assert new_token_balance >= 0, "No tokens found in script address"
    if new_token_balance > 0:
        multi_asset_return = build_multiAsset(parent_mint_policyID, tokenName, new_token_balance)
        min_val = min_value(context, spend_address, multi_asset=multi_asset_return, datum=datum)
        spected_tx_output = py.TransactionOutput(spend_address, py.Value(min_val, multi_asset_return), datum=datum)
        tx_builder.add_output(spected_tx_output)

    # tx_body = tx_builder.build(change_address=propietario.address)
    tx_signed = tx_builder.build_and_sign([propietario.signing_key], change_address=propietario.address)

    # Save the transaction

    
    # new_context = context

    # if isinstance(context, MockChainContext):
    
    #     context.submit_tx(tx)
    #     utxos_at_spend = context._utxos(spend_address.encode())
    #     logging.info(f"Buyer: {propietario.balance()}")
    #     logging.info(f"Beneficiary: {administrador.balance()}")
    #     logging.info(f"Spend script: {spected_tx_output}")
    #     assert utxos_at_spend[0].output == spected_tx_output, "Problems creating the transaction"
    # else:
    #     pass
    #     # result = context.evaluate_tx(tx)
        
    #     # context.submit_tx(tx)

    return tx_signed

def test_burn(
    contract_info: dict,
    tokenName: str, 
    burnQ: int) -> MockChainContext:

    context = contract_info["context"]
    mint_contract = contract_info["mint_contract"]
    parent_mint_policyID = contract_info["parent_mint_policyID"]
    propietario = contract_info["propietario"]
    administrador = contract_info["administrador"]
    
    tx_builder = py.TransactionBuilder(context)
    signatures = []
    signatures.append(py.VerificationKeyHash(bytes(propietario.address.payment_part)))
    signatures.append(py.VerificationKeyHash(bytes(administrador.address.payment_part)))
    # Build redeemer
    redeemer = pydantic_schemas.RedeemerBurn()
    tx_builder.add_minting_script(script=mint_contract.contract, redeemer=py.Redeemer(redeemer))
    # MultiAsset to trade
    multi_asset = build_multiAsset(parent_mint_policyID, tokenName, -burnQ)
    burn_utxo = find_utxos_with_tokens(context, propietario.address, multi_asset=multi_asset)
    tx_builder.add_input(burn_utxo)
    multi_asset_burn = build_multiAsset(parent_mint_policyID, tokenName, burnQ)
    tx_builder.mint = multi_asset_burn
    tx_builder.required_signers = signatures

    # Add input address to pay fees. This is the buyer address
    tx_builder.add_input_address(propietario.address)

    tx = tx_builder.build_and_sign([propietario.signing_key, administrador.signing_key], change_address=propietario.address)
    new_context = context

    if isinstance(context, MockChainContext):
    
        context.submit_tx(tx)
        logging.info(f"Buyer: {propietario.balance()}")
    else:
        result = context.evaluate_tx(tx)
        context.submit_tx(tx)


    return new_context

def test_confirm_and_submit(transaction_dir: Path):

    with open(transaction_dir, "r") as file:
        tx = json.load(file)
    cbor = bytes.fromhex(tx["cborHex"])
    chain_context = CardanoNetwork().get_chain_context()
    chain_context.submit_tx(cbor)

    os.remove(transaction_dir)


ROOT = Path(__file__).resolve().parent.parent

def build_contracts(toBC: bool, tokenName: str) -> dict:

    # 1. Initialize general variables

    base_dir = ROOT.joinpath("suantrazabilidadapi/.priv/contracts")
    contract_dir = base_dir / "project.py"

    # 2. Create the context and fund test wallets in MockContext or Cardano

    if toBC:
        context = CardanoNetwork().get_chain_context()
        administrador = setup_user(context, walletName="administrador")
        propietario = setup_user(context, walletName="propietario")
    else:
        context, administrador, beneficiary, propietario = deepcopy(setup_context())
    
    # 3. Build the mint contract and spend project contract
    utxo_to_spend = None
    if not Path(base_dir / "project").exists():

        logging.info("Create new set of contracts")

        (plutus_contract, utxo_to_spend) = build_mintProjectToken(contract_dir, context, administrador, tokenName) 

        mint_contract = create_contract(plutus_contract)

        mint_contract.dump(base_dir / "project")

        parent_mint_policyID = mint_contract.policy_id

        contract_dir = base_dir / "inversionista.py"
        plutus_contract = build_inversionista(contract_dir, parent_mint_policyID, tokenName)

        spend_contract = create_contract(plutus_contract)
        spend_contract.dump(base_dir / "inversionista")

    else:
        logging.info("Recover the contracts from files")

        with (base_dir / "project/script.cbor").open("r") as f:
            cbor_hex = f.read()

        cbor = bytes.fromhex(cbor_hex)
        mint_contract = create_contract(py.PlutusV2Script(cbor))

        with (base_dir / "inversionista/script.cbor").open("r") as f:
            cbor_hex = f.read()

        cbor = bytes.fromhex(cbor_hex)
        spend_contract = create_contract(py.PlutusV2Script(cbor))
        
    parent_mint_policyID = mint_contract.policy_id

    spend_address = spend_contract.testnet_addr

    contract_info = {
        "context": context, 
        "mint_contract": mint_contract,
        "spend_contract": spend_contract,
        "parent_mint_policyID": parent_mint_policyID,
        "spend_address": spend_address,
        "administrador": administrador,
        "propietario": propietario,
        "utxo_to_spend": utxo_to_spend
    }

    return contract_info

        # context.wait(1000)

if __name__ == "__main__":

    tokenName = "PROJECTtOKEN2"
    tokenQ = 100
    price = 1000
    buyQ = 1
    burnQ = -70

    exists = False

    contracts_info = build_contracts(toBC=True, tokenName=tokenName)
    
    if contracts_info["utxo_to_spend"]:
        context = test_mint_lock(contracts_info, tokenName, tokenQ)
        # TODO: confirm transaction

    redeemer = "buy"

    tx_signed = test_unlock(contracts_info, tokenName, buyQ, redeemer)

    logging.info(
            "fee %s ADA",
            int(tx_signed.transaction_body.fee) / 1000000,
        )
    logging.info(
        "output %s ADA",
        int(tx_signed.transaction_body.outputs[0].amount.coin) / 1000000,
    )

    base_dir = ROOT.joinpath("suantrazabilidadapi/.priv/transactions")
    transaction_dir = base_dir / f"{str(tx_signed.id)}.signed"
    save_transaction(tx_signed, transaction_dir)

    test_confirm_and_submit(transaction_dir)




    context = test_burn(contracts_info, tokenName, burnQ)



