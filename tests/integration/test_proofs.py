import pytest
from suantrazabilidadapi.utils.blockchain import Proofs

@pytest.fixture
def proofs():
    return Proofs()

def test_hash_function(proofs):
    data = "test_data"
    expected_hash = "0a98291db08300a6089ab2e5462e4181d9fda99a22e259a2fbd65400a185f97e"
    assert proofs.hash_function(data) == expected_hash

def test_create_merkle_tree(proofs):
    data_list = ["a", "b", "c", "d"]
    expected_root = "be789cfccae2bbeaab5c33a82d547db25c8c54b95ac857b9b64590ac7f7f66a6"
    merkle_tree = proofs.create_merkle_tree(data_list)
    assert merkle_tree[-1] == expected_root

def test_get_merkle_root(proofs):
    data_list = ["a", "b", "c", "d"]
    expected_root = "e648083716ae376ac63e78dd8b546e43af56c6bec4cbaf0abccd0fce07c4c032"
    assert proofs.get_merkle_root(data_list) == expected_root

def test_generate_proof(proofs):
    data_list = ["a", "b", "c", "d"]
    target_data = "a"
    proof = proofs.generate_proof(data_list, target_data)
    assert len(proof) > 0

def test_verify_proof(proofs):
    data_list = ["a", "b", "c", "d"]
    target_data = "a"
    root = proofs.get_merkle_root(data_list)
    proof = proofs.generate_proof(data_list, target_data)
    assert proofs.verify_proof(root, target_data, proof)