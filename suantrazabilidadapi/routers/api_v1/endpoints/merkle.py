import binascii
import os
from typing import Optional, Union

from fastapi import APIRouter, HTTPException
from pymerkle import DynamoDBTree, verify_inclusion

from suantrazabilidadapi.utils.generic import Constants

router = APIRouter()

@router.post(
    "/merkle-tree/",
    status_code=201,
    summary="Include the information provided in the merkle tree table and submit the digest to the blockchain as part of a metadata transaction",
    response_description="Blockchain transaction id confirmation",
)
async def merkleTree(project_id: str, body: dict = {}) -> dict:
    """Include result in merkle tree and submit information to the blockchain as part of a metadata transaction \n"""
    env = os.getenv("env")
    opts = { "app_name": project_id, "env": env }
    try:
        tree = DynamoDBTree(aws_access_key_id=Constants.AWS_ACCESS_KEY_ID, aws_secret_access_key=Constants.AWS_SECRET_ACCESS_KEY, region_name=Constants.REGION_NAME, **opts)
        hash = tree.hash_hex(body)

        index = tree.get_index_by_digest_hex(hash)
        if index:
            raise ValueError(f"Data already stored in merkle tree with index: {index}") 
        
        index = tree.append_entry(body)

        # root = tree.get_state()

        final_response = {
            "success": True,
            "msg": "Data stored in merkle tree",
            "project_id": project_id,
            "index": index,
            "data_hash": hash
            # "tx_id": tx_id,
        }
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    

@router.post(
    "/verify-inclusion/",
    status_code=201,
    summary="Verify the inclusion of a data in the merkle tree",
    response_description="Verification result",
)
async def verifyInclusion(project_id: str, index: Union[int, None] = None, body: dict = {}) -> dict:
    """ \n"""
    env = os.getenv("env")
    opts = { "app_name": project_id, "env": env }
    try:
        tree = DynamoDBTree(aws_access_key_id=Constants.AWS_ACCESS_KEY_ID, aws_secret_access_key=Constants.AWS_SECRET_ACCESS_KEY, region_name=Constants.REGION_NAME, **opts)
        hash = tree.hash_hex(body)
        # index = tree.get_index_by_digest_hex(hash)

        base = binascii.unhexlify(hash)

        size = tree.get_size()

        # TODO: obtain the root from the blockchain
        root = tree.get_state()
        # Generate proof
        # TODO: I need to generate a proof for each index because is not possible to know the index of the data in the tree
        inclusion = False
        if not index:
            for i in range(size):
                proof = tree.prove_inclusion(i + 1)
                inclusion = verify_inclusion(base, root, proof)
                if inclusion:
                    break
        else:
            proof = tree.prove_inclusion(index)
            inclusion = verify_inclusion(base, root, proof)

        print(inclusion)

        if inclusion:
            final_response = {
                "msg": "Verification of inclusion succesful",
                "project_id": project_id,
                "data_hash": hash,
                "inclusion": inclusion,
                "proof": proof.serialize(),
            }
        else:
            final_response = {
                "msg": "Verification of inclusion failed",
                "project_id": project_id,
                "data_hash": hash,
                "inclusion": inclusion,
                "proof": proof.serialize(),
            }
        return final_response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e