from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from routers.api_v1.endpoints import pydantic_schemas
from typing import List, Any
from sqlalchemy.orm import Session
import json
import sqlalchemy as sq

from db.dblib import get_db
from db.models import dbmodels
from kobo import kobo_api as kobo
import io
import pandas as pd
import numpy as np
from core.config import config
from kobo import manager

router = APIRouter()

URL_KOBO = "https://kf.kobotoolbox.org/"
API_VERSION = 2
kobo_tokens_dict = config(section="kobo")
MYTOKEN = kobo_tokens_dict["kobo_token"]

SUANBLOCKCHAIN = "suanblockchain"
desc_name_1 = "revision"
desc_name_2 = "version"

column_exclusions = [
    "note",
    "begin_group",
    "end_group"
]


@router.get(
    "/forms/",
    status_code=200,
    summary="Get the list of forms you have access to",
    response_description="List of forms",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_forms_from_kobo() -> dict:
    """Get the list of forms you have access to, and filtered if active, deployed, username = 'suanblockchain' and if the name contains revision and version \n 
        No updates or creation of records in PostgresQl DB.\n
    """

    meta = []

    km = manager.Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)
    my_forms = km.get_forms()
    for form in my_forms:
        deployment_active = form.metadata["deployment__active"]
        has_deployment = form.metadata["has_deployment"]
        owner = form.metadata["owner"]
        name = form.metadata["name"]
        # Filter forms active, deployed and owner username = 'suanblockchain'
        if deployment_active and has_deployment and owner == SUANBLOCKCHAIN and desc_name_1 in name and desc_name_2 in name:
            meta.append(form.metadata)
    
    return {"results": meta}

@router.get(
    "/forms/{form_id}/",
    status_code=200,
    summary="Fetch single form",
    response_description="Data from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_form_by_id(form_id: str):
    """Get form metadata with form_id.\n 
        No updates or creation of records in PostgresQl DB.\n
        **form_id**: represents the form_id for the form. For example: form_id = a3amV423RwsTrQgTu8G4mc.\n
    """
    km = manager.Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)
    form = km.get_form(form_id)
    return { "results": form.metadata }

@router.get(
    "/forms-data/{form_id}/",
    status_code=200,
    summary="Get data submissions from specific form",
    response_description="Data from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_form_data(form_id: str):
    """Get form data with form_id.\n 
        No updates or creation of records in PostgresQl DB.\n
        **form_id**: represents the form_id for the form. For example: form_id = a3amV423RwsTrQgTu8G4mc.\n
    """
    # db_projects_form = kobo.generic_kobo_request(form_id)
    km = manager.Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)
    form = km.get_form(form_id)
    form.fetch_data()
    df = form.data

    return {"results": json.loads(df.to_json())}


@router.post(
    "/forms/upgrade",
    status_code=201,
    summary="Create or upgrade kobo forms tables in postgresql DB",
    response_description="Kobo forms created",
)
async def create_koboForms(db: Session = Depends(get_db)) -> dict:
    """Create or upgrade kobo forms tables in postgresql DB\n 
        This endpoint is useful when a new form is created in Kobo so it needs to be registered in DB.\n
        Or when there are changes in existing forms which requires upgrades in postgresql DB tables.\n
    """
    form_id_list = []
    column_schema_list = []

    km = manager.Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)
    my_forms = km.get_forms()

    msg = f'No forms to update'

    for form in my_forms:
        column_schema = {}
        column_schema_dict = {}
        form_id = form.metadata["uid"]
        deployment_active = form.metadata["deployment__active"]
        has_deployment = form.metadata["has_deployment"]
        owner = form.metadata["owner"]
        name = form.metadata["name"]
        # Filter forms active, deployed and owner username = 'suanblockchain'
        if deployment_active and has_deployment and owner == SUANBLOCKCHAIN and desc_name_1 in name and desc_name_2 in name:

            form = km.get_form(form_id)
            form.fetch_data()
            form.display(columns_as='name', choices_as='name')
            form_bytestring = form.download_form('xls', False)
            form_template = pd.read_excel(io.BytesIO(form_bytestring))
            for index, row in form_template.iterrows():
                type = row["type"]
                if type not in column_exclusions:
                    if type == "text" or "select_one" in type or "select_multiple" in type or type == "file" or type == "image":
                        column_schema = {
                            row["name"]: sq.String
                        }
                    elif type == "integer":
                        column_schema = {
                            row["name"]: sq.Integer
                        }
                    elif type == "date":
                        column_schema = { row["name"]: sq.DateTime}
                    elif type == "decimal":
                        column_schema = { row["name"]: sq.Numeric}

                if column_schema != {}:
                    column_schema_dict.update(column_schema)

            form_id_list.append(form_id)
            column_schema_list.append(column_schema_dict)
        
    msg = dbmodels.kobo_data_tables(form_id_list, column_schema_list)
            
    return { "results": msg}

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



