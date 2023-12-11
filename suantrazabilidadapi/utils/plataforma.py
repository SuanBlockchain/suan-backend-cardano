
import pathlib
from dataclasses import dataclass
import requests
import os
import json

from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas

@dataclass()
class Start:
    headers = {'Content-Type': 'application/json'}
    ROOT = pathlib.Path(__file__).resolve().parent.parent
    plataformaSecrets = config(section="plataforma")


@dataclass()
class Plataforma(Start):

    def __post_init__(self):
        # self.graphqlEndpoint = self.plataformaSecrets["endpoint"]
        self.graphqlEndpoint = os.getenv('endpoint')
        # self.awsAppSyncApiKey = self.plataformaSecrets["key"]
        self.awsAppSyncApiKey = os.getenv('key')
        self.headers["x-api-key"] = self.awsAppSyncApiKey

    def post(self, operation_name: str, graphql_variables: dict) -> dict:

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

    def getWallets(self, walletId: str) -> dict:
        # try:
        graphql_variables = {
            "walletId": walletId
        }

        data = self.post('getWallets', graphql_variables)

        return data
    
    def createWallet(self, values) -> list[dict]:

        response = self.post('WalletMutation', values)
        return response
    