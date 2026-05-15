import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_invalid_token_returns_401(api_client):
    api_client.credentials(
        HTTP_AUTHORIZATION="Bearer invalid",
    )

    response = api_client.post(
        "/api/v1/products",
        {},
        format="json",
    )

    assert response.status_code == 401
