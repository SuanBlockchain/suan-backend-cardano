from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from db.models import dbmodels
from db.dblib import engine

from routers.api_v1.api import api_router
from core.config import settings


database_flag = "postgresql"  # Other option could be dynamodb

description = "Este API facilita la integración de datos con proyectos forestales para mejorar su trazabilidad - Suan"
title = "Suan Trazabilidad API"
version = "0.0.1"
contact = {"name": "Suan"}

dbmodels.Base.metadata.create_all(bind=engine)

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


# @root_router.get("/api/v1", status_code=200)
@suantrazabilidad.get("/")
async def root():
    return {"message": "SuanTrazabilidad Api"}


suantrazabilidad.include_router(root_router)
suantrazabilidad.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        suantrazabilidad, host="0.0.0.0", port=8001, reload=False, log_level="debug"
    )
