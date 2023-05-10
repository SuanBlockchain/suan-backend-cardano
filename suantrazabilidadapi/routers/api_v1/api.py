from fastapi import APIRouter

from .endpoints import kobo_projects, admin_api


api_router = APIRouter()
api_router.include_router(kobo_projects.router, prefix="/kobo", tags=["Kobo"])
api_router.include_router(admin_api.router, prefix="/projects", tags=["Projects"])
