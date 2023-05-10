from fastapi import APIRouter, Depends, HTTPException
from routers.api_v1.endpoints import pydantic_schemas
from typing import List
from sqlalchemy.orm import Session

from db.dblib import get_db
from db.models import dbmodels
from kobo import kobo_api as kobo

router = APIRouter()


@router.get(
    "/all-projects/",
    status_code=200,
    summary="Get all the data",
    response_description="Projects from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_kobo():
    db_projects_forms = kobo.generic_kobo_request()
    if db_projects_forms is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_projects_forms

@router.post(
    "/kobo-forms/",
    status_code=201,
    summary="Update kobo forms table",
    response_description="Kobo forms updated",
    # response_model=[pydantic_schemas.KoboFormResponse],
)
async def update_koboForms(db: Session = Depends(get_db)):

    SUANBLOCKCHAIN = "suanblockchain"
    DEPLOYED = True
    S = "shared"
    
    db_projects_forms = kobo.generic_kobo_request()
    if db_projects_forms is None:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        filtered_forms = []
        result = {}
        for project_form in db_projects_forms["results"]:
            owner_username = project_form["owner__username"]
            has_deployment = project_form["has_deployment"]
            status = project_form["status"]
            if owner_username == SUANBLOCKCHAIN and has_deployment == DEPLOYED and status == S:
                country = project_form["settings"].get("country", None)
                if country is not None:
                    country = country[0].get("label", "")
                
                form = dbmodels.Kobo_forms(
                    koboform_id = project_form["uid"],
                    name = project_form["name"],
                    description = project_form["settings"].get("description", ""),
                    organization = project_form["settings"].get("organization", ""),
                    country = country,
                    kind = project_form["kind"],
                    asset_type = project_form["asset_type"],
                    deployment_active = project_form["deployment__active"],
                    deployment_count = project_form["deployment__submission_count"],
                    owner_username = owner_username,
                    has_deployment = has_deployment,
                    status = status
                )
                filtered_forms.append(form)
                db.add(form)
                db.commit()
                db.refresh(form)
        result["results"] = filtered_forms
    return result


@router.get(
    "/projects-kobo/{kobo_id}",
    status_code=200,
    summary="Get the project from Kobo based on Kobo Id",
    response_description="Project from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_kobo(kobo_id: str):
    db_projects_form = kobo.generic_kobo_request(kobo_id)
    if db_projects_form is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_projects_form



