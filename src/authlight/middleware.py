from contextvars import ContextVar

from django.conf import settings
from django.urls import reverse

_request_jku: ContextVar[str] = ContextVar("authlight_jku", default="")


def current_jku() -> str:
    configured = getattr(settings, "JWT_JWKS_URL", "")
    if configured:
        return configured
    return _request_jku.get()


class JwkSetUrlMiddleware:
    """Remember this request's JWK Set URL so issued tokens can reference it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _request_jku.set(request.build_absolute_uri(reverse("jwks")))
        try:
            return self.get_response(request)
        finally:
            _request_jku.reset(token)
