import pathlib
from dataclasses import dataclass, field
import requests
import json
import boto3
import time

from suantrazabilidadapi.core.config import config

@dataclass()
class Start:
    headers = {'Content-Type': 'application/json'}
    ROOT = pathlib.Path(__file__).resolve().parent.parent

@dataclass()
class Plataforma(Start):
    graphqlSecrets = config(section="plataforma")

    def __post_init__(self):
        self.graphqlEndpoint = self.graphqlSecrets["endpoint"]
        self.awsAppSyncApiKey = self.graphqlSecrets["key"]
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

    def getProjects(self, projectId: int) -> dict:
        # try:
        graphql_variables = {
            "projectId": projectId
        }

        data = self.post('getProjects', graphql_variables)

        return data
    
    def createFeatures(self, id: int, values: dict) -> list[dict]:

        response_list = []
        isResult = False
        isOnMainCard = False

        for k, v in values.items():

            graphql_variables = {
                "featureID": k,
                "productID": id,
                "value": v,
                "isResult": isResult,
                "isOnMainCard": isOnMainCard
                }

            response = self.post('ProductFeatureMutation', graphql_variables)
            response_list.append(response)
        
        return response_list
    
    def createProject(self, id: int, name: str, description: str, categoryID: str) -> dict:

        status = "draft"
        isActive = True

        graphql_variables = {
            "id": id,
            "name": name,
            "description": description,
            "categoryID": categoryID,
            "isActive": isActive,
            "status": status
            }

        response = self.post('ProjectMutation', graphql_variables)
        return response
    
    def createDocument(self, productFeatureID: str, url: str) -> dict:

        # $data: AWSJSON! $productFeatureID: ID!, $timeStamp: AWSTimestamp!, $url: AWSURL!, $isApproved: Boolean!, $status: String!, $isUploadedToBlockChain: Boolean!, $userID: ID!

        userID = "a5e0ea8d-95f6-4a8b-bd13-e28f9fa49934"
        data = json.dumps({"empty": ""})
        timeStamp = int(time.time())
        isUploadedToBlockChain = False
        isApproved = False
        status = "pending"

        graphql_variables = {
            "data": data,
            "productFeatureID": productFeatureID,
            "timeStamp": timeStamp,
            "url": url,
            "isApproved": isApproved,
            "status": status,
            "isUploadedToBlockChain": isUploadedToBlockChain,
            "userID": userID
            }

        response = self.post('DocumentMutation', graphql_variables)
        return response

@dataclass()
class S3Files(Start):

    def __post_init__(self):
        self.profile_name: str = "suan"

    def upload_file(self, bucket_name: str, project_id: int, file_name: str) -> bool:

        session = boto3.Session(profile_name=self.profile_name)
        s3_client = session.client('s3')
        file_path = f'{self.ROOT}/utils/data/{file_name}'
        s3_key = f'{project_id}/{file_name}'
        try:
            s3_client.upload_file(file_path, bucket_name, s3_key)
            #TODO: delete file from temp folder
            return True
        except Exception as e:
            print(f'Error uploading file: {e}')
            return False