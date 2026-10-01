"""
Django settings for scam_project project.

Every deployment-specific value comes from environment variables, optionally
loaded from a `.env` file next to manage.py. Copy `.env.example` to `.env` and
edit it; never commit `.env`.

- No POSTGRES_HOST set  -> SQLite at db.sqlite3 (zero setup for volunteers).
- POSTGRES_HOST set     -> PostgreSQL (see docs/POSTGRES.md).

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Values already set in the real environment always win over .env. No ${VAR}
# expansion, so a password containing "${" is read exactly as written.
load_dotenv(BASE_DIR / '.env', override=False, interpolate=False)


def env_str(name, default=''):
    """Return the variable stripped of whitespace, or `default` if unset/empty."""
    value = os.environ.get(name, '').strip()
    return value or default


def env_bool(name, default=False):
    value = env_str(name).lower()
    if not value:
        return default
    if value in ('1', 'true', 'yes', 'on'):
        return True
    if value in ('0', 'false', 'no', 'off'):
        return False
    raise ImproperlyConfigured(f'{name} must be true or false, got {value!r}.')


def env_int(name, default):
    value = env_str(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise ImproperlyConfigured(f'{name} must be a whole number, got {value!r}.') from None


def env_list(name):
    """Comma-separated list, e.g. "example.org, www.example.org"."""
    return [item.strip() for item in env_str(name).split(',') if item.strip()]


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DJANGO_DEBUG', False)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env_str('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY is not set. Copy .env.example to .env and set '
            'DJANGO_SECRET_KEY (or set DJANGO_DEBUG=True for local development).'
        )
    SECRET_KEY = 'django-insecure-dev-only-key-never-use-in-production'

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Full origins (scheme + host), e.g. "https://scams.example.org".
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

# The main Dollar Scholars site, whose header and footer every page shows (loaded live from
# <DS_SITE_URL>/embed/site-header.js and site-footer.js). Empty = use this app's own copies.
DS_SITE_URL = env_str('DS_SITE_URL', 'https://dollarscholars.org').rstrip('/')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'scams'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'scam_project.urls'

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
                'scams.context_processors.site_embeds',
            ],
        },
    },
]

WSGI_APPLICATION = 'scam_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# The sslmode values libpq accepts; anything else would only fail at connect time.
POSTGRES_SSLMODES = ('disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full')

if env_str('POSTGRES_HOST'):
    missing = [name for name in ('POSTGRES_DB', 'POSTGRES_USER') if not env_str(name)]
    if missing:
        raise ImproperlyConfigured(
            f'POSTGRES_HOST is set, so PostgreSQL is used, but {" and ".join(missing)} '
            f'{"is" if len(missing) == 1 else "are"} missing. See .env.example and docs/POSTGRES.md.'
        )
    sslmode = env_str('POSTGRES_SSLMODE', 'prefer')
    if sslmode not in POSTGRES_SSLMODES:
        raise ImproperlyConfigured(
            f'POSTGRES_SSLMODE must be one of {", ".join(POSTGRES_SSLMODES)}, got {sslmode!r}.'
        )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env_str('POSTGRES_DB'),
            'USER': env_str('POSTGRES_USER'),
            # Not stripped: a password may legitimately contain spaces.
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': env_str('POSTGRES_HOST'),
            'PORT': env_str('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': env_int('POSTGRES_CONN_MAX_AGE', 60),
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                'sslmode': sslmode,
                'connect_timeout': env_int('POSTGRES_CONNECT_TIMEOUT', 10),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': Path(env_str('SQLITE_PATH') or BASE_DIR / 'db.sqlite3'),
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
# In production run `python manage.py collectstatic`; WhiteNoise serves STATIC_ROOT.

STATIC_URL = 'static/'
STATIC_ROOT = Path(env_str('DJANGO_STATIC_ROOT') or BASE_DIR / 'staticfiles')
# Pin WhiteNoise's dev behaviour to DEBUG as configured here, not to the DEBUG=False
# the test runner forces later (avoids "No directory at: staticfiles" warnings in tests).
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = DEBUG


# Production hardening (only when DEBUG is off)

if not DEBUG:
    # Cookies only over HTTPS. Set these to False only for a plain-HTTP test box.
    SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', True)
    CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', True)
    # Behind a reverse proxy (nginx, Caddy, ...) that terminates HTTPS and sets
    # X-Forwarded-Proto. Only enable it if the proxy always sets/overwrites that header.
    if env_bool('DJANGO_SECURE_PROXY_SSL_HEADER', False):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Opt in once the site is reachable over HTTPS (both off by default so a new VM can
    # start on plain HTTP). Start HSTS small (e.g. 3600) and raise it when all is well.
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)
    SECURE_HSTS_SECONDS = env_int('DJANGO_SECURE_HSTS_SECONDS', 0)


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
