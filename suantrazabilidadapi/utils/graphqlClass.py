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
        self.status = "draft"
        self.isActive = True
        self.isResult = False
        self.isOnMainCard = False

    def post(self, graphql_query: str, graphql_variables: dict) -> dict:

        try:
            rawResult = requests.post(
                self.graphqlEndpoint,
                json={"query": graphql_query, "variables": graphql_variables},
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
        try:
            graphql_variables = {
                "projectId": projectId
            }

            graphql_query = """
            query getProjects ($projectId: ID!) {
                    getProduct(id: $projectId) {
                    id
                    categoryID
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

            # rawResult = requests.post(self.graphqlEndpoint, json={"query": graphql_query, "variables": graphql_variables}, headers=self.headers)
            # rawResult.raise_for_status()  # Raise an exception if the request was not successful

            # data = json.loads(rawResult.content.decode("utf-8"))

            data = self.post(graphql_query, graphql_variables)

            return data

        except requests.exceptions.RequestException as e:
            print("An error occurred during the API request:", e)
            return {}  # Return an empty dictionary or any other suitable default value

        except (json.JSONDecodeError, KeyError) as e:
            print("An error occurred while processing the API response:", e)
            return {}  # Return an empty dictionary or any other suitable default value
    
    def createProject(self, id: int, name: str, description: str, categoryID: str, values: dict) -> dict:

        graphql_variables = {
            "id": id,
            "name": name,
            "description": description,
            "categoryID": categoryID,
            "isActive": self.isActive,
            "status": self.status
            }

        graphql_query = """
            mutation MyMutation($id: ID!, $name: String!, $description: String!, $categoryID: ID!, $isActive: Boolean!) {
                createProduct(input: {id: $id, name: $name, description: $description, categoryID: $categoryID, isActive: $isActive}) {
                    id
                }
            }
        """


        # try:
            # rawResult = requests.post(
            #     self.graphqlEndpoint,
            #     json={"query": graphql_query, "variables": graphql_variables},
            #     headers=self.headers
            # )
            # rawResult.raise_for_status()  # Raise an exception for non-2xx responses

            # data = json.loads(rawResult.content.decode("utf-8"))
        response = self.post(graphql_query, graphql_variables)


            # Process the data or perform additional operations

            # Return or use the processed data
            # response = {
            #     "success": True,
            #     "data": data
            # }

        # except requests.exceptions.RequestException as e:
        #     # Handle any exceptions that occur during the request
        #     response = {
        #         "success": False,
        #         "error": str(e)
        #     }

        for k, v in values.items():

            graphql_variables = {
                "featureID": k,
                "productID": id,
                "value": v,
                "isResult": self.isResult,
                "isOnMainCard": self.isOnMainCard
                }

            graphql_query = """
                mutation MyMutation ($featureID: ID! $productID: ID!, $value: String!, $isResult: Boolean!, $isOnMainCard: Boolean!) {
                createProductFeature(input: {featureID: $featureID, productID: $productID, value: $value, isResult: $isResult, isOnMainCard: $isOnMainCard}) 
                    {
                        id
                    }
                }
            """
            response = self.post(graphql_query, graphql_variables)

        # try:
        #     rawResult = requests.post(
        #         self.graphqlEndpoint,
        #         json={"query": graphql_query, "variables": graphql_variables},
        #         headers=self.headers
        #     )
        #     rawResult.raise_for_status()  # Raise an exception for non-2xx responses

        #     data = json.loads(rawResult.content.decode("utf-8"))
        #     # Process the data or perform additional operations

        #     # Return or use the processed data
        #     response = {
        #         "success": True,
        #         "data": data
        #     }

        # except requests.exceptions.RequestException as e:
        #     # Handle any exceptions that occur during the request
        #     response = {
        #         "success": False,
        #         "error": str(e)
        #     }


            # rawResult = requests.post(self.graphqlEndpoint, json={"query": graphql_query, "variables": graphql_variables}, headers=self.headers)


        # data = json.loads(rawResult.content.decode("utf-8"))

        return response