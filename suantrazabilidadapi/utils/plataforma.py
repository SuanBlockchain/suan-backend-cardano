import binascii
import json
import logging
import os
import pathlib
import uuid
from dataclasses import dataclass
from typing import Optional, Union, Any, Dict
from types import SimpleNamespace as Namespace
from blockfrost.utils import ApiError
from fastapi import HTTPException
from redis.asyncio import ConnectionPool, Redis
from redis.commands.search.query import Query
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.exceptions import ResponseError
from redis.commands.search.field import TextField

import boto3
import requests
from botocore.exceptions import ClientError
from pycardano import (
    Address,
    Asset,
    AssetName,
    ChainContext,
    MultiAsset,
    ScriptAll,
    ScriptHash,
    ScriptPubkey,
    TransactionBody,
    UTxO,
    AuxiliaryData,
    Metadata,
    AlonzoMetadata,
    HDWallet,
    PaymentVerificationKey,
    StakeVerificationKey,
    Network,
    ExtendedSigningKey
)

# from blockfrost import ApiUrls, BlockFrostApi

from pycardano.key import Key
from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
# from suantrazabilidadapi.utils.blockchain import Keys
from suantrazabilidadapi.utils.generic import Constants
from suantrazabilidadapi.utils.response import Response
from suantrazabilidadapi.utils.exception import ResponseDynamoDBException

plataformaSecrets = config(section="plataforma")
security = config(section="security")
optional = config(section="optional")
environment = security["env"]


