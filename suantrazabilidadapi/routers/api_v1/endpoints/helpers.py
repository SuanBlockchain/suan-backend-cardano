import binascii
import logging
from typing import Optional, Dict, Any

# import uuid
from cbor2 import loads
from fastapi import APIRouter, HTTPException
# import redis
# from redis.commands.search.query import Query
from pycardano import (
    Address,
    AssetName,
    Datum,
    HDWallet,
    InvalidHereAfter,
    MultiAsset,
    PaymentVerificationKey,
    ScriptAll,
    ScriptHash,
    ScriptPubkey,
    TransactionBuilder,
    TransactionOutput,
    Value,
    min_lovelace,
    ExtendedSigningKey,
)

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.utils.plataforma import Helpers, Plataforma, RedisClient
from suantrazabilidadapi.utils.response import Response
from suantrazabilidadapi.utils.exception import ResponseDynamoDBException, ResponseFindingUtxo


router = APIRouter()


@router.get(
    "/send-access-token/",
    status_code=201,
    summary="Get the token to access Suan Marketplace",
    response_description="Confirmation of token sent to provided address",
    # response_model=List[str],
)
async def sendAccessToken(
    wallet_id: str,
    destinAddress: str,
    marketplace_id: str,
    save_flag: bool = False,
):
    try:
        # Set generic variables
        scriptName = "NativeAccessToken"
        scriptCategory = "PlutusV2"
        script_type = "native"

        command_name = "getWalletById"

        graphql_variables = {"walletId": wallet_id}

        r = Plataforma().getWallet(command_name, graphql_variables)
        final_response = Response().handle_getWallet_response(getWallet_response=r)
        
        if not final_response["connection"] or not final_response.get("success", None):
            raise ResponseDynamoDBException(final_response["data"])
        
        walletInfo = final_response["data"]
        ########################
        """Obtain the payment sk and vk from the walletInfo"""
        ########################
        seed = walletInfo["seed"]
        hdwallet = HDWallet.from_seed(seed)
        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

        payment_vk = PaymentVerificationKey.from_primitive(
            child_hdwallet.public_key
        )
        pub_key_policy = ScriptPubkey(payment_vk.hash())
        policy = ScriptAll([pub_key_policy])
        # Calculate policy ID, which is the hash of the policy
        policy_id = policy.hash()
        policy_id_str = binascii.hexlify(policy_id.payload).decode("utf-8")

        ########################
        """Create the request in redis cache to be processed by the scheduler"""
        ########################
        # redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # rdb = redis.Redis.from_url(redis_url, decode_responses=True)
        token_string = "SandboxSuanAccess1"

        record = {
            "status": "pending",
            "destinAddress": destinAddress,
            "wallet_id": wallet_id,
            "token_string": token_string,
        }
        index_name = "AccessTokenIndex"
        redisclient = RedisClient()
        await redisclient.create_index(index_name)
        # key = str(uuid.uuid4())
        # rdb.json().set("AccessToken:" + key, "$", record)
        await redisclient.create_task(index_name, record)
        # query = Query("@status:pending")
        # result = rdb.ft(index_name).search(query)
        result = await redisclient.make_query(index_name, "@status:pending")
        redisclient.close()
        logging.info(result)

        ########################
        """3. Save the script if save_flag is true"""
        ########################
        if save_flag:
            variables = {
                "id": policy_id_str,
                "name": scriptName,
                "MainnetAddr": "na",
                "testnetAddr": "na",
                "cbor": "na",
                "pbk": wallet_id,
                "script_category": scriptCategory,
                "script_type": script_type,
                "Active": True,
                "token_name": token_string,
                "marketplaceID": marketplace_id,
            }

            responseWallet = Plataforma().createContract(graphql_variables)
            final_response = Response().handle_createContract_response(responseWallet)
            
            if not final_response["connection"] or not final_response.get("success", None):
                raise ResponseDynamoDBException(final_response["data"])
            
            r = Plataforma().createContract(variables)
            responseCreateScript = Response().handle_createContract_response(r)
            if not responseCreateScript["connection"] or not responseCreateScript.get("success", None):
                raise ResponseDynamoDBException(responseCreateScript["data"])
            
            final_response = {
                "success": True,
                "msg": "Token scheduled to be sent soon",
                "policy_id": policy_id_str,
                "tokenName": token_string,
            }
            # else:
            #     final_response = {
            #         "success": False,
            #         "msg": "Token scheduled to be sent soon but problems creating the script in dynamoDB",
            #         "data": responseCreateScript,
            #         "policy_id": policy_id_str,
            #         "tokenName": token_string,
            #     }
        else:
            final_response = {
                "success": True,
                "msg": "Token scheduled to be sent soon but script not saved in dynamoDB",
                "policy_id": policy_id_str,
                "tokenName": token_string,
            }

        return final_response

    except ResponseDynamoDBException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # Handling other types of exceptions
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/min-lovelace/",
    status_code=201,
    summary="Given utxo output details, obtain calculated min ADA required",
    response_description="Min Ada required for the utxo in lovelace",
)
async def minLovelace(addressDestin: pydantic_schemas.AddressDestin) -> int:
    """Min Ada required for the utxo in lovelace \n"""
    try:
        address = addressDestin.address

        # Get Multiassets
        multiAsset = None
        if addressDestin.multiAsset:
            for multiasset in addressDestin.multiAsset:
                policy_id = multiasset.policyid
                tokens = multiasset.tokens
                multiAsset = Helpers().build_multiAsset(
                    policy_id=policy_id, tq_dict=tokens
                )
        # Create Value type
        if multiAsset:
            amount = Value(addressDestin.lovelace, multiAsset)
        else:
            amount = Value(addressDestin.lovelace)

        datum = None
        if addressDestin.datum:
            datum = Datum(addressDestin.datum)

        output = TransactionOutput(address=address, amount=amount, datum=datum)

        chain_context = CardanoNetwork().get_chain_context()
        min_val = min_lovelace(chain_context, output)

        return min_val
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/tx-fee/",
    status_code=200,
    summary="Deserialized a transaction provided in cbor format to get the fee",
    response_description="Fee in lovelace",
)
async def getFeeFromCbor(txcbor: str) -> int:
    """Deserialized a transaction provided in cbor format to get the fee \n"""
    try:
        payload = bytes.fromhex(txcbor)
        value = loads(payload)
        if isinstance(value, list):
            fee = value[0][2]
        else:
            fee = value[2]

        return fee

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/oracle-datum/{action}",
    status_code=201,
    summary="Build and upload inline datum",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def oracleDatum(
    action: pydantic_schemas.OracleAction,
    oracle_data: pydantic_schemas.Oracle,
    core_wallet_id: str,
    oracle_wallet_id: Optional[str],
    oracle_token_name: Optional[str] = "SuanOracle",
) -> dict:
    try:

        command_name = "getWalletById"

        graphql_variables = {"walletId": core_wallet_id}

        # Check first that the core wallet to pay fees exists
        r = Plataforma().getWallet(command_name, graphql_variables)
        final_response = Response().handle_getWallet_response(getWallet_response=r)

        if not final_response["connection"] or not final_response.get("success", None):
            raise ResponseDynamoDBException(final_response["data"])


        coreWalletInfo = final_response["data"]

        # Get core wallet params
        seed = coreWalletInfo["seed"]
        hdwallet = HDWallet.from_seed(seed)
        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
        core_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)
        core_address = Address.from_primitive(coreWalletInfo["address"])

        graphql_variables = {"walletId": oracle_wallet_id}

        # Check first that the core wallet to pay fees exists
        r = Plataforma().getWallet(command_name, graphql_variables)
        oracleWalletResponse = Response().handle_getWallet_response(getWallet_response=r)

        if not final_response["connection"] or not final_response.get("success", None):
            raise ResponseDynamoDBException(final_response["data"])

        oracleWallet = oracleWalletResponse["data"]
        oracle_address = oracleWallet["address"]
        seed = oracleWallet["seed"]
        hdwallet = HDWallet.from_seed(seed)
        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

        oracle_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

        oracle_vkey = PaymentVerificationKey.from_primitive(
            child_hdwallet.public_key
        )

        chain_context = CardanoNetwork().get_chain_context()

        # Create a transaction builder
        builder = TransactionBuilder(chain_context)

        # Add core address as the input address
        builder.add_input_address(core_address)

        # Add oracle address as the input address
        oracle_address = Address.from_primitive(oracle_address)
        builder.add_input_address(oracle_address)

        must_before_slot = InvalidHereAfter(chain_context.last_block_slot + 10000)
        builder.ttl = must_before_slot.after

        ########################
        """3. Create the script and policy"""
        ########################
        # A policy that requires a signature from the policy key we generated above
        pub_key_policy = ScriptPubkey(oracle_vkey.hash())
        # Combine two policies using ScriptAll policy
        policy = ScriptAll([pub_key_policy])
        # Calculate policy ID, which is the hash of the policy
        policy_id = policy.hash()
        print(f"Policy ID: {policy_id}")
        with open(Constants().PROJECT_ROOT / "policy.id", "a+", encoding="utf-8") as f:
            f.truncate(0)
            f.write(str(policy_id))
        # Create the final native script that will be attached to the transaction
        native_scripts = [policy]

        # tokenName = b"SuanOracle"
        tokenName = bytes(oracle_token_name, encoding="utf-8")
        ########################
        """Define NFT"""
        ########################
        my_nft = MultiAsset.from_primitive(
            {
                policy_id.payload: {
                    tokenName: 1,
                }
            }
        )

        if action == "Create":
            builder.mint = my_nft
            # Set native script
            builder.native_scripts = native_scripts
            msg = f"{oracle_token_name} minted to store oracle data info in datum for Suan"
        else:
            oracle_utxo = None
            for utxo in chain_context.utxos(oracle_address):

                def f1(pi: ScriptHash, an: AssetName, a: int) -> bool:
                    return pi == policy_id and an.payload == tokenName and a == 1

                if utxo.output.amount.multi_asset.count(f1):
                    oracle_utxo = utxo

                    builder.add_input(oracle_utxo)

            msg = "Oracle datum updated"

            # Check if oracle_utxo exists and is found
            if not oracle_utxo:
                raise ResponseFindingUtxo(
                    f"Utxo for oracle token name {oracle_token_name} could not be found in {oracle_address}"
                )
        # Build the inline datum
        # precision = 14
        value_dict = {}
        for data in oracle_data.data:
            # policy_id = data.policy_id
            token_feed = pydantic_schemas.TokenFeed(
                tokenName=bytes(data.token, encoding="utf-8"), price=data.price
            )
            value_dict[bytes.fromhex(data.policy_id)] = token_feed

        datum = pydantic_schemas.DatumOracle(
            value_dict=value_dict,
            identifier=bytes.fromhex(str(oracle_vkey.hash())),
            validity=oracle_data.validity,
        )
        min_val = min_lovelace(
            chain_context,
            output=TransactionOutput(oracle_address, Value(0, my_nft), datum=datum),
        )
        builder.add_output(
            TransactionOutput(oracle_address, Value(min_val, my_nft), datum=datum)
        )

        signed_tx = builder.build_and_sign(
            [oracle_skey, core_skey], change_address=core_address
        )

        # Submit signed transaction to the network
        tx_id = signed_tx.transaction_body.hash().hex()
        chain_context.submit_tx(signed_tx)

        logging.info(f"transaction id: {tx_id}")
        logging.info(f"https://preview.cardanoscan.io/transaction/{tx_id}")

        ####################################################
        final_response = {
            "success": True,
            "msg": msg,
            "tx_id": tx_id,
            "oracle_id": oracle_wallet_id,
            "oracle_address": oracle_address.encode(),
            "cardanoScan": f"https://preview.cardanoscan.io/transaction/{tx_id}",
        }

        return final_response

    except ResponseFindingUtxo as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ResponseDynamoDBException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/send-metadata/{project_id}",
    status_code=201,
    summary="Build and upload inline datum",
    response_description="Response with transaction details and in cborhex format",
    # response_model=List[str],
)
async def sendMetadata(
    metadata: Dict[str, Any]
) -> dict:
    try:
        command_name = "getWalletAdmin"
        graphql_variables = {"isAdmin": True}
        listWallet_response = Plataforma().getWallet(command_name, graphql_variables)

        core_wallet = Response().handle_listWallets_response(listWallets_response=listWallet_response)

        if not core_wallet["connection"] or not core_wallet.get("success", None):
            raise ResponseDynamoDBException(core_wallet["data"])

        graphql_variables = {"walletId": core_wallet["data"]["items"][0]["id"]}
        
        r = Plataforma().getWallet("getWalletById", graphql_variables)
        final_response = Response().handle_getWallet_response(getWallet_response=r)

        if not final_response["connection"] or not final_response.get("success", None):
            raise ResponseDynamoDBException(final_response["data"])
        
        coreWalletInfo = final_response["data"]

        # Get core wallet params
        seed = coreWalletInfo["seed"]
        hdwallet = HDWallet.from_seed(seed)
        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
        core_skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)
        core_address = Address.from_primitive(coreWalletInfo["address"])

        
        return coreWalletInfo

    
    except ResponseDynamoDBException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e