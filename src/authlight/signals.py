from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission

from authlight.lockout import LOCKOUT_DETAIL
from authlight.models import TENANT_ADMINS_GROUP, GroupOwnership

TENANT_ADMIN_PERMISSIONS = {
    ("authlight", "user"): ("add_user", "change_user", "delete_user", "view_user"),
    ("auth", "group"): ("add_group", "change_group", "delete_group", "view_group"),
}


def ensure_tenant_admins_group(sender, **kwargs):
    create_permissions(apps.get_app_config("auth"), verbosity=0)
    create_permissions(apps.get_app_config("authlight"), verbosity=0)

    group, _created = Group.objects.get_or_create(name=TENANT_ADMINS_GROUP)
    GroupOwnership.objects.get_or_create(group=group)

    permissions = []
    for (app_label, model), codenames in TENANT_ADMIN_PERMISSIONS.items():
        permissions.extend(
            Permission.objects.filter(
                content_type__app_label=app_label,
                content_type__model=model,
                codename__in=codenames,
            )
        )
    group.permissions.set(permissions)
    expected = sum(len(codenames) for codenames in TENANT_ADMIN_PERMISSIONS.values())
    if len(permissions) != expected:
        raise RuntimeError(
            f"Tenant admins group has {len(permissions)} permissions, expected {expected}."
        )


def on_user_locked_out(sender, request, username, ip_address, **kwargs):
    path = getattr(request, "path", "") or ""
    if path.startswith("/api/"):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied(LOCKOUT_DETAIL)
