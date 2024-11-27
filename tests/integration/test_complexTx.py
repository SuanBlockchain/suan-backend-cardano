import os
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient

from pycardano import (
    PaymentVerificationKey,
    ScriptPubkey,
    ScriptAll,
    HDWallet,
    )

from suantrazabilidadapi.app import suantrazabilidad
from suantrazabilidadapi.core.config import config
from suantrazabilidadapi.utils.plataforma import CardanoApi, Plataforma
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

@pytest.mark.parametrize(
        "test_id", ["existing_id", "non_existing_id"], ids=["existing_id", "non_existing_id"]
)
def test_mint_tokens(client, headers, test_id):

    # TODO: The script for minting must be a Plutus script and not native script.
    # There must be a way to generate a Plutus script from the test contracts functions.
    # case1: utxo not found
    # case2: policy id not found
    # case3: send to an address that is not in the wallet
    policyid = ""
    utxo = {
        "transaction_id": "",
        "index": 0,
    }
    if test_id == "existing_id":
        plataforma = Plataforma()
        r = plataforma.getWallet("getWalletAdmin", {"isAdmin": True})
        final_response = Response().handle_listGeneric_response(operation_name="listWallets", listGeneric_response=r)
        wallet = final_response['data']['items'][0]
        wallet_id = wallet["id"]
        address = wallet["address"]
        cardano = CardanoApi()
        utxos = cardano.getAddressUtxos(address)
        assert utxos != []
        # build the utxo input
        utxo = {
            "transaction_id": utxos[0]["tx_hash"],
            "index": utxos[0]["tx_index"],
        }

        # Build the contract using the create-contract endpoint

        # script_type = "mintProjectToken"
        # name = "TestMintProjectToken"
        # token_name = "TestToken"
        # save_flag = False
        # response = client.get(
        #     f"/api/v1/contracts/create-contract/{script_type}?name={name}&wallet_id={wallet_id}&token_name={token_name}&save_flag={str(save_flag)}",
        #     headers=headers
        # )

        # Build the policy id as native script
        seed = wallet["seed"]
        hdwallet = HDWallet.from_seed(seed)
        child_wallet = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
        payment_vk = PaymentVerificationKey.from_primitive(child_wallet.public_key)
        pub_key_policy = ScriptPubkey(payment_vk.hash())
        policy = ScriptAll([pub_key_policy])
        policyid = policy.hash()

    else:
        wallet_id = "non_existent_wallet_id"

    mint = {
        "asset": {
            "policyid": policyid.payload.hex(),
            "tokens": {
                "tokenTest": 2000
            }
        }
    }

    metadata = {
        policyid.payload.hex(): {
        "name": "Test Token",
        "description": "This is a test token",
        }
    }

    body = {
        "wallet_id": wallet_id,
        "utxo": utxo,
        # "addresses": addresses,
        "metadata": metadata,
        "mint": mint,
    }

    response = client.post(
        "/api/v1/transactions/mint-tokens/Mint",
        json=body,
        headers=headers
    )

    if test_id == "existing_id":

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["success"] == True
        assert isinstance(response_data["tx_size"], int)
        assert isinstance(response_data["build_tx"]["fee"], int)

    else:
        assert response.status_code == 400
        response = response.json()
        assert response["detail"] == f"Wallet with id: {wallet_id} does not exist in DynamoDB"
