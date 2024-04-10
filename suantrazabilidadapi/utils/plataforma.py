
from dataclasses import dataclass
import requests
import os
import json
from typing import Union, Optional
from botocore.exceptions import ClientError
import boto3
import logging
import pathlib

from pycardano import TransactionBody, MultiAsset, Asset, AssetName, ScriptHash, ChainContext, Address, UTxO

from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.generic import Constants

# @dataclass()
# class Start:
#     headers = {'Content-Type': 'application/json'}
#     ROOT = pathlib.Path(__file__).resolve().parent.parent
#     plataformaSecrets = config(section="plataforma")
#     security = config(section="security")

plataformaSecrets = config(section="plataforma")
security = config(section="security")

@dataclass()
class Plataforma(Constants):

    def __post_init__(self):
        self.graphqlEndpoint = os.getenv('endpoint')
        self.awsAppSyncApiKey = os.getenv('graphql_key')
        self.HEADERS["x-api-key"] = self.awsAppSyncApiKey
        # koios_api_module = importlib.import_module("koios_api")
        # self.koios_api = koios_api_module
        self.S3_BUCKET_NAME = os.getenv('s3_bucket_name')
        self.S3_BUCKET_NAME_HIERARCHY = os.getenv('s3_bucket_name_hierarchy')
        self.AWS_ACCESS_KEY_ID = os.getenv('aws_access_key_id')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('aws_secret_access_key')
        # self.GRAPHQL = "graphql/queries.graphql"
        self.GRAPHQL = self.PROJECT_ROOT.joinpath("graphql/queries.graphql")

    def _post(self, operation_name: str, graphql_variables: Union[dict, None] = None) -> dict:

        with open(self.GRAPHQL, 'r') as file:
            graphqlQueries = file.read()
        try:
            rawResult = requests.post(
                self.graphqlEndpoint,
                json={"query": graphqlQueries, "operationName": operation_name, "variables": graphql_variables},
                headers=self.HEADERS
            )
            rawResult.raise_for_status()
            data = json.loads(rawResult.content.decode("utf-8"))
            response = {
                "success": True,
                "data": data
            }
        
        except requests.exceptions.RequestException as e:
            # Handle any exceptions that occur during the request
            response = {
                "success": False,
                "error": str(e)
            }
        
        return response

    def _nullDict(self, dictionary: dict) -> dict:

        for k, v in dictionary.items():
            if v is None:
                dictionary[k] = ""

        return dictionary

    def getProject(self, command_name: str, query_param: str) -> dict:

        if command_name == "id":
            graphql_variables = {
                "projectId": query_param
            }

            data = self._post('getProjectById', graphql_variables)

        return data
    
    def listProjects(self) -> dict:
        return self._post('listProjects')
    def getWallet(self, command_name: str, query_param: str) -> dict:

        if command_name == "id":
            graphql_variables = {
                "walletId": query_param
            }

            data = self._post('getWalletById', graphql_variables)

        elif command_name == "address":
            graphql_variables = {
                "address": query_param
            }

            data = self._post("getWalletByAddress", graphql_variables)

        return data
    
    def listWallets(self) -> dict:
        return self._post('listWallets')
    
    def createWallet(self, values) -> list[dict]:

        response = self._post('WalletMutation', values)
        return response
    
    def createContract(self, values) -> list[dict]:

        response = self._post('ScriptMutation', values)
        return response

    def getScript(self, command_name: str, query_param: str) -> dict:

        if command_name == "id":

            graphql_variables = {
                "id": query_param
            }

            data = self._post('getScriptById', graphql_variables)

            return data

    def listScripts(self) -> dict:
        return self._post('listScripts')

    def formatTxBody(self, txBody: TransactionBody) -> dict:
        """_summary_

        Args:
            txBody (TransactionBody): _description_

        Returns:
            dict: dictionary with transaction body fields formatted
        """
        # Format inputs
        utxoInputs = { index: f'{input.transaction_id.payload.hex()}#{input.index}' for index, input in enumerate(txBody.inputs)}

        # Format outputs
        utxoOutputs = {}
        for index, output in enumerate(txBody.outputs):
            
            multi_asset = {}
            for k, v in output.amount.multi_asset.data.items():
                assets = { assetName.payload: value for assetName, value in v.data.items()}
                multi_asset[k.to_cbor_hex()[4:]] = assets
            # datum_dict = None
            # if output.datum:
            #     datum_dict = {
            #         "beneficiary": output.datum.beneficiary.to_primitive(),
            #         "price": output.datum.price
            #     }
            utxoOutputs[index] = {
                "address": output.address.encode(),
                "amount": {
                    "coin": output.amount.coin,
                    "multi_asset": multi_asset
                },
                "lovelace": output.lovelace,
                "script": output.script,
                # "datum": datum_dict,
                # "datum_hash": output.datum_hash,
            }

        utxoOutputs = { k: self._nullDict(v) for k, v in utxoOutputs.items() }

        # Format mint
        mint_assets = {}
        if txBody.mint:
            for k, v in txBody.mint.data.items():
                mint_asset = { assetName.payload: value for assetName, value in v.data.items()}
                mint_assets[k.to_cbor_hex()[4:]] = mint_asset

        # Format signers
        signersOutput = []
        if txBody.required_signers:

            signersOutput = [ signers.payload.hex() for signers in txBody.required_signers]

        collateral = {}
        if txBody.collateral:
            collateral = { index: f'{input.transaction_id.payload.hex()}#{input.index}' for index, input in enumerate(txBody.collateral)}

        collateral_return = {}
        if txBody.collateral_return:
            collateral_multi_asset = {}
            for k, v in txBody.collateral_return.amount.multi_asset.data.items():
                collateral_assets = { assetName.payload: value for assetName, value in v.data.items()}
                collateral_multi_asset[k.to_cbor_hex()[4:]] = collateral_assets

            collateral_return = {
                "address": txBody.collateral_return.address.encode(),
                "amount": {
                    "coin": txBody.collateral_return.amount.coin,
                    "multi_asset": collateral_multi_asset
                },
                "lovelace": txBody.collateral_return.lovelace,
                "script": txBody.collateral_return.script,
                "datum": txBody.collateral_return.datum,
                "datum_hash": txBody.collateral_return.datum_hash,
            }

            collateral_return = self._nullDict(collateral_return)

        script_data_hash = ""
        if txBody.script_data_hash:
            script_data_hash = txBody.script_data_hash.payload.hex()

        formatTxBody = {

            "auxiliary_data_hash": txBody.auxiliary_data_hash.payload.hex() if txBody.auxiliary_data_hash else ""
            ,"certificates": txBody.certificates
            ,"collateral": collateral
            ,"collateral_return": collateral_return
            ,"fee": txBody.fee
            ,"tx_id": txBody.id.payload.hex()
            ,"inputs": utxoInputs
            ,"outputs": utxoOutputs
            ,"mint": mint_assets
            ,"network_id": txBody.network_id
            ,"reference_inputs": txBody.reference_inputs
            ,"required_signers": signersOutput
            ,"script_data_hash": script_data_hash
            ,"total_collateral": txBody.total_collateral
            ,"ttl": txBody.ttl
            ,"update": txBody.update
            ,"validity_start": txBody.validity_start
            ,"withdraws": txBody.withdraws

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

    def list_files(self, folder_path= "") -> list:
        s3_client = self._initializeBoto2Client()
        try:
            response = s3_client.list_objects_v2(Bucket=self.S3_BUCKET_NAME, Prefix=folder_path)

            # Extract file information from the response
            files = []
            for obj in response.get('Contents', []):
                files.append(obj['Key'])

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

            response = s3_client.get_object(Bucket = self.S3_BUCKET_NAME, Key=f"{self.S3_BUCKET_NAME_HIERARCHY}/{file_name}")
            content = response["Body"].read().decode('utf-8')
            return {"success": True, "content": content}

        except Exception as e:
            logging.error(e)
            return {"success":False, "error": str(e)}

    def upload_file(self, file_path: pathlib.Path) -> bool:
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :return: True if file was uploaded, else False
        """
        s3_client = self._initializeBoto2Client()
        try:
            s3_client.upload_file(file_path, self.S3_BUCKET_NAME,  f"{self.S3_BUCKET_NAME_HIERARCHY}/{file_path.name}")
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
                file_name = os.path.relpath(local_file_path, folder_path).replace('\\', '/')
                folder = root.split("/")
                folder = os.path.join(folder[-2], folder[-1])
                s3_key = os.path.join(self.S3_BUCKET_NAME_HIERARCHY, file_name)

                try:
                    s3_client.upload_file(local_file_path, self.S3_BUCKET_NAME, s3_key)
                    uploaded.append(file_name)
                    print(f"Uploaded {file_name} to S3://{self.S3_BUCKET_NAME}/{s3_key}")
                except Exception as e:
                    error.append(file_name)
                    print(f"Error uploading {local_file_path} to S3: {e}")
        
        return {"uploaded": uploaded, "error": error}

@dataclass()
class CardanoApi(Constants):

    def __post_init__(self):
        # koios_api_module = importlib.import_module("koios_api")
        # self.koios_api = koios_api_module
        pass

    def getAddressInfo(self, address: Union[str, list[str]]) -> list[dict]:
        
        address_response = self.KOIOS_API.get_address_info(address)
        asset_response = self.KOIOS_API.get_address_assets(address)
        
        # # Group data2 by "address" key
        for item in address_response:
            assets = []
            for asset in asset_response:
                if asset["address"] == item["address"]:
                    assets.append(dict(map(lambda item: (item[0], bytes.fromhex(item[1]).decode("utf-8")) if item[0] == "asset_name" else item, filter(lambda item: item[0] != "address", asset.items()))))

            item["assets"] = assets

        return address_response

    def getUtxoInfo(self, utxo: Union[str, list[str]], extended: bool=False) -> list[dict]:

        utxo_info = self.KOIOS_API.get_utxo_info(utxo, extended)
        return utxo_info
    
    def getAccountTxs(self, account: str, after_block_height: int = 0) -> list:

        account_txs = self.KOIOS_API.get_account_txs(account, after_block_height)
        tx_hashes = [tx["tx_hash"] for tx in account_txs]
        transactions = self.KOIOS_API.get_tx_info(tx_hashes)

        final_response = sorted(transactions, key=lambda x: x["absolute_slot"], reverse=True)
        
        return final_response
    
    def getAccountUtxos(self, account: str, skip: int, limit: int) -> list[dict]:

        return self.KOIOS_API.get_account_utxos(account, True, skip, limit)

    def txStatus(self, txId: Union[str, list[str]]) -> list:

        status_response = self.KOIOS_API.get_tx_status(txId)

        return status_response
    
@dataclass()
class Helpers:

    def __post_init__(self):
        pass

    def makeMultiAsset(self, addressesDestin: pydantic_schemas.AddressDestin) -> Optional[MultiAsset]:
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

    def build_DatumProjectParams(self, pkh: str) -> pydantic_schemas.DatumProjectParams:

        datum = pydantic_schemas.DatumProjectParams(
            beneficiary=bytes.fromhex(pkh)
        )
        return datum
    
    def find_utxos_with_tokens(self, context: ChainContext, address: Union[Address, str], multi_asset: MultiAsset) -> Union[UTxO, None]:
        candidate_utxo = None
        if isinstance(address, Address):
            address = address.encode()
        
        # TODO: acummulate utxos with tokens when there's more than one utxo and the request cannot be fulfill with just one
        for policy_id, asset in multi_asset.data.items():
            for tn_bytes, amount in asset.data.items():

                for utxo in context.utxos(address):
                    def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
                        return pi == policy_id and an.payload == tn_bytes.payload and a >= amount
                    if utxo.output.amount.multi_asset.count(f):
                        candidate_utxo = utxo
                        break
                
                assert isinstance(candidate_utxo, UTxO), "Not enough tokens found in Utxo"
        
        return candidate_utxo