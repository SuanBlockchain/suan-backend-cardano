import pytest
from starlette.testclient import TestClient

from suantrazabilidadapi.app import suantrazabilidad


@pytest.fixture
def client():
    return TestClient(suantrazabilidad)


def test_base_route(client):
    """
    GIVEN
    WHEN health check endpoint is called with GET method
    THEN response with status 200 and body OK is returned
    """
    response = client.get("/")
    assert response.status_code == 200
