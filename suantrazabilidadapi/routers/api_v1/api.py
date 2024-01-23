from fastapi import APIRouter

from ...utils import security

from .endpoints import wallet, transactions

api_router = APIRouter()

api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
# api_router.include_router(security.router, prefix="/security", tags=["Security"])