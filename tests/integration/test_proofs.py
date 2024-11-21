import pytest
from suantrazabilidadapi.utils.blockchain import Proofs
from pycardano import PaymentKeyPair
from typing import Union
from unittest.mock import patch

from suantrazabilidadapi.utils.exception import ResponseDynamoDBException

@pytest.fixture
def proofs() -> Proofs:
    return Proofs()

@pytest.fixture
def key_pair() -> PaymentKeyPair:
    key_pair = PaymentKeyPair.generate()
    return key_pair

def test_hash_function(proofs: Proofs):
    data = "test_data"
    expected_hash = "e7d87b738825c33824cf3fd32b7314161fc8c425129163ff5e7260fc7288da36"
    assert proofs.hash_function(data) == expected_hash

def test_create_merkle_tree(proofs: Proofs):
    data_list = ["a", "b", "c", "d"]
    expected_root = "12a40550c10c6339bf6f271445270e49b844d6c9e8abc36b9b642be532befe94"
    merkle_tree = proofs.create_merkle_tree(data_list)
    assert merkle_tree[-1] == expected_root

def test_get_merkle_root(proofs: Proofs):
    data_list = ["a", "b", "c", "d"]
    expected_root = "58c89d709329eb37285837b042ab6ff72c7c8f74de0446b091b6a0131c102cfd"
    assert proofs.get_merkle_root(data_list) == expected_root

def test_generate_proof(proofs: Proofs):
    data_list = ["a", "b", "c", "d"]
    target_data = "a"
    proof = proofs.generate_proof(data_list, target_data)
    assert len(proof) > 0

def test_verify_proof(proofs: Proofs):
    data_list = ["a", "b", "c", "d"]
    target_data = "a"
    root = proofs.get_merkle_root(data_list)
    proof = proofs.generate_proof(data_list, target_data)
    assert proofs.verify_proof(root, target_data, proof)

def test_sign_data(proofs: Proofs, key_pair: PaymentKeyPair):
    skey = key_pair.signing_key
    data = "test_data"
    signature = proofs.sign_data(data, skey)
    assert isinstance(signature, Union[str, dict])

def test_verify_signature(proofs: Proofs, key_pair: PaymentKeyPair):
    skey = key_pair.signing_key
    # vkey = key_pair.verification_key
    data = "test_data"
    signature = proofs.sign_data(data, skey)
    assert proofs.verify_signature(signature)

@patch('suantrazabilidadapi.utils.blockchain.Plataforma.createMerkleTree')
@patch('suantrazabilidadapi.utils.blockchain.Response.handle_createMerkleTree_response')
def test_insert_node_success(mock_handle_response, mock_create_merkle_tree, proofs):
    mock_create_merkle_tree.return_value = {"data": {"node_id": 1}}
    mock_handle_response.return_value = {"connection": True, "success": True, "data": {"node_id": 1}}

    parent_id = None
    data = "test_data"
    level = 0
    hash_value = "test_hash"

    node_id = proofs.insert_node(parent_id, data, level, hash_value)
    assert node_id == 1

@patch('suantrazabilidadapi.utils.blockchain.Plataforma.createMerkleTree')
@patch('suantrazabilidadapi.utils.blockchain.Response.handle_createMerkleTree_response')
def test_insert_node_failure(mock_handle_response, mock_create_merkle_tree, proofs):
    mock_create_merkle_tree.return_value = {"data": {"node_id": 1}}
    mock_handle_response.return_value = {"connection": False, "success": False, "data": "Error"}

    parent_id = None
    data = "test_data"
    level = 0
    hash_value = "test_hash"

    with pytest.raises(ResponseDynamoDBException):
        proofs.insert_node(parent_id, data, level, hash_value)
        @patch('suantrazabilidadapi.utils.blockchain.Plataforma.createMerkleTree')
        @patch('suantrazabilidadapi.utils.blockchain.Response.handle_createMerkleTree_response')
        def test_insert_node_invalid_data(mock_handle_response, mock_create_merkle_tree, proofs):
            mock_create_merkle_tree.return_value = {"data": {"node_id": 1}}
            mock_handle_response.return_value = {"connection": True, "success": True, "data": {"node_id": 1}}

            parent_id = None
            data = None  # Invalid data
            level = 0
            hash_value = "test_hash"

            with pytest.raises(ValueError):
                proofs.insert_node(parent_id, data, level, hash_value)