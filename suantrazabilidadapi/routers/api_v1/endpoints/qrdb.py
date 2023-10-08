from fastapi import APIRouter, HTTPException
from logging import basicConfig, getLogger, INFO

from suantrazabilidadapi.utils.qrdbClass import Qrdb

logger = getLogger(__name__)
basicConfig(level=INFO)

router = APIRouter()

@router.get(
    "/create-ledger/",
    status_code=200,
    summary="Create a new ledger with the specified name.",
    response_description="Succesful creation",
    # response_model=List[pydantic_schemas.ProjectBase],
)
async def create_ledger(ledger_name: str):
    """
    Create a ledger and wait for it to be active.
    """
    try:
        qrdb = Qrdb()
        result = await qrdb.create_ledger(ledger_name)
        qrdb.wait_for_active(ledger_name)
        return {"result": result}
    except Exception as e:
        msg = f'Unable to create the ledger or ledger already exists with name {ledger_name}!'
        logger.exception(msg)
        raise HTTPException(status_code=500, detail=msg)

@router.get(
    "/create-table/",
    status_code=200,
    summary="Create a new table in ledger DB with the specified name.",
    response_description="Succesful creation",
    # response_model=List[pydantic_schemas.ProjectBase],
)
def create_table(ledger_name: str='project-tracking', table_name: str='default', index_attribute: str='defaultId') -> list:
    """
    Create a table and wait for it to be active.
    """
    try:
        qrdb = Qrdb()
        table_result = qrdb.create_table(ledger_name, table_name)
        index_result = qrdb.create_index(ledger_name, table_name, index_attribute)
        return [
            {"table_result": table_result},
            {"index_result": index_result}
        ]
    except Exception as e:
        msg = f'Error creating table: {table_name} in ledger: {ledger_name}'
        logger.exception(msg)
        raise HTTPException(status_code=500, detail=msg)