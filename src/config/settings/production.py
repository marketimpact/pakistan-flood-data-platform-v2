from .base import *
import os

# SECURITY
DEBUG = False
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "a-default-secret-key-for-local-builds"
)
ALLOWED_HOSTS = [
    "flood-data-platform.onrender.com",
    "localhost",
]  # Add your Render app URL

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# DATABASE
# Use dj-database-url to parse the DATABASE_URL from Render
import dj_database_url

DATABASES = {"default": dj_database_url.config(conn_max_age=600, ssl_require=True)}

# STATIC FILES with WhiteNoise
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MIDDLEWARE.insert(
    1, "whitenoise.middleware.WhiteNoiseMiddleware"
)  # Insert after SecurityMiddleware
