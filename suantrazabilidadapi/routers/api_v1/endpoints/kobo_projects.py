from fastapi import APIRouter, Depends, HTTPException
from routers.api_v1.endpoints import pydantic_schemas
from typing import List
from sqlalchemy.orm import Session

from db.dblib import get_db
from db.models import dbmodels
from kobo import kobo_api as kobo

router = APIRouter()


@router.get(
    "/all/",
    status_code=200,
    summary="Get all the data",
    response_description="Projects from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_kobo():
    db_projects = kobo.make_kobo_request()
    if db_projects is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_projects


@router.get(
    "/projects-kobo/{kobo_id}",
    status_code=200,
    summary="Get the project from Kobo based on Kobo Id",
    response_description="Project from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_kobo(kobo_id: str):
    db_projects = kobo.make_kobo_request(kobo_id)
    if db_projects is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_projects


@router.post(
    "/projects/",
    status_code=201,
    summary="Create Project",
    response_description="Project saved in database",
    response_model=pydantic_schemas.ProjectBase,
)
async def save_project(
    project: pydantic_schemas.ProjectBase, db: Session = Depends(get_db)
):
    db_project = dbmodels.Projects(
        name=project.name,
        country=project.country,
        sector=project.sector,
        url=project.url,
        owner=project.owner,
        uid=project.uid,
        kind=project.kind,
        asset_type=project.asset_type,
        version_id=project.version_id,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project
