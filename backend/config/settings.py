"""Django settings for School CRM & ERP backend.

Environment-driven configuration for development/staging/production.
Baseline decisions: D-002, D-010, D-011, D-014.
"""

from __future__ import annotations

import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    POSTGRES_PORT=(int, 5432),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
)

ENV_FILE = BASE_DIR.parent / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)

DJANGO_ENV = env("DJANGO_ENV", default="development")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "apps.core",
    "apps.institutions",
    "apps.accounts",
    "apps.permissions",
    "apps.audit",
    "apps.guardians",
    "apps.admissions",
    "apps.students",
    "apps.imports",
    "apps.employees",
    "apps.academics",
    "apps.teaching",
    "apps.attendance",
    "apps.examinations",
    "apps.transcripts",
    "apps.alumni",
    "apps.finance",
    "apps.notifications",
    "apps.accounting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="school_erp"),
        "USER": env("POSTGRES_USER", default="school_erp"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="change-me"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

if DJANGO_ENV != "docker" and env("DATABASE_URL", default=None):
    DATABASES["default"] = env.db("DATABASE_URL")

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

LANGUAGE_CODE = env("DEFAULT_LANGUAGE_CODE", default="en-ng")
TIME_ZONE = env("DEFAULT_TIME_ZONE", default="Africa/Lagos")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
PRIVATE_MEDIA_ROOT = BASE_DIR / env("PRIVATE_MEDIA_ROOT", default="private-media")
PUBLIC_MEDIA_ROOT = BASE_DIR / env("PUBLIC_MEDIA_ROOT", default="public-media")
DOCUMENT_UPLOAD_MAX_BYTES = env.int("DOCUMENT_UPLOAD_MAX_BYTES", default=10 * 1024 * 1024)
DOCUMENT_MALWARE_SCAN_HOOK = env("DOCUMENT_MALWARE_SCAN_HOOK", default="")
TRANSCRIPT_VERIFICATION_BASE_URL = env(
    "TRANSCRIPT_VERIFICATION_BASE_URL", default="/verify/transcripts"
)
TEACHING_DEFAULT_WORKLOAD_MAX_HOURS = env.int("TEACHING_DEFAULT_WORKLOAD_MAX_HOURS", default=40)
EXAMINATIONS_DEFAULT_GRADING_SCALE_CODE = env(
    "EXAMINATIONS_DEFAULT_GRADING_SCALE_CODE", default="DEFAULT"
)
EXAMINATIONS_DEFAULT_GRADING_SCALE_NAME = env(
    "EXAMINATIONS_DEFAULT_GRADING_SCALE_NAME", default="Default Grading Scale"
)
EXAMINATIONS_DEFAULT_PASS_MARK = env("EXAMINATIONS_DEFAULT_PASS_MARK", default="50")
EXAMINATIONS_DEFAULT_GRADING_POLICY_CODE = env(
    "EXAMINATIONS_DEFAULT_GRADING_POLICY_CODE", default="DEFAULT"
)
EXAMINATIONS_DEFAULT_GRADING_POLICY_NAME = env(
    "EXAMINATIONS_DEFAULT_GRADING_POLICY_NAME", default="Default Grading Policy"
)

if STORAGE_BACKEND == "s3":
    STORAGES["private_documents"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": env("AWS_PRIVATE_STORAGE_BUCKET", default="school-erp-private"),
            "location": env("AWS_PRIVATE_STORAGE_LOCATION", default="documents"),
            "default_acl": "private",
            "querystring_auth": True,
        },
    }
else:
    STORAGES["private_documents"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(PRIVATE_MEDIA_ROOT), "base_url": None},
    }
STORAGES["public_media"] = {
    "BACKEND": "django.core.files.storage.FileSystemStorage",
    "OPTIONS": {"location": str(PUBLIC_MEDIA_ROOT), "base_url": MEDIA_URL},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.permissions.permissions.IsAuthenticatedAndActive",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "School CRM & ERP API",
    "DESCRIPTION": "Phase 1 foundation API (MVP in progress).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# CORS / CSRF (D-011)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Cookies / security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE")
CSRF_COOKIE_HTTPONLY = False  # must be readable by frontend for CSRF header flows if used
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if not DEBUG else None
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=False)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = env.bool("CELERY_TASK_ACKS_LATE", default=True)
CELERY_WORKER_PREFETCH_MULTIPLIER = env.int("CELERY_WORKER_PREFETCH_MULTIPLIER", default=1)
CELERY_RESULT_EXPIRES = env.int("CELERY_RESULT_EXPIRES", default=86400)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = env.bool(
    "CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP", default=True
)
CELERY_BEAT_SCHEDULE_FILENAME = env("CELERY_BEAT_SCHEDULE_FILENAME", default="celerybeat-schedule")

PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", default="mock")
PAYMENT_FLUTTERWAVE_SECRET_KEY = env("PAYMENT_FLUTTERWAVE_SECRET_KEY", default="")
PAYMENT_FLUTTERWAVE_PUBLIC_KEY = env("PAYMENT_FLUTTERWAVE_PUBLIC_KEY", default="")
PAYMENT_FLUTTERWAVE_WEBHOOK_SECRET_HASH = env(
    "PAYMENT_FLUTTERWAVE_WEBHOOK_SECRET_HASH", default=""
)
PAYMENT_FLUTTERWAVE_BASE_URL = env(
    "PAYMENT_FLUTTERWAVE_BASE_URL", default="https://api.flutterwave.com/v3"
)
PAYMENT_WEBHOOK_SECRETS = {
    k.removeprefix("PAYMENT_WEBHOOK_SECRET_").lower(): v
    for k, v in os.environ.items()
    if k.startswith("PAYMENT_WEBHOOK_SECRET_") and v
}
if PAYMENT_FLUTTERWAVE_WEBHOOK_SECRET_HASH:
    PAYMENT_WEBHOOK_SECRETS.setdefault(
        "flutterwave", PAYMENT_FLUTTERWAVE_WEBHOOK_SECRET_HASH
    )

# Email
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# Logging (basic, structured-ready placeholder)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Project defaults
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", default="NGN")
DEFAULT_DATE_FORMAT = env("DEFAULT_DATE_FORMAT", default="DD/MM/YYYY")
