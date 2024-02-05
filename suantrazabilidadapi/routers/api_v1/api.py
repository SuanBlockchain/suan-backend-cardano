from fastapi import APIRouter, Security

from suantrazabilidadapi.utils.security import get_api_key

from .endpoints import wallet, transactions

api_router = APIRouter()

api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"], dependencies=[Security(get_api_key)])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"], dependencies=[Security(get_api_key)])