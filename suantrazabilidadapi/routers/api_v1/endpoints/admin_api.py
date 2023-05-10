from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from db.dblib import get_db
from routers.api_v1.endpoints import pydantic_schemas
from db.models import dbmodels

router = APIRouter()

@router.get(
    "/all-projects",
    summary="Get all projects stored in local database",
    response_description="List of projects",
    response_model=List[pydantic_schemas.ProjectBase],
)
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_projects = db.query(dbmodels.Projects).offset(skip).limit(limit).all()
    if db_projects is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_projects

@router.post(
    "/project/",
    status_code=201,
    summary="Create Project",
    response_description="Project saved in database",
    response_model=pydantic_schemas.ProjectBase,
)
async def save_project(
    project: pydantic_schemas.ProjectBase, db: Session = Depends(get_db)
):
    db_project = dbmodels.Projects(
        suanid=project.suanid,
        name=project.name,
        description=project.description,
        categoryid=project.categoryid,
        status=project.status,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project