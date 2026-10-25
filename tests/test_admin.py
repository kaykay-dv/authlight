import pytest
from django.contrib.auth.models import Group
from django.test import Client

from authlight.models import User
from tests.helpers import PASSWORD, post_admin

ADMIN = "/console/"


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="root",
        email="root@example.com",
        password=PASSWORD,
    )


@pytest.fixture
def tenant_admins(db):
    return Group.objects.get(name="Tenant admins")


def _tenant_admin(superuser, tenant_admins, username):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        is_staff=True,
        created_by=superuser,
    )
    user.groups.add(tenant_admins)
    return user


@pytest.fixture
def admin_a(superuser, tenant_admins):
    return _tenant_admin(superuser, tenant_admins, "admin-a")


@pytest.fixture
def admin_b(superuser, tenant_admins):
    return _tenant_admin(superuser, tenant_admins, "admin-b")


def _create_user(client, username, email, **extra):
    post_admin(
        client,
        f"{ADMIN}authlight/user/add/",
        {
            "username": username,
            "email": email,
            "usable_password": "true",
            "password1": PASSWORD,
            "password2": PASSWORD,
            **extra,
        },
    )


def _create_group(client, name):
    post_admin(client, f"{ADMIN}auth/group/add/", {"name": name})


@pytest.mark.django_db
def test_admin_is_not_served_under_the_default_path(superuser):
    client = Client()
    assert client.get("/admin/").status_code == 404
    assert client.get("/admin/login/").status_code == 404

    client.force_login(superuser)
    assert client.get(ADMIN).status_code == 200
    assert client.get(f"{ADMIN}login/").status_code == 302


@pytest.mark.django_db
def test_admin_index_pools_users_and_groups_and_hides_axes(superuser):
    client = Client()
    client.force_login(superuser)
    response = client.get(ADMIN)
    assert response.status_code == 200

    sections = {
        app["name"]: {model["object_name"] for model in app["models"]}
        for app in response.context["app_list"]
    }
    assert {"User", "Group"} <= sections["Authentication and Authorization"]
    assert "Authlight" not in sections
    assert "Axes" not in sections
    assert "Logs and security" not in sections

    # axes models are not registered in the admin at all
    assert client.get(f"{ADMIN}axes/accessattempt/").status_code == 404
    assert client.get(f"{ADMIN}axes/accesslog/").status_code == 404
    assert client.get(f"{ADMIN}axes/accessfailurelog/").status_code == 404


@pytest.mark.django_db
def test_tenant_admins_see_only_rows_they_created(admin_a, admin_b, superuser):
    client_a = Client()
    client_a.force_login(admin_a)
    _create_user(client_a, "user-of-a", "user-of-a@example.com")
    _create_group(client_a, "group-of-a")

    client_b = Client()
    client_b.force_login(admin_b)
    _create_user(client_b, "user-of-b", "user-of-b@example.com")
    _create_group(client_b, "group-of-b")

    User.objects.create_user(
        username="public-user",
        email="public-user@example.com",
        password=PASSWORD,
    )

    user_a = User.objects.get(username="user-of-a")
    user_b = User.objects.get(username="user-of-b")
    group_a = Group.objects.get(name="group-of-a")
    group_b = Group.objects.get(name="group-of-b")
    assert user_a.created_by_id == admin_a.pk
    assert user_b.created_by_id == admin_b.pk
    assert user_a.is_staff is False
    assert user_a.is_superuser is False
    assert group_a.ownership.created_by_id == admin_a.pk
    assert group_b.ownership.created_by_id == admin_b.pk

    users_page = client_a.get(f"{ADMIN}authlight/user/")
    assert users_page.status_code == 200
    users_html = users_page.content.decode()
    assert "user-of-a" in users_html
    assert "user-of-b" not in users_html
    assert "public-user" not in users_html

    groups_page = client_a.get(f"{ADMIN}auth/group/")
    assert groups_page.status_code == 200
    groups_html = groups_page.content.decode()
    assert "group-of-a" in groups_html
    assert "group-of-b" not in groups_html
    assert "Tenant admins" not in groups_html

    assert client_a.get(f"{ADMIN}authlight/user/{user_b.pk}/change/").status_code == 404
    assert client_a.get(f"{ADMIN}auth/group/{group_b.pk}/change/").status_code == 404
    assert client_a.get(f"{ADMIN}authlight/user/{user_a.pk}/change/").status_code == 200

    change_html = client_a.get(f"{ADMIN}authlight/user/{user_a.pk}/change/").content.decode()
    assert "group-of-a" in change_html
    assert "group-of-b" not in change_html

    super_client = Client()
    super_client.force_login(superuser)
    super_users = super_client.get(f"{ADMIN}authlight/user/").content.decode()
    assert "user-of-a" in super_users
    assert "user-of-b" in super_users
    assert "public-user" in super_users
    super_groups = super_client.get(f"{ADMIN}auth/group/").content.decode()
    assert "group-of-a" in super_groups
    assert "group-of-b" in super_groups


@pytest.mark.django_db
def test_tenant_admin_create_form_cannot_set_staff_or_superuser(admin_a):
    client = Client()
    client.force_login(admin_a)
    form = client.get(f"{ADMIN}authlight/user/add/")
    assert form.status_code == 200
    html = form.content.decode()
    assert 'name="is_staff"' not in html
    assert 'name="is_superuser"' not in html

    group_form = client.get(f"{ADMIN}auth/group/add/")
    assert 'name="permissions"' not in group_form.content.decode()

    _create_user(
        client,
        "plain-user",
        "plain-user@example.com",
        is_staff="on",
        is_superuser="on",
    )
    user = User.objects.get(username="plain-user")
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.created_by_id == admin_a.pk

    change = client.get(f"{ADMIN}authlight/user/{user.pk}/change/")
    change_html = change.content.decode()
    assert 'name="is_staff"' not in change_html
    assert 'name="is_superuser"' not in change_html
    assert 'name="user_permissions"' not in change_html


@pytest.mark.django_db
def test_staff_without_tenant_permissions_cannot_list_users(superuser):
    staff = User.objects.create_user(
        username="staff-only",
        email="staff-only@example.com",
        password=PASSWORD,
        is_staff=True,
        created_by=superuser,
    )
    client = Client()
    client.force_login(staff)
    assert client.get(f"{ADMIN}authlight/user/").status_code == 403
    assert client.get(f"{ADMIN}auth/group/").status_code == 403
