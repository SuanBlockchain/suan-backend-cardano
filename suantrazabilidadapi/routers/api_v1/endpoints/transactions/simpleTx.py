import opshin.prelude as oprelude
from fastapi import APIRouter, HTTPException
from pycardano import (
    Address,
    Asset,
    AssetName,
    AuxiliaryData,
    InvalidHereAfter,
    MultiAsset,
    ScriptHash,
    TransactionBuilder,
    TransactionOutput,
    Value,
    min_lovelace,
)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.plataforma import CardanoApi, Helpers, Plataforma

router = APIRouter()


@router.post(
    "/build-tx/",
    status_code=201,
    summary="Build the transaction off-chain for validation before signing",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def buildTx(send: pydantic_schemas.BuildTx) -> dict:
    try:
        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", send.wallet_id)
        if r["data"].get("data", None) is not None:
            userWalletInfo = r["data"]["data"]["getWallet"]
            if userWalletInfo is None:
                raise ValueError(
                    f"Wallet with id: {send.wallet_id} does not exist in DynamoDB"
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

                metadata = {}
                if send.metadata is not None and send.metadata != {}:
                    auxiliary_data, metadata = Helpers().build_metadata(send.metadata)
                    # Set transaction metadata
                    if isinstance(auxiliary_data, AuxiliaryData):
                        builder.auxiliary_data = auxiliary_data
                    else:
                        raise ValueError(auxiliary_data)

                addresses = send.addresses
                for address in addresses:
                    multi_asset = MultiAsset()
                    if address.multiAsset:
                        for item in address.multiAsset:
                            my_asset = Asset()
                            for name, quantity in item.tokens.items():
                                my_asset.data.update(
                                    {AssetName(bytes(name, encoding="utf-8")): quantity}
                                )

                            multi_asset[ScriptHash(bytes.fromhex(item.policyid))] = (
                                my_asset
                            )

                    multi_asset_value = Value(0, multi_asset)

                    datum = None
                    if address.datum:
                        datum = pydantic_schemas.DatumProjectParams(
                            beneficiary=oprelude.Address(
                                payment_credential=bytes.fromhex(
                                    address.datum.beneficiary
                                ),
                                staking_credential=oprelude.NoStakingCredential(),
                            )
                        )

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

                build_body = builder.build(
                    change_address=user_address, merge_change=True
                )

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
                    "cbor": str(build_body.to_cbor_hex()),
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
