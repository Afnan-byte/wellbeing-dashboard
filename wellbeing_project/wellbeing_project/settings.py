"""
Django settings for wellbeing_project project.
"""

from pathlib import Path
import os

# ---------------------------------------------------------
# BASE DIRECTORY
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------
# SECRET KEY & DEBUG
# ---------------------------------------------------------
SECRET_KEY = 'django-insecure-6zg6dkd-&)*nr6k^65usiw=)o3buh-1ja1sp)!_eu!66*8^60h'
DEBUG = True

ALLOWED_HOSTS = [
    'wellbeing-dashboard-1.onrender.com',
    'localhost',
    '127.0.0.1'
]


# ---------------------------------------------------------
# APPLICATIONS (Removed admin & auth - not needed)
# ---------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
]


# ---------------------------------------------------------
# MIDDLEWARE (Removed auth middleware)
# ---------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ---------------------------------------------------------
# URLS & TEMPLATES
# ---------------------------------------------------------
ROOT_URLCONF = 'wellbeing_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wellbeing_project.wsgi.application'


# ---------------------------------------------------------
# DATABASE - Using signed cookies for sessions (no DB needed)
# ---------------------------------------------------------
DATABASES = {}

# Use cookie-based sessions instead of database
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24 hours


# ---------------------------------------------------------
# LANGUAGE / TIMEZONE
# ---------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Whitenoise for serving static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ---------------------------------------------------------
# GOOGLE SHEETS CONFIG
# ---------------------------------------------------------
GOOGLE_SHEET_ID = "1TyaCIHmIJ501S77rguNyoVKMje1viPJnrW5J40fFGos"