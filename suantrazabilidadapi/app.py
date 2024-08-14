from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uuid
from datetime import datetime, timedelta, timezone
import os
from contextlib import asynccontextmanager
import asyncio
import signal


from .core.config import settings, config
from .routers.api_v1.api import api_router
from .utils.security import generate_api_key
from . import __version__
from .utils.blockchain import CardanoNetwork

description = "Este API facilita la integración de datos con proyectos forestales para mejorar su trazabilidad - Suan"
title = "Suan Trazabilidad API"
version = __version__
contact = {"name": "Suan"}


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Define the watchmedo command
    watchmedo_command = [
        "watchmedo",
        "auto-restart",
        "--directory=./",
        "--pattern=*.py",
        "--recursive",
        "--",
        "celery",
        "-A",
        "suantrazabilidadapi.app.celery",
        "worker",
        "--loglevel",
        "info",
    ]

    # Start the watchmedo command as a subprocess
    process = await asyncio.create_subprocess_exec(*watchmedo_command)
    print("watchmedo started")

    try:
        yield
    finally:
        # Terminate the subprocess when the application shuts down
        process.send_signal(signal.SIGTERM)
        await process.wait()
        print("watchmedo terminated")


suantrazabilidad = FastAPI(
    title=title,
    description=description,
    contact=contact,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=version,
    debug=True,
    # lifespan=lifespan,
)

from celery import Celery
import time

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

security = config(section="security")

# TODO: use SSM store parameters to store the username and password in rabbitmq.yml
local_rabbit_mq_username = security["local_rabbit_mq_username"]
local_rabbit_mq_password = security["local_rabbit_mq_password"]

rabbitmq_endpoint = os.getenv("RABBIT_MQ_ENDPOINT")
# rabbitmq_user = os.getenv("RABBIT_MQ_USERNAME")
# rabbitmq_password = os.getenv("RABBIT_MQ_PASSWORD")
redis_endpoint = os.getenv("REDIS_ENDPOINT")

broker_url = f"amqps://{local_rabbit_mq_username}:{local_rabbit_mq_password}@{rabbitmq_endpoint}:5671"
backend_url = f"redis://{redis_endpoint}:6379/0"

celery = Celery(
    "app",
    broker=broker_url,
    # backend=backend_url,
)

celery.conf.update(
    broker_transport_options={
        "region": "us-east-2",
        "queue_name_prefix": "celery-",
        "visibility_timeout": 3600,
        "polling_interval": 1,
    },
    task_default_queue="default",
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
    },
)


@celery.task(name="app.send_push_notification")
def send_push_notification(device_token: str):
    time.sleep(10)  # simulates slow network call to firebase/sns
    with open("notification.log", mode="a") as notification_log:
        response = f"Successfully sent push notification to: {device_token}\n"
        notification_log.write(response)


@suantrazabilidad.get("/push/{device_token}")
async def notify(device_token: str):
    send_push_notification.delay(device_token)
    return {"message": "Notification sent"}


sessions = {}


# Middleware to handle sessions
@suantrazabilidad.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"started": True}

        CardanoNetwork().check_ogmios_service_health()

    request.state.session_id = session_id
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    response = await call_next(request)

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        expires=expire_time,
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
