from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# import uvicorn
# import asyncio

from .core.config import settings
from .routers.api_v1.api import api_router
from .utils.security import generate_api_key
from .utils.generic import Constants

# from .utils.backend_tasks import app as app_rocketry

load_dotenv()

description = "Este API facilita la integración de datos con proyectos forestales para mejorar su trazabilidad - Suan"
title = "Suan Trazabilidad API"
version = "0.0.1"
contact = {"name": "Suan"}

suantrazabilidad = FastAPI(
    title=title,
    description=description,
    contact=contact,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=True,
)

root_router = APIRouter()

suantrazabilidad.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.middleware.gzip import GZipMiddleware

suantrazabilidad.add_middleware(GZipMiddleware, minimum_size=1000)


##################################################################
# Start of the endpoints
##################################################################


@suantrazabilidad.get("/")
async def root():
    """Basic HTML response."""
    body = (
        "<html>"
        "<body style='padding: 10px;'>"
        "<h1>Bienvenidos al API de la Billetera de Plataforma</h1>"
        "<div>"
        "Check the docs: <a href='/docs'>here</a>"
        "</div>"
        "</body>"
        "</html>"
    )

    return HTMLResponse(content=body)


@suantrazabilidad.get("/generate-api-key")
async def get_new_api_key():
    api_key = generate_api_key()
    return {"api_key": api_key}


@suantrazabilidad.get(path="/query-tip")
async def query_tip():
    tip = Constants().KOIOS_API.get_tip()
    return tip[0]


@suantrazabilidad.get(path="/ogmios1")
async def ogmios1():
    import ogmios

    with ogmios.Client(
        host="ogmiosbackend.test.api.local", port=1337, secure=False, http_only=False
    ) as client:
        print(client.connection)
        tip, _ = client.query_ledger_tip.execute()

    return tip


@suantrazabilidad.get(path="/ogmios")
async def ogmios():
    import websockets
    import ogmios.model.ogmios_model as om
    import ogmios.model.model_map as mm
    import os

    url = "ws://ogmiosbackend.test.api.local:1337"
    OGMIOS_URL = os.getenv("OGMIOS_URL")
    print(OGMIOS_URL)
    async with websockets.connect(url) as websocket:
        rpc_version = "2.0"
        method = mm.Method.queryLedgerState_tip.value
        pld = om.QueryLedgerStateTip(
            jsonrpc=rpc_version,
            method=method,
            id=None,
        )
        await websocket.send(pld.json())
        response = await websocket.recv()

    return response


@suantrazabilidad.get(path="/ogmios-requests")
async def ogmiosRequests():

    import requests

    import ogmios.model.ogmios_model as om
    import ogmios.model.model_map as mm

    # URL to send the request to
    url = "http://ogmiosbackend.test.api.local:1337"

    rpc_version = "2.0"
    method = mm.Method.queryLedgerState_tip.value
    pld = om.QueryLedgerStateTip(
        jsonrpc=rpc_version,
        method=method,
        id=None,
    )

    response = requests.post(url, data=pld.json())

    # Send a GET request
    # response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        print(data)
    else:
        print(f"Failed to retrieve data: {response.status_code}")


suantrazabilidad.include_router(root_router)
suantrazabilidad.include_router(api_router, prefix=settings.API_V1_STR)


# async def main():
#     "Run Rocketry and FastAPI"
#     server = Server(
#         config=uvicorn.Config(suantrazabilidad, workers=1, loop="asyncio", port=8083)
#     )

#     api = asyncio.create_task(server.serve())
#     sched = asyncio.create_task(app_rocketry.serve())

#     await asyncio.wait([sched, api])


if __name__ == "__main__":
    # Use this for debugging purposes only
    # logger.warning("Running in development mode. Do not run like this in production.")
    import uvicorn

    uvicorn.run(
        suantrazabilidad, host="0.0.0.0", port=8001, reload=False, log_level="debug"
    )

    # import logging

    # logger = logging.getLogger("rocketry.task")
    # logger.addHandler(logging.StreamHandler())
    # asyncio.run(main())
