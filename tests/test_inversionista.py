from typing import List, Optional
from functools import cache
from pathlib import Path
from copy import deepcopy
import pycardano as py
from opshin.builder import build, PlutusContract
import logging
import binascii
import json
import os

# sys.setrecursionlimit(args.recursion_limit)

import sys
sys.path.append('./')
from utils.mock import MockChainContext, MockUser
from tests.utils.helpers import build_mintProjectToken, build_spend, find_utxos_with_tokens, min_value, save_transaction
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork

ROOT = Path(__file__).resolve().parent.parent
base_dir = ROOT.joinpath("suantrazabilidadapi/.priv/contracts")

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

    signed_tx = tx_builder.build_and_sign([administrador.signing_key], change_address=administrador.address)
    tx_id = signed_tx.transaction_body.hash().hex()
    new_context = context
    if isinstance(context, MockChainContext):
        context.submit_tx(signed_tx)
        utxos_at_spend = context._utxos(spend_address.encode())
        assert utxos_at_spend[0].output == spected_tx_output, "Problems creating the transaction"
    else:
        #TODO: Check what to do with the result of the evaluation
        result = context.evaluate_tx(signed_tx)
        context.submit_tx(signed_tx)

    return tx_id

def test_unlock_buy(
    contract_info: dict,
    tokenName: str, 
    buyQ: int) -> py.Transaction:

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
    redeemer = pydantic_schemas.RedeemerBuy()
    # Find the utxo at the contract
    spend_utxo = find_utxos_with_tokens(context, spend_address, multi_asset=multi_asset_buy)

    oracle_asset = build_multiAsset("bee96517f9dab275358a141351f4010b077d5997d382430604938b9a", "SuanOracleTest", 1)
    oracle_address = py.Address.from_primitive("addr_test1vqk6jh4xqxmp80dv2tay9hu8cmzhezyes76alt8ezevlpssxz77zr")
    oracle_utxo = find_utxos_with_tokens(context, oracle_address, multi_asset=oracle_asset)
    tx_builder.reference_inputs.add(oracle_utxo)
    # Build Transaction Output to contract
    pkh = binascii.hexlify(administrador.pkh.payload).decode('utf-8')
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
    tx_builder.add_output(py.TransactionOutput(administrador.address, py.Value(2_000_000)))
    # tx_builder.add_output(py.TransactionOutput("addr_test1qzttu3gj6vtz6e6j4p4pnmyw52x5j7kw47kce4hux9fv445khez395ck94n492r2r8kgag5df9avatad3nt0cv2jettqxfwfwv", py.Value(20_000_000)))
    
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

    return tx_signed

def test_unlock_unlist(
    contract_info: dict,
    tokenName: str, 
    unlock: int) -> py.Transaction:

    context = contract_info["context"]
    administrador = contract_info["administrador"]
    spend_address = contract_info["spend_address"]
    spend_contract = contract_info["spend_contract"]
    parent_mint_policyID = contract_info["parent_mint_policyID"]
    propietario = contract_info["propietario"]
    
    tx_builder = py.TransactionBuilder(context)

    # Take out all the tokens from the spend address
    balance = spend_utxo.output.amount.multi_asset.data.get(py.ScriptHash(bytes.fromhex(parent_mint_policyID)), {b"": 0}).get(py.AssetName(bytes(tokenName, encoding="utf-8")), {b"":0})
    # MultiAsset to trade
    multi_asset_unlist = build_multiAsset(parent_mint_policyID, tokenName, balance)

    # Build redeemer
    redeemer = pydantic_schemas.RedeemerUnlist()
    # Find the utxo at the contract
    spend_utxo = find_utxos_with_tokens(context, spend_address, multi_asset=multi_asset_unlist)

    # Build Transaction Output to contract
    tx_builder.add_script_input(
        spend_utxo,
        spend_contract.contract,
        redeemer=py.Redeemer(redeemer)
        )

    # Add input address to pay fees. This is the buyer address
    tx_builder.add_input_address(propietario.address)
    
    # Build Transaction Output to buyer
    min_val = min_value(context, propietario.address, multi_asset=multi_asset_unlist)
    tx_builder.add_output(py.TransactionOutput(propietario.address, py.Value(min_val, multi_asset_unlist)))

    # tx_body = tx_builder.build(change_address=propietario.address)
    tx_signed = tx_builder.build_and_sign([propietario.signing_key, administrador.signing_key], change_address=propietario.address)

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

    signed_tx = tx_builder.build_and_sign([propietario.signing_key, administrador.signing_key], change_address=propietario.address)
    new_context = context
    tx_id = signed_tx.transaction_body.hash().hex()

    if isinstance(context, MockChainContext):
    
        context.submit_tx(signed_tx)
        logging.info(f"Buyer: {propietario.balance()}")
    else:
        result = context.evaluate_tx(signed_tx)
        context.submit_tx(signed_tx)


    return tx_id

