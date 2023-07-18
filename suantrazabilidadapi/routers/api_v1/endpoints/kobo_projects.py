from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sqlalchemy as sq
from sqlalchemy.exc import SQLAlchemyError
import json

from suantrazabilidadapi.db.dblib import get_db
from suantrazabilidadapi.db.models import dbmodels, mixins
from suantrazabilidadapi.kobo.manager import Manager
import io
import pandas as pd
import math

router = APIRouter()

SUANBLOCKCHAIN = "suanblockchain"
desc_name_1 = "revision"
desc_name_2 = "version"

def filter_form(forms) -> list:

    form_list = []

    for form in forms:

        deployment_active = form.metadata["deployment__active"]
        has_deployment = form.metadata["has_deployment"]
        owner = form.metadata["owner"]
        name = form.metadata["name"]
        # Filter forms active, deployed and owner username = 'suanblockchain'
        if deployment_active and has_deployment and owner == SUANBLOCKCHAIN and desc_name_1 in name and desc_name_2 in name:
            form_list.append(form)

    return form_list

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

    km = Manager()
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
async def get_form_by_id(form_id: str) -> dict:
    """Get form metadata with form_id.\n 
        No updates or creation of records in PostgresQl DB.\n
        **form_id**: represents the form_id for the form. For example: form_id = a3amV423RwsTrQgTu8G4mc.\n
    """
    km = Manager()
    form = km.get_form(form_id)
    return { "results": form.metadata }

