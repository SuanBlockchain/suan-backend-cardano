from pymerkle import SqliteTree, verify_consistency, verify_inclusion, MerkleProof
from pymerkle.hasher import MerkleHasher

# db_instance = SqliteTree('merkle.db')
# db_instance.delete_db()
tree = SqliteTree('merkle.db')

index = tree.append_entry(b'foo')

data = tree.get_entry(index) # Get the bynary stored in DB
assert data == b'foo'

size = tree.get_size() # Get the number of leaves
print(size)

data_hash = tree.get_leaf(index) # Get the hash of the leaf
print(data_hash)
data_hash_hex = tree.get_leaf_hex(index) # Get the hash of the leaf
print(data_hash_hex)

# Compute hashes

hasher = MerkleHasher(tree.algorithm, tree.security)

hasher_blake = MerkleHasher(tree.algorithm, False) # Create a hasher with a different algorithm

manual_hash = hasher_blake.hash_buff(b"Hello world") # Hash the entry
print(manual_hash)

manual_hash = hasher_blake.hash_hex(b"Hello world") # Hash the entry
print(manual_hash)

# manual_hash_hex = hasher_blake.hash_hex(b"Hello world") # Hash the entry and return it in hexadecimal
# print(manual_hash_hex)



two_hash = hasher.hash_pair(b'1d2039fa7971f4bf01a1c20cb2a3fe7af46865ca9cd9b840c2063df8fec4ff75', b'1d2039fa7971f4bf01a1c20cb2a3fe7af46865ca9cd9b840c2063df8fec4ff75') # Hash two entries
print(two_hash)

two_hash = hasher.hash_pair_hex(b'1d2039fa7971f4bf01a1c20cb2a3fe7af46865ca9cd9b840c2063df8fec4ff75', b'1d2039fa7971f4bf01a1c20cb2a3fe7af46865ca9cd9b840c2063df8fec4ff75') # Hash two entries
print(two_hash)
two_hash = hasher.hash_pair_hex(b'1d2039fa7971f4bf01a1c20cb2a3fe7af46865ca9cd9b840c2063df8fec4ff75', b'b7841aaeb873d8a62b9bd149af01d902a50dbe8db1087b29ddd6d943d5aeb6ca') # Hash two entries
print(two_hash)

empty_hash = hasher.hash_empty() # Hash the empty entry
print(empty_hash)

empty_hash_hex = hasher.hash_empty_hex() # Hash the empty entry
print(empty_hash_hex)

raw_hash = hasher.hash_raw(b'foo') # Hash the entry without prepending security prefixes
print(raw_hash)

hash_raw_hex = hasher.hash_raw_hex(b'foo') # Hash the entry without prepending security prefixes
print(hash_raw_hex)

# States
state = tree.get_state() # Get the state of the tree
print(state)

state = tree.get_state_hex() # Get the state of the tree
print(state)

state_two = tree.get_state(2) # Get the state of the tree at a specific level
print(state_two)

state_two = tree.get_state_hex(2) # Get the state of the tree at a specific level
print(state_two)

# Proofs

"""Given any intermediate state, 
an inclusion proof is a path of hashes proving that a certain data entry has been appended at some previous moment 
and that the tree has not been afterwards tampered. Below the inclusion proof for the 3-rd entry against 
the state corresponding to the first 5 leaves:"""

proof = tree.prove_inclusion(3, 4) # Get the inclusion proof
print(proof)
# Verification
base = tree.get_leaf(3)
root = tree.get_state(4)

inclusion = verify_inclusion(base, root, proof)
print(inclusion)

"""Given any two intermediate states, a consistency proof is a path of hashes proving that the second is a valid later state 
of the first, i.e., that the tree has not been tampered with in the meanwhile. 
Below the consistency proof for the states with three and five leaves respectively:"""

state1 = tree.get_state(3)
state2 = tree.get_state(4)

proof = tree.prove_consistency(3, 4) # Get the consistency proof

consistency = verify_consistency(state1, state2, proof)
print(consistency)

# Serialization

proof_bytes = proof.serialize() # Serialize the proof 
print(proof_bytes)

proof_copy = MerkleProof.deserialize(proof_bytes) # Deserialize the proof
print(proof_copy)
