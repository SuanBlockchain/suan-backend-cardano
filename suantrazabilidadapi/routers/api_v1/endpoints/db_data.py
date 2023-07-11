from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from suantrazabilidadapi.db.models import dbmodels

from suantrazabilidadapi.db.dblib import get_db

router = APIRouter()




@router.get(
    "/projects-db/",
    status_code=200,
    summary="Get available projects in local db",
    response_description="Projects from local db",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_db(skip: int= 0, limit: int = 100, db: Session = Depends(get_db)) -> dict:
    """Get the projects available in local db\n
    """
    result = {}
    results = db.query(dbmodels.Projects).offset(skip).limit(limit).all()
    if results is not None:
        msg = f'No projects found in local DB!!'
        result = {"results": msg}
    result = {"results": results}
    return result