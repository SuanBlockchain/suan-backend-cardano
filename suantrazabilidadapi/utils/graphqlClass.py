from dataclasses import dataclass
from suantrazabilidadapi.core.config import config

import requests
import json


@dataclass()
class Start:
    # params = {"format": "json"}
    headers = {'Content-Type': 'application/json'}
    # pass


@dataclass()
class Plataforma(Start):
    graphqlSecrets = config(section="plataforma")


    def __post_init__(self):
        self.graphqlEndpoint = self.graphqlSecrets["endpoint"]
        self.awsAppSyncApiKey = self.graphqlSecrets["key"]
        self.headers["x-api-key"] = self.awsAppSyncApiKey

    def getProjects(self, projectId) -> dict:

        graphql_variables = {
                "projectId": projectId
            }

        graphql_query = """
           query getProjects ($projectId: ID!) {
                getProduct(id: $projectId) {
                id
                amountToBuy
                categoryID
                counterNumberOfTimesBuyed
                createdAt
                description
                isActive
                name
                order
                status
                updatedAt
                images {
                    items {
                    id
                    productID
                    title
                    imageURL
                    imageURLToDisplay
                    format
                    carouselDescription
                    order
                    }
                }
                productFeatures(filter: {isToBlockChain: {eq: true}}) {
                    items {
                    featureID
                    value
                    }
                }
                }
            }
                    """

        rawResult = requests.post(self.graphqlEndpoint, json={"query": graphql_query, "variables": graphql_variables}, headers=self.headers)
        data = json.loads(rawResult.content.decode("utf-8"))

        return data
    
    def createProject(self, id: str, name: dict, categoryID: str, isActive: bool) -> dict:

        for name in name.values():

            graphql_variables = {
                "id": id,
                "name": name,
                "categoryID": categoryID,
                "isActive": isActive
                }

            graphql_query = """
            mutation MyMutation($id: ID! $name: String!, $categoryID: ID!, $isActive: Boolean!) {
                createProduct(input: {id: $id, name: $name, categoryID: $categoryID, isActive: $isActive}) {
                    id
                }
            }
        """


            try:
                rawResult = requests.post(
                    self.graphqlEndpoint,
                    json={"query": graphql_query, "variables": graphql_variables},
                    headers=self.headers
                )
                rawResult.raise_for_status()  # Raise an exception for non-2xx responses

                data = json.loads(rawResult.content.decode("utf-8"))
                # Process the data or perform additional operations

                # Return or use the processed data
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

            # rawResult = requests.post(self.graphqlEndpoint, json={"query": graphql_query, "variables": graphql_variables}, headers=self.headers)


        # data = json.loads(rawResult.content.decode("utf-8"))

        return response