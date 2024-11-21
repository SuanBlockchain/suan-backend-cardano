from fastapi import APIRouter, Security

from suantrazabilidadapi.utils.security import get_api_key, merkle_api_key

from .endpoints import projects, transactions, wallet, helpers, ogmios, contracts, merkle


api_router = APIRouter()

api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"],
    dependencies=[Security(get_api_key)],
)
api_router.include_router(
    wallet.router,
    prefix="/wallet",
    tags=["Wallet"],
    dependencies=[Security(get_api_key)],
)
api_router.include_router(
    transactions.intermediate_router,
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[Security(get_api_key)],
)
api_router.include_router(
    contracts.router,
    prefix="/contracts",
    tags=["Contracts"],
    dependencies=[Security(get_api_key)],
)
api_router.include_router(
    ogmios.router,
    prefix="/ogmios",
    tags=["Ogmios"],
    # dependencies=[Security(get_api_key)],
)
api_router.include_router(
    helpers.router,
    prefix="/helpers",
    tags=["Helpers"],
    dependencies=[Security(get_api_key)],
)
api_router.include_router(
    merkle.router,
    prefix="/merkle",
    tags=["MerkleTree"],
    dependencies=[Security(merkle_api_key)],
)