@router.get(
    "/forms-data/{form_id}/",
    status_code=200,
    summary="Get data submissions from specific form",
    response_description="Data from Kobo",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def get_form_data(form_id: str) -> dict:
    """Get form data with form_id.\n 
        No updates or creation of records in PostgresQl DB.\n
        **form_id**: represents the form_id for the form. For example: form_id = a3amV423RwsTrQgTu8G4mc.\n
    """
    # db_projects_form = kobo.generic_kobo_request(form_id)
    km = Manager()
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
async def create_koboForms() -> dict:
    """Create or upgrade kobo forms tables in postgresql DB\n 
        This endpoint is useful when a new form is created in Kobo so it needs to be registered in DB.\n
        Or when there are changes in existing forms which requires upgrades in postgresql DB tables.\n
    """
    form_id_list = []
    column_schema_list = []

    km = Manager()
    my_forms = km.get_forms()

    msg = f'No forms to update'

    # Filter forms active, deployed and owner username = 'suanblockchain'
    filtered_forms = filter_form(my_forms)

    for form in filtered_forms:
        form_id = form.metadata["uid"]

        form = km.get_form(form_id)
        form.fetch_data()
        # form.display(columns_as='name', choices_as='name')
        form_bytestring = form.download_form('xls', False)
        form_template = pd.read_excel(io.BytesIO(form_bytestring))
        column_schema_dict = mixins.build_schema(form_template)

        form_id_list.append(form_id)
        column_schema_list.append(column_schema_dict)
        
    msg = dbmodels.kobo_data_tables(form_id_list, column_schema_list)
            
    return { "results": msg}

@router.post("/data/upgrade/",
    status_code=201,
    summary="Create kobo data in all existing forms tables",
    response_description="Kobo data created in postgresql DB",
)
async def create_dataForms(db: Session = Depends(get_db)) -> dict:
    """Create data for all kobo forms tables existing in postgresql DB.\n 
        It creates only non existing data, which means that data already existing is ignored and not updated.\n
        It can be slow when there are many data in kobo as it is not filtering by date so
        it takes all the available data registries and check one by one if created in PostgresQL DB.\n
    """

    km = Manager()
    forms = km.get_forms()

    if forms == []:
        raise HTTPException(status_code=404, detail="Forms are empty")
    else:

        filtered_forms = filter_form(forms)

        msgs = []

        for form in filtered_forms:
            # if uid not in koboform_id: # if form is not yet there in DB
            
            form_id = form.metadata["uid"]
            form = km.get_form(form_id)
            form.fetch_data()
            data_frame = form.data

            if data_frame is not None:

                form_bytestring = form.download_form('xls', False)
                form_template = pd.read_excel(io.BytesIO(form_bytestring))
                column_schema_dict = mixins.build_schema(form_template)

                column_schema_dict.update({"kobo_id": sq.Integer})

                table_class = mixins.create_dataType(form_id, column_schema_dict)

                data_list = data_frame.to_dict(orient='records')
                
                filtered_data_list = []
                filtered_data = []
                id_list = []
                data_sets = []
                for data in data_list:
                    _id = data["_id"]
                    id_list.append(_id)
                query = db.query(table_class.kobo_id).filter(table_class.kobo_id.in_(id_list))
                results = query.all()
                if results == []:
                    for data in data_list:
                        filtered_data = {k: None if isinstance(v, float) and math.isnan(v) else v for k, v in data.items() if k in column_schema_dict}
                        filtered_data["kobo_id"] = data["_id"]
                        filtered_data_list.append(filtered_data)

                    for item in filtered_data_list:
                        data_set = table_class(**item)
                        data_sets.append(data_set)
                    for data_set in data_sets:
                        db.add(data_set)
                    try:
                        db.commit()
                        msg = f'Data updated succesfully in postgresQL for form: {form_id}'
                        print(msg)
                        msgs.append(msg)
                    except SQLAlchemyError as e:
                        db.rollback()
                        msg = f'An error occurred during the database commit:", {str(e)} for form: {form_id}'
                        print(msg)
                        msgs.append(msg)
                else:
                    msg = f'No data to update for form: {form_id}'
                    print(msg)
                    msgs.append(msg)
            else:
                msg = f'No data to update for form: {form_id}'
                print(msg)
                msgs.append(msg)
                    
    return { "results": msgs}


@router.post("/data/upgrade/{form_id}/",
    status_code=201,
    summary="Create kobo data in kobo_data table",
    response_description="Kobo data created",
)
async def create_dataFormsById(form_id: str, db: Session = Depends(get_db)) -> dict:
    """Create data for existing Forms using the Id\n 
        It creates only non existing data, which means that data already existing is ignored and not updated.\n
        It can be slow when there is many data in kobo as it is not filtering by date so
        it takes all the available data registries and check one by one if created in PostgresQL DB.\n
        **form_id**: represents the form_id for the form. For example: form_id = a3amV423RwsTrQgTu8G4mc.\n
    """

    km = Manager()
    form = km.get_form(form_id)

    if form == []:
        raise HTTPException(status_code=404, detail="Form not found")
    else:
        form_id = form.metadata["uid"]
        form = km.get_form(form_id)
        form.fetch_data()
        data_frame = form.data

        if data_frame is not None:

            form_bytestring = form.download_form('xls', False)
            form_template = pd.read_excel(io.BytesIO(form_bytestring))
            column_schema_dict = mixins.build_schema(form_template)

            column_schema_dict.update({"kobo_id": sq.Integer})

            table_class = mixins.create_dataType(form_id, column_schema_dict)

            data_list = data_frame.to_dict(orient='records')
            
            filtered_data_list = []
            filtered_data = []
            id_list = []
            data_sets = []
            for data in data_list:
                _id = data["_id"]
                id_list.append(_id)
            query = db.query(table_class.kobo_id).filter(table_class.kobo_id.in_(id_list))
            results = query.all()
            if results == []:
                for data in data_list:
                    filtered_data = {k: None if isinstance(v, float) and math.isnan(v) else v for k, v in data.items() if k in column_schema_dict}
                    filtered_data["kobo_id"] = data["_id"]
                    filtered_data_list.append(filtered_data)

                for item in filtered_data_list:
                    data_set = table_class(**item)
                    data_sets.append(data_set)
                for data_set in data_sets:
                    db.add(data_set)
                try:
                    db.commit()
                    msg = f'Data updated succesfully in postgresQL for form: {form_id}'
                    print(msg)
                except SQLAlchemyError as e:
                    db.rollback()
                    msg = f'An error occurred during the database commit:", {str(e)} for form: {form_id}'
                    print(msg)
            else:
                msg = f'No data to update for form: {form_id}'
                print(msg)
        else:
            msg = f'No data to update for form: {form_id}'
            print(msg)

    return { "results": msg}