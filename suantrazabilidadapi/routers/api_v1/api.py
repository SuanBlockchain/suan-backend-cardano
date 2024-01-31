from fastapi import APIRouter, Security

from suantrazabilidadapi.utils.security import get_api_key_for_platform, get_api_key_for_data

from .endpoints import wallet, transactions, data

api_router = APIRouter()

api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"], dependencies=[Security(get_api_key_for_platform)])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"], dependencies=[Security(get_api_key_for_platform)])
api_router.include_router(data.router, prefix="/data", tags=["Datos"], )