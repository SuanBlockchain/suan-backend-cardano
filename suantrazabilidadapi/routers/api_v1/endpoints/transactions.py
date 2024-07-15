from itertools import chain
import logging
from copy import deepcopy
from typing import Dict, List, Optional

import opshin.prelude as oprelude
from fastapi import APIRouter, HTTPException
from pycardano import (
    Address,
    AlonzoMetadata,
    Asset,
    AssetName,
    AuxiliaryData,
    Datum,
    DatumHash,
    ExtendedSigningKey,
    HDWallet,
    InvalidHereAfter,
    Metadata,
    MultiAsset,
    NativeScript,
    PaymentVerificationKey,
    PlutusV1Script,
    PlutusV2Script,
    Redeemer,
    ScriptHash,
    Transaction,
    TransactionBody,
    TransactionBuilder,
    TransactionOutput,
    TransactionWitnessSet,
    Value,
    VerificationKeyHash,
    VerificationKeyWitness,
    min_lovelace,
    plutus_script_hash,
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
                            ),
                            price=address.datum.price,
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

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f"Tx Build",
                    "build_tx": format_body,
                    "cbor": str(build_body.to_cbor_hex()),
                    "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                }
        else:
            if r["success"] == True:
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", send.wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
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
                master_address = Address.from_primitive(walletInfo["address"])
                builder.add_input_address(master_address)

                pkh = bytes(master_address.payment_part)

                # Validate utxo
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
                    if r["data"].get("data", None) is not None:
                        contractInfo = r["data"]["data"]["getScript"]
                        if contractInfo is None:
                            raise ValueError(
                                f"Script with policyId does not exist in database"
                            )
                        else:
                            cbor_hex = contractInfo.get("cbor", None)
                            cbor = bytes.fromhex(cbor_hex)
                            plutus_script = PlutusV2Script(cbor)
                    else:
                        raise ValueError(f"Error fetching Script from database")

                    script_hash = plutus_script_hash(plutus_script)
                    logging.info(f"script_hash: {script_hash}")

                    # Redeemer action
                    if mint_redeemer == "Mint":
                        redeemer = pydantic_schemas.RedeemerMint()
                    elif mint_redeemer == "Burn":
                        redeemer = pydantic_schemas.RedeemerBurn()
                    else:
                        raise ValueError(f"Wrong redeemer")

                    builder.add_minting_script(
                        script=plutus_script, redeemer=Redeemer(redeemer)
                    )

                    mint_multiassets = MultiAsset.from_primitive(
                        {bytes(script_hash): tokens_bytes}
                    )

                    builder.mint = mint_multiassets

                    # If burn, insert the utxo that contains the asset
                    for tn_bytes, amount in tokens_bytes.items():
                        if amount < 0:
                            burn_utxo = None
                            candidate_burn_utxo = []
                            for utxo in chain_context.utxos(master_address):

                                def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
                                    return (
                                        pi == script_hash
                                        and an.payload == tn_bytes
                                        and a >= -amount
                                    )

                                if utxo.output.amount.multi_asset.count(f):
                                    burn_utxo = utxo

                                    builder.add_input(burn_utxo)

                            if not burn_utxo:
                                q = 0
                                for utxo in chain_context.utxos(master_address):

                                    def f1(
                                        pi: ScriptHash, an: AssetName, a: int
                                    ) -> bool:
                                        return (
                                            pi == script_hash and an.payload == tn_bytes
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
                tmp_builder = deepcopy(builder)
                redeemers = tmp_builder.redeemers

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f"Tx Mint Tokens",
                    "build_tx": format_body,
                    "cbor": str(tx_cbor),
                    "redeemer_cbor": Redeemer.to_cbor_hex(
                        redeemers[0]
                    ),  # Redeemers is a list, but assume that only 1 redeemer is passed
                    "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                }
        else:
            if r["success"] == True:
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/claim-tx/{claim_redeemer}",
    status_code=201,
    summary="Build the transaction off-chain for validation before signing",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def claimTx(
    claim_redeemer: pydantic_schemas.ClaimRedeem, claim: pydantic_schemas.Claim
) -> dict:
    try:
        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", claim.wallet_id)
        if r["data"].get("data", None) is not None:
            userWalletInfo = r["data"]["data"]["getWallet"]
            if userWalletInfo is None:
                raise ValueError(
                    f"Wallet with id: {claim.wallet_id} does not exist in DynamoDB"
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
                utxo_to_spend = None
                for utxo in chain_context.utxos(user_address):
                    if utxo.output.amount.coin > 3_000_000:
                        utxo_to_spend = utxo
                        break
                assert (
                    utxo_to_spend is not None
                ), "UTxO not found to spend! You must have a utxo with more than 3 ADA"

                builder.add_input(utxo_to_spend)
                must_before_slot = InvalidHereAfter(
                    chain_context.last_block_slot + 10000
                )
                # Since an InvalidHereAfter
                builder.ttl = must_before_slot.after

                # Get the contract address and cbor from policyId

                r = Plataforma().getScript("id", claim.spendPolicyId)
                if r["success"] == True:
                    contractInfo = r["data"]["data"]["getScript"]
                    if contractInfo is None:
                        raise ValueError(
                            f"Contract with id: {claim.spendPolicyId} does not exist in DynamoDB"
                        )
                    else:
                        testnet_address = contractInfo.get("testnetAddr", None)
                        cbor_hex = contractInfo.get("cbor", None)
                        parent_mint_policyID = contractInfo.get("scriptParentID", None)
                        tokenName = contractInfo.get("token_name", None)

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
                    raise ValueError(f"Wrong redeemer")

                # Section to handle and calculate the script
                # Get script utxo to spend where tokens are located
                utxo_from_contract = []
                tn_bytes = bytes(tokenName, encoding="utf-8")
                amount = quantity_request
                utxos_found = False

                # Find the utxo to spend
                for utxo in chain_context.utxos(testnet_address):

                    def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
                        return (
                            pi == script_hash and an.payload == tn_bytes and a >= amount
                        )

                    if utxo.output.amount.multi_asset.count(f):
                        utxo_from_contract.append(utxo)
                        utxos_found = True
                        break

                if utxo_from_contract == []:
                    q = 0
                    for utxo in chain_context.utxos(testnet_address):

                        def f1(pi: ScriptHash, an: AssetName, a: int) -> bool:
                            return pi == script_hash and an.payload == tn_bytes

                        if utxo.output.amount.multi_asset.count(f1):
                            utxo_from_contract.append(utxo)
                            union_multiasset = utxo.output.amount.multi_asset.data
                            for asset in union_multiasset.values():
                                q += int(list(asset.data.values())[0])
                            if q >= amount:
                                utxos_found = True
                                break

                    # if utxo.output.amount.coin >= 1_000_000:
                    #     utxo_from_contract = utxo
                    #     break
                assert utxos_found, "UTxO not found to spend!"
                logging.info(
                    f"Found utxos to spend: {[(utxo.input.transaction_id.to_cbor_hex(), str(utxo.input.index)) for utxo in utxo_from_contract]}"
                )

                # Find the balance and add the output to send tokens back to the contract
                balance = 0
                for x in utxo_from_contract:
                    # builder.add_input(x)

                    # Calculate the change of tokens back to the contract
                    balance += x.output.amount.multi_asset.data.get(
                        script_hash, {b"": 0}
                    ).get(AssetName(tn_bytes), {b"": 0})

                    beneficiary = x.output.datum.cbor.hex()
                    datum = Helpers().build_DatumProjectParams(pkh=beneficiary)
                    cbor = bytes.fromhex(cbor_hex)
                    plutus_script = PlutusV2Script(cbor)

                    # builder.add_script_input(
                    #     utxo_from_contract,
                    #     plutus_script,
                    #     redeemer=Redeemer(redeemer),
                    # )
                    builder.add_script_input(
                        x, plutus_script, redeemer=Redeemer(redeemer)
                    )

                new_token_balance = balance - quantity_request
                if new_token_balance < 0:
                    raise ValueError(f"Not enough tokens found in script address")
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

                oracle_utxo = Helpers().build_reference_input_oracle(chain_context)

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
                tmp_builder = deepcopy(builder)
                redeemers = tmp_builder.redeemers

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f"Tx Build",
                    "build_tx": format_body,
                    "cbor": str(tx_cbor),
                    "redeemer_cbor": Redeemer.to_cbor_hex(
                        redeemers[0]
                    ),  # Redeemers is a list, but assume that only 1 redeemer is passed
                    "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                    # "tx_id": str(signed_tx.id)
                }
        else:
            if r["success"] == True:
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                if r["success"] == True:
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
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f"Tx Build",
                    "build_tx": format_body,
                    "cbor": str(tx_cbor),
                    "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                }
        else:
            if r["success"] == True:
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/unlock-order/{order_side}",
    status_code=201,
    summary="Unlock order placed in swap contract",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def unlockOrder(
    order: pydantic_schemas.UnlockOrder, order_side: pydantic_schemas.ClaimRedeem
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
                if r["success"] == True:
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
                    raise ValueError(f"Wrong redeemer")

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

                oracle_utxo = Helpers().build_reference_input_oracle(chain_context)

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
                tmp_builder = deepcopy(builder)
                redeemers = tmp_builder.redeemers

                # Processing the tx body
                format_body = Plataforma().formatTxBody(build_body)

                transaction_id_list = []
                for utxo in build_body.inputs:
                    transaction_id = f"{utxo.to_cbor_hex()[6:70]}#{utxo.index}"
                    transaction_id_list.append(transaction_id)

                utxo_list_info = CardanoApi().getUtxoInfo(transaction_id_list, True)

                final_response = {
                    "success": True,
                    "msg": f"Tx Build",
                    "build_tx": format_body,
                    "cbor": str(tx_cbor),
                    "redeemer_cbor": Redeemer.to_cbor_hex(
                        redeemers[0]
                    ),  # Redeemers is a list, but assume that only 1 redeemer is passed
                    "metadata_cbor": metadata.to_cbor_hex() if metadata else "",
                    "utxos_info": utxo_list_info,
                    "tx_size": len(build_body.to_cbor()),
                    # "tx_id": str(signed_tx.id)
                }
        else:
            if r["success"] == True:
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/sign-submit/",
    status_code=201,
    summary="Sign and submit transaction in cborhex format",
    response_description="Response with transaction submission confirmation",
)
async def signSubmit(signSubmit: pydantic_schemas.SignSubmit) -> dict:
    try:
        ########################
        """1. Get wallet info"""
        ########################
        r = Plataforma().getWallet("id", signSubmit.wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
            if walletInfo is None:
                final_response = {
                    "success": True,
                    "msg": f"Wallet with id: {signSubmit.wallet_id} does not exist in DynamoDB",
                    "data": r["data"],
                }
            else:
                seed = walletInfo["seed"]
                hdwallet = HDWallet.from_seed(seed)
                child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

                payment_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

                payment_vk = PaymentVerificationKey.from_primitive(
                    child_hdwallet.public_key
                )

                ########################
                """2. Build transaction"""
                ########################
                cbor_hex = signSubmit.cbor
                tx_body = TransactionBody.from_cbor(cbor_hex)

                signature = payment_skey.sign(tx_body.hash())
                vk_witnesses = [VerificationKeyWitness(payment_vk, signature)]

                auxiliary_data: Optional[AuxiliaryData] = None
                native_scripts: List[NativeScript] = []
                plutus_v1_scripts: List[PlutusV1Script] = []
                plutus_v2_scripts: List[PlutusV2Script] = []
                datums: Dict[DatumHash, Datum] = {}

                redeemers: List[Redeemer] = []
                if signSubmit.redeemers_cbor:
                    for redeemer_cbor in signSubmit.redeemers_cbor:
                        if redeemer_cbor is not None and redeemer_cbor != []:
                            redeemer = Redeemer.from_cbor(bytes.fromhex(redeemer_cbor))
                            redeemers.append(redeemer)
                if signSubmit.scriptIds:
                    for scriptId in signSubmit.scriptIds:
                        r = Plataforma().getScript("id", scriptId)
                        if r["success"] == True:
                            contractInfo = r["data"]["data"]["getScript"]
                            if contractInfo is None:
                                raise ValueError(
                                    f"Contract with id: {scriptId} does not exist in DynamoDB"
                                )
                            else:
                                cbor_hex = contractInfo.get("cbor", None)

                                cbor = bytes.fromhex(cbor_hex)
                                plutus_v2_script = PlutusV2Script(cbor)
                                plutus_v2_scripts.append(plutus_v2_script)

                witness_set = TransactionWitnessSet(
                    vkey_witnesses=vk_witnesses,
                    native_scripts=native_scripts if native_scripts else None,
                    plutus_v1_script=plutus_v1_scripts if plutus_v1_scripts else None,
                    plutus_v2_script=plutus_v2_scripts if plutus_v2_scripts else None,
                    redeemer=redeemers if redeemers else None,
                    plutus_data=list(datums.values()) if datums else None,
                )

                if signSubmit.metadata_cbor:
                    metadata = Metadata.from_cbor(
                        bytes.fromhex(signSubmit.metadata_cbor)
                    )
                    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=metadata))

                signed_tx = Transaction(tx_body, witness_set, True, auxiliary_data)
                chain_context = CardanoNetwork().get_chain_context()
                chain_context.submit_tx(signed_tx.to_cbor())
                tx_id = tx_body.hash().hex()

                logging.info(f"transaction id: {tx_id}")
                logging.info(f"https://preview.cardanoscan.io/transaction/{tx_id}")

                final_response = {
                    "success": True,
                    "msg": "Tx submitted to the blockchain",
                    "tx_id": tx_id,
                    "cardanoScan": f"https://preview.cardanoscan.io/transaction/{tx_id}",
                }

        else:
            if r["success"] == True:
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
    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e))