def test_confirm_and_submit(transaction_dir: Path):

    with open(transaction_dir, "r") as file:
        tx = json.load(file)
    cbor = bytes.fromhex(tx["cborHex"])
    chain_context = CardanoNetwork().get_chain_context()
    chain_context.submit_tx(cbor)

    os.remove(transaction_dir)

# def test_create_order(contracts_info):


def build_contracts(toBC: bool, tokenName: str) -> dict:

    # 1. Initialize general variables

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
        plutus_contract = build_spend(contract_dir, parent_mint_policyID, tokenName)

        spend_contract = create_contract(plutus_contract)
        spend_contract.dump(base_dir / "inversionista")

        parent_spend_policyID = spend_contract.policy_id

        # contract_dir = base_dir / "swap.py"
        # swap_contract = build_spend(contract_dir, parent_spend_policyID, tokenName)

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

        # with(base_dir / "swap/script.cbor").open("r") as f:
        #     cbor_hex = f.read()

        # cbor = bytes.fromhex(cbor_hex)
        # swap_contract = create_contract(py.PlutusV2Script(cbor))
        
    parent_mint_policyID = mint_contract.policy_id

    spend_address = spend_contract.testnet_addr
    spend_policyID = spend_contract.policy_id

    # swap_address = swap_contract.testnet_addr

    contracts_info = {
        "context": context, 
        "mint_contract": mint_contract,
        "spend_contract": spend_contract,
        "parent_mint_policyID": parent_mint_policyID,
        "spend_address": spend_address,
        "administrador": administrador,
        "propietario": propietario,
        "utxo_to_spend": utxo_to_spend,
        "spend_policyID": spend_policyID,
        # "swap_address": swap_address
    }

    return contracts_info

        # context.wait(1000)

def create_oracle(token_policy_id: str, token_name: str, price: int, validity: int) -> str:
    context = CardanoNetwork().get_chain_context()
    suanOracle = setup_user(context, walletName="suanOracleTest")
    tx_builder = py.TransactionBuilder(context)
    suanOracleAddress = py.Address.from_primitive(str(suanOracle.address))
    tx_builder.add_input_address(suanOracleAddress)
    must_before_slot = py.InvalidHereAfter(context.last_block_slot + 10000)
    tx_builder.ttl = must_before_slot.after

    pkh = py.VerificationKeyHash(bytes(suanOracle.address.payment_part))

    pub_key_policy = py.ScriptPubkey(pkh)

    policy = py.ScriptAll([pub_key_policy])
    # Calculate policy ID, which is the hash of the policy
    oracle_policy_id = policy.hash()
    with open(base_dir / "oraclepolicy.id", "a+") as f:
        f.truncate(0)
        f.write(str(oracle_policy_id))
    # Create the final native script that will be attached to the transaction
    native_scripts = [policy]

    tokenName = b"SuanOracleTest"
    ########################
    """Define NFT"""
    ########################
    my_nft = py.MultiAsset.from_primitive(
        {
            oracle_policy_id.payload: {
                tokenName: 1,  
            }
        }
    )
    tx_builder.mint = my_nft
    # Set native script
    tx_builder.native_scripts = native_scripts

    value_dict = {}
    token_feed = pydantic_schemas.TokenFeed(
        tokenName= bytes(token_name, encoding="utf-8"),
        price=price
    )
    value_dict[bytes.fromhex(token_policy_id)] = token_feed
    datum = pydantic_schemas.DatumOracle(
        value_dict=value_dict,
        identifier=pkh.payload,
        validity= validity
    )
    min_val = py.min_lovelace(
        context, output=py.TransactionOutput(suanOracleAddress, py.Value(0, my_nft), datum=datum)
    )
    tx_builder.add_output(py.TransactionOutput(suanOracleAddress, py.Value(min_val, my_nft), datum=datum))
    signed_tx = tx_builder.build_and_sign([suanOracle.signing_key], change_address=suanOracleAddress)
    tx_id = signed_tx.transaction_body.hash().hex()
    context.submit_tx(signed_tx)
    return tx_id

