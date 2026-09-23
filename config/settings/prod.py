from .base import *  # noqa: F401, F403
import environ

env = environ.Env()

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

# ---------------------------------------------------------------------------
# Cache — precisa ser COMPARTILHADO entre processos
# ---------------------------------------------------------------------------
# O LocMemCache (default implicito do Django) guarda tudo na memoria de cada
# processo. Em producao, com varios workers, cada um fica com a sua copia — e o
# comando de carga, que roda num processo a parte, invalida so a memoria dele.
# Os workers que atendem o painel continuariam servindo indicadores velhos ate
# o TTL expirar, que e exatamente o bug que a invalidacao automatica de
# core/cache.py existe para evitar.
#
# Com REDIS_URL definida usamos Redis; sem ela, o cache vai para uma tabela no
# proprio PostgreSQL. As duas opcoes sao compartilhadas entre workers, que e o
# que importa aqui. O DatabaseCache nao exige infraestrutura nova, mas a tabela
# precisa ser criada uma vez: `python manage.py createcachetable`.
_REDIS_URL = env("REDIS_URL", default="")

if _REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
            # Isola as chaves do painel caso a instancia Redis seja
            # compartilhada com outro sistema.
            "KEY_PREFIX": "painel",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "painel_cache",
            "KEY_PREFIX": "painel",
        }
    }

SECURE_HSTS_SECONDS = 31536000
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
