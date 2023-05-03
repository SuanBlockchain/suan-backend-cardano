from fastapi import APIRouter, Depends, HTTPException
from routers.api_v1.endpoints import pydantic_schemas
from typing import List
from sqlalchemy.orm import Session

from db.dblib import get_db
from db.models import dbmodels

router = APIRouter()


@router.get(
    "/projects",
    summary="Get current available projects",
    response_description="List of projects",
    response_model=List[pydantic_schemas.ProjectBase],
)
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_projects = db.query(dbmodels.Projects).offset(skip).limit(limit).all()
    if db_projects is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_projects


@router.post(
    "/projects/",
    summary="Create Project",
    response_description="Project saved in database",
    response_model=pydantic_schemas.ProjectBase,
)
def save_project(project: pydantic_schemas.ProjectBase, db: Session = Depends(get_db)):
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
