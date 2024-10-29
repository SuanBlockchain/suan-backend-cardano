import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pycardano import (
    AlonzoMetadata,
    AuxiliaryData,
    Datum,
    DatumHash,
    ExtendedSigningKey,
    HDWallet,
    Metadata,
    NativeScript,
    PaymentVerificationKey,
    PlutusV1Script,
    PlutusV2Script,
    Redeemer,
    Transaction,
    TransactionBody,
    TransactionWitnessSet,
    VerificationKeyWitness,
    RedeemerMap,
    PlutusV3Script
)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.plataforma import Plataforma
from suantrazabilidadapi.utils.exception import ResponseDynamoDBException
from suantrazabilidadapi.utils.response import Response

router = APIRouter()


@router.post(
    "/sign-submit/",
    status_code=201,
    summary="Sign and submit transaction in cborhex format",
    response_description="Response with transaction submission confirmation",
)
async def sign_submit(signSubmit: pydantic_schemas.SignSubmit) -> dict:
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
                plutus_v3_scripts: List[PlutusV3Script] = []
                datums: Dict[DatumHash, Datum] = {}

                redeemers: List[Redeemer] = []
                if signSubmit.redeemers_cbor:
                    # Redeemer.from_cbor(redeemer_cbor)
                    # redeemers = Redeemer.from_cbor(bytes.fromhex(redeemer_cbor))
                    for redeemer_cbor in signSubmit.redeemers_cbor:
                        if redeemer_cbor is not None and redeemer_cbor != []:
                            redeemers = RedeemerMap.from_cbor(redeemer_cbor)
                            # redeemers.append(redeemer)
                if signSubmit.scriptIds:
                    for scriptId in signSubmit.scriptIds:
                        # Get the contract address and cbor from policyId
                        # Consultar en base de datos
                        command_name = "getScriptById"

                        graphql_variables = {"id": scriptId}

                        r = Plataforma().getScript(command_name, graphql_variables)
                        final_response = Response().handle_getScript_response(getWallet_response=r)

                        if not final_response["connection"] or not final_response.get("success", None):
                            raise ResponseDynamoDBException(final_response["data"])
                        
                        contractInfo = final_response["data"]

                        cbor_hex = contractInfo.get("cbor", None)

                        cbor = bytes.fromhex(cbor_hex)
                        plutus_v2_script = PlutusV2Script(cbor)
                        plutus_v2_scripts.append(plutus_v2_script)
                        # plutus_v3_script = PlutusV3Script(cbor)
                        # plutus_v3_scripts.append(plutus_v3_script)

                witness_set = TransactionWitnessSet(
                    vkey_witnesses=vk_witnesses,
                    native_scripts=native_scripts if native_scripts else None,
                    plutus_v1_script=plutus_v1_scripts if plutus_v1_scripts else None,
                    plutus_v2_script=plutus_v2_scripts if plutus_v2_scripts else None,
                    plutus_v3_script=plutus_v3_scripts if plutus_v3_scripts else None,
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
    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e)) from e
