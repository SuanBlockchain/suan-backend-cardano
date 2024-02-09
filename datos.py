import asyncio
import logging
import uvicorn

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from datosapi.routers.api_v1.api import api_router
from datosapi.core.config import settings
from datosapi.scheduler import app as rocketryapp

# from dotenv import load_dotenv
# load_dotenv()

########################
# FastAPI declaration section
########################

description = "Este API facilita la integración de datos con proyectos forestales para mejorar su trazabilidad - Suan"
title = "Suan Trazabilidad API"
version = "0.0.1"
contact = {"name": "Suan"}

datos = FastAPI(
    title=title,
    description=description,
    contact=contact,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=True,
)

root_router = APIRouter()

datos.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@datos.get("/")
async def root():
    """Basic HTML response."""
    body = (
        "<html>"
        "<body style='padding: 10px;'>"
        "<h1>Bienvenidos al API de Suan Trazabilidad</h1>"
    "<div>"
        "Check the docs: <a href='/docs'>here</a>"
        "</div>"
        "</body>"
        "</html>"
    )

    return HTMLResponse(content=body)

datos.include_router(root_router)
datos.include_router(api_router, prefix=settings.API_V1_STR)

########################
# New
########################
class Server(uvicorn.Server):
    """Customized uvicorn.Server
    
    Uvicorn server overrides signals and we need to include
    Rocketry to the signals."""
    def handle_exit(self, sig: int, frame) -> None:
        rocketryapp.session.shut_down()
        return super().handle_exit(sig, frame)


async def main():
    "Run Rocketry and FastAPI"
    server = Server(config=uvicorn.Config(datos, workers=1, loop="asyncio"))

    api = asyncio.create_task(server.serve())
    sched = asyncio.create_task(rocketryapp.serve())

    await asyncio.wait([api, sched])

if __name__ == "__main__":

    # Print Rocketry's logs to terminal
    logger = logging.getLogger("rocketry.task")
    logger.addHandler(logging.StreamHandler())

    # Run both applications
    asyncio.run(main())