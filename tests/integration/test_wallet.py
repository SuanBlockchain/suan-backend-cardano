import os
from dotenv import load_dotenv
import pytest
from starlette.testclient import TestClient
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

def test_get_wallets_endpoint(client, headers):  

    response = client.get("/api/v1/wallet/get-wallets/", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert response["connection"] == True
    assert response["success"] == True
    assert 'data' in response
    assert 'items' in response['data']
    assert len(response['data']['items']) > 0

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

    elif test_id == "id_valid_but_not_found" or test_id == "address_valid_but_not_found":
        response = client.get(f"/api/v1/wallet/get-wallet/{command_name}?query_param={query_param}", headers=headers)
        assert response.status_code == 200
        response = response.json()
        assert response["connection"] == True
        assert response["success"] == False

def test_get_wallet_admin_endpoint(client, headers):  

    response = client.get("/api/v1/wallet/get-wallet-admin/", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert response["connection"] == True
    assert response["success"] == True
    assert 'data' in response
    assert 'items' in response['data']
    assert len(response['data']['items']) > 0

def test_generate_words_endpoint(client, headers):  

    response = client.get("/api/v1/wallet/generate-words/?size=24", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert isinstance(response, str)
    words = response.split()
    assert len(words) == 24

def test_create_wallet_endpoint(client, headers):
    mnemonic_words = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    wallet_type = "user"
    userID = "test_user"
    save_flag = False

    response = client.post(
        f"/api/v1/wallet/create-wallet/?mnemonic_words={mnemonic_words}&wallet_type={wallet_type}&userID={userID}&save_flag={save_flag}",
        headers=headers
    )

    assert response.status_code == 201
    response = response.json()
    assert response["success"] == True
    assert 'wallet_id' in response["data"]
    assert 'address' in response["data"]
    assert 'stake_address' in response["data"]

    wallet_info = Plataforma().generateWallet(mnemonic_words)
    wallet_id = wallet_info[0]
    assert wallet_id == response["data"]["wallet_id"]
    assert str(wallet_info[4]) == response["data"]["address"]
    assert str(wallet_info[5]) == response["data"]["stake_address"]

def test_query_address_endpoint(client, headers):
    address = "addr_test1vpdjpghjxlh8v35r8atus9yqx3g0fx52pnanv7ynxv2wkjqng6f8v"

    response = client.get(f"/api/v1/wallet/query-address/?address={address}", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert 'balance' in response
    assert 'stake_address' in response
    assert 'script_address' in response
    assert 'assets' in response
    assert response["stake_address"] is None
    assert int(response["balance"]) == 0
    assert response["script_address"] is False
    assert response["assets"] == []

def test_address_txs_endpoint(client, headers):
    address = "addr_test1vpdjpghjxlh8v35r8atus9yqx3g0fx52pnanv7ynxv2wkjqng6f8v"
    from_block = None
    to_block = None
    page_number = 1
    limit = 10
    "address=addr_test1vpdjpghjxlh8v35r8atus9yqx3g0fx52pnanv7ynxv2wkjqng6f8v&page_number=1&limit=10"
    response = client.get(f"/api/v1/wallet/address-tx/?address={address}&page_number={page_number}&limit={limit}", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert isinstance(response, list)

def test_address_utxos_endpoint(client, headers):
    address = "addr_test1vpdjpghjxlh8v35r8atus9yqx3g0fx52pnanv7ynxv2wkjqng6f8v"
    page_number = 1
    limit = 10

    response = client.get(f"/api/v1/wallet/address-utxo/?address={address}&page_number={page_number}&limit={limit}", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert isinstance(response, list)

def test_address_details_endpoint(client, headers):
    address = "addr_test1vpdjpghjxlh8v35r8atus9yqx3g0fx52pnanv7ynxv2wkjqng6f8v"

    response = client.get(f"/api/v1/wallet/address-details/?address={address}", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert 'amount' in response
    assert 'stake_address' in response
    assert 'type' in response
    assert 'script' in response

    assert response["stake_address"] is None
    assert isinstance(response["amount"], list)
    assert 'unit' in response["amount"][0]
    assert 'quantity' in response["amount"][0]
    assert 'decimals' in response["amount"][0]
    assert 'has_nft_onchain_metadata' in response["amount"][0]
    assert response["script"] is False
    assert response["type"] == "shelley"

def test_account_utxos_endpoint(client, headers):
    policy_id = "8726ae04e47a9d651336da628998eda52c7b4ab0a4f86deb90e51d83"

    response = client.get(f"/api/v1/wallet/asset-info/?policy_id={policy_id}", headers=headers)

    assert response.status_code == 200
    response = response.json()
    assert isinstance(response, list)
    assert 'asset' in response[0]
    assert 'policy_id' in response[0]
    assert 'asset_name' in response[0]
    assert 'fingerprint' in response[0]
    assert 'quantity' in response[0]
    assert 'initial_mint_tx_hash' in response[0]
    assert 'mint_or_burn_count' in response[0]
    assert 'onchain_metadata' in response[0]
    assert 'metadata' in response[0]
    assert response[0]["policy_id"] == policy_id
