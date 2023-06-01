from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.models import dbmodels

from db.dblib import get_db

router = APIRouter()




@router.get(
    "/forms-db/",
    status_code=200,
    summary="Get available forms in local db",
    response_description="Projects from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_kobo(db: Session = Depends(get_db)) -> dict:
    """Get the forms available in local db\n
    """
    result = {}
    results = db.query(dbmodels.Kobo_forms.koboform_id).all()
    if results !=[]:
        db_kobo_id = [t[0] for t in results]
        result["results"] = db_kobo_id
    return result