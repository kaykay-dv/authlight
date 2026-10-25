from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.translation import gettext_lazy as _

TENANT_ADMINS_GROUP = "Tenant admins"


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    created_by = models.ForeignKey(
        "self",
        verbose_name=_("created by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_users",
    )

    def __str__(self):
        return self.get_username()


class GroupOwnership(models.Model):
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name="ownership",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_groups",
    )

    class Meta:
        verbose_name = _("group ownership")
        verbose_name_plural = _("group ownerships")

    def __str__(self):
        return f"Ownership of {self.group}"
