"""
Pengaturan proyek Sistem Pakar Diagnosa Perkembangan Anak Usia Dini
TK YPPK Kristus Terang Dunia Waena.

Nilai rahasia dan pengaturan server dapat diganti lewat environment variable
(DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS) tanpa mengubah file ini.
"""

import os
from pathlib import Path

from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Keamanan
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-%$y0k=2i8pssl$4mq^y&3u#mk9@%yfnq(u$#mab$sbhr&=8hm4",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]",'*'] + [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()
]

# ---------------------------------------------------------------------------
# Aplikasi
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'expert',
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

ROOT_URLCONF = 'sp_diagnosa_anak.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'expert.context_processors.sekolah',
            ],
        },
    },
]

WSGI_APPLICATION = 'sp_diagnosa_anak.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Login guru
# ---------------------------------------------------------------------------
LOGIN_URL = 'masuk'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'

# True  = halaman diagnosis, data anak, riwayat, dan statistik hanya untuk guru
#         yang sudah login (disarankan, karena berisi data pribadi anak).
# False = semua halaman dapat dibuka tanpa login (misalnya untuk demo).
WAJIB_LOGIN = os.environ.get("SP_WAJIB_LOGIN", "1") == "1"

# ---------------------------------------------------------------------------
# Bahasa & zona waktu (Waena, Jayapura = WIT)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Jayapura'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# File statis & media
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Identitas sekolah (tampil di halaman Kontak, footer, dan laporan PDF).
# Silakan lengkapi telepon dan email sekolah.
# ---------------------------------------------------------------------------
SEKOLAH = {
    "nama": "TK YPPK Kristus Terang Dunia Waena",
    "nama_singkat": "TK YPPK KTD Waena",
    "alamat": "Waena, Distrik Heram, Kota Jayapura, Papua",
    "telepon": "",
    "email": "",
    "kepala_sekolah": "",
}

MESSAGE_TAGS = {
    message_constants.ERROR: "danger",  # kelas Bootstrap "alert-danger"
}
