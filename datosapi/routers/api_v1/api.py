from fastapi import APIRouter, Security

from ...utils.security import get_api_key

from .endpoints import data

api_router = APIRouter()

api_router.include_router(data.router, prefix="/data", tags=["Datos"], dependencies=[Security(get_api_key)])