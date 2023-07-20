from fastapi import APIRouter, Depends
import json
from sqlalchemy.orm import Session
import pandas as pd

from suantrazabilidadapi.db.dblib import get_db
from suantrazabilidadapi.utils.graphqlClass import Plataforma, S3Files
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
    bucket_name = "plataforma.docs"
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

        response_list = []
        s3_msgs = []

        for data in filtered_list:
            project_id = data["_id"]
            response = plataforma.getProjects(project_id)

            if response["success"] == True:
            
                if response["data"]["data"]["getProduct"] is None:

                    # Values specific to the project table
                    project_name = data["A_asset_names"]
                    project_description = data["A_description"]
                    project_category = data["A_category"]

                    response = plataforma.createProject(project_id, project_name, project_description, project_category)

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
                                print("Nothing to update in the dictionary")

                            if fixed_index != 0:
                                filtered_data.update(someJson_dict)

                        except ValueError:
                            next
                    
                    responseFeatures = plataforma.createFeatures(project_id, filtered_data)
                    response.update(responseFeatures)
                    print(response)

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
                                    s3_url = f'{s3Root}/{bucket_name}/{project_id}/{filename}'
                                    print(s3_url)
                                    responseDocuments = plataforma.createDocument(feature_id, s3_url)
                                    print(responseDocuments)
                    s3_msgs_dict = {project_id: s3_msgs}

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
            if s3_msgs_dict != {}:
                response_list.append(response.update(s3_msgs_dict))
            else:
                response_list.append(response)
    else:
        response_list = {
            "success": True,
            "data": "Problems fetching the data"
        }
    return {"results": response_list}
