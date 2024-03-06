from opshin.prelude import *
from pycardano import *
from fastapi import APIRouter, HTTPException
import subprocess
from typing import Optional

from suantrazabilidadapi.utils.blockchain import Keys, Contracts
from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas


router = APIRouter()

@dataclass()
class ReferenceParams(PlutusData):
    CONSTR_ID = 0
    tokenName: TokenName
    pkh: PubKeyHash

@router.post("/load-contract/{script_type}", status_code=201,
summary="From parameters load or build a smart contract",
    response_description="script hash",)

async def loadContract(script_type: pydantic_schemas.ScriptType, walletName: str, tokenName: str, project_id: Optional[str] = None) -> dict:

    """From parameters load or build a smart contract\n
    """
    try:
        if script_type == "mintSuanCO2":
            contract_name = "suanco2"
            
            # Build parameters to build the SUANCO2 contract

            # Token name in bytes
            tn_bytes = bytes(tokenName, encoding="utf-8")
            # Contract verification key
            contract_vkey = Keys().load_or_create_key_pair(walletName)[1]
            params_string = f'\'{{  \"bytes\": \"{tn_bytes}\",     \"bytes\": \"{bytes(contract_vkey.hash())}\"}}\''

        # Get the location of the contract
        script_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath(f"{contract_name}.py")
        plutus_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath(f"build/{contract_name}")
        if not plutus_path.exists():
            # Build and save the contract locally
            build_contract = subprocess.run(f"opshin build any {script_path} -o {plutus_path}".split(), input=params_string, text=True, capture_output=True, check=True)
            
            if build_contract.stderr != "":
                raise HTTPException(status_code=400, detail=str(e)) 
            
            msg = f"Built new contract at: {build_contract.stdout}"

        else:
            msg = f"Existing contract found"

        plutus_script, script_hash, script_address = Contracts().get_contract(f"{plutus_path}/script.cbor")

        result = {"msg": msg, "contract_name": contract_name, "script_hash": script_hash.to_cbor_hex()[4:], "script_address": script_address.encode() }
        

        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



    # Build the transaction


    # script_hash = plutus_script_hash(plutus_script)
    # print(script_hash)
    # get Keys to sign and pay
    # payment_skey, payment_vkey = Keys().load_or_create_key_pair("payment")
    # chain_context = CardanoNetwork().get_chain_context()
    # builder = TransactionBuilder(chain_context)
    # builder.add_minting_script(script=plutus_script, redeemer=Redeemer(0))
    # builder.mint = MultiAsset.from_primitive({bytes(script_hash): {tn_bytes: 1}})

    # address = Address(payment_vkey.hash(), network=CardanoNetwork().NETWORK)
    # destinAddress = "addr_test1qzrfa2rjtq3ky6shssmw5jj4f03qg7jvmcfkwnn77f38jxrmc4fy0srznhncjyz55t80r0tg2ptjf2hk5eut4c087ujqd8j3yl"

    # builder.add_input_address(address)

    # min_val = min_lovelace(
    # chain_context, output=TransactionOutput(destinAddress, Value(0, builder.mint))
    # )
    # builder.add_output(TransactionOutput(destinAddress, Value(min_val, builder.mint)))

    # contract_vkey_hash: VerificationKeyHash = contract_vkey.hash()
    # payment_vkey_hash: VerificationKeyHash = payment_vkey.hash()
    # builder.required_signers = [contract_vkey_hash, payment_vkey_hash]

    # signed_tx = builder.build_and_sign([contract_skey, payment_skey], change_address=address)
    # tx_id = signed_tx.transaction_body.hash().hex()
    # chain_context.submit_tx(signed_tx)











# @click.command()
# @click.argument("wallet_name")
# @click.argument("token_name")
# @click.option( "--amount", type=int, default=1)
# @click.option(
#     "--script",
#     type=click.Choice(["free", "nft", "signed"]),
#     default="nft",
# # )
# def main(wallet_name: str, token_name: str, amount: int, script: str):
#     # Load chain context
#     context = get_chain_context()

#     # Get payment address
#     payment_address = get_address(wallet_name)

#     # Get input utxo
#     utxo_to_spend = None
#     for utxo in context.utxos(payment_address):
#         if utxo.output.amount.coin > 3000000:
#             utxo_to_spend = utxo
#             break
#     assert utxo_to_spend is not None, "UTxO not found to spend!"

#     tn_bytes = bytes(token_name, encoding="utf-8")
#     signatures = []
#     if script == "nft":
#         # Build script
#         script_path = lecture_dir.joinpath("nft.py")
#         oref = TxOutRef(
#             id=TxId(bytes(utxo_to_spend.input.transaction_id)),
#             idx=utxo_to_spend.input.index,
#         )
#         plutus_script = build(script_path, oref, tn_bytes)
#     elif script == "signed":
#         # Build script
#         script_path = lecture_dir.joinpath("signed.py")
#         pkh = bytes(get_address(wallet_name).payment_part)
#         signatures.append(VerificationKeyHash(pkh))
#         plutus_script = build(script_path, pkh)
#     else:
#         cbor_path = assets_dir.joinpath(script, "script.cbor")
#         with open(cbor_path, "r") as f:
#             cbor_hex = f.read()
#         cbor = bytes.fromhex(cbor_hex)
#         plutus_script = PlutusV2Script(cbor)

#     # Load script info
#     script_hash = plutus_script_hash(plutus_script)

#     # Build the transaction
#     builder = TransactionBuilder(context)
#     builder.add_minting_script(script=plutus_script, redeemer=Redeemer(0))
#     builder.mint = MultiAsset.from_primitive({bytes(script_hash): {tn_bytes: amount}})
#     if amount > 0:
#         builder.add_input(utxo_to_spend)
#         builder.add_output(
#             TransactionOutput(
#                 payment_address, amount=Value(coin=2000000, multi_asset=builder.mint)
#             )
#         )
#     else:
#         assert script != "nft", "lecture nft script doesn't allow burning"
#         burn_utxo = None

#         def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
#             return pi == script_hash and an.payload == tn_bytes and a >= -amount

#         for utxo in context.utxos(payment_address):
#             if utxo.output.amount.multi_asset.count(f):
#                 burn_utxo = utxo
#         builder.add_input(burn_utxo)
#         assert burn_utxo, "UTxO containing token not found!"

#     builder.required_signers = signatures

#     # Sign the transaction
#     payment_vkey, payment_skey, payment_address = get_signing_info(wallet_name)
#     signed_tx = builder.build_and_sign(
#         signing_keys=[payment_skey],
#         change_address=payment_address,
#     )

#     # Submit the transaction
#     context.submit_tx(signed_tx)

#     print(f"transaction id: {signed_tx.id}")
#     print(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{signed_tx.id}")
