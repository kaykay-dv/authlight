import jwt
import pytest
from django.conf import settings
from django.test import override_settings
from jwt.algorithms import RSAAlgorithm
from rest_framework.test import APIClient

from authlight.models import User
from tests.helpers import PASSWORD


@pytest.mark.django_db
def test_create_user_obtain_refresh_and_verify():
    client = APIClient()
    created = client.post(
        "/api/users/",
        {
            "username": "ada",
            "email": "ada@example.com",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "password": PASSWORD,
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.json() == {
        "id": created.json()["id"],
        "username": "ada",
        "email": "ada@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }

    user = User.objects.get(username="ada")
    assert user.created_by_id is None
    assert user.is_staff is False
    assert user.is_active is True
    assert user.email == "ada@example.com"
    assert user.first_name == "Ada"
    assert user.last_name == "Lovelace"

    from django.contrib.auth.models import Group

    group = Group.objects.create(name="readers")
    user.groups.add(group)

    obtained = client.post(
        "/api/token/",
        {"username": "ada", "password": PASSWORD},
        format="json",
    )
    assert obtained.status_code == 200
    access = obtained.json()["access"]
    refresh = obtained.json()["refresh"]
    payload = jwt.decode(
        access,
        settings.SIMPLE_JWT["VERIFYING_KEY"],
        algorithms=["RS256"],
    )
    header = jwt.get_unverified_header(access)
    assert header["alg"] == "RS256"
    assert header["jku"] == "http://testserver/api/keys/"
    refresh_header = jwt.get_unverified_header(refresh)
    assert refresh_header["kid"] == header["kid"]
    assert refresh_header["jku"] == header["jku"]
    assert payload["username"] == "ada"
    assert payload["email"] == "ada@example.com"
    assert payload["groups"] == ["readers"]
    assert payload["user_id"] == str(user.pk)

    refreshed = client.post(
        "/api/token/refresh/",
        {"refresh": refresh},
        format="json",
    )
    assert refreshed.status_code == 200
    refreshed_access = refreshed.json()["access"]
    refreshed_payload = jwt.decode(
        refreshed_access,
        settings.SIMPLE_JWT["VERIFYING_KEY"],
        algorithms=["RS256"],
    )
    assert refreshed_payload["groups"] == ["readers"]
    assert jwt.get_unverified_header(refreshed_access)["jku"] == header["jku"]

    verified = client.post(
        "/api/token/verify/",
        {"token": access},
        format="json",
    )
    assert verified.status_code == 200

    published = client.get("/api/keys/public/")
    assert published.status_code == 200
    assert published.json() == {
        "alg": "RS256",
        "public_key": settings.SIMPLE_JWT["VERIFYING_KEY"],
    }
    assert "PRIVATE" not in published.json()["public_key"]

    jwks = client.get("/api/keys/")
    assert jwks.status_code == 200
    assert jwks["Access-Control-Allow-Origin"] == "*"
    key = jwks.json()["keys"][0]
    assert key["kid"] == header["kid"]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert key["use"] == "sig"
    assert "d" not in key
    resolved = RSAAlgorithm.from_jwk(key)
    assert jwt.decode(access, resolved, algorithms=["RS256"])["user_id"] == str(user.pk)


@pytest.mark.django_db
def test_configured_jku_overrides_the_request_host():
    client = APIClient()
    client.post(
        "/api/users/",
        {
            "username": "ada",
            "email": "ada@example.com",
            "password": PASSWORD,
        },
        format="json",
    )
    with override_settings(JWT_JWKS_URL="https://auth.example.com/api/keys/"):
        obtained = client.post(
            "/api/token/",
            {"username": "ada", "password": PASSWORD},
            format="json",
        )
    assert obtained.status_code == 200
    header = jwt.get_unverified_header(obtained.json()["access"])
    assert header["jku"] == "https://auth.example.com/api/keys/"
    assert header["kid"]


@pytest.mark.django_db
def test_create_user_names_are_optional():
    client = APIClient()
    response = client.post(
        "/api/users/",
        {
            "username": "ada",
            "email": "ada@example.com",
            "password": PASSWORD,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["first_name"] == ""
    assert response.json()["last_name"] == ""
    user = User.objects.get(username="ada")
    assert user.first_name == ""
    assert user.last_name == ""


def _access_token(client, username):
    obtained = client.post(
        "/api/token/",
        {"username": username, "password": PASSWORD},
        format="json",
    )
    assert obtained.status_code == 200
    return obtained.json()["access"]


@pytest.mark.django_db
def test_user_updates_own_profile_with_put_and_patch():
    client = APIClient()
    created = client.post(
        "/api/users/",
        {
            "username": "ada",
            "email": "ada@example.com",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "password": PASSWORD,
        },
        format="json",
    )
    user_id = created.json()["id"]
    client.post(
        "/api/users/",
        {
            "username": "grace",
            "email": "grace@example.com",
            "password": PASSWORD,
        },
        format="json",
    )
    url = f"/api/users/{user_id}/"
    profile = {
        "username": "ada",
        "email": "ada@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }

    anonymous = client.put(url, profile, format="json")
    assert anonymous.status_code == 401

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_access_token(client, 'grace')}")
    forbidden = client.patch(url, {"first_name": "Grace"}, format="json")
    assert forbidden.status_code == 403
    assert User.objects.get(pk=user_id).first_name == "Ada"

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_access_token(client, 'ada')}")
    replaced = client.put(
        url,
        {
            "username": "ada.lovelace",
            "email": "countess@example.com",
            "first_name": "Augusta",
            "last_name": "King",
            "password": "should-be-ignored",
            "is_staff": True,
        },
        format="json",
    )
    assert replaced.status_code == 200
    assert replaced.json() == {
        "id": user_id,
        "username": "ada.lovelace",
        "email": "countess@example.com",
        "first_name": "Augusta",
        "last_name": "King",
    }
    user = User.objects.get(pk=user_id)
    assert user.check_password(PASSWORD)
    assert user.is_staff is False

    patched = client.patch(url, {"first_name": "Ada"}, format="json")
    assert patched.status_code == 200
    assert patched.json()["first_name"] == "Ada"
    assert patched.json()["last_name"] == "King"
    assert patched.json()["email"] == "countess@example.com"


@pytest.mark.django_db
def test_put_profile_requires_every_field():
    client = APIClient()
    created = client.post(
        "/api/users/",
        {
            "username": "ada",
            "email": "ada@example.com",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "password": PASSWORD,
        },
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {_access_token(client, 'ada')}")
    response = client.put(
        f"/api/users/{created.json()['id']}/",
        {"first_name": "Augusta"},
        format="json",
    )
    assert response.status_code == 400
    user = User.objects.get(username="ada")
    assert user.first_name == "Ada"
    assert user.email == "ada@example.com"
