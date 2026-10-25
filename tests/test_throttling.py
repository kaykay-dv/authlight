import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from authlight.project.settings import (
    DEFAULT_API_THROTTLE_ANON,
    DEFAULT_API_THROTTLE_USER,
    DEFAULT_API_THROTTLE_USER_CREATE_ANON,
    DEFAULT_API_THROTTLE_USER_CREATE_USER,
)
from tests.helpers import PASSWORD


def test_throttle_defaults():
    assert DEFAULT_API_THROTTLE_ANON == "5/hour"
    assert DEFAULT_API_THROTTLE_USER == "500/hour"
    assert DEFAULT_API_THROTTLE_USER_CREATE_ANON == "5/hour"
    assert DEFAULT_API_THROTTLE_USER_CREATE_USER == "5/hour"


def throttle(**rates):
    merged = {
        "anon": "100000/hour",
        "user": "100000/hour",
        "user_create_anon": "100000/hour",
        "user_create_user": "100000/hour",
        **rates,
    }
    return override_settings(
        REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": merged,
        }
    )


def _create_user(client, username):
    response = client.post(
        "/api/users/",
        {
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()["id"]


def _token(client, username):
    response = client.post(
        "/api/token/",
        {"username": username, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()["access"]


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_anonymous_and_authenticated_limits_are_separate():
    with throttle(anon="1/hour", user="2/hour"):
        setup = APIClient(REMOTE_ADDR="10.1.0.9")
        user_id = _create_user(setup, "ada")
        access = _token(setup, "ada")

        anon = APIClient(REMOTE_ADDR="10.1.0.1")
        denied = anon.post("/api/token/verify/", {"token": "nope"}, format="json")
        assert denied.status_code == 401
        blocked = anon.post("/api/token/verify/", {"token": "nope"}, format="json")
        assert blocked.status_code == 429

        other_ip = APIClient(REMOTE_ADDR="10.1.0.2")
        still_open = other_ip.post("/api/token/verify/", {"token": "nope"}, format="json")
        assert still_open.status_code == 401

        authed = APIClient(REMOTE_ADDR="10.1.0.1")
        authed.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        url = f"/api/users/{user_id}/"
        assert authed.patch(url, {"first_name": "Ada"}, format="json").status_code == 200
        assert authed.patch(url, {"first_name": "Ada"}, format="json").status_code == 200
        assert authed.patch(url, {"first_name": "Ada"}, format="json").status_code == 429


@pytest.mark.django_db
def test_authenticated_users_do_not_share_a_limit():
    with throttle(user="1/hour", user_create_anon="10/hour"):
        owner = APIClient(REMOTE_ADDR="10.2.0.1")
        ada_id = _create_user(owner, "ada")
        grace_id = _create_user(owner, "grace")
        ada = APIClient()
        ada.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner, 'ada')}")
        grace = APIClient()
        grace.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner, 'grace')}")

        assert ada.patch(f"/api/users/{ada_id}/", {"first_name": "A"}, format="json").status_code == 200
        assert ada.patch(f"/api/users/{ada_id}/", {"first_name": "B"}, format="json").status_code == 429
        assert (
            grace.patch(f"/api/users/{grace_id}/", {"first_name": "G"}, format="json").status_code
            == 200
        )


@pytest.mark.django_db
def test_user_creation_limits_are_separate_from_the_api_limits():
    with throttle(anon="5/hour", user="5/hour", user_create_anon="2/hour", user_create_user="1/hour"):
        anon = APIClient(REMOTE_ADDR="10.3.0.1")
        assert anon.post("/api/users/", {}, format="json").status_code == 400
        assert anon.post("/api/users/", {}, format="json").status_code == 400
        assert anon.post("/api/users/", {}, format="json").status_code == 429
        assert anon.post("/api/token/verify/", {"token": "nope"}, format="json").status_code == 401

        creator = APIClient(REMOTE_ADDR="10.3.0.2")
        ada_id = _create_user(creator, "ada")
        access = _token(creator, "ada")
        creator.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert creator.post("/api/users/", {}, format="json").status_code == 400
        assert creator.post("/api/users/", {}, format="json").status_code == 429
        assert (
            creator.patch(f"/api/users/{ada_id}/", {"first_name": "Ada"}, format="json").status_code
            == 200
        )

        still_anonymous = APIClient(REMOTE_ADDR="10.3.0.3")
        assert still_anonymous.post("/api/users/", {}, format="json").status_code == 400


def test_docs_are_not_throttled():
    with throttle(anon="1/hour"):
        client = APIClient(REMOTE_ADDR="10.4.0.1")
        assert client.get("/api/docs/").status_code == 200
        assert client.get("/api/docs/").status_code == 200
        for _ in range(2):
            schema = client.get(
                "/api/docs/schema/",
                HTTP_ACCEPT="application/vnd.oai.openapi+json",
            )
            assert schema.status_code == 200
