import jwt
from django.conf import settings

from authlight.keys import public_jwk
from authlight.middleware import current_jku


def install_jwk_header() -> None:
    """Add kid and jku to tokens signed by simplejwt."""
    from rest_framework_simplejwt.state import token_backend

    if getattr(token_backend.encode, "_authlight_jwk", False):
        return

    def encode(payload):
        jwt_payload = payload.copy()
        if token_backend.audience is not None:
            jwt_payload["aud"] = token_backend.audience
        if token_backend.issuer is not None:
            jwt_payload["iss"] = token_backend.issuer
        jwk = public_jwk(settings.SIMPLE_JWT["VERIFYING_KEY"])
        headers = {"kid": jwk["kid"]}
        jku = current_jku()
        if jku:
            headers["jku"] = jku
        token = jwt.encode(
            jwt_payload,
            token_backend.prepared_signing_key,
            algorithm=token_backend.algorithm,
            headers=headers,
            json_encoder=token_backend.json_encoder,
        )
        if isinstance(token, bytes):
            return token.decode("utf-8")
        return token

    encode._authlight_jwk = True
    token_backend.encode = encode