@dataclass()
class Plataforma(Constants):
    """Class representing all the methods to interact with Plataforma"""

    def __post_init__(self):
        if environment == "internal":
            self.graphqlEndpoint = os.getenv("endpoint_internal")
            self.awsAppSyncApiKey = os.getenv("graphql_key_internal")
        elif environment == "dev":
            self.graphqlEndpoint = os.getenv("endpoint_dev")
            self.awsAppSyncApiKey = os.getenv("graphql_key_dev")
        elif environment == "prod":
            self.graphqlEndpoint = os.getenv("endpoint_prod")
            self.awsAppSyncApiKey = os.getenv("graphql_key_prod")

        self.HEADERS["x-api-key"] = self.awsAppSyncApiKey

        self.GRAPHQL = self.PROJECT_ROOT.joinpath("graphql/queries.graphql")
        # Section for Oracle queries
        # self.oracleGraphqlEndpoint = os.getenv("oracle_endpoint")
        # self.oracleAwsAppSyncApiKey = os.getenv("oracle_graphql_key")
        # self.ORACLE_GRAPHQL = self.PROJECT_ROOT.joinpath("graphql/oracle_queries.graphql")

    def _post(
        self, operation_name: str, graphql_variables: Union[dict, None] = None, application: str = ""
    ) -> dict:
        
        if application == "oracle":
            self.graphqlEndpoint = os.getenv("oracle_endpoint")
            self.awsAppSyncApiKey = os.getenv("oracle_graphql_key")
            self.GRAPHQL = self.PROJECT_ROOT.joinpath("graphql/oracle_queries.graphql")


        self.HEADERS["x-api-key"] = self.awsAppSyncApiKey
        with open(self.GRAPHQL, "r", encoding="utf-8") as file:
            graphqlQueries = file.read()
        try:
            rawResult = requests.post(
                self.graphqlEndpoint,
                json={
                    "query": graphqlQueries,
                    "operationName": operation_name,
                    "variables": graphql_variables,
                },
                headers=self.HEADERS,
                timeout=10
            )
            rawResult.raise_for_status()
            data = json.loads(rawResult.content.decode("utf-8"))
            response = {"success": True, "data": data}

        except requests.exceptions.RequestException as e:
            # Handle any exceptions that occur during the request
            response = {"success": False, "error": str(e)}

        return response

    def _nullDict(self, dictionary: dict) -> dict:
        for k, v in dictionary.items():
            if v is None:
                dictionary[k] = ""

        return dictionary

    def genericGet(self, operation_name: str, query_param: str, application: str = "") -> dict:

        data = self._post(operation_name, query_param, application)

        return data
    
    def getProject(self, command_name: str, query_param: str) -> dict:
        data = {}
        if command_name == "id":
            graphql_variables = {"projectId": query_param}

            data = self._post("getProjectById", graphql_variables)

        return data

    def listProjects(self) -> dict:
        return self._post("listProjects")

    #TODO: Function to be decomissioned in the future. Move to genericGet
    def getWallet(self, command_name: str, graphql_variables: dict) -> dict:

        data = self._post(command_name, graphql_variables)

        return data

    def listWallets(self) -> dict:
        return self._post("listWallets")

    def generateWallet(self, mnemonic_words) -> tuple[str, str, ExtendedSigningKey, Key, Address, Address]:

        hdwallet = HDWallet.from_mnemonic(mnemonic_words)

        child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
        skey = ExtendedSigningKey.from_hdwallet(child_hdwallet)

        payment_verification_key = PaymentVerificationKey.from_primitive(
            child_hdwallet.public_key
        )
        staking_verification_key = StakeVerificationKey.from_primitive(
            child_hdwallet.public_key
        )
        pkh = payment_verification_key.hash()
        address = Address(
            payment_part=pkh,
            staking_part=staking_verification_key.hash(),
            network=Network.TESTNET,
        )
        stake_address = Address(
            payment_part=None,
            staking_part=staking_verification_key.hash(),
            network=Network.TESTNET,
        )

        wallet_id = binascii.hexlify(pkh.payload).decode("utf-8")

        seed = binascii.hexlify(hdwallet._seed).decode("utf-8")  # pylint: disable=protected-access

        return wallet_id, seed, skey, payment_verification_key, address, stake_address

    def createWallet(self, values, mutation_type: str) -> list[dict]:

        operation_name = "WalletMutation" if mutation_type == "user" else "WalletMutationWithouttUserID"

        response = self._post(operation_name, values)
        return response

    def createContract(self, values: dict) -> list[dict]:
        response = self._post("ScriptMutation", values)
        return response

    #TODO: Function to be decomissioned in the future. Move to genericGet
    def getScript(self, command_name: str, graphql_variables: str) -> dict:

        data = self._post(command_name, graphql_variables)

        return data

    def listScripts(self) -> dict:
        return self._post("listScripts")

    def listMarketplaces(self, command_name: str, query_param: str) -> dict:
        if command_name == "oracleWalletID":
            graphql_variables = {"oracleWalletID": query_param}

            data = self._post("getMarketplaceByOracle", graphql_variables)

            return data

    def formatTxBody(self, txBody: TransactionBody) -> dict:
        """_summary_

        Args:
            txBody (TransactionBody): _description_

        Returns:
            dict: dictionary with transaction body fields formatted
        """
        # Format inputs
        utxoInputs = {
            index: f"{input.transaction_id.payload.hex()}#{input.index}"
            for index, input in enumerate(txBody.inputs)
        }

        # Format outputs
        utxoOutputs = {}
        for index, output in enumerate(txBody.outputs):
            multi_asset = {}
            for k, v in output.amount.multi_asset.data.items():
                assets = {
                    assetName.payload: value for assetName, value in v.data.items()
                }
                multi_asset[k.to_cbor_hex()[4:]] = assets

            utxoOutputs[index] = {
                "address": output.address.encode(),
                "amount": {"coin": output.amount.coin, "multi_asset": multi_asset},
                "lovelace": output.lovelace,
                "script": output.script,
                # "datum": datum_dict,
                # "datum_hash": output.datum_hash,
            }

        utxoOutputs = {k: self._nullDict(v) for k, v in utxoOutputs.items()}

        # Format mint
        mint_assets = {}
        if txBody.mint:
            for k, v in txBody.mint.data.items():
                mint_asset = {
                    assetName.payload: value for assetName, value in v.data.items()
                }
                mint_assets[k.to_cbor_hex()[4:]] = mint_asset

        # Format signers
        signersOutput = []
        if txBody.required_signers:
            signersOutput = [
                signers.payload.hex() for signers in txBody.required_signers
            ]

        collateral = {}
        if txBody.collateral:
            collateral = {
                index: f"{input.transaction_id.payload.hex()}#{input.index}"
                for index, input in enumerate(txBody.collateral)
            }

        collateral_return = {}
        if txBody.collateral_return:
            collateral_multi_asset = {}
            for k, v in txBody.collateral_return.amount.multi_asset.data.items():
                collateral_assets = {
                    assetName.payload: value for assetName, value in v.data.items()
                }
                collateral_multi_asset[k.to_cbor_hex()[4:]] = collateral_assets

            collateral_return = {
                "address": txBody.collateral_return.address.encode(),
                "amount": {
                    "coin": txBody.collateral_return.amount.coin,
                    "multi_asset": collateral_multi_asset,
                },
                "lovelace": txBody.collateral_return.lovelace,
                "script": txBody.collateral_return.script,
                "datum": txBody.collateral_return.datum,
                "datum_hash": txBody.collateral_return.datum_hash,
            }

            collateral_return = self._nullDict(collateral_return)

        referenceInputs = {}
        if txBody.reference_inputs:
            # Format if reference inputs exits
            referenceInputs = {
                index: f"{reference_input.transaction_id.payload.hex()}#{reference_input.index}"
                for index, reference_input in enumerate(txBody.reference_inputs)
            }

        script_data_hash = ""
        if txBody.script_data_hash:
            script_data_hash = txBody.script_data_hash.payload.hex()

        formatTxBody = {
            "auxiliary_data_hash": (
                txBody.auxiliary_data_hash.payload.hex()
                if txBody.auxiliary_data_hash
                else ""
            ),
            "certificates": txBody.certificates,
            "collateral": collateral,
            "collateral_return": collateral_return,
            "fee": txBody.fee,
            "tx_id": txBody.id.payload.hex(),
            "inputs": utxoInputs,
            "outputs": utxoOutputs,
            "mint": mint_assets,
            "network_id": txBody.network_id,
            "reference_inputs": referenceInputs,
            "required_signers": signersOutput,
            "script_data_hash": script_data_hash,
            "total_collateral": txBody.total_collateral,
            "ttl": txBody.ttl,
            "update": txBody.update,
            "validity_start": txBody.validity_start,
            "withdraws": txBody.withdraws,
        }

        formatTxBody = self._nullDict(formatTxBody)

        return formatTxBody

    def _initializeBoto2Client(self):
        # Upload the file
        return boto3.client(
            "s3",
            region_name=self.REGION_NAME,
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
        )

    def list_files(self, folder_path="") -> list:
        s3_client = self._initializeBoto2Client()
        try:
            response = s3_client.list_objects_v2(
                Bucket=self.S3_BUCKET_NAME, Prefix=folder_path
            )

            # Extract file information from the response
            files = []
            for obj in response.get("Contents", []):
                files.append(obj["Key"])

            return files

        except Exception as e:
            print(f"Error listing files in S3 bucket: {e}")
            return []

    def read_file(self, file_name: str) -> dict:
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :return: True if file was uploaded, else False
        """

        # Upload the file
        s3_client = self._initializeBoto2Client()
        try:
            response = s3_client.get_object(
                Bucket=self.S3_BUCKET_NAME,
                Key=f"{self.S3_BUCKET_NAME_HIERARCHY}/{file_name}",
            )
            content = response["Body"].read().decode("utf-8")
            return {"success": True, "content": content}

        except Exception as e:
            logging.error(e)
            return {"success": False, "error": str(e)}

    def upload_file(self, file_path: pathlib.Path) -> bool:
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :return: True if file was uploaded, else False
        """
        s3_client = self._initializeBoto2Client()
        try:
            s3_client.upload_file(
                file_path,
                self.S3_BUCKET_NAME,
                f"{self.S3_BUCKET_NAME_HIERARCHY}/{file_path.name}",
            )
        except ClientError as e:
            logging.error(e)
            return False
        return True

    def upload_folder(self, folder_path) -> dict:
        s3_client = self._initializeBoto2Client()
        uploaded = []
        error = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                local_file_path = os.path.join(root, file)
                file_name = os.path.relpath(local_file_path, folder_path).replace(
                    "\\", "/"
                )
                folder = root.split("/")
                folder = os.path.join(folder[-2], folder[-1])
                s3_key = os.path.join(self.S3_BUCKET_NAME_HIERARCHY, file_name)

                try:
                    s3_client.upload_file(local_file_path, self.S3_BUCKET_NAME, s3_key)
                    uploaded.append(file_name)
                    print(
                        f"Uploaded {file_name} to S3://{self.S3_BUCKET_NAME}/{s3_key}"
                    )
                except Exception as e:
                    error.append(file_name)
                    print(f"Error uploading {local_file_path} to S3: {e}")

        return {"uploaded": uploaded, "error": error}

    #TODO: Function to be decomissioned in the future. Move to genericGet
    def getConsultaApiByIdAndVerificado(self, command_name: str, graphql_variables: dict) -> dict:

        data = self._post(command_name, graphql_variables, application="oracle")

        return data
    
    #TODO: Function to be decomissioned in the future. Move to genericGet
    def getMerkleTree(self, command_name: str, graphql_variables: dict) -> dict:

        data = self._post(command_name, graphql_variables, application="oracle")

        return data

    def createMerkleTree(self, values: dict) -> list[dict]:
        response = self._post("createMerkleTree", values, application="oracle")
        return response

