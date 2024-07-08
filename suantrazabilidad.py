from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# import asyncio
# import uvicorn

from suantrazabilidadapi.core.config import settings
from suantrazabilidadapi.routers.api_v1.api import api_router
from suantrazabilidadapi.utils.security import generate_api_key
from suantrazabilidadapi.utils.generic import Constants

# from suantrazabilidadapi.utils.backend_tasks import app as app_rocketry

load_dotenv()

description = "Este API es el backend de la wallet de Plataforma - Suan"
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


# class Server(uvicorn.Server):
#     """Customized uvicorn.Server

#     Uvicorn server overrides signals and we need to include
#     Rocketry to the signals."""

#     def handle_exit(self, sig: int, frame) -> None:
#         app_rocketry.session.shut_down()
#         return super().handle_exit(sig, frame)


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


suantrazabilidad.include_router(root_router)
suantrazabilidad.include_router(api_router, prefix=settings.API_V1_STR)


# async def main():
#     "Run Rocketry and FastAPI"
#     server = Server(config=uvicorn.Config(suantrazabilidad, workers=1, loop="asyncio"))

#     api = asyncio.create_task(server.serve())
#     sched = asyncio.create_task(app_rocketry.serve())

#     await asyncio.wait([sched, api])


if __name__ == "__main__":
    # Use this for debugging purposes only
    load_dotenv()
    import logging
    import os
    import uvicorn

    env = os.getenv("env")
    if env == "dev":
        logging.warning(f"Running in {env} mode. Do not run like this in production")
    elif env == "prod":
        logging.warning(f"Running in {env} mode. Change the mode to run locally")

    # logger = logging.getLogger("rocketry.task")
    # logger.addHandler(logging.StreamHandler())
    # asyncio.run(main())

    uvicorn.run(
        suantrazabilidad, host="0.0.0.0", port=8001, reload=False, log_level="debug"
    )
