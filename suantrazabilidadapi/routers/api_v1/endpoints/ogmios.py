from fastapi import APIRouter
import websockets
import ogmios.model.ogmios_model as om
import ogmios.model.model_map as mm
import json
import requests
import os

from suantrazabilidadapi.utils.generic import Constants


router = APIRouter()

# Load variables to decide if running local or in cloud


@router.get(path="/tip")
async def ogmiosTip():
    """Get the tip from Cardano Blockchain using Ogmios Backend Service with ogmios library"""
    import ogmios

    with ogmios.Client(
        host=Constants.OGMIOS_URL,
        port=Constants.OGMIOS_PORT,
        secure=False,
        http_only=False,
    ) as client:
        tip, _ = client.query_ledger_tip.execute()

    return tip


@router.get(path="/ogmios-ws-tip")
async def ogmiosTipWs():
    """Get the tip from Cardano Blockchain using Ogmios Backend Service with websockets"""

    url = f"ws://{Constants.OGMIOS_URL}:{Constants.OGMIOS_PORT}"

    async with websockets.connect(url) as websocket:
        rpc_version = "2.0"
        method = mm.Method.queryLedgerState_tip.value
        # method = ""
        pld = om.QueryLedgerStateTip(
            jsonrpc=rpc_version,
            method=method,
            id=None,
        )
        await websocket.send(pld.json())
        response = await websocket.recv()

    return json.loads(response)


# if not Constants.COPILOT_SERVICE_DISCOVERY_ENDPOINT:

#     @router.get(path="/ogmios-health")
#     async def ogmiosRequests():
#         """Get ogmios health statistics. This endpoint only works in localhost"""

#         url = f"http://{Constants.OGMIOS_URL}:{Constants.OGMIOS_PORT}/health"

# try:
#     response = requests.get(url)
#     response.raise_for_status()
# except requests.exceptions.RequestException as e:
#     raise HTTPException(status_code=503, detail=f"Failed to connect to the service: {e}")

# try:
#     health_data = response.json()
# except json.JSONDecodeError as e:
#     raise HTTPException(status_code=500, detail=f"Failed to parse JSON response: {e}")

# try:
#     url = f"http://{Constants.OGMIOS_URL}:{Constants.OGMIOS_PORT}/health"

#     # response = requests.post(url, data=pld.json())
#     response = requests.get(url)
#     response.raise_for_status()

#     # Parse the JSON response
#     data = response.json()

#     return data
# # JSONResponse(status_code=500, content={"Failed to connect to the service": str(e)})

# except requests.exceptions.RequestException as e:
#     msg = f"Failed to connect to the service: {e}"
#     raise HTTPException(status_code=500, detail=msg)
# except Exception as e:
#     msg = f"Error with the endpoint"
#     raise HTTPException(status_code=500, detail=msg)
