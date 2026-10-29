import pytest
from django.test import Client, override_settings
from rest_framework.test import APIClient

from authlight.models import User
from tests.helpers import PASSWORD

SPA_ORIGIN = "http://localhost:5173"
OTHER_ORIGIN = "https://evil.example"


def _preflight(path, origin=SPA_ORIGIN):
    return Client().options(
        path,
        HTTP_ORIGIN=origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
    )


@pytest.mark.django_db
def test_spa_preflight_for_login_is_allowed():
    response = _preflight("/api/token/")
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == SPA_ORIGIN
    assert "authorization" in response["Access-Control-Allow-Headers"].lower()
    assert "content-type" in response["Access-Control-Allow-Headers"].lower()
    assert "POST" in response["Access-Control-Allow-Methods"]
    assert "Access-Control-Allow-Credentials" not in response


@pytest.mark.django_db
def test_login_response_echoes_allowed_spa_origin():
    User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=PASSWORD,
    )
    client = APIClient()
    response = client.post(
        "/api/token/",
        {"username": "ada", "password": PASSWORD},
        format="json",
        HTTP_ORIGIN=SPA_ORIGIN,
    )
    assert response.status_code == 200
    assert "access" in response.json()
    assert response["Access-Control-Allow-Origin"] == SPA_ORIGIN
    assert "Access-Control-Allow-Credentials" not in response


@pytest.mark.django_db
def test_unknown_origin_is_not_allowed_on_login():
    response = _preflight("/api/token/", origin=OTHER_ORIGIN)
    assert response.status_code in (200, 403)
    assert response.get("Access-Control-Allow-Origin") != OTHER_ORIGIN


@pytest.mark.django_db
def test_admin_is_not_cors_enabled():
    response = _preflight("/console/login/")
    assert response.get("Access-Control-Allow-Origin") is None


@pytest.mark.django_db
def test_jwks_stays_open_for_any_origin():
    client = APIClient()
    response = client.get("/api/keys/", HTTP_ORIGIN="https://jwt.io")
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"


@pytest.mark.django_db
@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:4173"])
def test_configured_origin_replaces_the_defaults():
    allowed = _preflight("/api/token/", origin="http://localhost:4173")
    denied = _preflight("/api/token/", origin=SPA_ORIGIN)
    assert allowed["Access-Control-Allow-Origin"] == "http://localhost:4173"
    assert denied.get("Access-Control-Allow-Origin") != SPA_ORIGIN
