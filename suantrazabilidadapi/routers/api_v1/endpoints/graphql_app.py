from fastapi import APIRouter
import json

from suantrazabilidadapi.utils.graphqlClass import Plataforma
from suantrazabilidadapi.kobo.manager import Manager
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas

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
        "/plataforma/{command_name}",
        status_code=200,
        summary="Put register data in Plataforma for related projects",
        response_description="Succesfully project created"
        )
def put_project() -> dict:

    form_id = "avJvoP4AH7Kj2LgVrdwdpj"
    
    km = Manager()

    form = km.get_form(form_id)
    form.fetch_data()
    df = form.data

    df_json = json.loads(df.to_json())

    name_dict = df_json["A_asset_names"]
    description_dict = df_json["A_description"]

    #TODO: pack the name_dict and description_dict into a new dict with both name and description ready
    categoryID = "PROYECTO_PLANTACIONES"
    isActive = False

    plataforma = Plataforma()
    result = plataforma.createProject(name_dict, categoryID, isActive)

    return {"results": result}
