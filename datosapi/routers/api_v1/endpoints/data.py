from fastapi import APIRouter, HTTPException
import httpx

# from datosapi.routers.api_v1.endpoints import pydantic_schemas


router = APIRouter()

@router.get("/get-polygon/", status_code=200,
summary="Get detail info about a polygon from land id",
    response_description="Land details",)

async def getPolygon(id_catastral: str):
    """Get detail info about a polygon from land id
    """
    try:
        BASE_URL = "https://services2.arcgis.com/RVvWzU3lgJISqdke/ArcGIS/rest/services/CATASTRO_PUBLICO_Noviembre_2023_gdb/FeatureServer/17/query?"
        query = f"where=NUMERO_DEL_PREDIO IN ('{id_catastral}')"
        tail_options = "&objectIds=&time=&resultType=none&outFields=*&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnDistinctValues=false&cacheHint=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&sqlFormat=none&f=pjson&token="

        URL = BASE_URL + query + tail_options
        print(URL)

        response = httpx.get(URL)
        response.raise_for_status()
        result = response.json()
        return result
       


    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
