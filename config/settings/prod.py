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
# Arquivos estaticos — WhiteNoise
# ---------------------------------------------------------------------------
# Com DEBUG=False o Django para de servir /static/ por conta propria. Se nada
# na frente fizer isso, o painel sobe sem CSS nem JS. O WhiteNoise faz o
# proprio Django servir esses arquivos de forma eficiente.
#
# Se o servidor web da Prodemge tambem servir /static/, ele atende a
# requisicao antes de ela chegar ao Python e o WhiteNoise simplesmente nao e
# acionado — por isso ligar aqui e seguro nos dois cenarios.
#
# Posicao recomendada pela propria lib: logo apos o SecurityMiddleware, para
# os headers de seguranca valerem tambem para os estaticos. Mesma posicao que
# o Modo Compartilhar do dev.py ja usa.
_WHITENOISE = "whitenoise.middleware.WhiteNoiseMiddleware"

if _WHITENOISE not in MIDDLEWARE:  # noqa: F405
    _idx_security = MIDDLEWARE.index(  # noqa: F405
        "django.middleware.security.SecurityMiddleware"
    )
    MIDDLEWARE = [  # noqa: F405
        *MIDDLEWARE[: _idx_security + 1],  # noqa: F405
        _WHITENOISE,
        *MIDDLEWARE[_idx_security + 1:],  # noqa: F405
    ]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Compressed: serve .gz/.br pre-comprimidos, gerados no collectstatic.
    # Manifest: renomeia cada arquivo com o hash do conteudo, para o navegador
    # nunca reaproveitar um CSS antigo depois de um deploy.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
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

# HSTS em subdominios — desligado ate alguem confirmar que pode ligar.
#
# SECURE_HSTS_INCLUDE_SUBDOMAINS=True instrui o navegador a RECUSAR HTTP em
# todos os subdominios do dominio, por ate um ano. Se algum subdominio da
# Prodemge ainda responder so em HTTP, ele fica inacessivel para quem visitou
# o painel — e isso nao se desfaz do lado do servidor: o navegador ja guardou
# a instrucao. Por isso o default e False, e ligar e decisao de quem conhece
# todos os subdominios.
#
# SECURE_HSTS_PRELOAD so faz sentido depois do anterior, e e ainda mais dificil
# de reverter: uma vez na lista de preload dos navegadores, o dominio fica
# marcado por meses.
#
# Configuraveis por ambiente para nao exigir alteracao de codigo quando a
# confirmacao vier.
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