@dataclass()
class CardanoApi(Constants):
    """Class with endpoints to interact with the blockchain"""

    def __post_init__(self):
        pass

    def _namespace_to_dict(self, obj):
        if isinstance(obj, list):
            return [self._namespace_to_dict(item) for item in obj]
        elif isinstance(obj, Namespace):
            return {
                key: self._namespace_to_dict(value) for key, value in vars(obj).items()
            }
        else:
            return obj

    def getTip(self) -> dict:
        try:
            return self.BLOCKFROST_API.block_latest(return_type="json")
        
        except ApiError as e:
            return {
                "error": f"Unexpected error: {e.status_code} - {e.error}: {e.message}"
            }

    def getAddressInfo(self, address: str) -> list[dict]:
        try:
            address_response = self.BLOCKFROST_API.address(address, return_type="json")

            final_response = {
                "address": address_response["address"],
                "stake_address": address_response["stake_address"],
                "script_address": address_response["script"],
            }

            # # Group data2 by "address" key
            assets = []
            for amount in address_response["amount"]:
                unit = amount["unit"]
                if amount["unit"] == "lovelace":
                    final_response["balance"] = amount["quantity"]
                else:  # unit != "lovelace":
                    policy_id = unit[:56]
                    name_bytes = unit[56:]
                    assets.append(
                        {
                            "policy_id": policy_id,
                            "asset_name": bytes.fromhex(name_bytes).decode("utf-8"),
                            "quantity": amount["quantity"],
                        }
                    )

            final_response["assets"] = assets

        except ApiError as e:

            if e.status_code == 404:
                return {"error": "The address has never been used."}
            else:
                return {
                    "error": f"Unexpected error: {e.status_code} - {e.error}: {e.message}"
                }

        return final_response

    def getUtxoInfo(self, txhash: str) -> list[dict]:
        utxo_info = self.BLOCKFROST_API.transaction_utxos(txhash, return_type="json")
        return utxo_info

    def getAddressTxs(
        self,
        address: str,
        from_block: str,
        to_block: str,
        page_number: int,
        limit: int,
    ) -> list[dict]:
        transactions = self.BLOCKFROST_API.address_transactions(
            address=address,
            from_block=from_block,
            to_block=to_block,
            return_type="json",
            count=limit,
            page=page_number,
            order="desc",
        )
        final_response = []
        for transaction in transactions:
            tx_hash = transaction["tx_hash"]
            trx = self.BLOCKFROST_API.transaction_utxos(tx_hash, return_type="json")
            if trx:
                trx_details = self.BLOCKFROST_API.transaction(
                    tx_hash, return_type="json"
                )
                metadata = self.BLOCKFROST_API.transaction_metadata(
                    tx_hash, return_type="json"
                )
                fees = trx_details["fees"]
                size = trx_details["size"]
                trx["fees"] = fees
                trx["size"] = size
                trx["metadata"] = metadata
                trx["block_height"] = transaction["block_height"]
                trx["block_time"] = transaction["block_time"]

            final_response.append(trx)

        return final_response

    def getAddressUtxos(self, address: str, page_number: int, limit: int) -> list[dict]:
        """Get a list of all UTxOs currently present in the provided address \n

        Args:
            address (str): Bech32 address
            page_number (int, optional): The page number for listing the results. Defaults to 1.
            limit (int, optional): The number of results displayed on one page. Defaults to 10.

        Returns:
            list[dict]: list of utxos
        """
        return self.BLOCKFROST_API.address_utxos(
            address, return_type="json", count=limit, page=page_number
        )

    def getAddressDetails(
        self,
        address: str,
    ) -> dict:

        try:
            return self.BLOCKFROST_API.address_extended(address, return_type="json")
        except ApiError as e:

            if e.status_code == 404:
                return {"error": "The address has never been used."}
            else:
                return {
                    "error": f"Unexpected error: {e.status_code} - {e.error}: {e.message}"
                }

    def assetInfo(self, policy_id: str) -> list:
        asset_list = self.BLOCKFROST_API.assets_policy(policy_id, return_type="json")

        asset_details_list = []
        for asset in asset_list:
            asset_name = asset.get("asset", "")
            asset_details = self.BLOCKFROST_API.asset(asset_name, return_type="json")
            asset_details_list.append(asset_details)

        return asset_details_list


