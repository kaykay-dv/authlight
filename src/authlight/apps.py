from django.apps import AppConfig


class AuthlightConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authlight"
    verbose_name = "Authlight"

    def ready(self):
        from django.db.models.signals import post_migrate

        from axes.signals import user_locked_out

        from authlight import schema  # noqa: F401
        from authlight.signals import ensure_tenant_admins_group, on_user_locked_out
        from authlight.signing import install_jwk_header

        install_jwk_header()

        post_migrate.connect(
            ensure_tenant_admins_group,
            sender=self,
            dispatch_uid="authlight.ensure_tenant_admins_group",
        )
        user_locked_out.connect(
            on_user_locked_out,
            dispatch_uid="authlight.on_user_locked_out",
        )
