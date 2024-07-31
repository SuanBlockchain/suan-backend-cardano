from fastapi import APIRouter, HTTPException
import websockets
import ogmios.model.ogmios_model as om
import ogmios.model.model_map as mm
import json
import requests

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


if not Constants.COPILOT_SERVICE_DISCOVERY_ENDPOINT:

    @router.get(path="/ogmios-health")
    async def ogmiosRequests():
        """Get ogmios health statistics. This endpoint only works in localhost"""

        try:
            url = f"http://{Constants.OGMIOS_URL}:{Constants.OGMIOS_PORT}/health"

            # response = requests.post(url, data=pld.json())
            response = requests.get(url)

            # Parse the JSON response
            data = response.json()

            return data
        except Exception as e:
            msg = f"Error with the endpoint"
            raise HTTPException(status_code=500, detail=msg)
