"""Django settings for KILO. Every secret and deployment-specific value comes from the environment
(see .env.example); nothing confidential lives in the repository."""
import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


DEBUG = env_bool('DEBUG')
TESTING = 'test' in sys.argv

SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG or TESTING:
        SECRET_KEY = 'insecure-development-key-do-not-use-in-production'
    else:
        raise ImproperlyConfigured('Set the SECRET_KEY environment variable (see .env.example).')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):          # set automatically on Render
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
if os.environ.get('RENDER_EXTERNAL_URL'):
    CSRF_TRUSTED_ORIGINS.append(os.environ['RENDER_EXTERNAL_URL'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'myapp',
    'support',
]

MIDDLEWARE = [
    'support.middleware.RequestLoggingMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'

# ---- SQL database: SQLite locally, PostgreSQL in production via DATABASE_URL ----
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}', conn_max_age=600),
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

# ---- Auth ----
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# ---- REST API: session auth for the browser, token auth for other clients ----
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}

# ---- HTTPS / cookies (production defaults on, local development off) ----
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = env_bool('SECURE_COOKIES', not DEBUG and not TESTING)
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ---- MongoDB (chat logs + feedback) ----
MONGODB_URI = os.environ.get('MONGODB_URI', '')
MONGODB_DB = os.environ.get('MONGODB_DB', 'kilo_assistant')

# ---- AI assistant (optional LLM; the FAQ engine works without a key) ----
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-haiku-5-5')
LLM_TIMEOUT_SECONDS = float(os.environ.get('LLM_TIMEOUT_SECONDS', '8'))
CHAT_MAX_MESSAGE_LENGTH = 500
CHAT_RATE_LIMIT = int(os.environ.get('CHAT_RATE_LIMIT', '20'))                      # messages ...
CHAT_RATE_WINDOW_SECONDS = int(os.environ.get('CHAT_RATE_WINDOW_SECONDS', '60'))    # ... per window

# ---- Third-party API: Open Food Facts (food lookup) with timeout + fallback ----
FOOD_API_TIMEOUT_SECONDS = float(os.environ.get('FOOD_API_TIMEOUT_SECONDS', '4'))

# ---- Logging: one line per request on the console and in logs/requests.log ----
LOG_DIR = BASE_DIR / 'logs'
LOGGING = {'version': 1, 'disable_existing_loggers': False}
if not TESTING:
    LOG_DIR.mkdir(exist_ok=True)
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {'plain': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'}},
        'handlers': {
            'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'},
            'requests_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(LOG_DIR / 'requests.log'),
                'maxBytes': 1_000_000, 'backupCount': 3, 'formatter': 'plain',
            },
        },
        'loggers': {
            'requests': {'handlers': ['console', 'requests_file'], 'level': 'INFO', 'propagate': False},
            'support': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        },
    }
