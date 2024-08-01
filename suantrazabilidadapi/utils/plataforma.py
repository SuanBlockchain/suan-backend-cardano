import binascii
import json
import logging
import os
import pathlib
from dataclasses import dataclass
from typing import Optional, Union, Any, Dict
from types import SimpleNamespace as Namespace

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
)

# from blockfrost import ApiUrls, BlockFrostApi

from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.blockchain import Keys
from suantrazabilidadapi.utils.generic import Constants

plataformaSecrets = config(section="plataforma")
security = config(section="security")
environment = security["env"]


@dataclass()
class Plataforma(Constants):
    def __post_init__(self):
        if environment == "dev":
            self.graphqlEndpoint = os.getenv("endpoint_dev")
            self.awsAppSyncApiKey = os.getenv("graphql_key_dev")
        elif environment == "prod":
            self.graphqlEndpoint = os.getenv("endpoint_prod")
            self.awsAppSyncApiKey = os.getenv("graphql_key_prod")

        self.HEADERS["x-api-key"] = self.awsAppSyncApiKey
        self.S3_BUCKET_NAME = os.getenv("s3_bucket_name")
        self.S3_BUCKET_NAME_HIERARCHY = os.getenv("s3_bucket_name_hierarchy")
        self.AWS_ACCESS_KEY_ID = os.getenv("aws_access_key_id")
        self.AWS_SECRET_ACCESS_KEY = os.getenv("aws_secret_access_key")
        # self.GRAPHQL = "graphql/queries.graphql"
        self.GRAPHQL = self.PROJECT_ROOT.joinpath("graphql/queries.graphql")
        # self.BASE_URL = ApiUrls.preview.value
        # self.BLOCK_FROST_PROJECT_ID = plataformaSecrets["block_frost_project_id"]
        # self.BLOCKFROST_API = BlockFrostApi(
        #     project_id=self.BLOCK_FROST_PROJECT_ID, base_url=self.BASE_URL
        # )

    def _post(
        self, operation_name: str, graphql_variables: Union[dict, None] = None
    ) -> dict:
        with open(self.GRAPHQL, "r") as file:
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

    def getProject(self, command_name: str, query_param: str) -> dict:
        if command_name == "id":
            graphql_variables = {"projectId": query_param}

            data = self._post("getProjectById", graphql_variables)

        return data

    def listProjects(self) -> dict:
        return self._post("listProjects")

    def getWallet(self, command_name: str, query_param: str) -> dict:
        if command_name == "id":
            graphql_variables = {"walletId": query_param}

            data = self._post("getWalletById", graphql_variables)

        elif command_name == "address":
            graphql_variables = {"address": query_param}

            data = self._post("getWalletByAddress", graphql_variables)

        return data

    def getWalletbyToken(self) -> dict:
        return self._post("getWalletByToken")

    def listWallets(self) -> dict:
        return self._post("listWallets")

    def updateWalletWithToken(self, values) -> list[dict]:
        response = self._post("WalletTokenUpdate", values)
        return response

    def createWallet(self, values) -> list[dict]:
        response = self._post("WalletMutation", values)
        return response

    def createContract(self, values) -> list[dict]:
        response = self._post("ScriptMutation", values)
        return response

    def getScript(self, command_name: str, query_param: str) -> dict:
        if command_name == "id":
            graphql_variables = {"id": query_param}

            data = self._post("getScriptById", graphql_variables)

            return data

    def listScripts(self) -> dict:
        return self._post("listScripts")

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
        for root, dirs, files in os.walk(folder_path):
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


@dataclass()
class CardanoApi(Constants):
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

    def getAddressInfo(self, address: Union[str, list[str]]) -> list[dict]:
        # address_response = self.KOIOS_API.get_address_info(address)
        # asset_response = self.KOIOS_API.get_address_assets(address)

        # address_response1 = self.BLOCKFROST_API.address_total(address)
        # address_response2 = self.BLOCKFROST_API.address_transactions(address)
        address_response = self.BLOCKFROST_API.address(address, return_type="json")
        # address_response = self.BLOCKFROST_API.address_utxos(
        #     address, return_type="json"
        # )
        # address_response4 = self.BLOCKFROST_API.address_utxos_asset(address)
        print(address_response)

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

        return final_response

    def getUtxoInfo(self, txhash: str) -> list[dict]:
        utxo_info = self.BLOCKFROST_API.transaction_utxos(txhash, return_type="json")
        # utxo_info = self.KOIOS_API.get_utxo_info(utxo, extended)
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
        return self.BLOCKFROST_API.address_extended(address, return_type="json")

    def txStatus(self, txId: Union[str, list[str]]) -> list:
        status_response = self.KOIOS_API.get_tx_status(txId)

        return status_response

    def assetInfo(self, policy_id: str) -> list:
        asset_info = self.KOIOS_API.get_policy_asset_info(policy_id)

        return asset_info


@dataclass()
class Helpers:
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
        for utxo_in_context in context.utxos(address):
            if (
                utxo_in_context.input.transaction_id.payload.hex() == transaction_id
                and utxo_in_context.input.index == index
            ):
                utxo_existence = True
                utxo_is = utxo_in_context
                break

        return utxo_existence, utxo_is

    # def validate_utxos_existente1(
    #     self, context: ChainContext, address: Union[Address, str], utxo: str
    # ) -> tuple[bool, UTxO]:
    #     utxo_existence = False
    #     for utxo_in_context in context.utxos(address):
    #         if utxo_in_context.input.transaction_id.payload.hex() == utxo:
    #             utxo_existence = True
    #             utxo_is = utxo_in_context
    #             break

    #     return utxo_existence, utxo_is

    def build_oraclePolicyId(
        self, oracle_wallet_name: Optional[str] = "SuanOracle"
    ) -> str:
        # Recreate oracle policyId
        oracle_walletInfo = Keys().load_or_create_key_pair(oracle_wallet_name)
        pub_key_policy = ScriptPubkey(oracle_walletInfo[2].hash())
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
        oracle_token_name: str = Constants.ORACLE_TOKEN_NAME,
    ) -> Union[UTxO, None]:

        oracle_walletInfo = Keys().load_or_create_key_pair(Constants.ORACLE_WALLET_NAME)
        oracle_address = oracle_walletInfo[3]
        oracle_asset = self.build_multiAsset(
            policy_id=self.build_oraclePolicyId(Constants.ORACLE_WALLET_NAME),
            tq_dict={oracle_token_name: 1},
        )
        oracle_utxo = self.find_utxos_with_tokens(
            chain_context, oracle_address, multi_asset=oracle_asset
        )
        return oracle_utxo
