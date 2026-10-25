import os

os.environ.setdefault(
    "DJANGO_SECRET_KEY",
    "test-secret-key-not-for-production",
)
os.environ.setdefault("DJANGO_DEBUG", "true")
os.environ.setdefault(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver",
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "authlight.project.settings")
