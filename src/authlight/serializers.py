from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from authlight.models import User


class AuthlightTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.get_username()
        token["email"] = user.email
        token["groups"] = list(
            user.groups.order_by("name").values_list("name", flat=True)
        )
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user_logged_in.send(
            sender=self.user.__class__,
            request=self.context["request"],
            user=self.user,
        )
        return data


class PublicKeySerializer(serializers.Serializer):
    alg = serializers.CharField()
    public_key = serializers.CharField()


class JsonWebKeySerializer(serializers.Serializer):
    kty = serializers.CharField()
    use = serializers.CharField()
    alg = serializers.CharField()
    kid = serializers.CharField()
    n = serializers.CharField()
    e = serializers.CharField()


class JwkSetSerializer(serializers.Serializer):
    keys = JsonWebKeySerializer(many=True)


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password")

    def validate(self, attrs):
        user = User(
            username=attrs["username"],
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")
        extra_kwargs = {
            "username": {"required": True},
            "email": {"required": True},
            "first_name": {"required": True, "allow_blank": True},
            "last_name": {"required": True, "allow_blank": True},
        }
