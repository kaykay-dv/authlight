import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from authlight.keys import read_key_pair, write_keypair
from authlight.project.initialize import write_default_env


def _secret(env_file: Path) -> str:
    for line in env_file.read_text().splitlines():
        if line.startswith("DJANGO_SECRET_KEY="):
            return line.split("=", 1)[1]
    raise AssertionError("DJANGO_SECRET_KEY missing")



def test_write_default_env_uses_local_defaults(tmp_path):
    env_file = tmp_path / ".env"
    assert write_default_env(env_file) is True
    text = env_file.read_text()
    secret = _secret(env_file)
    assert len(secret) >= 32
    assert "change-me" not in text
    assert "DJANGO_DEBUG=true" in text
    assert "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1" in text
    assert "DJANGO_ADMIN_URL" not in text
    assert "DATABASE_URL=sqlite:///db.sqlite3" in text
    assert "JWT_ACCESS_TOKEN_LIFETIME_MINUTES=5" in text
    assert "JWT_REFRESH_TOKEN_LIFETIME_DAYS=1" in text
    assert "AXES_FAILURE_LIMIT=5" in text
    assert "AXES_COOLOFF_HOURS=1" in text
    assert "API_THROTTLE_ANON=5/hour" in text
    assert "API_THROTTLE_USER=500/hour" in text
    assert "API_THROTTLE_USER_CREATE_ANON=5/hour" in text
    assert "API_THROTTLE_USER_CREATE_USER=5/hour" in text
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600

    assert write_default_env(env_file) is False
    assert _secret(env_file) == secret

    assert write_default_env(env_file, force=True) is True
    assert _secret(env_file) != secret


def test_write_keypair_keeps_existing_keys_until_forced(tmp_path):
    assert write_keypair(tmp_path) is True
    private_path = tmp_path / "jwt_private.pem"
    public_path = tmp_path / "jwt_public.pem"
    private = private_path.read_text()
    public = public_path.read_text()
    assert private.startswith("-----BEGIN PRIVATE KEY-----")
    assert public.startswith("-----BEGIN PUBLIC KEY-----")
    assert stat.S_IMODE(private_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(public_path.stat().st_mode) == 0o644
    assert read_key_pair(private_path, public_path) == (private, public)

    assert write_keypair(tmp_path) is False
    assert private_path.read_text() == private

    assert write_keypair(tmp_path, force=True) is True
    assert private_path.read_text() != private


def test_read_key_pair_requires_both_files(tmp_path):
    with pytest.raises(ImproperlyConfigured):
        read_key_pair(tmp_path / "jwt_private.pem", tmp_path / "jwt_public.pem")


def test_init_command_creates_env_and_database(tmp_path):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("DJANGO_", "JWT_", "AXES_")) or key == "DATABASE_URL":
            del env[key]
    src = Path(__file__).resolve().parents[1] / "src"
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")

    completed = subprocess.run(
        [sys.executable, "-m", "authlight", "init"],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "generated secret" in completed.stdout
    assert "jwt_private.pem" in completed.stdout
    assert (tmp_path / "db.sqlite3").is_file()
    secret = _secret(tmp_path / ".env")
    private = (tmp_path / "jwt_private.pem").read_text()
    assert private.startswith("-----BEGIN PRIVATE KEY-----")
    assert (tmp_path / "jwt_public.pem").read_text().startswith("-----BEGIN PUBLIC KEY-----")

    again = subprocess.run(
        [sys.executable, "-m", "authlight", "init"],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Using existing" in again.stdout
    assert "existing JWT key pair" in again.stdout
    assert _secret(tmp_path / ".env") == secret
    assert (tmp_path / "jwt_private.pem").read_text() == private
