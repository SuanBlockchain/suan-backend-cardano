from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uuid
import os
from datetime import datetime, timedelta


from .core.config import settings
from .routers.api_v1.api import api_router
from .utils.security import generate_api_key
from . import __version__
from .utils.blockchain import CardanoNetwork

# from .utils.backend_tasks import app as app_rocketry

load_dotenv()

description = "Este API facilita la integración de datos con proyectos forestales para mejorar su trazabilidad - Suan"
title = "Suan Trazabilidad API"
version = __version__
contact = {"name": "Suan"}

suantrazabilidad = FastAPI(
    title=title,
    description=description,
    contact=contact,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=version,
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

sessions = {}


# Middleware to handle sessions
@suantrazabilidad.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"started": True}

        CardanoNetwork().check_ogmios_service_health()
        print(os.getenv("CHAIN_BACKEND"))

    request.state.session_id = session_id
    expire_time = datetime.now() + timedelta(days=1)
    response = await call_next(request)

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        # expires=expire_time,
        secure=True,
    )
    return response


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
