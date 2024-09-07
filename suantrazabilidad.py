from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uuid

from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime, timedelta, timezone
from celery import Celery

from suantrazabilidadapi.celery.main import lifespan
from suantrazabilidadapi.core.config import settings
from suantrazabilidadapi.routers.api_v1.api import api_router
from suantrazabilidadapi.utils.blockchain import CardanoNetwork
from suantrazabilidadapi.utils.security import generate_api_key
from suantrazabilidadapi import __version__
from suantrazabilidadapi.celery.tasks import send_push_notification

################################################################
load_dotenv()

description = "Este API es el backend de la wallet de Plataforma - Suan"
title = "Suan Trazabilidad API"
version = __version__
contact = {"name": "Suan"}


#########################
# Section to declare the celery app
#########################
celery_app = Celery(
    "suantrazabilidad",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)
# celery_app.autodiscover_tasks(["suantrazabilidadapi"])
celery_app.conf.update(
    imports=["suantrazabilidadapi.celery.tasks"],
    # CELERY_TASK_DEFAULT_EXPIRES=None,
    # CELERY_TASK_DEFAULT_EXPIRES=timedelta(minutes=10),
    # task_always_eager=True,
    # broker_transport_options={
    #     "region": "us-east-2",
    #     "queue_name_prefix": "celery-",
    #     "visibility_timeout": 3600,
    #     "polling_interval": 1,
    #     # "sts_role_arn": "arn:aws:iam::036134507423:user/suan-luis.restrepo",
    #     # "predefined_queues": {
    #     #     "celery": {
    #     #         "url": "https://sqs.us-east-2.amazonaws.com/036134507423/TempTesting"
    #     #     }
    #     # },
    # },
    # CELERY_BEAT_SCHEDULE={
    #     "send_access_token": {
    #         "task": "send_access_token",
    #         "schedule": 30,
    #         "options": {"queue": "celery"},
    #     },
    # },
)

celery_app.conf.beat_schedule = {
    "run-me-every-thirty-seconds": {
        "task": "access-token-task",
        "schedule": 120,
        "options": {"queue": "celery"},
    }
}


#########################
# FastAPI declaration
#########################
suantrazabilidad = FastAPI(
    title=title,
    description=description,
    contact=contact,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=__version__,
    debug=True,
    lifespan=lifespan,
)

root_router = APIRouter()

suantrazabilidad.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# suantrazabilidad.add_middleware(HTTPSRedirectMiddleware)

# from fastapi.middleware.trustedhost import TrustedHostMiddleware

# suantrazabilidad.add_middleware(
#     TrustedHostMiddleware, allowed_hosts=["example.com", "*.example.com"]
# )

# Simple in-memory session store
# TODO: handle cache memory with redis
sessions = {}


suantrazabilidad.add_middleware(GZipMiddleware, minimum_size=1000)


#########################
# Section to set additional tools to handle middleware
#########################
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


# def get_session(request: Request) -> Optional[dict]:
#     session_id = request.cookies.get("session_id")
#     return sessions.get(session_id)


# def on_session_start(session_id: str):
#     # Event triggered when a new session starts
#     print(f"New session started with ID: {session_id}")
#     # Additional logic for when a session starts can go here
#     CardanoNetwork().check_ogmios_service_health()


##################################################################
# Start of the endpoints
##################################################################


@suantrazabilidad.get("/push/{device_token}")
async def notify(device_token: str):
    send_push_notification.delay(device_token)
    return {"message": "Notification sent"}


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

    uvicorn.run(
        suantrazabilidad, host="0.0.0.0", port=8001, reload=False, log_level="debug"
    )
