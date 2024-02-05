from fastapi import APIRouter, HTTPException
import httpx

# from datosapi.routers.api_v1.endpoints import pydantic_schemas


router = APIRouter()

class Constants:
    BASE_URL = "https://services2.arcgis.com/RVvWzU3lgJISqdke/ArcGIS/rest/services/CATASTRO_PUBLICO_Noviembre_2023_gdb/FeatureServer"
    COMMAND = "query?"

@router.get("/features-1/", status_code=200,
summary="Get generic parameters from land code (Catastro id)",
    response_description="Land details",)

async def features1(id_catastral: str):
    """Get generic parameters from land code (Catastro id)
    """
    try:
        tableNumber = 17
        query = f"where=NUMERO_DEL_PREDIO IN ('{id_catastral}')"
        tail_options = (
            '&objectIds='
            '&time='
            '&resultType=none'
            '&outFields=*'
            '&returnIdsOnly=false'
            '&returnUniqueIdsOnly=false'
            '&returnCountOnly=false'
            '&returnDistinctValues=false'
            '&cacheHint=false'
            '&orderByFields='
            '&groupByFieldsForStatistics='
            '&outStatistics='
            '&having='
            '&resultOffset='
            '&resultRecordCount='
            '&sqlFormat=none'
            '&f=pjson'
            '&token='
        )

        URL = f'{Constants.BASE_URL}/{tableNumber}/{Constants.COMMAND}{query}{tail_options}'
        print(URL)

        response = httpx.get(URL)
        response.raise_for_status()
        result = response.json()
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.get("/features-2/", status_code=200,
summary="Get more precise info from land code (Catastro id)",
    response_description="Land details",)

async def features2(id_catastral: str):
    """Get more precise info from land code (Catastro id)
    """
    try:
        tableNumber = 18
        query = f"where=NUMERO_DEL_PREDIO IN ('{id_catastral}')"
        tail_options = (
            '&objectIds='
            '&time='
            '&resultType=none'
            '&outFields=*'
            '&returnIdsOnly=false'
            '&returnUniqueIdsOnly=false'
            '&returnCountOnly=false'
            '&returnDistinctValues=false'
            '&cacheHint=false'
            '&orderByFields='
            '&groupByFieldsForStatistics='
            '&outStatistics='
            '&having='
            '&resultOffset='
            '&resultRecordCount='
            '&sqlFormat=none'
            '&f=pjson'
            '&token='
        )

        URL = f'{Constants.BASE_URL}/{tableNumber}/{Constants.COMMAND}{query}{tail_options}'

        response = httpx.get(URL)
        response.raise_for_status()
        result = response.json()
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/polygon/", status_code=200,
summary="Get coordinates of the polygon related to the code id (Catastro id)",
    response_description="Polygon details",)

async def features2(id_catastral: str):
    """Get coordinates of the polygon related to the code id (Catastro id)
    """
    try:
        tableNumber = 14
        query = f"where=CODIGO IN ('{id_catastral}')"
        tail_options = (
            '&objectIds='
            '&time='
            '&geometry='
            '&geometryType=esriGeometryPoint'
            '&inSR='
            '&spatialRel=esriSpatialRelIntersects'
            '&resultType=none'
            '&distance=0.0'
            '&units=esriSRUnit_Meter'
            '&relationParam='
            '&returnGeodetic=false'
            '&outFields='
            '&returnGeometry=true'
            '&returnCentroid=false'
            '&returnEnvelope=false'
            '&featureEncoding=esriDefault'
            '&multipatchOption=xyFootprint'
            '&maxAllowableOffset='
            '&geometryPrecision='
            '&outSR='
            '&defaultSR='
            '&datumTransformation='
            '&applyVCSProjection=false'
            '&returnIdsOnly=false'
            '&returnUniqueIdsOnly=false'
            '&returnCountOnly=false'
            '&returnExtentOnly=false'
            '&returnQueryGeometry=false'
            '&returnDistinctValues=false'
            '&cacheHint=false'
            '&orderByFields='
            '&groupByFieldsForStatistics='
            '&outStatistics='
            '&having='
            '&resultOffset='
            '&resultRecordCount='
            '&returnZ=false'
            '&returnM=false'
            '&returnExceededLimitFeatures=true'
            '&quantizationParameters='
            '&sqlFormat=none'
            '&f=pgeojson'
            '&token='
        )


        URL = f'{Constants.BASE_URL}/{tableNumber}/{Constants.COMMAND}{query}{tail_options}'

        response = httpx.get(URL)
        response.raise_for_status()
        result = response.json()
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))