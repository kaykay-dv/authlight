from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from authlight.views import (
    AxesTokenObtainPairView,
    JwkSetView,
    PublicKeyView,
    TokenRefreshView,
    TokenVerifyView,
    UserCreateView,
    UserUpdateView,
)


class SchemaView(SpectacularAPIView):
    throttle_classes = []


class SwaggerView(SpectacularSwaggerView):
    throttle_classes = []

urlpatterns = [
    path("api/docs/schema/", SchemaView.as_view(), name="schema"),
    path(
        "api/docs/",
        SwaggerView.as_view(url_name="schema"),
        name="api-docs",
    ),
    path("api/token/", AxesTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/keys/", JwkSetView.as_view(), name="jwks"),
    path("api/keys/public/", PublicKeyView.as_view(), name="public_key"),
    path("api/users/", UserCreateView.as_view(), name="users"),
    path("api/users/<int:id>/", UserUpdateView.as_view(), name="user"),
]
