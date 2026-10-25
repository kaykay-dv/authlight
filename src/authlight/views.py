from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView as SimpleJWTTokenRefreshView,
    TokenVerifyView as SimpleJWTTokenVerifyView,
)

from axes.decorators import axes_dispatch

from authlight.keys import public_jwk
from authlight.models import User
from authlight.serializers import (
    AuthlightTokenObtainPairSerializer,
    JwkSetSerializer,
    PublicKeySerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from authlight.throttling import UserCreateAnonThrottle, UserCreateUserThrottle


class IsOwnUser(permissions.BasePermission):
    message = "You can only update your own user."

    def has_object_permission(self, request, view, obj):
        return obj.pk == request.user.pk


@extend_schema(
    summary="Obtain JWT tokens",
    description=(
        "Returns an access token and a refresh token. The access token "
        "includes user_id, username, email, and groups."
    ),
    tags=["Authentication"],
)
@method_decorator(axes_dispatch, name="dispatch")
class AxesTokenObtainPairView(TokenObtainPairView):
    serializer_class = AuthlightTokenObtainPairSerializer


@extend_schema(summary="Refresh an access token", tags=["Authentication"])
class TokenRefreshView(SimpleJWTTokenRefreshView):
    pass


@extend_schema(summary="Verify a token", tags=["Authentication"])
class TokenVerifyView(SimpleJWTTokenVerifyView):
    pass


@extend_schema(
    summary="Get the token JWK Set",
    description=(
        "RFC 7517 key set for the RS256 public key. Issued tokens reference "
        "this URL in the jku header and identify the key with kid."
    ),
    tags=["Authentication"],
    responses={200: JwkSetSerializer},
)
class JwkSetView(APIView):
    serializer_class = JwkSetSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        response = Response({"keys": [public_jwk(jwt_settings.VERIFYING_KEY)]})
        response["Access-Control-Allow-Origin"] = "*"
        return response


@extend_schema(
    summary="Get the token public key",
    description=(
        "Returns the RS256 public key for verifying access and refresh tokens. "
        "The private key is not included."
    ),
    tags=["Authentication"],
    responses={200: PublicKeySerializer},
)
class PublicKeyView(APIView):
    serializer_class = PublicKeySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        return Response(
            {
                "alg": jwt_settings.ALGORITHM,
                "public_key": jwt_settings.VERIFYING_KEY,
            }
        )


@extend_schema(
    summary="Create a user",
    tags=["Authentication"],
    responses={201: UserSerializer},
)
class UserCreateView(generics.CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [UserCreateAnonThrottle, UserCreateUserThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Update a user",
    description=(
        "PUT replaces the profile. PATCH changes the fields you send. "
        "The access token must belong to this user id."
    ),
    tags=["Authentication"],
    responses={200: UserSerializer},
)
class UserUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnUser]
    lookup_url_kwarg = "id"

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(UserSerializer(instance).data)
