
import pathlib
from dataclasses import dataclass
import requests
import os
import json
import importlib
from typing import Union

from pycardano import *

from suantrazabilidadapi.core.config import config

@dataclass()
class Start:
    headers = {'Content-Type': 'application/json'}
    ROOT = pathlib.Path(__file__).resolve().parent.parent
    plataformaSecrets = config(section="plataforma")


@dataclass()
class Plataforma(Start):

    def __post_init__(self):
        self.graphqlEndpoint = os.getenv('endpoint')
        self.awsAppSyncApiKey = os.getenv('key')
        self.headers["x-api-key"] = self.awsAppSyncApiKey
        koios_api_module = importlib.import_module("koios_api")
        self.koios_api = koios_api_module

    def _post(self, operation_name: str, graphql_variables: Union[dict, None] = None) -> dict:

        with open(f'{self.ROOT}/graphql/queries.graphql', 'r') as file:
            graphqlQueries = file.read()
        try:
            rawResult = requests.post(
                self.graphqlEndpoint,
                json={"query": graphqlQueries, "operationName": operation_name, "variables": graphql_variables},
                headers=self.headers
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

    def formatTxBody(self, txBody: TransactionBody) -> dict:
        """_summary_

        Args:
            txBody (TransactionBody): _description_

        Returns:
            dict: dictionary with transaction body fields formatted
        """

        utxoInputs = { index: f'{input.transaction_id.payload.hex()}#{input.index}' for index, input in enumerate(txBody.inputs)}

        utxoOutputs = {}
        for index, output in enumerate(txBody.outputs):
            
            multi_asset = {}
            for k, v in output.amount.multi_asset.data.items():
                assets = { assetName.payload: value for assetName, value in v.data.items()}
                multi_asset[k.to_cbor_hex()[4:]] = assets

            utxoOutputs[index] = {
                "address": output.address.encode(),
                "amount": {
                    "coin": output.amount.coin,
                    "multi_asset": multi_asset
                },
                "lovelace": output.lovelace,
                "script": output.script,
                "datum": output.datum,
                "datum_hash": output.datum_hash,
            }

        utxoOutputs = { k: self._nullDict(v) for k, v in utxoOutputs.items() }

        formatTxBody = {

            "auxiliary_data_hash": txBody.auxiliary_data_hash
            ,"certificates": txBody.certificates
            ,"collateral": txBody.collateral
            ,"collateral_return": txBody.collateral_return
            ,"fee": txBody.fee
            ,"tx_id": txBody.id.payload.hex()
            ,"inputs": utxoInputs
            ,"outputs": utxoOutputs
            ,"mint": txBody.mint
            ,"network_id": txBody.network_id
            ,"reference_inputs": txBody.reference_inputs
            ,"required_signers": txBody.required_signers
            ,"script_data_hash": txBody.script_data_hash
            ,"total_collateral": txBody.total_collateral
            ,"ttl": txBody.ttl
            ,"update": txBody.update
            ,"validity_start": txBody.validity_start
            ,"withdraws": txBody.withdraws

        }

        formatTxBody = self._nullDict(formatTxBody)

        return formatTxBody


@dataclass()
class CardanoApi(Start):

    def __post_init__(self):
        koios_api_module = importlib.import_module("koios_api")
        self.koios_api = koios_api_module

    def getAddressInfo(self, address: Union[str, list[str]]) -> list[dict]:
        
        address_response = self.koios_api.get_address_info(address)
        asset_response = self.koios_api.get_address_assets(address)
        
        # # Group data2 by "address" key
        for item in address_response:
            assets = []
            for asset in asset_response:
                if asset["address"] == item["address"]:
                    assets.append(dict(map(lambda item: (item[0], bytes.fromhex(item[1]).decode("utf-8")) if item[0] == "asset_name" else item, filter(lambda item: item[0] != "address", asset.items()))))

            item["assets"] = assets

        return address_response

    def getUtxoInfo(self, utxo: Union[str, list[str]], extended: bool=False) -> list[dict]:

        utxo_info = self.koios_api.get_utxo_info(utxo, extended)
        return utxo_info
    
    def getAccountTxs(self, account: str, after_block_height: int = 0) -> list:

        account_txs = self.koios_api.get_account_txs(account, after_block_height)
        tx_hashes = [tx["tx_hash"] for tx in account_txs]
        transactions = self.koios_api.get_tx_info(tx_hashes)

        final_response = sorted(transactions, key=lambda x: x["absolute_slot"], reverse=True)
        
        return final_response
    
    def get_tx_info(self, txs: Union[str, list[str]]) -> list:

        return 
    
    def txStatus(self, txId: Union[str, list[str]]) -> list:

        status_response = self.koios_api.get_tx_status(txId)

        return status_response