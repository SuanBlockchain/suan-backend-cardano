from fastapi import APIRouter

from .simpleTx import router as routerSimpleTx
from .complexTx import router as routerComplexTx
from .orderTx import router as routerOrders
from .signSubmit import router as routerSignSubmit


intermediate_router = APIRouter()

intermediate_router.include_router(routerSimpleTx)
intermediate_router.include_router(routerComplexTx)
intermediate_router.include_router(routerOrders)
intermediate_router.include_router(routerSignSubmit)
