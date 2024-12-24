import os
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient
from suantrazabilidadapi.app import suantrazabilidad
from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.utils.plataforma import Plataforma

security = config(section="security")
load_dotenv()


@pytest.fixture
def client():
    return TestClient(suantrazabilidad)

@pytest.fixture
def headers():
    return {
        "accept": "application/json",
        "x-api-key": os.getenv("platform_api_key_internal"),
    }

def build_tx(client, headers, body):

    response = client.post(
        "/api/v1/transactions/build-tx",
        json=body,
        headers=headers
    )

    return response

@pytest.mark.parametrize(
        "test_id", 
        [
            "existing_id", 
            "non_existing_id",
        ], 
        ids=["existing_id", "non_existing_id"]
)
def test_build_simple_tx(client, headers, test_id):

    if test_id == "existing_id":
        plataforma = Plataforma()
        response = plataforma.listWallets()
        wallet = response['data']["data"]['listWallets']['items'][0]
        wallet_id = wallet["id"]
    else:
        wallet_id = "non_existent_wallet_id"


    addresses = [
        {
            "address": "addr_test1vpdjpghjxlh8v35r8atus9yqx3g0fx52pnanv7ynxv2wkjqng6f8v",
            "lovelace": 1000000,
            "multiAsset": []
        }
    ]
    # TODO: test with metadata
    body = {
        "wallet_id": wallet_id,
        "addresses": addresses,
        "metadata": {}
    }

    response = build_tx(client, headers, body)

    if test_id == "existing_id":

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["success"] == True
        assert isinstance(response_data["tx_size"], int)
        assert isinstance(response_data["build_tx"]["fee"], int)

        cbor = response_data["cbor"]
        metadata_cbor = response_data["metadata_cbor"]
        body = {
            "wallet_id": wallet_id,
            "cbor": cbor,
            "metadata": metadata_cbor
        }
        response = client.post(
            "/api/v1/transactions/sign-submit?mockSubmit=true",
            json=body,
            headers=headers
        )

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["success"] == True
        assert response_data["tx_id"] != None
        assert response_data["msg"] == "Tx submitted to the blockchain"

    else:
        assert response.status_code == 400
        response = response.json()
        assert response["detail"] == f"Wallet with id: {wallet_id} does not exist in DynamoDB"
