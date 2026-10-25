from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from authlight.models import User

admin.site.unregister(Group)


class OwnedObjectAdmin(admin.ModelAdmin):
    """Return 404 when an object is outside the caller's queryset."""

    def _get_obj_does_not_exist_redirect(self, request, opts, object_id):
        raise Http404(
            f"{opts.verbose_name} with ID {unquote(object_id)} doesn't exist."
        )


class AuthlightUserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class AuthlightUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class UserAdmin(OwnedObjectAdmin, DjangoUserAdmin):
    form = AuthlightUserChangeForm
    add_form = AuthlightUserCreationForm
    readonly_fields = ("last_login", "date_joined", "created_by")
    list_display = ("username", "email", "is_staff", "created_by")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Ownership"), {"fields": ("created_by",)}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    tenant_fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (_("Access"), {"fields": ("is_active", "groups")}),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        if request.user.is_superuser:
            return self.fieldsets
        return self.tenant_fieldsets

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(created_by=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups" and not request.user.is_superuser:
            kwargs["queryset"] = Group.objects.filter(
                ownership__created_by=request.user
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class GroupAdmin(OwnedObjectAdmin, DjangoGroupAdmin):
    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return ((None, {"fields": ("name", "permissions")}),)
        return ((None, {"fields": ("name",)}),)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(ownership__created_by=request.user)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from authlight.models import GroupOwnership

        ownership, _created = GroupOwnership.objects.get_or_create(group=obj)
        if not change:
            ownership.created_by = request.user
            ownership.save(update_fields=["created_by"])


admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.site_header = "Authlight"
admin.site.site_title = "Authlight"
admin.site.index_title = "Authentication"
