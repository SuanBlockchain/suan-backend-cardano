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

@pytest.mark.parametrize(
    "query_param, test_id",
    [
        ("param1", "id_not_valid"),
        ("f66d78b4a3cb3d37afa0ec36461e51ecbde00f26c8f0a68f94b69880", "id_valid_but_not_found"),
        ("", "id_valid_but_found")
    ],
    ids=[
        "id_not_valid",
        "id_valid_but_not_found",
        "id_valid_but_found"
    ]
)
def test_signSubmit(client, headers, query_param, test_id):
    
    response = client.get("/api/v1/wallet/get-wallet-admin/", headers=headers)

    wallet_id = response.json()["data"]["items"][0]["id"]

    body = {
        "wallet_id": wallet_id,
        
    }

    response = client.post(
        "http://localhost:8001/api/v1/transactions/sign-submit/",
        json=body,
        headers=headers
    )

    if test_id == "id_valid_but_found":
        plataforma = Plataforma()
        response = plataforma.listScripts()
        script = response['data']["data"]['listScripts']['items'][0]
        query_param = script['id']

        response = client.get(f"/api/v1/contracts/get-script/id?query_param={query_param}", headers=headers)

        assert response.status_code == 200
        response = response.json()
        assert response["connection"] == True
        assert response["success"] == True
        assert 'data' in response
        assert response['data']['id'] == query_param

    
    elif test_id == "id_not_valid":
        response = client.get(f"/api/v1/contracts/get-script/id?query_param={query_param}", headers=headers)
        assert response.status_code == 400
        response = response.json()
        assert response["detail"] == f"Not valid id format"

    elif test_id == "id_valid_but_not_found":
        response = client.get(f"/api/v1/contracts/get-script/id?query_param={query_param}", headers=headers)
        assert response.status_code == 200
        response = response.json()
        assert response["connection"] == True
        assert response["success"] == False

@pytest.mark.parametrize(
        "save_flag, test_id, token_name", 
        [
            (False, "existing_id", ""), 
            (False, "existing_id", "TestToken"), 
            (False, "non_existing_id", ""),
            (False, "non_existing_id", "TestToken"),
            (True, "existing_id", ""), 
            (True, "existing_id", "TestToken"), 
            (True, "non_existing_id", ""),
            (True, "non_existing_id", "TestToken"),
        ], 
            
        ids=["id_noToken_noSafe", "id_withToken_noSafe", "non_id_noToken_noSafe", "non_id_withToken_noSafe", "id_noToken_Safe", "id_withToken_Safe", "non_id_noToken_Safe", "non_id_withToken_Safe"]
)
def test_create_mintProjectToken(client, headers, save_flag, test_id, token_name):

    script_type = "mintProjectToken"
    name = "TestMintProjectToken"
    # TODO: test the case when save_flag = True


    if test_id == "existing_id":

        response = client.get("/api/v1/wallet/get-wallet-admin/", headers=headers)

        wallet_id = response.json()["data"]["items"][0]["id"]

    else:
        wallet_id = "non_existent_wallet_id"

    response = create_contract(client, headers, script_type, name, wallet_id, token_name, save_flag)

    if test_id == "existing_id":

        if token_name == "":
            assert response.status_code == 400
            response = response.json()
            assert response["detail"] == "Token name is required for this script type"
        else:
            assert response.status_code == 200
            response = response.json()
            assert response["success"] == True
            if not save_flag:
                assert response["msg"] == "Script created but not stored in Database"
            else:
                platform = Plataforma()
                platform.deleteScript(script_id=response["data"]["id"])
                assert response["msg"] == "Script created"
                assert isinstance(response["data"], dict)
                assert "id" in response["data"]
                assert "utxo_to_spend" in response["data"]
                assert "testnet_address" in response["data"]
                assert "mainnet_address" in response["data"]
    else:
        assert response.status_code == 400
        response = response.json()
        assert response["detail"] == f"Wallet with id: {wallet_id} does not exist in DynamoDB"
