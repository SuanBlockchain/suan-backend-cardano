from copy import deepcopy

import opshin.prelude as oprelude
from fastapi import APIRouter, HTTPException
from pycardano import (
    Address,
    AuxiliaryData,
    InvalidHereAfter,
    PlutusV2Script,
    Redeemer,
    TransactionBuilder,
    TransactionOutput,
    Value,
    VerificationKeyHash,
    min_lovelace,
)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.plataforma import CardanoApi, Helpers, Plataforma
from suantrazabilidadapi.utils.generic import Constants

router = APIRouter()


@router.post(
    "/create-order/",
    status_code=201,
    summary="Create order to sell tokens for specific tokenA/tokenB pair",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def createOrder(
    order: pydantic_schemas.Order, order_side: pydantic_schemas.ClaimRedeem
) -> dict:
    try:
        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", order.wallet_id)
        if r["data"].get("data", None) is not None:
            userWalletInfo = r["data"]["data"]["getWallet"]
            if userWalletInfo is None:
                raise ValueError(
                    f"Wallet with id: {order.wallet_id} does not exist in DynamoDB"
                )
            else:
                ########################
                """2. Build transaction"""
                ########################
                chain_context = CardanoNetwork().get_chain_context()

                # Create a transaction builder
                builder = TransactionBuilder(chain_context)

                # Add user own address as the input address
                owner_address = Address.from_primitive(userWalletInfo["address"])
                builder.add_input_address(owner_address)

                # builder.add_input(utxo_to_spend)
                must_before_slot = InvalidHereAfter(
                    chain_context.last_block_slot + 10000
                )
                # Since an InvalidHereAfter
                builder.ttl = must_before_slot.after

                multi_asset = Helpers().build_multiAsset(
                    policy_id=order.tokenA.policy_id.decode("utf-8"),
                    tq_dict={order.tokenA.token_name.decode("utf-8"): order.qtokenA},
                )

                order_side = pydantic_schemas.RedeemerBuy()

                pkh = bytes(owner_address.payment_part)

                policy_id_tokenA = order.tokenA.policy_id.decode("utf-8")

                token_name_tokenA = order.tokenA.token_name
                tokenA = pydantic_schemas.Token(
                    policy_id=oprelude.PolicyId(bytes.fromhex(policy_id_tokenA)),
                    token_name=token_name_tokenA,
                )

                datum = pydantic_schemas.DatumSwap(
                    owner=pkh,
                    order_side=order_side,
                    tokenA=tokenA,
                    tokenB=order.tokenB,
                    price=order.price,
                )

                # Get the contract address and cbor from policyId

                r = Plataforma().getScript("id", order.orderPolicyId)
                if r["success"]:
                    contractInfo = r["data"]["data"]["getScript"]
                    if contractInfo is None:
                        raise ValueError(
                            f"Contract with id: {order.orderPolicyId} does not exist in DynamoDB"
                        )
                    else:
                        order_address = contractInfo.get("testnetAddr", None)

                min_val = min_lovelace(
                    chain_context,
                    output=TransactionOutput(
                        order_address, Value(0, multi_asset), datum=datum
                    ),
                )
                builder.add_output(
                    TransactionOutput(
                        order_address,
                        Value(min_val, multi_asset),
                        datum=datum,
                    )
                )
                metadata = {}
                if order.metadata is not None and order.metadata != {}:
                    auxiliary_data, metadata = Helpers().build_metadata(order.metadata)
                    # Set transaction metadata
                    if isinstance(auxiliary_data, AuxiliaryData):
                        builder.auxiliary_data = auxiliary_data
                    else:
                        raise ValueError(auxiliary_data)

                signatures = []
                signatures.append(VerificationKeyHash(pkh))
                builder.required_signers = signatures

                build_body = builder.build(change_address=owner_address)
                tx_cbor = build_body.to_cbor_hex()

                # Processing the tx body
                format_body = Plataforma().formatTxBody(
                    build_body
                )  # TODO: sacar de acá el index del utxo

                utxo_list_info = []
                for utxo in build_body.inputs:
                    utxo_details = CardanoApi().getUtxoInfo(utxo.to_cbor_hex()[6:70])
                    for utxo_output in utxo_details["outputs"]:
                        if utxo_output["output_index"] == utxo.index:
                            utxo_output["utxo_hash"] = (
                                f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                            )
                            utxo_list_info.append(utxo_output)

                final_response = {
                    "success": True,
                    "msg": "Tx Build",
                    "build_tx": format_body,
                    "cbor": str(tx_cbor),
                    "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                }
        else:
            if r["success"]:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"],
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"],
                }

        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/unlock-order/{order_side}",
    status_code=201,
    summary="Unlock order placed in swap contract",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def unlockOrder(
    order: pydantic_schemas.UnlockOrder,
    order_side: pydantic_schemas.ClaimRedeem,
    oracle_token_name: str = Constants.ORACLE_TOKEN_NAME,
) -> dict:
    try:
        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", order.wallet_id)
        if r["data"].get("data", None) is not None:
            userWalletInfo = r["data"]["data"]["getWallet"]
            if userWalletInfo is None:
                raise ValueError(
                    f"Wallet with id: {order.wallet_id} does not exist in DynamoDB"
                )
            else:
                ########################
                """2. Build transaction"""
                ########################
                chain_context = CardanoNetwork().get_chain_context()

                # Create a transaction builder
                builder = TransactionBuilder(chain_context)

                # Add user own address as the input address
                user_address = Address.from_primitive(userWalletInfo["address"])
                builder.add_input_address(user_address)

                must_before_slot = InvalidHereAfter(
                    chain_context.last_block_slot + 10000
                )
                # Since an InvalidHereAfter
                builder.ttl = must_before_slot.after

                # Get the contract address and cbor from policyId

                r = Plataforma().getScript("id", order.orderPolicyId)
                if r["success"]:
                    contractInfo = r["data"]["data"]["getScript"]
                    if contractInfo is None:
                        raise ValueError(
                            f"Contract with id: {order.spendPolicyId} does not exist in DynamoDB"
                        )
                    else:
                        order_address = contractInfo.get("testnetAddr", None)
                        cbor_hex = contractInfo.get("cbor", None)

                # Redeemer action
                if order_side == "Buy":
                    redeemer = pydantic_schemas.RedeemerBuy()
                elif order_side == "Sell":
                    redeemer = pydantic_schemas.RedeemerSell()
                elif order_side == "Unlist":
                    redeemer = pydantic_schemas.RedeemerUnlist()
                else:
                    raise ValueError("Wrong redeemer")

                # Validate utxo
                if order.utxo:
                    transaction_id = order.utxo.transaction_id
                    index = order.utxo.index
                    utxo_results = Helpers().validate_utxos_existente(
                        chain_context, order_address, transaction_id, index
                    )
                    if utxo_results[0]:
                        cbor = bytes.fromhex(cbor_hex)
                        plutus_script = PlutusV2Script(cbor)
                        builder.add_script_input(
                            utxo=utxo_results[1],
                            script=plutus_script,
                            redeemer=Redeemer(redeemer),
                        )
                    else:
                        raise ValueError("No utxo found in contract")
                else:
                    raise ValueError("No utxo found in body message")

                oracle_utxo = Helpers().build_reference_input_oracle(
                    chain_context, oracle_token_name
                )

                assert oracle_utxo is not None, "Oracle UTxO not found!"
                builder.reference_inputs.add(oracle_utxo)

                metadata = {}
                if order.metadata is not None and order.metadata != {}:
                    auxiliary_data, metadata = Helpers().build_metadata(order.metadata)
                    # Set transaction metadata
                    if isinstance(auxiliary_data, AuxiliaryData):
                        builder.auxiliary_data = auxiliary_data
                    else:
                        raise ValueError(auxiliary_data)

                addresses = order.addresses
                for address in addresses:
                    multi_asset = Helpers().multiAssetFromAddress(address)
                    multi_asset_value = Value(0, multi_asset)

                    datum = None

                    # Calculate the minimum amount of lovelace that need to be transfered in the utxo
                    min_val = min_lovelace(
                        chain_context,
                        output=TransactionOutput(
                            Address.decode(address.address),
                            multi_asset_value,
                            datum=datum,
                        ),
                    )
                    if address.lovelace <= min_val:
                        builder.add_output(
                            TransactionOutput(
                                Address.decode(address.address),
                                Value(min_val, multi_asset),
                                datum=datum,
                            )
                        )
                    else:
                        builder.add_output(
                            TransactionOutput(
                                Address.decode(address.address),
                                Value(address.lovelace, multi_asset),
                                datum=datum,
                            )
                        )

                pkh = bytes(user_address.payment_part)
                signatures = []
                signatures.append(VerificationKeyHash(pkh))
                builder.required_signers = signatures

                build_body = builder.build(change_address=user_address)
                tx_cbor = build_body.to_cbor_hex()
                redeemers = builder.redeemers()
                # tmp_builder = deepcopy(builder)
                # redeemers = tmp_builder.redeemers

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                utxo_list_info = []
                for utxo in build_body.inputs:
                    utxo_details = CardanoApi().getUtxoInfo(utxo.to_cbor_hex()[6:70])
                    for utxo_output in utxo_details["outputs"]:
                        if utxo_output["output_index"] == utxo.index:
                            utxo_output["utxo_hash"] = (
                                f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                            )
                            utxo_list_info.append(utxo_output)

                final_response = {
                    "success": True,
                    "msg": "Tx Build",
                    "build_tx": format_body,
                    "cbor": str(tx_cbor),
                    "redeemer_cbor": redeemers.to_cbor_hex(),
                    "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                    # "tx_id": str(signed_tx.id)
                }
        else:
            if r["success"]:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"],
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"],
                }

        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
