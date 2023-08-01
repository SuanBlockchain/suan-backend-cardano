from fastapi import APIRouter, Depends
import json
from sqlalchemy.orm import Session
import pandas as pd

from suantrazabilidadapi.db.dblib import get_db
from suantrazabilidadapi.utils.projectClass import Plataforma, S3Files
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
        summary="Put registered data in Plataforma for related projects",
        response_description="Succesfully project created"
        )
def put_project(db: Session = Depends(get_db)) -> dict:

    name_list = []
    format_list = []
    proyecto_list = []
    featureName_list = []
    featureType_list = []

    form_id = "avJvoP4AH7Kj2LgVrdwdpj"
    bucket_name = "kiosuanbcrjsappcad3eb2dd1b14457b491c910d5aa45dd145518-dev"
    s3Root = "https://s3.amazonaws.com"
    
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

        s3_msgs = []
        final_response = {}
        response_list = []

        for data in filtered_list:
            project_id = data["_id"]
            r = plataforma.getProjects(project_id)

            if r["success"] == True:
                
                # This assumes that the project does not exists at all. If project exists in Dynamo the update process is ignored.
                #TODO: Create an endpoint to update registries for existing projects.
                if r["data"]["data"]["getProduct"] is None:

                    # Values specific to the project table
                    project_name = data["A_asset_names"]
                    project_description = data["A_description"]
                    project_category = data["A_category"]

                    project_response = plataforma.createProject(project_id, project_name, project_description, project_category)

                    # Values specific to the product features
                    fixed_index = 0
                    filtered_data = {}
                    fileJson ={}
                    for k, v in data.items():
                        # try is used here to handle the error when the index(k) is not found
                        try:
                            index = name_list.index(k)
                            if format_list[index] not in ["Json", "File"] and v is not None:
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
                            elif format_list[index] == "File" and v is not None:
                                # Special treatment to file type data
                                fileJson[featureName_list[index]] = v
                            else:
                                # Fill the generic productFeatures non existing in reference table
                                filtered_data["GLOBAL_TOKEN_NAME"] = project_id

                            if fixed_index != 0:
                                filtered_data.update(someJson_dict)

                        except ValueError:
                            next
                    
                    responseFeatures = plataforma.createFeatures(project_id, filtered_data)

                    # Handle attachments
                    files = form.get_ProjectAttachments(project_id)
                    s3files = S3Files()
                    for (filename, url) in files:
                        s3_ok = s3files.upload_file(bucket_name, project_id, filename)
                        s3_msgs.append(f'{filename} uploaded? {s3_ok}')
                        if s3_ok:
                            responseFileFeatures = plataforma.createFeatures(project_id, fileJson)
                            for fileFeatures in responseFileFeatures:
                                if fileFeatures["success"]:
                                    feature_id = fileFeatures["data"]["data"]["createProductFeature"]["id"]
                                    s3_url = f'{s3Root}/{bucket_name}/public/{project_id}/{filename}'
                                    print(s3_url)
                                    responseDocuments = plataforma.createDocument(feature_id, s3_url)
                                else:
                                    responseDocuments = {
                                        "success": False,
                                        "error": f'Error creating document feature for file: {filename}'
                                    }
                        else:
                            responseDocuments = {
                                "success": False,
                                "error": f'Could not upload file into S3: {filename}'
                            }

                    final_response = {
                            "project": project_response,
                            "features": responseFeatures,
                            "documents": responseDocuments
                            
                        }
                else:
                    final_response = {
                        "success": True,
                        "msg": "Project already exists in DynamoDB",
                        "data": r["data"]
                    }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        
            response_list.append(final_response)
    else:
        response_list = [{
            "success": True,
            "data": "Problems fetching the data"
        }]
    

    return {"results": response_list}
