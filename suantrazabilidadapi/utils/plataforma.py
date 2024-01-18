
import pathlib
from dataclasses import dataclass
import requests
import os
import json
import importlib
from typing import Union

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

    def post(self, operation_name: str, graphql_variables: Union[dict, None] = None) -> dict:

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

    def getWallet(self, walletId: str) -> dict:
        # try:
        graphql_variables = {
            "walletId": walletId
        }

        data = self.post('getWallet', graphql_variables)

        return data
    
    def listWallets(self) -> dict:
        return self.post('listWallets')
    
    def createWallet(self, values) -> list[dict]:

        response = self.post('WalletMutation', values)
        return response
    
    def getAddressInfo(self, address: list[str]) -> list[dict]:
        
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
    