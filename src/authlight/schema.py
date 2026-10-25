from drf_spectacular.contrib.rest_framework_simplejwt import (
    TokenObtainPairSerializerExtension,
)


class AuthlightTokenObtainPairSerializerExtension(TokenObtainPairSerializerExtension):
    target_class = "authlight.serializers.AuthlightTokenObtainPairSerializer"
