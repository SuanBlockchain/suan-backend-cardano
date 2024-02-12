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


#     from fastapi import FastAPI, Depends, HTTPException
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# app = FastAPI()

# # Implement your token verification logic here
# def verify_jwt(credentials: HTTPAuthorizationCredentials) -> bool:
   
#    token = str(credentials.credentials)
#    # Implement your verification logic here, e.g., by checking against a database
#    # Or Send a request to an authentication service to verify the token
#    # url = settings.auth_service_url + "/verify"
#    # response = requests.post(url, json={"token": str(token)})
#    # Return True if the token is valid, else return 401 response
#    return True  # Replace this with your actual verification logic
#    # if not valid
#    # raise HTTPException(status_code=401, detail="Invalid credentials")
   

# class JWTBearer(HTTPBearer):
#    async def __call__(self, request: Request):
#        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
#        if credentials and verify_jwt(credentials):
#            return credentials.credentials


# @app.get("/protected_resource")
# async def get_protected_resource(Depends(JWTBearer())):
#    return {"message": f"Welcome!"}
