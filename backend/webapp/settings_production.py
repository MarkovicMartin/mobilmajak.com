"""
Django settings for webapp project - PRODUCTION

PRODUCTION ONLY - použije se na VPS serveru
"""

import pymysql
pymysql.install_as_MySQLdb()
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    '80.211.198.189',  # VPS IP adresa
    'localhost',
    '127.0.0.1',
    'mobilmajak.com',
    'www.mobilmajak.com',
    'staging.mobilmajak.com',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'users',
    'news',
    'analytics',
    'shifts',
    'web_pristupy',
    'stores',
    'orders',
    'tasks',
    'plans',
    'tickets',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'users.middleware.ApiCsrfMiddleware',  # Vlastní CSRF middleware pro API
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'webapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'webapp.wsgi.application'

# Database - stejná MySQL databáze na Webglobe
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'multi_724223'),
        'USER': os.getenv('DB_USER', 'multi_724223'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'db.dw300.webglobe.com'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Prague'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images) - pro Nginx
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings - PRODUKČNÍ (pouze specifické domény)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://mobilmajak.com",
    "http://mobilmajak.com",
    "https://www.mobilmajak.com",
    "http://www.mobilmajak.com",
    "https://staging.mobilmajak.com",
    "http://staging.mobilmajak.com",
    "http://80.211.198.189",  # VPS IP
]
CORS_ALLOW_CREDENTIALS = True

# Security settings pro HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = True  # Automatický redirect na HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Nginx proxy - Django rozpozná HTTPS

# Session settings - PRODUKČNÍ
SESSION_COOKIE_SECURE = True  # HTTPS je nyní dostupné
SESSION_COOKIE_HTTPONLY = False  # Pro JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24 hodin

# CSRF settings - PRODUKČNÍ
CSRF_COOKIE_SECURE = True  # HTTPS je nyní dostupné
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'https://mobilmajak.com',
    'http://mobilmajak.com',
    'https://www.mobilmajak.com',
    'http://www.mobilmajak.com',
    'https://staging.mobilmajak.com',
    'http://staging.mobilmajak.com',
    'http://80.211.198.189',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'users.authentication.WebUserSessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# Custom authentication backend
AUTHENTICATION_BACKENDS = [
    'users.auth_backend.WebUserAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# N8N webhooky pro notifikace ticketů (nový ticket, nový komentář)
TICKET_WEBHOOK_URLS = [
    'https://80-211-198-189.sslip.io/webhook/e06d3356-c8d9-4bbd-bf15-2f9701962278',
    'https://80-211-198-189.sslip.io/webhook-test/e06d3356-c8d9-4bbd-bf15-2f9701962278',
]

# Logování pro produkci
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}

# Vytvoření logs složky pokud neexistuje
os.makedirs(BASE_DIR / 'logs', exist_ok=True) 