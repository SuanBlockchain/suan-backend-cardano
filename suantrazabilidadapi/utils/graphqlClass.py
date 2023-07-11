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

    def getCategories(self) -> dict:

        graphql_variables = {}
        graphql_query = """
            query getCategories {
                        listCategories {
                            items {
                                id
                                products {
                                    items {
                                        id
                                    }
                                }
                                name
                            }
                        }
                    }
                    """

        rawResult = requests.post(self.graphqlEndpoint, json={"query": graphql_query, "variables": graphql_variables}, headers=self.headers)
        data = json.loads(rawResult.content.decode("utf-8"))

        return data