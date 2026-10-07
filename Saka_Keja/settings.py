"""
Django settings for Saka_Keja project.

Works locally (SQLite, /media/) and on Vercel (Postgres, S3 photo storage)
depending on which environment variables are set.
"""

import os
import urllib.parse
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------- Core ----------
# On Vercel, set SECRET_KEY and DEBUG=False in Environment Variables.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-key-change-me")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".vercel.app"]
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"]
# When you buy a domain, add it to both lists, e.g.
# ALLOWED_HOSTS += ["sakakeja.co.ke", "www.sakakeja.co.ke"]
# CSRF_TRUSTED_ORIGINS += ["https://sakakeja.co.ke", "https://www.sakakeja.co.ke"]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True


# ---------- Application definition ----------
INSTALLED_APPS = [
    'accounts',
    'properties',
    'inquiries',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Saka_Keja.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'inquiries.context_processors.unread_inquiries',
            ],
        },
    },
]

WSGI_APPLICATION = 'Saka_Keja.wsgi.application'


# ---------- Database ----------
# Vercel's disk is read-only, so SQLite cannot be used in production.
# DATABASE_URL is set automatically by the Neon database you added.
if os.environ.get("DATABASE_URL"):
    _db = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db.path.lstrip("/"),
            "USER": urllib.parse.unquote(_db.username or ""),
            "PASSWORD": urllib.parse.unquote(_db.password or ""),
            "HOST": _db.hostname,
            "PORT": _db.port or 5432,
            "OPTIONS": {"sslmode": "require"},
            "CONN_MAX_AGE": 0,                    # serverless: don't keep connections open
            "DISABLE_SERVER_SIDE_CURSORS": True,  # needed with pooled connections
        }
    }
else:
    # Local development keeps using SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ---------- Password validation ----------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------- Internationalization ----------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ---------- Static files ----------
# Vercel runs collectstatic automatically when STATIC_ROOT is set
# and serves the files from its CDN.
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ---------- Media (house photos) ----------
# Uploaded photos cannot be saved on Vercel's disk, so in production they go
# to an S3-compatible bucket. Locally (no S3_BUCKET set) they still go to /media/.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

if os.environ.get("S3_BUCKET"):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ["S3_BUCKET"],
            "endpoint_url": os.environ["S3_ENDPOINT"],
            "region_name": os.environ.get("S3_REGION", "auto"),
            "access_key": os.environ["S3_ACCESS_KEY"],
            "secret_key": os.environ["S3_SECRET_KEY"],
            # Public address that browsers use to load the photos
            "custom_domain": os.environ["S3_PUBLIC_DOMAIN"],
            "addressing_style": "path",
            "querystring_auth": False,
            "file_overwrite": False,
        },
    }


# ---------- Email ----------
# Django 6.1 uses MAILERS instead of the old EMAIL_* settings.
# Locally (no EMAIL_HOST set) emails are printed in the terminal, so you can
# read OTP codes and reset links there. In production set the EMAIL_* variables
# in Vercel to send real email through an SMTP service.
if os.environ.get("EMAIL_HOST"):
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": os.environ["EMAIL_HOST"],
                "port": int(os.environ.get("EMAIL_PORT", "587")),
                "username": os.environ["EMAIL_HOST_USER"],
                "password": os.environ["EMAIL_HOST_PASSWORD"],
                "use_tls": True,
            },
        },
    }
else:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.console.EmailBackend",
        },
    }

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Saka Keja <noreply@sakakeja.co.ke>")


# ---------- Accounts ----------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGOUT_REDIRECT_URL = "properties:home"