import os
import pytest
from dotenv import load_dotenv

from starlette.testclient import TestClient

from suantrazabilidadapi.app import suantrazabilidad
from suantrazabilidadapi.core.config import config


@pytest.fixture
def client():

    return TestClient(suantrazabilidad)

# @pytest.fixture
# def setUp():
os.environ['env'] = 'test'
security = config(section="security")
load_dotenv()
environment = security["env"]

def test_get_wallets(client: TestClient, ):
    """pass"""
    # monkeypatch.setenv('API_KEY', 'uipizkaW8SZMHDLbw-L-Ub9kPUgnw3JVekvzwtG8nrw')
    headers = {
        'x-api-key': os.getenv('PLATFORM_API_KEY_TEST')  # Retrieve the API key from the environment
    }
    response = client.get("/api/v1/wallet/get-wallets/", headers=headers)
    print (response)
