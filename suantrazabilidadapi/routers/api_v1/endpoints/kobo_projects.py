from fastapi import APIRouter, Depends, HTTPException
from routers.api_v1.endpoints import pydantic_schemas
from typing import List, Any
from sqlalchemy.orm import Session

from db.dblib import get_db
from db.models import dbmodels
from kobo import kobo_api as kobo
import io
import pandas as pd

router = APIRouter()


@router.get(
    "/all-projects/",
    status_code=200,
    summary="Get all data",
    response_description="Projects from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_kobo() -> dict:
    """Get all kobo data available for any project and any form.\n 
        No updates or creation of records in PostgresQl DB.\n
    """
    db_projects_forms = kobo.generic_kobo_request()
    if db_projects_forms is None:
        raise HTTPException(status_code=404, detail="Problems getting project data from Kobo")
    return db_projects_forms

@router.get(
    "/projects-kobo/{kobo_id}/",
    status_code=200,
    summary="Get the data from specific form",
    response_description="Data from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_projects_from_kobo_by_id(kobo_id: str):
    """Get kobo data by filtering from kobo_id.\n 
        It just query kobo database and get all the data available in the specified form.\n
        No updates or creation of records in PostgresQl DB.\n
        **kobo_id**: represents the kobo_id for the form. For example: kobo_id = a3amV423RwsTrQgTu8G4mc.\n
    """
    db_projects_form = kobo.generic_kobo_request(kobo_id)
    if db_projects_form is None:
        raise HTTPException(status_code=404, detail=f"Project with {kobo_id} not found")
    return db_projects_form

@router.post(
    "/kobo-forms/",
    status_code=201,
    summary="Create kobo forms in kobo_forms table",
    response_description="Kobo forms created",
)
async def create_koboForms(db: Session = Depends(get_db)) -> dict:
    """Create generic data associated to the form itself.\n 
        This endpoint is useful when new form is created in Kobo so it needs to be registered in DB.\n
    """

    SUANBLOCKCHAIN = "suanblockchain"
    DEPLOYED = True
    S = "shared"
    desc_name_1 = "revision"
    desc_name_2 = "version"
    
    db_projects_forms = kobo.generic_kobo_request()
    if db_projects_forms is None:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        filtered_forms = []
        result = {}
        results = db.query(dbmodels.Kobo_forms.koboform_id).all()
        koboform_id = [t[0] for t in results]
        for project_form in db_projects_forms["results"]:
            uid = project_form["uid"]
            if uid not in koboform_id: # if form is not yet there in DB
                owner_username = project_form["owner__username"]
                has_deployment = project_form["has_deployment"]
                status = project_form["status"]
                name = project_form["name"]
                if owner_username == SUANBLOCKCHAIN and has_deployment == DEPLOYED and status == S and desc_name_1 in name and desc_name_2 in name:
                    
                    # Here is the implementation of the dynamic creation of the tables following excel schema
                    for file in project_form["downloads"]:
                        for v in file.values():
                            if v == "xls":

                                url = file["url"].split("?")[0][:-1]+'.xls'
                    form_format = kobo.kobo_api(url)
                    if form_format.status_code == 200:
                        data = pd.read_excel(io.BytesIO(form_format.content))
                        print(data)
                        with open(f'./{uid}.xls', 'wb') as file:
                            file.write(form_format.content)
                        print('Excel file format sucessfully Downloaded: ', uid)
                    else:
                        print('Failed to download the file: ', uid)

                    country = project_form["settings"]["country"]
                    if country != []:
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
            else:
                filtered_forms.append({f'Koboform with uid {uid} already created'})
        result["results"] = filtered_forms
    
    return result

@router.post("/{command_name}/",
    status_code=201,
    summary="Create kobo data in kobo_data table",
    response_description="Kobo data created",
)
async def create_dataForms(command_name: pydantic_schemas.KoboFormId, db: Session = Depends(get_db)) -> dict:
    """Create data for all the existing projects.\n 
        It creates only non existing data, which means that data already existing is ignored and not updated.\n
        It can be slow when there is many data in kobo as it is not filtering by date so
        it takes all the available data registries and check one by one if created in PostgresQL DB.\n
        Command_names: \n
        **parcelas**: represents the form with kobo_id = aAfruCuf8SbUd4jaztbmto\n
        **caracterizacion**: represents the form with kobo_id = a44ciRM8GHh5XHyJu4XEKn\n
        **postulacion**: represents the form with kobo_id = avJvoP4AH7Kj2LgVrdwdpj\n
    """
    prefix1 = ""
    if command_name is pydantic_schemas.KoboFormId.parcelas:
        kobo_id = "aAfruCuf8SbUd4jaztbmto"
        prefix1 = "A_data"
    elif command_name is pydantic_schemas.KoboFormId.caracterizacion:
        kobo_id = "a44ciRM8GHh5XHyJu4XEKn"
    elif command_name is pydantic_schemas.KoboFormId.postulacion:
        kobo_id = "avJvoP4AH7Kj2LgVrdwdpj"

    data = kobo.generic_kobo_request(kobo_id)
    if data == []:
        raise HTTPException(status_code=404, detail="Problems getting data or data empty")
    else:
        data_list = []
        result = {}
        db_kobo_id = []
        query = db.query(dbmodels.Kobo_forms.id).filter(dbmodels.Kobo_forms.koboform_id == kobo_id)
        forms_table_id = query.first()[0]
        query = db.query(dbmodels.Kobo_data.kobo_id).filter(dbmodels.Kobo_data.id_form == forms_table_id)
        results = query.all()
        if results !=[]:
            db_kobo_id = [t[0] for t in results]
        for item in data["results"]:
            _id = item["_id"]
            suanID = item["I_suanID"]
            query = db.query(dbmodels.Projects.id).filter(dbmodels.Projects.suanid == suanID)
            project_table_id = query.first()[0]
            if _id not in db_kobo_id or results == []:
                data_set = dbmodels.Kobo_data(
                    id_form = forms_table_id,
                    id_suan = project_table_id,
                    username = item.get(f'{prefix1}/A_username', ""),
                    # username = item["username"],
                    phonenumber = item["phonenumber"],
                    kobo_id = _id,
                    submission_time = item["_submission_time"],
                    text = item.get(f'{prefix1}/text', ""),
                    geopoint_map = item.get(f'{prefix1}/geopoint_map', ""),
                    annotate = item.get(f'{prefix1}/annotate', ""),
                    text_001 = item.get(f'{prefix1}/text_001', ""),
                    geotrace = item.get(f'{prefix1}/geotrace', ""),
                    text_002 = item.get(f'{prefix1}/text_002', ""),
                    geoshape = item.get(f'{prefix1}/geoshape', ""),
                    geopoint_hide = item.get(f'{prefix1}/geopoint_hide', ""),
                    audit = item.get("meta/audit", "")
                )
                data_list.append(data_set)
                db.add(data_set)
                db.commit()
                db.refresh(data_set)
            else:
                data_list.append({f'Data set with _id: {_id} already exists in database'})
        result["results"] = data_list
    
    return result



