"""Minimal Django settings for isolated Vallora booking API (port 8002)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "vallora-api-isolated")
DEBUG = False
ALLOWED_HOSTS = [
    "api.vallora.cz",
    "127.0.0.1",
    "localhost",
    "194.182.87.138",
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "corsheaders",
    "vallora",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "https://vallora.cz",
    "https://www.vallora.cz",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
]

ROOT_URLCONF = "webapp.urls_vallora"
WSGI_APPLICATION = "webapp.wsgi_vallora.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "vallora_api.sqlite3",
    }
}

LANGUAGE_CODE = "cs"
TIME_ZONE = "Europe/Prague"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    },
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
