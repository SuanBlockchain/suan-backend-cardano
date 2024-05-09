
# from utils.mock import MockChainContext, MockUser
# from typing import List, Optional
# from functools import cache
import sys
sys.path.append('./')
from pathlib import Path

import pycardano as py

from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from tests.utils.helpers import (
    build_mintSwapToken,
    setup_user,
    setup_users,
    create_contract,
    build_multiAsset,
    min_value
) 

ROOT = Path(__file__).resolve().parent.parent
base_dir = ROOT.joinpath("suantrazabilidadapi/.priv/contracts")

# @cache
# def setup_context(script: Optional[str] = None):
#     context = MockChainContext()
#     # enable opshin validator debugging
#     # context.opshin_scripts[plutus_script] = inversionista.validator
#     return context, setup_user(context), setup_user(context)

# def send_value(
#     context: MockChainContext, u1: MockUser, value: py.Value, u2: MockUser
# ):
#     builder = py.TransactionBuilder(context)
#     builder.add_input_address(u1.address)
#     builder.add_output(py.TransactionOutput(u2.address, value))
#     tx = builder.build_and_sign([u1.signing_key], change_address=u1.address)
#     context.submit_tx(tx)
#     return context


# def test_simple_spend():
#     # Create the mock py chain context
#     context = MockChainContext()
#     # Create 3 users and assign each 10 ADA
#     users = setup_users(context)
#     # Send 1 ADA from user 0 to user 1
#     send_value(context, users[0], py.Value(coin=1_000_000), users[1])
#     # Send 1 ADA from user 1 to user 2
#     send_value(context, users[1], py.Value(coin=1_000_000), users[2])


# def test_not_enough_funds():
#     context = MockChainContext()
#     users = setup_users(context)
#     # Send 100 ADA from user 0 to user 1
#     try:
#         send_value(context, users[0], py.Value(coin=100_000_000), users[1])
#         validates = True
#     except py.UTxOSelectionException:
#         validates = False
#     assert not validates, "transaction must fail"

def test_mint_swap():
    context = CardanoNetwork().get_chain_context()
    administrador = setup_user(context, walletName="administrador")

    contract_dir = base_dir / "swaptoken.py"
    nft_swap_token = "nft_swap_test"
    plutus_contract = build_mintSwapToken(contract_dir, context, administrador, nft_swap_token) 
    
    swaptoken_contract = create_contract(plutus_contract)
    swaptoken_contract.dump(base_dir / "swaptoken1")

    tx_builder = py.TransactionBuilder(context)
    tx_builder.add_input_address(administrador.address)

    signatures = []

    redeemer = pydantic_schemas.RedeemerMint() # to Mint the swapToken
    signatures.append(py.VerificationKeyHash(bytes(administrador.address.payment_part)))

    tx_builder.add_minting_script(script=swaptoken_contract.contract, redeemer=py.Redeemer(redeemer))
    multi_asset = build_multiAsset(swaptoken_contract.policy_id, nft_swap_token, 1)

    tx_builder.mint = multi_asset
    tx_builder.required_signers = signatures

    must_before_slot = py.InvalidHereAfter(context.last_block_slot + 10000)
    # Since an InvalidHereAfter
    tx_builder.ttl = must_before_slot.after

    min_val = min_value(context, administrador.address, multi_asset)

    tx_builder.add_output(py.TransactionOutput(administrador.address, py.Value(min_val, multi_asset)))

    signed_tx = tx_builder.build_and_sign([administrador.signing_key], change_address=administrador.address)

    result = context.evaluate_tx(signed_tx)

    context.submit_tx(signed_tx)

    print(result)
    return signed_tx

def test_burn_swap():

    with(base_dir / "swaptoken/script.cbor").open("r") as f:
        cbor_hex = f.read()

    cbor = bytes.fromhex(cbor_hex)
    swaptoken_contract = create_contract(py.PlutusV2Script(cbor))

    nft_swap_token = "nft_swap_PROJECTtOKEN3"

    context = CardanoNetwork().get_chain_context()
    administrador = setup_user(context, walletName="administrador")
    propietario = setup_user(context, walletName="propietario")

    tx_builder = py.TransactionBuilder(context)
    tx_builder.add_input_address(propietario.address)

    # Find a collateral UTxO
    non_nft_utxo = None
    for utxo in context.utxos(propietario.address):
        # multi_asset should be empty for collateral utxo
        if not utxo.output.amount.multi_asset and utxo.output.amount.coin >= 5000000:
            non_nft_utxo = utxo
            break
    assert isinstance(non_nft_utxo, py.UTxO), "No collateral UTxOs found!"
    tx_builder.collaterals.append(non_nft_utxo)

    signatures = []

    redeemer = pydantic_schemas.RedeemerBurn() # to Mint the swapToken
    signatures.append(py.VerificationKeyHash(bytes(propietario.address.payment_part)))
    signatures.append(py.VerificationKeyHash(bytes(administrador.address.payment_part)))

    tx_builder.add_minting_script(script=swaptoken_contract.contract, redeemer=py.Redeemer(redeemer))
    multi_asset = build_multiAsset(swaptoken_contract.policy_id, nft_swap_token, -1)

    tx_builder.mint = multi_asset
    tx_builder.required_signers = signatures

    must_before_slot = py.InvalidHereAfter(context.last_block_slot + 10000)
    # Since an InvalidHereAfter
    tx_builder.ttl = must_before_slot.after

    # min_val = min_value(context, administrador.address, multi_asset)

    # tx_builder.add_output(py.TransactionOutput(administrador.address, py.Value(min_val, multi_asset)))

    signed_tx = tx_builder.build_and_sign([administrador.signing_key, propietario.signing_key], change_address=propietario.address)

    result = context.evaluate_tx(signed_tx)

    context.submit_tx(signed_tx)

    print(result)

if __name__ == "__main__":

    # test_mint_swap()
    test_burn_swap()