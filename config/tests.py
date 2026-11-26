import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_openapi_schema_exposes_jwt_bearer_auth():
    response = APIClient().get("/api/schema/")

    assert response.status_code == 200
    schema = response.content.decode()
    assert "bearerAuth:" in schema
    assert "/api/v1/auth/login/" in schema


def test_swagger_ui_is_available():
    response = APIClient().get("/api/docs/")

    assert response.status_code == 200
    assert "SwaggerUIBundle" in response.content.decode()
