import functools
import logging

from fastapi import APIRouter, HTTPException
from pycardano import (
    Address,
    AssetName,
    AuxiliaryData,
    InvalidHereAfter,
    MultiAsset,
    Redeemer,
    ScriptHash,
    TransactionBuilder,
    TransactionOutput,
    Value,
    VerificationKeyHash,
    min_lovelace,
    plutus_script_hash,
    PlutusV2Script
)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.plataforma import CardanoApi, Helpers, Plataforma, RedisClient
from suantrazabilidadapi.utils.response import Response
from suantrazabilidadapi.utils.exception import ResponseProcessingError

router = APIRouter()


@router.post(
    "/mint-tokens/{mint_redeemer}",
    status_code=201,
    summary="Build the transaction off-chain for validation before signing",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def mintTokens(
    mint_redeemer: pydantic_schemas.MintRedeem, send: pydantic_schemas.TokenGenesis
) -> dict:
    try:
        ########################
        """Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", send.wallet_id)
        wallet_response = Response().handle_getWallet_response(getWallet_response=r)
        final_response = wallet_response
        walletInfo = wallet_response.get("data", None)
        if wallet_response["success"] and walletInfo:

            ########################
            """Build transaction"""
            ########################
            chain_context = CardanoNetwork().get_chain_context()

            # Create a transaction builder
            builder = TransactionBuilder(chain_context)

            # Add user own address as the input address
            master_address = Address.from_primitive(walletInfo["address"])
            builder.add_input_address(master_address)

            pkh = bytes(master_address.payment_part)

            # Validate utxo
            utxo_results = ()
            if send.utxo:
                transaction_id = send.utxo.transaction_id
                index = send.utxo.index
                utxo_results = Helpers().validate_utxos_existente(
                    chain_context, master_address, transaction_id, index
                )

            builder.add_input(utxo_results[1])

            signatures = []
            if send.mint is not None or send.mint != {}:
                tokens_bytes = {
                    bytes(tokenName, encoding="utf-8"): q
                    for tokenName, q in send.mint.asset.tokens.items()
                }
                signatures.append(VerificationKeyHash(pkh))

                # Consultar en base de datos
                script_id = send.mint.asset.policyid

                r = Plataforma().getScript("id", script_id)
                script_response = Response().handle_getScript_response(r)
                scriptInfo = script_response.get("data", None)
                if not script_response["success"] and not scriptInfo:
                    raise ResponseProcessingError("Script with policyId does not exist in database")

                cbor_hex = scriptInfo.get("cbor", None)
                cbor = bytes.fromhex(cbor_hex)
                plutus_script = PlutusV2Script(cbor)

                script_hash = plutus_script_hash(plutus_script)
                logging.info(f"script_hash: {script_hash}")

                # Redeemer action
                if mint_redeemer == "Mint":
                    redeemer = pydantic_schemas.RedeemerMint()
                elif mint_redeemer == "Burn":
                    redeemer = pydantic_schemas.RedeemerBurn()
                else:
                    raise ValueError("Wrong redeemer")

                builder.add_minting_script(
                    script=plutus_script, redeemer=Redeemer(redeemer)
                )

                mint_multiassets = MultiAsset.from_primitive(
                    {bytes(script_hash): tokens_bytes}
                )

                builder.mint = mint_multiassets

                # If burn, insert the utxo that contains the asset
                amount = 0
                for tn_bytes, amount in tokens_bytes.items():
                    if amount < 0:
                        burn_utxo = None
                        candidate_burn_utxo = []
                        for utxo in chain_context.utxos(master_address):

                            f = functools.partial(
                                lambda pi, an, a, script_hash, tn_bytes, amount: (
                                    pi == script_hash
                                    and an.payload == tn_bytes  # Type: Ignore
                                    and a >= -amount
                                ),
                                script_hash=script_hash,
                                tn_bytes=tn_bytes,
                                amount=amount
                            )

                            if utxo.output.amount.multi_asset.count(f):
                                burn_utxo = utxo

                                builder.add_input(burn_utxo)

                        if not burn_utxo:
                            q = 0
                            for utxo in chain_context.utxos(master_address):

                                f1 = functools.partial(
                                    lambda pi, an, script_hash, tn_bytes: (
                                        pi == script_hash and an.payload == tn_bytes
                                    ),
                                    script_hash=script_hash,
                                    tn_bytes=tn_bytes
                                )

                                if utxo.output.amount.multi_asset.count(f1):
                                    candidate_burn_utxo.append(utxo)
                                    union_multiasset = (
                                        utxo.output.amount.multi_asset.data
                                    )
                                    for asset in union_multiasset.values():
                                        q += int(list(asset.data.values())[0])

                            if q >= -amount:
                                for x in candidate_burn_utxo:
                                    builder.add_input(x)
                            else:
                                raise ValueError(
                                    "UTxO containing token to burn not found!"
                                )

            builder.required_signers = signatures

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

            if send.addresses:
                for address in send.addresses:
                    multi_asset = Helpers().multiAssetFromAddress(
                        addressesDestin=address
                    )

                    multi_asset_value = Value(0, multi_asset)

                    datum = None
                    if address.datum:
                        datum = Helpers().build_DatumProjectParams(
                            pkh=address.datum.beneficiary
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
            else:
                if amount > 0:
                    # Calculate the minimum amount of lovelace to be transfered in the utxo
                    min_val = min_lovelace(
                        chain_context,
                        output=TransactionOutput(
                            master_address, Value(0, mint_multiassets), datum=datum
                        ),
                    )
                    builder.add_output(
                        TransactionOutput(
                            master_address,
                            Value(min_val, mint_multiassets),
                            datum=datum,
                        )
                    )

            build_body = builder.build(change_address=master_address)
            tx_cbor = build_body.to_cbor_hex()
            redeemers = builder.redeemers()

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
                "msg": "Tx Mint Tokens",
                "build_tx": format_body,
                "cbor": str(tx_cbor),
                "redeemer_cbor": redeemers.to_cbor_hex(),
                # "redeemer_cbor": Redeemer.to_cbor_hex(
                #     redeemers[0]
                # ),  # Redeemers is a list, but assume that only 1 redeemer is passed
                "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                "utxos_info": utxo_list_info,
                "tx_size": len(build_body.to_cbor()),
            }

        return final_response
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e)) from e
    except ResponseProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/claim-tx/{claim_redeemer}",
    status_code=201,
    summary="Build the transaction off-chain for validation before signing",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def claimTx(
    claim_redeemer: pydantic_schemas.ClaimRedeem,
    claim: pydantic_schemas.Claim,
    oracle_wallet_id: str,
) -> dict:
    try:
        ########################
        """Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", claim.wallet_id)
        wallet_response = Response().handle_getWallet_response(getWallet_response=r)
        userWalletInfo = wallet_response.get("data", None)
        final_response = wallet_response
        if wallet_response["success"] and userWalletInfo:
            ########################
            """Create the request in redis cache to be processed by the scheduler"""
            ########################
            index_name = "MultipleContractBuy"
            record = {
                "status": "pending",
                "destinAddresses": claim.addresses,
                "wallet_id": wallet_id,
                "spendPolicyId": claim.spendPolicyId,
                "oracle_wallet_id": oracle_wallet_id,
                "metadata": metadata
            }
            redisclient = RedisClient()
            await redisclient.create_index(index_name)
            await redisclient.create_task(index_name, record)
            result = await redisclient.make_query(index_name, "@status:pending")
            redisclient.close()
            logging.info(result)





            ########################
            """Build transaction"""
            ########################

            chain_context = CardanoNetwork().get_chain_context()

            # Create a transaction builder
            builder = TransactionBuilder(chain_context)

            # Add user own address as the input address
            user_address = Address.from_primitive(userWalletInfo["address"])
            builder.add_input_address(user_address)  # I just commented this
            # utxo_to_spend = None
            # for utxo in chain_context.utxos(user_address):
            #     if utxo.output.amount.coin > 3_000_000:
            #         utxo_to_spend = utxo
            #         break
            # assert (
            #     utxo_to_spend is not None
            # ), "UTxO not found to spend! You must have a utxo with more than 3 ADA"

            # builder.add_input(utxo_to_spend)
            must_before_slot = InvalidHereAfter(
                chain_context.last_block_slot + 10000
            )
            # Since an InvalidHereAfter
            builder.ttl = must_before_slot.after

            # Get the contract address and cbor from policyId
            parent_mint_policyID = ""
            r = Plataforma().getScript("id", claim.spendPolicyId)
            script_response = Response().handle_getScript_response(r)
            scriptInfo = script_response.get("data", None)
            if not script_response["success"] and not scriptInfo:
                raise ResponseProcessingError("Script with policyId does not exist in database")

            testnet_address = scriptInfo.get("testnetAddr", None)
            cbor_hex = scriptInfo.get("cbor", None)
            parent_mint_policyID = scriptInfo.get("scriptParentID", None)
            tokenName = scriptInfo.get("token_name", None)

            metadata = {}
            if claim.metadata is not None and claim.metadata != {}:
                auxiliary_data, metadata = Helpers().build_metadata(claim.metadata)
                # Set transaction metadata
                if isinstance(auxiliary_data, AuxiliaryData):
                    builder.auxiliary_data = auxiliary_data
                else:
                    raise ValueError(auxiliary_data)

            quantity_request = 0
            addresses = claim.addresses
            script_hash = ScriptHash(bytes.fromhex(parent_mint_policyID))
            for address in addresses:
                multi_asset = Helpers().multiAssetFromAddress(address)
                if multi_asset:
                    quantity = multi_asset.data.get(script_hash, 0).data.get(
                        AssetName(bytes(tokenName, encoding="utf-8")), 0
                    )
                    if quantity > 0 and not address.datum:
                        quantity_request += quantity

                multi_asset_value = Value(0, multi_asset)

                # Calculate the minimum amount of lovelace that need to be transfered in the utxo
                min_val = min_lovelace(
                    chain_context,
                    output=TransactionOutput(
                        Address.decode(address.address),
                        multi_asset_value,
                    ),
                )
                if address.lovelace <= min_val:
                    builder.add_output(
                        TransactionOutput(
                            Address.decode(address.address),
                            Value(min_val, multi_asset),
                        )
                    )
                else:
                    builder.add_output(
                        TransactionOutput(
                            Address.decode(address.address),
                            Value(address.lovelace, multi_asset),
                        )
                    )

            # Redeemer action
            if claim_redeemer == "Buy":
                redeemer = pydantic_schemas.RedeemerBuy()
            elif claim_redeemer == "Sell":
                redeemer = pydantic_schemas.RedeemerSell()
            elif claim_redeemer == "Unlist":
                redeemer = pydantic_schemas.RedeemerUnlist()
            else:
                raise ValueError("Wrong redeemer")

            # Section to handle and calculate the script
            # Get script utxo to spend where tokens are located
            utxo_from_contract = []
            tn_bytes = bytes(tokenName, encoding="utf-8")
            # amount = quantity_request
            utxos_found = False

            # Find the utxo to spend
            for utxo in chain_context.utxos(testnet_address):

                def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
                    return (
                        pi == script_hash
                        and an.payload == tn_bytes
                        and a >= quantity_request
                    )

                if utxo.output.amount.multi_asset.count(f):
                    utxo_from_contract.append(utxo)
                    utxos_found = True
                    break

            if not utxo_from_contract:
                q = 0
                for utxo in chain_context.utxos(testnet_address):

                    def f1(pi: ScriptHash, an: AssetName) -> bool:
                        return pi == script_hash and an.payload == tn_bytes

                    if utxo.output.amount.multi_asset.count(f1):
                        utxo_from_contract.append(utxo)
                        union_multiasset = utxo.output.amount.multi_asset.data
                        for asset in union_multiasset.values():
                            q += int(list(asset.data.values())[0])
                        if q >= quantity_request:
                            utxos_found = True
                            break

            assert utxos_found, "UTxO not found to spend!"
            logging.info(
                f"Found utxos to spend: {[(utxo.input.transaction_id, str(utxo.input.index)) for utxo in utxo_from_contract]}"
            )

            # Find the balance and add the output to send tokens back to the contract
            balance = 0
            for x in utxo_from_contract:
                # builder.add_input(x)

                # Calculate the change of tokens back to the contract
                balance += x.output.amount.multi_asset.data.get(
                    script_hash, {b"": 0}
                ).get(AssetName(tn_bytes), {b"": 0})

                beneficiary = x.output.datum.cbor.hex()[10:-2]
                datum = Helpers().build_DatumProjectParams(pkh=beneficiary)
                cbor = bytes.fromhex(cbor_hex)
                plutus_script = PlutusV2Script(cbor)

                builder.add_script_input(
                    x, plutus_script, redeemer=Redeemer(redeemer)
                )

            new_token_balance = balance - quantity_request
            if new_token_balance < 0:
                raise ValueError("Not enough tokens found in script address")

            if new_token_balance > 0:
                multi_asset_to_contract = Helpers().build_multiAsset(
                    policy_id=parent_mint_policyID,
                    tq_dict={tokenName: new_token_balance},
                )
                multi_asset_value_to_contract = Value(0, multi_asset_to_contract)

                # Calculate the minimum amount of lovelace that need to be transfered in the utxo
                min_val = min_lovelace(
                    chain_context,
                    output=TransactionOutput(
                        Address.decode(testnet_address),
                        multi_asset_value_to_contract,
                        datum=datum,
                    ),
                )
                builder.add_output(
                    TransactionOutput(
                        Address.decode(testnet_address),
                        Value(min_val, multi_asset_to_contract),
                        datum=datum,
                    )
                )
            # End of the contract implementation

            oracle_utxo = Helpers().build_reference_input_oracle(
                chain_context, oracle_wallet_id
            )

            assert oracle_utxo is not None, "Oracle UTxO not found!"
            logging.info(
                f"Found oracle utxo: {oracle_utxo.input.transaction_id} and index: {oracle_utxo.input.index}"
            )
            builder.reference_inputs.add(oracle_utxo)

            pkh = bytes(user_address.payment_part)
            signatures = []
            signatures.append(VerificationKeyHash(pkh))
            builder.required_signers = signatures

            build_body = builder.build(change_address=user_address)
            tx_cbor = build_body.to_cbor_hex()
            # tmp_builder = deepcopy(builder)
            # redeemer_report = Redeemer(redeemer)
            redeemers = builder.redeemers()

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
                # utxo_list_info.append(utxo_details)
                # transaction_id = f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                # transaction_id_list.append(transaction_id)

            # utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

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
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e)) from e
    except ResponseProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
