from fastapi import APIRouter

from .endpoints import projects_api


api_router = APIRouter()
api_router.include_router(projects_api.router, prefix="/main", tags=["Projects"])
