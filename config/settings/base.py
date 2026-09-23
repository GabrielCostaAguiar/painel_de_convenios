from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# Se DATA_DIR não estiver definido (ou estiver vazio) no .env, usa BASE_DIR/data
_data_dir_env = env("DATA_DIR", default="")
DATA_DIR = str(_data_dir_env if _data_dir_env else BASE_DIR / "data")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.dashboard",
    "apps.convenios",
    "apps.pipeline",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Destino do collectstatic. Sobrescrevivel por ambiente porque em alguns
# deploys o diretorio servido pelo servidor web fica fora do projeto.
_static_root_env = env("STATIC_ROOT", default="")
STATIC_ROOT = _static_root_env if _static_root_env else BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tempo de vida do cache de indicadores Gold (apps/dashboard/services.py).
# Declarado aqui para o numero ficar visivel a quem opera, em vez de viver
# como default embutido no codigo. As chaves e a invalidacao estao em
# core/cache.py.
GOLD_CACHE_SECONDS = env.int("GOLD_CACHE_SECONDS", default=3600)

# Inclui as tabelas do GRP na etapa Silver e na carga do `rodar_pipeline`.
# Default False de proposito: o GRP ainda esta em teste, e uma falha ou
# ausencia de arquivo GRP nao pode afetar a atualizacao diaria do painel
# SIGCON. Com False, o `rodar_pipeline` se comporta exatamente como antes de o
# GRP existir. A carga avulsa continua disponivel por
# `python manage.py carregar_grp`, independente deste setting.
PIPELINE_INCLUIR_GRP = env.bool("PIPELINE_INCLUIR_GRP", default=False)

# CACHES nao e definido aqui: cada ambiente escolhe o seu (LocMemCache em
# dev.py, Redis ou banco em prod.py). Ver a nota em prod.py sobre por que o
# LocMemCache nao serve para producao.
