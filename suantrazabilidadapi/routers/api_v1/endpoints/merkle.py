import os

from fastapi import APIRouter, HTTPException
from pymerkle import DynamoDBTree

from suantrazabilidadapi.utils.generic import Constants

router = APIRouter()



@router.post(
    "/merkle-tree/",
    status_code=201,
    summary="Include the information provided in the merkle tree table and submit the digest to the blockchain as part of a metadata transaction",
    response_description="Blockchain transaction id confirmation",
)
async def merkleTree(project_id: str, result_id: str, body: dict = {}) -> dict:
    """Submit inforomation to the blockchain as part of a metadata transaction \n"""
    env = os.getenv("env")
    opts = { "app_name": project_id, "env": env }
    try:
        tree = DynamoDBTree(aws_access_key_id=Constants.AWS_ACCESS_KEY_ID, aws_secret_access_key=Constants.AWS_SECRET_ACCESS_KEY, region_name=Constants.REGION_NAME, opts=opts)
        if not tree.create_table():
            # TODO: query the table filtering by hash info
            index = tree.append_entry(body)
        final_response = {
            "success": True,
            "msg": "Data stored in merkle tree",
            "project_id": project_id,
            "index": index,
            # "tx_id": tx_id,
        }
        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e