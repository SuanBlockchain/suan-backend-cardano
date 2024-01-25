from fastapi.security import APIKeyHeader
from fastapi import HTTPException, status, Security

import secrets
from suantrazabilidadapi.core.config import config
import os

security = config(section="security")
graphqlEndpoint = os.getenv('endpoint')

API_KEYS = {
        "datos": os.getenv("data_api_key"),
        "plataforma": os.getenv("platform_api_key")
    }

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def get_api_key(
    api_key_header: str = Security(api_key_header),
) -> str:
    """Retrieve and validate an API key from the query parameters or HTTP header.

    Args:
        api_key_query: The API key passed as a query parameter.
        api_key_header: The API key passed in the HTTP header.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If the API key is invalid or missing.
    """
    if api_key_header in API_KEYS.values():
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )

def generate_api_key():
    # Generate a random 32-character string using secrets.token_urlsafe()
    return secrets.token_urlsafe(32)












# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# router = APIRouter()

# @router.get("/items/")
# async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
#     return {"token": token}

