from .base import *  # noqa: F401, F403
from pathlib import Path

import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# -----------------------------------------------------------------------
# Modo compartilhar — exposição temporária via túnel (cloudflared) para
# colegas testarem e darem feedback. Liga só com a env var MODO_COMPARTILHAR=1;
# sem ela, nada neste bloco tem efeito e o dev continua exatamente como antes.
# Passo a passo completo em COMPARTILHAR.md.
# -----------------------------------------------------------------------

if env.bool("MODO_COMPARTILHAR", default=False):
    DEBUG = False

    ALLOWED_HOSTS = list(set(ALLOWED_HOSTS) | {".trycloudflare.com", "localhost", "127.0.0.1"})

    CSRF_TRUSTED_ORIGINS = ["https://*.trycloudflare.com"]

    # WhiteNoise logo após SecurityMiddleware (posição recomendada pela lib);
    # Basic Auth no topo, antes de qualquer outro middleware — inclusive dos
    # estáticos, para que o CSS não fique acessível sem login.
    _security_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
    MIDDLEWARE = [
        *MIDDLEWARE[:_security_idx + 1],
        "whitenoise.middleware.WhiteNoiseMiddleware",
        *MIDDLEWARE[_security_idx + 1:],
    ]
    MIDDLEWARE = ["core.middleware.basic_auth.ShareBasicAuthMiddleware", *MIDDLEWARE]

    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