@dataclass()
class Helpers:
    """Class with generic methods to convert datatypes and parse data"""

    def __post_init__(self):
        pass

    def multiAssetFromAddress(
        self, addressesDestin: pydantic_schemas.AddressDestin
    ) -> Optional[MultiAsset]:
        # TODO: deprecated. use build_multiAsset
        multi_asset = None
        if addressesDestin:
            multi_asset = MultiAsset()
            if addressesDestin.multiAsset:
                for asset in addressesDestin.multiAsset:
                    policy_id = asset.policyid
                    my_asset = Asset()
                    for name, quantity in asset.tokens.items():
                        my_asset.data.update({AssetName(name.encode()): quantity})
                    multi_asset[ScriptHash(bytes.fromhex(policy_id))] = my_asset

        return multi_asset

    def build_multiAsset(self, policy_id: str, tq_dict: dict) -> MultiAsset:
        multi_asset = MultiAsset()
        my_asset = Asset()
        for tokenName, quantity in tq_dict.items():
            my_asset.data.update(
                {AssetName(bytes(tokenName, encoding="utf-8")): quantity}
            )
        multi_asset[ScriptHash(bytes.fromhex(policy_id))] = my_asset

        return multi_asset

    def build_DatumProjectParams(self, pkh: str) -> pydantic_schemas.DatumProjectParams:
        datum = pydantic_schemas.DatumProjectParams(beneficiary=bytes.fromhex(pkh))
        return datum

    def find_utxos_with_tokens(
        self,
        context: ChainContext,
        address: Union[Address, str],
        multi_asset: MultiAsset,
    ) -> Union[UTxO, None]:
        candidate_utxo = None
        if isinstance(address, Address):
            address = address.encode()

        # TODO: acummulate utxos with tokens when there's more than one utxo and the request cannot be fulfill with just one
        for policy_id, asset in multi_asset.data.items():
            for tn_bytes, amount in asset.data.items():
                for utxo in context.utxos(address):

                    def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
                        return (
                            pi == policy_id
                            and an.payload == tn_bytes.payload
                            and a >= amount
                        )

                    if utxo.output.amount.multi_asset.count(f):
                        candidate_utxo = utxo
                        break

                assert isinstance(
                    candidate_utxo, UTxO
                ), "Not enough tokens found in Utxo"

        return candidate_utxo

    def validate_utxos_existente(
        self,
        context: ChainContext,
        address: Union[Address, str],
        transaction_id: str,
        index: int,
    ) -> tuple[bool, UTxO]:
        utxo_existence = False
        utxo_is = None
        utxos = context.utxos(address)
        logging.info(f"utxos: {utxos}")
        for utxo_in_context in context.utxos(address):
            if (
                utxo_in_context.input.transaction_id.payload.hex() == transaction_id
                and utxo_in_context.input.index == index
            ):
                utxo_existence = True
                utxo_is = utxo_in_context
                break

        return utxo_existence, utxo_is

    def build_oraclePolicyId(
        self, oracle_vkey: PaymentVerificationKey
    ) -> str:
        # Recreate oracle policyId
        # oracle_walletInfo = Keys().load_or_create_key_pair(oracle_wallet_name)
        pub_key_policy = ScriptPubkey(oracle_vkey.hash())
        # Combine two policies using ScriptAll policy
        policy = ScriptAll([pub_key_policy])
        # Calculate policy ID, which is the hash of the policy
        oracle_policy_id = binascii.hexlify(policy.hash().payload).decode("utf-8")

        return oracle_policy_id

    def build_metadata(
        self, metadata: Dict[str, Dict[str, Any]]
    ) -> tuple[Union[AuxiliaryData, str], Metadata]:
        # https://github.com/cardano-foundation/CIPs/tree/master/CIP-0020
        main_key = int(list(metadata.keys())[0])
        metadata_f = {}
        if not isinstance(main_key, int):
            auxiliary_data = "Metadata is not enclosed by an integer index"
        else:
            metadata_f = Metadata({main_key: metadata[str(main_key)]})
            auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=metadata_f))
        # Set transaction metadata

        return auxiliary_data, metadata_f

    def build_reference_input_oracle(
        self,
        chain_context: ChainContext,
        oracle_wallet_id: str
    ) -> Union[UTxO, None]:
        try:
            oracle_utxo = None
            
            command_name = "getWalletById"

            graphql_variables = {"walletId": oracle_wallet_id}

            r = Plataforma().getWallet(command_name, graphql_variables)
            final_response = Response().handle_getWallet_response(getWallet_response=r)
            
            if not final_response["connection"] or not final_response.get("success", None):
                raise ResponseDynamoDBException(final_response["data"])
            

            oracleWallet = final_response["data"]
            oracle_address = oracleWallet["address"]

            seed = oracleWallet["seed"]
            hdwallet = HDWallet.from_seed(seed)
            child_hdwallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")

            oracle_vkey = PaymentVerificationKey.from_primitive(
                child_hdwallet.public_key
            )

            # Get the oracle token name

            response = Plataforma().listMarketplaces("oracleWalletID", oracle_wallet_id)
            marketplaceResponse = Response().handle_listMarketplaces_response(response)

            if not final_response["connection"] or not final_response.get("success", None):
                raise ResponseDynamoDBException(final_response["data"])
            
            marketplaceInfo = marketplaceResponse["data"]

            oracle_token_name = marketplaceInfo["oracleTokenName"]

            oracle_asset = self.build_multiAsset(
                policy_id=self.build_oraclePolicyId(oracle_vkey),
                tq_dict={oracle_token_name: 1},
            )
            oracle_utxo = self.find_utxos_with_tokens(
                chain_context, oracle_address, multi_asset=oracle_asset
            )
                
            return oracle_utxo
        except ResponseDynamoDBException as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            # Handling other types of exceptions
            raise HTTPException(status_code=500, detail=str(e)) from e

