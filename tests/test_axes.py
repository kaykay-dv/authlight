import pytest
from django.test import Client
from rest_framework.test import APIClient

ADMIN = "/console/"

from authlight.lockout import LOCKOUT_DETAIL
from authlight.models import User
from tests.helpers import PASSWORD


def _user(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        is_staff=True,
    )


def _admin_login(client, username, password):
    client.get(f"{ADMIN}login/")
    return client.post(
        f"{ADMIN}login/",
        {
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            "next": ADMIN,
        },
    )


@pytest.mark.django_db
def test_token_obtain_locks_out(settings):
    settings.AXES_FAILURE_LIMIT = 2
    user = _user("token-user")
    client = APIClient()
    for _ in range(2):
        failed = client.post(
            "/api/token/",
            {"username": user.username, "password": "wrong-password"},
            format="json",
        )
        assert failed.status_code in (401, 403)

    locked = client.post(
        "/api/token/",
        {"username": user.username, "password": PASSWORD},
        format="json",
    )
    assert locked.status_code == 403
    assert locked.json()["detail"] == LOCKOUT_DETAIL


@pytest.mark.django_db
def test_successful_token_obtain_resets_failures(settings):
    settings.AXES_FAILURE_LIMIT = 2
    user = _user("reset-user")
    client = APIClient()
    first_failure = client.post(
        "/api/token/",
        {"username": user.username, "password": "wrong-password"},
        format="json",
    )
    assert first_failure.status_code == 401

    success = client.post(
        "/api/token/",
        {"username": user.username, "password": PASSWORD},
        format="json",
    )
    assert success.status_code == 200

    second_failure = client.post(
        "/api/token/",
        {"username": user.username, "password": "wrong-password"},
        format="json",
    )
    assert second_failure.status_code == 401


@pytest.mark.django_db
def test_admin_login_locks_out(settings):
    settings.AXES_FAILURE_LIMIT = 2
    user = _user("admin-login-user")
    client = Client()
    for _ in range(2):
        _admin_login(client, user.username, "wrong-password")

    locked = _admin_login(client, user.username, PASSWORD)
    assert locked.status_code == 429
    assert b"too many login attempts" in locked.content.lower()
    assert locked["Content-Type"].startswith("text/html")