def burn_oracle() -> str:
    context = CardanoNetwork().get_chain_context()
    suanOracle = setup_user(context, walletName="suanOracleTest")
    tx_builder = py.TransactionBuilder(context)
    suanOracleAddress = py.Address.from_primitive(str(suanOracle.address))
    tx_builder.add_input_address(suanOracleAddress)
    must_before_slot = py.InvalidHereAfter(context.last_block_slot + 10000)
    tx_builder.ttl = must_before_slot.after

    pkh = py.VerificationKeyHash(bytes(suanOracle.address.payment_part))

    pub_key_policy = py.ScriptPubkey(pkh)

    policy = py.ScriptAll([pub_key_policy])
    # Calculate policy ID, which is the hash of the policy
    oracle_policy_id = policy.hash()
    with open(base_dir / "oraclepolicy.id", "a+") as f:
        f.truncate(0)
        f.write(str(oracle_policy_id))
    # Create the final native script that will be attached to the transaction
    native_scripts = [policy]

    tokenName = b"SuanOracleTest"
    my_nft = py.MultiAsset.from_primitive(
        {
            oracle_policy_id.payload: {
                tokenName: -1,  
            }
        }
    )

    burn_utxo = None
    for utxo in context.utxos(suanOracleAddress):
        def f(pi: py.ScriptHash, an: py.AssetName, a: int) -> bool:
            return pi == oracle_policy_id and an.payload == tokenName and a >= 1
        if utxo.output.amount.multi_asset.count(f):
            burn_utxo = utxo
            
            tx_builder.add_input(burn_utxo)

    if not burn_utxo:
        raise ValueError("UTxO containing token to burn not found!")
    
    tx_builder.mint = my_nft
    # Set native script
    tx_builder.native_scripts = native_scripts
    signed_tx = tx_builder.build_and_sign([suanOracle.signing_key], change_address=suanOracleAddress)
    tx_id = signed_tx.transaction_body.hash().hex()
    context.submit_tx(signed_tx)
    return tx_id


if __name__ == "__main__":

    tokenName = "PROJECTtOKEN3"
    tokenQ = 2
    price = 3_000_000
    buyQ = 1
    unlock = 1
    burnQ = -2

    contracts_info = build_contracts(toBC=True, tokenName=tokenName)

    if contracts_info["utxo_to_spend"]:
        tx_id = create_oracle(contracts_info["parent_mint_policyID"], tokenName, price, validity=1878695)
        logging.info(f"created oracle datum with tx_id: {tx_id}")
        tx_id = test_mint_lock(contracts_info, tokenName, tokenQ)
        logging.info(f"Locked tokens in spend contract tx_id: {tx_id}")
        # TODO: confirm transaction


    tx_signed = test_unlock_buy(contracts_info, tokenName, buyQ)

    logging.info(f"transaction signed: {tx_signed.transaction_body.hash().hex()}")

    base_dir = ROOT.joinpath("suantrazabilidadapi/.priv/transactions")
    transaction_dir = base_dir / f"{str(tx_signed.id)}.signed"
    save_transaction(tx_signed, transaction_dir)

    test_confirm_and_submit(transaction_dir)

    tx_signed = test_unlock_unlist(contracts_info. tokenName, unlock)
    transaction_dir = base_dir / f"{str(tx_signed.id)}.signed"
    save_transaction(tx_signed, transaction_dir)

    test_confirm_and_submit(transaction_dir)
    
    # Test swap

    # test_create_order(contracts_info)


    tx_id = test_burn(contracts_info, tokenName, burnQ)
    logging.info(f"burned project tokens with tx_id: {tx_id}")

    tx_id = burn_oracle()
    logging.info(f"burned oracle token with tx_id: {tx_id}")