@dataclass()
class RedisClient:
    """Class to handle data from and to Redis DB"""

    def __post_init__(self):
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.pool = ConnectionPool.from_url(self.REDIS_URL, decode_responses=True)
        self.schemas = self._initialize_schemas()
        self.rdb = Redis(connection_pool=self.pool)

    def _initialize_schemas(self):
        # Define multiple schemas in a dictionary
        return {
            "AccessToken": (
                TextField("$.action", as_name="action"),
                TextField("$.status", as_name="status"),
                TextField("$.destinAddress", as_name="destinAddress"),
                TextField("$.wallet_id", as_name="wallet_id"),
                TextField("$.token_string", as_name="token_string"),
            ),
            "MultipleContractBuy": (
                TextField("$.action", as_name="action"),
                TextField("$.status", as_name="status"),
                TextField("$.destinAddress", as_name="destinAddress"),
                TextField("$.wallet_id", as_name="wallet_id"),
                TextField("$.spendPolicyId", as_name="spendPolicyId"),
            ),
            # Add more schemas here as needed
        }

    # async def get_connection(self):
    #     return Redis(connection_pool=self.pool)

    async def close(self):
        await self.pool.disconnect()

    async def create_index(self, index_name):
        # rdb = await self.get_connection()
        schema = self.schemas.get(index_name)
        if not schema:
            logging.error(f"Schema for {index_name} not found.")
            return
        try:
            # Check if the index already exists
            index_info = await self.rdb.ft(index_name).info()
            if index_info.get("index_name") == index_name:
                logging.info(f"Index {index_name} already exists.")
                return
        except ResponseError as e:
            if "Unknown index name" in e.args[0]:
                # If the index does not exist, create it
                definition = IndexDefinition(prefix=[f"{index_name}:"], index_type=IndexType.JSON)
                await self.rdb.ft(index_name).create_index(schema, definition=definition)
                print(f"Index {index_name} created successfully.")

    async def create_task(self, index_name: str, record: dict):
        key = f"{index_name}:{str(uuid.uuid4())}"
        # rdb = await self.get_connection()
        await self.rdb.json().set(key, "$", record)
        logging.info(f"Task created with key: {key}")

    async def make_query(self, index_name: str, query_string: str):
        query = Query(query_string)
        # rdb = await self.get_connection()
        return self.rdb.ft(index_name).search(query)
