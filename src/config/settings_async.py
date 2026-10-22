import os
from config.settings import *

# Activate django-async-backend for PostgreSQL
INSTALLED_APPS = ["django_async_backend"] + [app for app in INSTALLED_APPS if app != "django_async_backend"]

# Using django-async-backend true async psycopg3 connection pool
DATABASES = {
    "default": {
        "ENGINE": "django_async_backend.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "pool": {
                "min_size": int(os.environ.get("DB_POOL_MIN_SIZE", "5")),
                "max_size": int(os.environ.get("DB_POOL_MAX_SIZE", "50")),
            },
        },
    }
}

IS_ASYNC_BACKEND = True
