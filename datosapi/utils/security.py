from fastapi.security import APIKeyHeader
from fastapi import HTTPException, status, Security

# from core.config import config
from ..core.config import config
import os

security = config(section="security")
graphqlEndpoint = os.getenv('endpoint')

API_KEYS = {
        "data": os.getenv("data_api_key")
    }

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def get_api_key(
    api_key_header: str = Security(api_key_header)
) -> str:
    """Retrieve and validate an API key from the query parameters or HTTP header.

    Args:
        api_key_query: The API key passed as a query parameter.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If the API key is invalid or missing.
    """
    key = API_KEYS["data"]
    if api_key_header == key:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )
