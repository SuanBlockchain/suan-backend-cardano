from fastapi import APIRouter

from .endpoints import kobo_projects


api_router = APIRouter()
api_router.include_router(kobo_projects.router, prefix="/kobo", tags=["Kobo"])