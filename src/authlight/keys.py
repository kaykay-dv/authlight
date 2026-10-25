import base64
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.exceptions import ImproperlyConfigured
from jwt.algorithms import RSAAlgorithm

PRIVATE_KEY_NAME = "jwt_private.pem"
PUBLIC_KEY_NAME = "jwt_public.pem"


def generate_rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def read_key_pair(private_path: Path, public_path: Path) -> tuple[str, str]:
    missing = [path for path in (private_path, public_path) if not path.is_file()]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise ImproperlyConfigured(
            f"JWT key file not found: {names}. Run authlight init to generate a key pair."
        )
    return private_path.read_text(), public_path.read_text()


def write_keypair(directory: Path, *, force: bool = False) -> bool:
    """Write an RSA key pair. Return True when the files are created or replaced."""
    private_path = directory / PRIVATE_KEY_NAME
    public_path = directory / PUBLIC_KEY_NAME
    if private_path.exists() and public_path.exists() and not force:
        return False
    private_pem, public_pem = generate_rsa_keypair()
    _write_file(private_path, private_pem, 0o600)
    _write_file(public_path, public_pem, 0o644)
    return True


def public_jwk(public_pem: str) -> dict:
    """RFC 7517 public key for an RSA PEM, with an RFC 7638 thumbprint as kid."""
    return dict(_public_jwk(public_pem))


@lru_cache(maxsize=2)
def _public_jwk(public_pem: str) -> dict:
    key = serialization.load_pem_public_key(public_pem.encode())
    jwk = json.loads(RSAAlgorithm.to_jwk(key))
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    jwk["kid"] = _thumbprint(jwk["n"], jwk["e"])
    return jwk


def _thumbprint(modulus: str, exponent: str) -> str:
    canonical = json.dumps(
        {"e": exponent, "kty": "RSA", "n": modulus},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    digest = hashlib.sha256(canonical).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _write_file(path: Path, contents: str, mode: int) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w") as handle:
        handle.write(contents)
    path.chmod(mode)
