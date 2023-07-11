from fastapi import APIRouter
import requests

from suantrazabilidadapi.utils.graphqlClass import Plataforma

router = APIRouter()
# Example route to query the external GraphQL server
@router.get("/items/{item_id}")
def get_item_from_graphql(item_id: str) -> dict:
    plataforma = Plataforma()
    result = plataforma.getCategories()

    return result

# Other routes and FastAPI configuration...
