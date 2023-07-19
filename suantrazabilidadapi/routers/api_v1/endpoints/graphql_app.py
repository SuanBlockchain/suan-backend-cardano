from fastapi import APIRouter, Depends
import json
from sqlalchemy.orm import Session
import pandas as pd
from sqlalchemy import or_, not_

from suantrazabilidadapi.db.dblib import get_db
from suantrazabilidadapi.utils.graphqlClass import Plataforma
from suantrazabilidadapi.kobo.manager import Manager
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas
from suantrazabilidadapi.db.models import dbmodels

router = APIRouter()


@router.get(
        "/get-projects/{command_name}",
        status_code=200,
        summary="Get project info from Plataforma",
        response_description="Project data info"
        )
def get_item_from_graphql(command_name: pydantic_schemas.Form) -> dict:

    #TODO: for the time being use this logic, but it should go to a postgresql table where the forms are mapped with the kobo_id value
    if command_name == "registro":
        form_id = "avJvoP4AH7Kj2LgVrdwdpj"
    
    km = Manager()

    form = km.get_form(form_id)
    form.fetch_data()
    df = form.data

    return {"results": json.loads(df.to_json())}

@router.post(
        "/plataforma/",
        status_code=200,
        summary="Put register data in Plataforma for related projects",
        response_description="Succesfully project created"
        )
def put_project(db: Session = Depends(get_db)) -> dict:

    name_list = []
    format_list = []
    proyecto_list = []
    featureName_list = []
    featureType_list = []

    form_id = "avJvoP4AH7Kj2LgVrdwdpj"
    
    km = Manager()

    form = km.get_form(form_id)
    form.fetch_data()
    df = form.data

    if df is not None:
        # Check the format of features to integrate between kobo and Plataforma app
        query = db.query(dbmodels.Principalform).filter(dbmodels.Principalform.format != "NaN")
        results = query.all()

        for result in results:
            name_list.append(result.name)
            proyecto_list.append(result.proyecto)
            featureName_list.append(result.featureName)
            featureType_list.append(result.featureType)
            format_list.append(result.format)

        data_list = df.to_dict(orient="records")

        # Filter out NaN values from dictionaries
        filtered_list = [
            {key: value for key, value in d.items() if pd.notnull(value)}
            for d in data_list
        ]

        plataforma = Plataforma()

        response_list = []

        for data in filtered_list:
            project_id = data["_id"]
            response = plataforma.getProjects(project_id)

            if response["success"] == True:
            
                if response["data"]["data"]["getProduct"] is None:

                    #TODO: get_attachments by only selected projects. 
                    # Create temp folder to store the downloaded files and then delete them once done.
                    form.get_attachments()
                    # Values specific to the project table
                    project_name = data["A_asset_names"]
                    project_description = data["A_description"]
                    project_category = data["A_category"]

                    # Values specific to the product features
                    fixed_index = 0
                    filtered_data = {}
                    for k, v in data.items():
                        try:
                            index = name_list.index(k)
                            if format_list[index] != "Json" and v is not None:
                                filtered_data[featureName_list[index]] =  v
                            elif format_list[index] == "Json" and k == featureName_list[index]:
                                fixed_index = 0
                                someJson_list = []
                                someJson_list.append({
                                    k: v
                                })
                                someJson_dict = { k: [{ k: v}]}
                                fixed_index = index
                            elif format_list[index] == "Json" and k != featureName_list[index]:
                                someJson_list.append({ k: v })
                                someJson_dict[featureName_list[fixed_index]] = someJson_list
                            else:
                                print("Nothing to update in the dictionary")

                            if fixed_index != 0:
                                filtered_data.update(someJson_dict)

                        except ValueError:
                            next

                    response = plataforma.createProject(project_id, project_name, project_description, project_category, filtered_data)
                
                else:
                    response = {
                        "success": True,
                        "msg": "Project already exists in DynamoDB",
                        "data": response["data"]
                    }
            else:
                response = {
                    "success": False,
                    "msg": "Something happened",
                    "data": response["data"]
                }
        
            response_list.append(response)

    else:
        response_list = {
            "success": True,
            "data": "Form data is empty"
        }
    return {"results": response_list}
