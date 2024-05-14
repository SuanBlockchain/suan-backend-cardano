from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .core.config import settings
from .routers.api_v1.api import api_router
from .utils.security import generate_api_key

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

if __name__ == "__main__":
    # Use this for debugging purposes only
    # logger.warning("Running in development mode. Do not run like this in production.")
    import uvicorn

    uvicorn.run(
        suantrazabilidad, host="0.0.0.0", port=8001, reload=False, log_level="debug"
    )
