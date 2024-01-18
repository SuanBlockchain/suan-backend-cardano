from fastapi import APIRouter

from .endpoints import wallet, transactions

api_router = APIRouter()
# api_router.include_router(kobo_projects.router, prefix="/kobo", tags=["Kobo"])
# api_router.include_router(db_data.router, prefix="/data", tags=["Data"])
# api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
# api_router.include_router(qrdb.router, prefix="/qrdb", tags=["QRDB"])