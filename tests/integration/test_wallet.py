import os
from dotenv import load_dotenv
import pytest
from starlette.testclient import TestClient
from suantrazabilidadapi.app import suantrazabilidad
from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.utils.plataforma import Plataforma
from suantrazabilidadapi.utils.response import Response


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

# def test_get_wallets():

#     plataforma = Plataforma()
#     response = plataforma.listWallets()

#     assert response["success"] == True
#     assert 'data' in response["data"]
#     assert 'listWallets' in response['data']["data"]
#     assert 'items' in response['data']["data"]['listWallets']
#     assert len(response['data']["data"]['listWallets']['items']) > 0

#     wallet = response['data']["data"]['listWallets']['items'][0]
#     assert 'id' in wallet
#     assert 'name' in wallet
#     assert 'userID' in wallet
#     assert 'address' in wallet
#     assert 'isAdmin' in wallet

#     final_response = Response().handle_listWallets_response(response)
    
#     assert final_response["connection"] == True
#     assert final_response["success"] == True
#     assert 'data' in final_response
#     assert 'items' in final_response['data']
#     assert len(final_response['data']['items']) > 0

def test_get_wallets_endpoint(client, headers):  

    response = client.get("/api/v1/wallet/get-wallets/", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert response["connection"] == True
    assert response["success"] == True
    assert 'data' in response
    assert 'items' in response['data']
    assert len(response['data']['items']) > 0

# @pytest.mark.parametrize("wallet_id", ["1", ""], ids=["wallet_not_found", "wallet_success"])
# def test_get_wallet(wallet_id):
#     # Add a mock wallet to the table
#     plataforma = Plataforma()
#     command_name = "getWalletById"

#     if wallet_id == "":
#         response = plataforma.listWallets()
#         wallet = response['data']["data"]['listWallets']['items'][0]
#         wallet_id = wallet['id']

#         graphql_variables = {"walletId": wallet_id}

#         response = plataforma.getWallet(command_name, graphql_variables)

#         assert response["success"] == True
#         assert 'data' in response["data"]
#         assert 'getWallet' in response['data']["data"]
#         assert 'id' in response['data']["data"]['getWallet']
#         assert 'name' in response['data']["data"]['getWallet']
#         assert 'userID' in response['data']["data"]['getWallet']
#         assert 'address' in response['data']["data"]['getWallet']
#         assert wallet_id == response['data']["data"]['getWallet']['id']

#         final_response = Response().handle_getWallet_response(response)

#         assert final_response["connection"] == True
#         assert final_response["success"] == True
#         assert 'data' in final_response
#         assert 'id' in final_response['data']
#         assert 'name' in final_response['data']
#         assert 'userID' in final_response['data']
#         assert 'address' in final_response['data']
#         assert wallet_id in final_response['data']['id']

#     else:
#         graphql_variables = {"walletId": wallet_id}
#         response = plataforma.getWallet(command_name, graphql_variables)
        
#         assert response["success"] == True
#         assert 'data' in response["data"]
#         assert 'getWallet' in response['data']["data"]
#         assert response['data']["data"]['getWallet'] is None

#         final_response = Response().handle_getWallet_response(response)

#         assert final_response["connection"] == True
#         assert final_response["success"] == False

@pytest.mark.parametrize(
    "command_name, query_param, test_id",
    [
        ("id", "param1", "id_not_valid"),
        ("id", "f66d78b4a3cb3d37afa0ec36461e51ecbde00f26c8f0a68f94b69880", "id_valid_but_not_found"),
        ("id", "", "id_valid_but_found"),
        ("address", "param1", "address_not_valid"),
        ("address", "addr_test1vpdjpghjxlh8v35r8atus9yqx3g0fx52pnanv7ynxv2wkjqng6f8v", "address_valid_but_not_found"),
        ("address", "", "address_valid_but_found"),
    ],
    ids=[
        "id_not_valid",
        "id_valid_but_not_found",
        "id_valid_but_found",
        "address_not_valid",
        "address_valid_but_not_found",
        "address_valid_but_found",
    ]
)
def test_get_wallet_endpoint(client, command_name, query_param, test_id, headers):
    

    if test_id == "id_valid_but_found" or test_id == "address_valid_but_found":
        plataforma = Plataforma()
        response = plataforma.listWallets()
        wallet = response['data']["data"]['listWallets']['items'][0]

        if command_name == "id":
            wallet_id = wallet['id']
            query_param = wallet_id
        elif command_name == "address":
            address = wallet['address']
            query_param = address

        response = client.get(f"/api/v1/wallet/get-wallet/{command_name}?query_param={query_param}", headers=headers)

        assert response.status_code == 200
        response = response.json()
        assert response["connection"] == True
        assert response["success"] == True
        assert 'data' in response
        if command_name == "id":
            assert response['data']['id'] == wallet_id

        elif command_name == "address":
            assert response['data']['items'][0]['address'] == address
    
    elif test_id == "id_not_valid" or test_id == "address_not_valid":
        response = client.get(f"/api/v1/wallet/get-wallet/{command_name}?query_param={query_param}", headers=headers)
        assert response.status_code == 400
        response = response.json()
        assert response["detail"] == f"Not valid {command_name} format"
        # assert response["success"] == False
        # assert 'data' in response
        # assert response['data'] == None
    elif test_id == "id_valid_but_not_found" or test_id == "address_valid_but_not_found":
        response = client.get(f"/api/v1/wallet/get-wallet/{command_name}?query_param={query_param}", headers=headers)
        assert response.status_code == 200
        response = response.json()
        assert response["connection"] == True
        assert response["success"] == False
        