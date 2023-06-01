from fastapi import APIRouter

from .endpoints import kobo_projects, db_data


api_router = APIRouter()
api_router.include_router(kobo_projects.router, prefix="/kobo", tags=["Kobo"])
api_router.include_router(db_data.router, prefix="/data", tags=["Data"])