"""Test settings for flood data platform."""

from .base import *

# Use PostgreSQL for tests (configured via DATABASE_URL in CI)
import dj_database_url
import os

if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(
            default=os.environ.get("DATABASE_URL"),
            conn_max_age=600,
        )
    }
else:
    # Fallback to SQLite for local tests
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# Don't disable migrations - they're needed for proper database setup

# Test-specific settings
DEBUG = False
TESTING = True

# Disable caching
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Test email backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Test media settings
MEDIA_ROOT = "/tmp/test_media"
MEDIA_URL = "/test_media/"

# Test static files
STATIC_ROOT = "/tmp/test_static"

# Test API key
GOOGLE_FLOOD_HUB_API_KEY = "test_api_key_for_testing"

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Test-specific security settings
SECRET_KEY = "test-secret-key-for-testing-only"
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
