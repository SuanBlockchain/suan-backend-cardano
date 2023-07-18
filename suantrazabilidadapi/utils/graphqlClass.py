import pathlib
from dataclasses import dataclass
import requests
import json

from suantrazabilidadapi.core.config import config

@dataclass()
class Start:
    # params = {"format": "json"}
    headers = {'Content-Type': 'application/json'}
    # pass

ROOT = pathlib.Path(__file__).resolve().parent.parent

@dataclass()
class Plataforma(Start):
    graphqlSecrets = config(section="plataforma")

    def __post_init__(self):
        self.graphqlEndpoint = self.graphqlSecrets["endpoint"]
        self.awsAppSyncApiKey = self.graphqlSecrets["key"]
        self.headers["x-api-key"] = self.awsAppSyncApiKey
        self.status = "draft"
        self.isActive = True
        self.isResult = False
        self.isOnMainCard = False

    def post(self, operation_name: str, graphql_variables: dict) -> dict:

        with open(f'{ROOT}/graphql/queries.graphql', 'r') as file:
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

    def getProjects(self, projectId: int) -> dict:
        # try:
        graphql_variables = {
            "projectId": projectId
        }

        data = self.post('getProjects', graphql_variables)

        return data
    
    def createProject(self, id: int, name: str, description: str, categoryID: str, values: dict) -> dict:

        graphql_variables = {
            "id": id,
            "name": name,
            "description": description,
            "categoryID": categoryID,
            "isActive": self.isActive,
            "status": self.status
            }

        response = self.post('ProjectMutation', graphql_variables)

        for k, v in values.items():

            graphql_variables = {
                "featureID": k,
                "productID": id,
                "value": v,
                "isResult": self.isResult,
                "isOnMainCard": self.isOnMainCard
                }

            response = self.post('ProductFeatureMutation', graphql_variables)

        return response