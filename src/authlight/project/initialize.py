import argparse
import os
import secrets
import stat
from pathlib import Path

from authlight.keys import PRIVATE_KEY_NAME, PUBLIC_KEY_NAME, write_keypair

ENV_TEMPLATE = """\
DJANGO_SECRET_KEY={secret}
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=5
JWT_REFRESH_TOKEN_LIFETIME_DAYS=1
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_HOURS=1
API_THROTTLE_ANON=5/hour
API_THROTTLE_USER=500/hour
API_THROTTLE_USER_CREATE_ANON=5/hour
API_THROTTLE_USER_CREATE_USER=5/hour
"""


def write_default_env(path: Path, *, force: bool = False) -> bool:
    """Write local defaults. Return True when the file is created or replaced."""
    if path.exists() and not force:
        return False
    secret = secrets.token_urlsafe(48)
    path.write_text(ENV_TEMPLATE.format(secret=secret))
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return True


def initialize(base_dir: Path | None = None, *, force: bool = False) -> None:
    base_dir = (base_dir or Path.cwd()).resolve()
    env_path = base_dir / ".env"
    existed = env_path.exists()
    wrote = write_default_env(env_path, force=force)
    if wrote and existed:
        print(f"Replaced {env_path}. Existing sessions and tokens will not validate.")
    elif wrote:
        print(f"Wrote {env_path} with a generated secret and local defaults.")
    else:
        print(f"Using existing {env_path}")

    private_existed = (base_dir / PRIVATE_KEY_NAME).exists()
    public_existed = (base_dir / PUBLIC_KEY_NAME).exists()
    keys_written = write_keypair(base_dir, force=force)
    if keys_written and (private_existed or public_existed):
        print("Replaced the JWT key pair. Existing tokens will not validate.")
    elif keys_written:
        print(f"Wrote {PRIVATE_KEY_NAME} and {PUBLIC_KEY_NAME}.")
    else:
        print("Using the existing JWT key pair.")

    previous = Path.cwd()
    os.chdir(base_dir)
    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "authlight.project.settings")
        from django.core.management import execute_from_command_line

        execute_from_command_line(["authlight", "migrate", "--noinput"])
    finally:
        os.chdir(previous)
    print("Database is ready. Next: authlight createsuperuser && authlight runserver")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="authlight init",
        description="Create a local .env with generated defaults and apply migrations.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing .env and JWT key pair. Existing tokens will not validate.",
    )
    args = parser.parse_args(argv)
    initialize(force=args.force)
