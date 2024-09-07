from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
from celery import Celery


from .core.config import settings
from .routers.api_v1.api import api_router
from .utils.security import generate_api_key
from . import __version__
from .celery.main import lifespan
from .celery.tasks import send_push_notification

description = "Este API facilita la integración de datos con proyectos forestales para mejorar su trazabilidad - Suan"
title = "Suan Trazabilidad API"
version = __version__
contact = {"name": "Suan"}


# @asynccontextmanager
# async def lifespan(app: FastAPI):

#     # Define the watchmedo command
#     watchmedo_command = [
#         "watchmedo",
#         "auto-restart",
#         "--directory=./",
#         "--pattern=*.py",
#         "--recursive",
#         "--",
#         "celery",
#         "-A",
#         "suantrazabilidadapi.app.celery",
#         "worker",
#         "--loglevel",
#         "info",
#     ]

#     # Start the watchmedo command as a subprocess
#     process = await asyncio.create_subprocess_exec(*watchmedo_command)
#     print("watchmedo started")

#     try:
#         yield
#     finally:
#         # Terminate the subprocess when the application shuts down
#         process.send_signal(signal.SIGTERM)
#         await process.wait()
#         print("watchmedo terminated")

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

#########################
# Section to declare the celery app
#########################
celery_app = Celery(
    "app",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(
    imports=["suantrazabilidadapi.celery.tasks"],
)

celery_app.conf.beat_schedule = {
    "run-me-every-thirty-seconds": {
        "task": "schedule_task",
        "schedule": 120,
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
    version=version,
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


suantrazabilidad.add_middleware(GZipMiddleware, minimum_size=1000)


# class SuppressLogsMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         if request.url.path == "/":
#             # Replace the logger with a no-op logger to suppress logs
#             import logging

#             logging.getLogger("uvicorn.access").disabled = True
#         response = await call_next(request)
#         if request.url.path == "/":
#             # Re-enable the logger after the request is processed
#             logging.getLogger("uvicorn.access").disabled = False
#         return response


# suantrazabilidad.add_middleware(SuppressLogsMiddleware)


sessions = {}


# Middleware to handle sessions
# @suantrazabilidad.middleware("http")
# async def session_middleware(request: Request, call_next):
#     session_id = request.cookies.get("session_id")
#     if not session_id or session_id not in sessions:
#         session_id = str(uuid.uuid4())
#         sessions[session_id] = {"started": True}

#         CardanoNetwork().check_ogmios_service_health()

#     request.state.session_id = session_id
#     expire_time = datetime.now(timezone.utc) + timedelta(minutes=10)
#     response = await call_next(request)

#     response.set_cookie(
#         key="session_id",
#         value=session_id,
#         httponly=True,
#         expires=expire_time,
#         secure=True,
#     )
#     return response


##################################################################
# Start of the endpoints
##################################################################


@suantrazabilidad.get("/push/{devices_token}")
async def notify(devices_token: str):
    send_push_notification.delay(devices_token)
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
