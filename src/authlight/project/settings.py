import sys
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

from authlight.keys import generate_rsa_keypair, read_key_pair

cwd = Path.cwd()
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 5),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 1),
    AXES_FAILURE_LIMIT=(int, 5),
    AXES_COOLOFF_HOURS=(int, 1),
)

env_file = cwd / ".env"
if env_file.is_file():
    env.read_env(env_file)

RUNNING_TESTS = "pytest" in sys.modules
DEBUG = True if RUNNING_TESTS else env("DJANGO_DEBUG")
_secret = env.str("DJANGO_SECRET_KEY", default="")
if _secret:
    SECRET_KEY = _secret
elif DEBUG:
    SECRET_KEY = "dev-only-insecure-key-not-for-production-use"
else:
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY when DJANGO_DEBUG is false."
    )

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{cwd / 'db.sqlite3'}",
    )
}

AUTH_USER_MODEL = "authlight.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "corsheaders",
    "axes",
    "authlight.apps.AuthlightConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "authlight.middleware.JwkSetUrlMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "authlight.project.urls"
WSGI_APPLICATION = "authlight.project.wsgi.application"
ASGI_APPLICATION = "authlight.project.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # authlight's own templates first, so admin/base_site.html
        # overrides django.contrib.admin's.
        "DIRS": [Path(__file__).resolve().parent.parent / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if RUNNING_TESTS:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEFAULT_API_THROTTLE_ANON = "5/hour"
DEFAULT_API_THROTTLE_USER = "500/hour"
DEFAULT_API_THROTTLE_USER_CREATE_ANON = "5/hour"
DEFAULT_API_THROTTLE_USER_CREATE_USER = "5/hour"
_TEST_THROTTLE_RATE = "100000/hour"


def _throttle_rate(name, default):
    if RUNNING_TESTS:
        return _TEST_THROTTLE_RATE
    return env.str(name, default=default)


AXES_FAILURE_LIMIT = env("AXES_FAILURE_LIMIT")
AXES_COOLOFF_TIME = timedelta(hours=env("AXES_COOLOFF_HOURS"))
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = "authlight.lockout.lockout_response"
# Keep axes' records out of the Django admin; the lockout itself is unaffected.
AXES_ENABLE_ADMIN = False


def _key_path(name: str, default: str) -> Path:
    path = Path(env.str(name, default=default))
    if not path.is_absolute():
        path = cwd / path
    return path


if RUNNING_TESTS:
    _signing_key, _verifying_key = generate_rsa_keypair()
else:
    _signing_key, _verifying_key = read_key_pair(
        _key_path("JWT_PRIVATE_KEY_FILE", "jwt_private.pem"),
        _key_path("JWT_PUBLIC_KEY_FILE", "jwt_public.pem"),
    )

SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": _signing_key,
    "VERIFYING_KEY": _verifying_key,
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES")
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")),
}

# Absolute JWK Set URL written into issued tokens. Empty uses the request host.
JWT_JWKS_URL = env.str("JWT_JWKS_URL", default="")

# SPA login from another origin (e.g. Vite on :5173). Bearer tokens only —
# no cookies — so credentials are off and an allowlist is enough.
# GET /api/keys/ still sets Access-Control-Allow-Origin: * for jwt.io.
DEFAULT_CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOWED_ORIGINS = [
    origin
    for origin in env.list("CORS_ALLOWED_ORIGINS", default=DEFAULT_CORS_ALLOWED_ORIGINS)
    if origin
]
CORS_ALLOW_CREDENTIALS = False
CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "authlight.throttling.AnonThrottle",
        "authlight.throttling.UserThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": _throttle_rate("API_THROTTLE_ANON", DEFAULT_API_THROTTLE_ANON),
        "user": _throttle_rate("API_THROTTLE_USER", DEFAULT_API_THROTTLE_USER),
        "user_create_anon": _throttle_rate(
            "API_THROTTLE_USER_CREATE_ANON",
            DEFAULT_API_THROTTLE_USER_CREATE_ANON,
        ),
        "user_create_user": _throttle_rate(
            "API_THROTTLE_USER_CREATE_USER",
            DEFAULT_API_THROTTLE_USER_CREATE_USER,
        ),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Authlight",
    "DESCRIPTION": (
        "JWT authentication provider. Access tokens are signed with RS256 "
        "and include user_id, username, email, and groups. The token header "
        "jku points at the RFC 7517 key set /api/keys/."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_AUTHENTICATION": [],
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
}

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
