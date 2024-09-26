from fastapi import APIRouter, HTTPException

from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.utils.plataforma import Plataforma

router = APIRouter()

# @router.get("/get-wallets/", status_code=200,
# summary="Get all the wallets registered in Plataforma",
#     response_description="Wallet details",)

# async def getWallets():
#     """Get all the wallets registered in Plataforma
#     """
#     try:
#         r = Plataforma().listWallets()
#         if r["data"].get("data", None) is not None:
#             wallet_list = r["data"]["data"]["listWallets"]["items"]
#             if wallet_list == []:
#                 final_response = {
#                     "success": True,
#                     "msg": 'No wallets present in the table',
#                     "data": r["data"]
#                 }
#             else:
#                 final_response = {
#                     "success": True,
#                     "msg": 'List of wallets',
#                     "data": wallet_list
#                 }
#         else:
#             if r["success"] == True:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["data"]["errors"]
#                 }
#             else:
#                 final_response = {
#                     "success": False,
#                     "msg": "Error fetching data",
#                     "data": r["error"]
#                 }

#         return final_response


#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/get-project/{command_name}",
    status_code=200,
    summary="Get the project with specific id as registered in Plataforma",
    response_description="Project details",
)
async def getProject(
    command_name: pydantic_schemas.projectCommandName, query_param: str
):
    """Get the project with specific id as registered in Plataforma"""
    try:
        if command_name == "id":
            # Validate the id

            r = Plataforma().getProject(command_name, query_param)

            if r["data"].get("data", None) is not None:
                projectInfo = r["data"]["data"]["getProduct"]

                if projectInfo is None:
                    final_response = {
                        "success": True,
                        "msg": f"Project with id: {query_param} does not exist in DynamoDB",
                        "data": r["data"],
                    }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Project info",
                        "data": projectInfo,
                    }

            else:
                if r["success"]:
                    final_response = {
                        "success": False,
                        "msg": "Error fetching data",
                        "data": r["data"]["errors"],
                    }
                else:
                    final_response = {
                        "success": False,
                        "msg": "Error fetching data",
                        "data": r["error"],
                    }

        return final_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        msg = "Error with the endpoint"
        raise HTTPException(status_code=500, detail=msg) from e
