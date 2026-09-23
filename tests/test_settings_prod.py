"""
Testes das settings de produção (config/settings/prod.py).

Rodam num **subprocesso**: importar as settings de prod no processo do pytest
contaminaria o resto da suíte (django.setup() só acontece uma vez por processo,
e o pytest-django já configurou as de dev). O subprocesso também deixa passar
as variáveis de ambiente fictícias sem vazar para os outros testes.

Nada aqui conecta em banco ou Redis — só inspeciona a configuração resultante.
"""
import json
import os
import subprocess
import sys

import pytest

# Variáveis mínimas para prod.py importar. Valores fictícios: nenhum teste
# abre conexão.
ENV_BASE = {
    "DJANGO_SECRET_KEY": "dummy-para-teste-de-settings",
    "DJANGO_ALLOWED_HOSTS": "painel.exemplo.mg.gov.br",
    "DB_NAME": "dummy",
    "DB_USER": "u",
    "DB_PASSWORD": "p",
}

# Lê as settings de prod e devolve como JSON o que interessa aos testes.
_SONDA = """
import django, json, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()
from django.conf import settings

print("---JSON---")
print(json.dumps({
    "cache_backend": settings.CACHES["default"]["BACKEND"],
    "cache_location": str(settings.CACHES["default"].get("LOCATION", "")),
    "cache_key_prefix": settings.CACHES["default"].get("KEY_PREFIX", ""),
    "middleware": list(settings.MIDDLEWARE),
    "static_root": str(settings.STATIC_ROOT or ""),
    "staticfiles_backend": settings.STORAGES["staticfiles"]["BACKEND"],
    "gold_cache_seconds": settings.GOLD_CACHE_SECONDS,
    "debug": settings.DEBUG,
    "hsts_seconds": settings.SECURE_HSTS_SECONDS,
    "hsts_include_subdomains": settings.SECURE_HSTS_INCLUDE_SUBDOMAINS,
    "hsts_preload": settings.SECURE_HSTS_PRELOAD,
    "pipeline_incluir_grp": settings.PIPELINE_INCLUIR_GRP,
}))
"""


def _settings_de_prod(**extra_env) -> dict:
    """Importa config.settings.prod num subprocesso e devolve o dict da sonda."""
    env = {**os.environ, **ENV_BASE, **extra_env}
    # Garante que uma REDIS_URL do ambiente real não interfira no caso "sem Redis".
    if "REDIS_URL" not in extra_env:
        env.pop("REDIS_URL", None)
    env.pop("DJANGO_SETTINGS_MODULE", None)

    proc = subprocess.run(
        [sys.executable, "-c", _SONDA],
        capture_output=True, text=True, env=env, cwd=os.getcwd(),
    )
    if proc.returncode != 0:
        pytest.fail(f"falha ao carregar settings de prod:\n{proc.stdout}\n{proc.stderr}")

    _, _, payload = proc.stdout.partition("---JSON---")
    return json.loads(payload.strip())


@pytest.fixture(scope="module")
def prod_sem_redis():
    return _settings_de_prod()


@pytest.fixture(scope="module")
def prod_com_redis():
    return _settings_de_prod(REDIS_URL="redis://localhost:6379/1")


# ---------------------------------------------------------------------------
# Cache compartilhado
# ---------------------------------------------------------------------------

LOCMEM = "django.core.cache.backends.locmem.LocMemCache"


def test_sem_redis_usa_cache_no_banco(prod_sem_redis):
    """Sem REDIS_URL, cai no DatabaseCache — compartilhado via PostgreSQL."""
    assert prod_sem_redis["cache_backend"] == "django.core.cache.backends.db.DatabaseCache"
    assert prod_sem_redis["cache_location"] == "painel_cache"


def test_com_redis_usa_cache_redis(prod_com_redis):
    assert prod_com_redis["cache_backend"] == "django.core.cache.backends.redis.RedisCache"
    assert prod_com_redis["cache_location"] == "redis://localhost:6379/1"
    assert prod_com_redis["cache_key_prefix"] == "painel"


@pytest.mark.parametrize("fixture", ["prod_sem_redis", "prod_com_redis"])
def test_producao_nunca_usa_locmemcache(fixture, request):
    """
    O LocMemCache é por processo: com vários workers, a invalidação disparada
    pelo comando de carga não chegaria a nenhum deles.
    """
    assert request.getfixturevalue(fixture)["cache_backend"] != LOCMEM


def test_gold_cache_seconds_tem_default_de_uma_hora(prod_sem_redis):
    assert prod_sem_redis["gold_cache_seconds"] == 3600


def test_gold_cache_seconds_e_configuravel_por_env():
    assert _settings_de_prod(GOLD_CACHE_SECONDS="60")["gold_cache_seconds"] == 60


# ---------------------------------------------------------------------------
# Arquivos estáticos
# ---------------------------------------------------------------------------

SECURITY_MIDDLEWARE = "django.middleware.security.SecurityMiddleware"
WHITENOISE_MIDDLEWARE = "whitenoise.middleware.WhiteNoiseMiddleware"


def test_whitenoise_esta_logo_apos_o_security_middleware(prod_sem_redis):
    """
    Com DEBUG=False o Django não serve /static/ sozinho. A posição é a
    recomendada pela lib: depois do SecurityMiddleware, para os headers de
    segurança valerem também nos estáticos, e antes de todo o resto.
    """
    middleware = prod_sem_redis["middleware"]

    assert WHITENOISE_MIDDLEWARE in middleware
    assert middleware.index(WHITENOISE_MIDDLEWARE) == middleware.index(SECURITY_MIDDLEWARE) + 1


def test_whitenoise_aparece_uma_vez_so(prod_sem_redis):
    """Guarda contra duplicação se um dia o middleware entrar também no base.py."""
    assert prod_sem_redis["middleware"].count(WHITENOISE_MIDDLEWARE) == 1


def test_static_root_esta_definido(prod_sem_redis):
    """Sem STATIC_ROOT o collectstatic não tem para onde copiar."""
    assert prod_sem_redis["static_root"]


def test_static_root_e_configuravel_por_env(tmp_path):
    destino = str(tmp_path / "estaticos")
    assert _settings_de_prod(STATIC_ROOT=destino)["static_root"] == destino


def test_storage_de_estaticos_e_do_whitenoise(prod_sem_redis):
    assert prod_sem_redis["staticfiles_backend"].startswith("whitenoise.storage.")


# ---------------------------------------------------------------------------
# Segurança
# ---------------------------------------------------------------------------

def test_debug_desligado(prod_sem_redis):
    assert prod_sem_redis["debug"] is False


def test_hsts_seconds_permanece_em_um_ano(prod_sem_redis):
    assert prod_sem_redis["hsts_seconds"] == 31536000


def test_hsts_de_subdominios_desligado_por_padrao(prod_sem_redis):
    """
    Decisão registrada: ligar sem confirmar que TODOS os subdomínios são HTTPS
    deixaria qualquer subdomínio em HTTP inacessível para quem já visitou o
    painel — e o navegador guarda a instrução, então não se desfaz do lado do
    servidor.
    """
    assert prod_sem_redis["hsts_include_subdomains"] is False
    assert prod_sem_redis["hsts_preload"] is False


def test_hsts_de_subdominios_e_configuravel_por_env():
    """Quando a confirmação vier, liga por variável — sem alterar código."""
    resultado = _settings_de_prod(
        SECURE_HSTS_INCLUDE_SUBDOMAINS="True",
        SECURE_HSTS_PRELOAD="True",
    )

    assert resultado["hsts_include_subdomains"] is True
    assert resultado["hsts_preload"] is True


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def test_grp_fora_do_pipeline_por_padrao(prod_sem_redis):
    """O GRP está em teste: não pode afetar a atualização diária do SIGCON."""
    assert prod_sem_redis["pipeline_incluir_grp"] is False


def test_grp_no_pipeline_e_configuravel_por_env():
    assert _settings_de_prod(PIPELINE_INCLUIR_GRP="True")["pipeline_incluir_grp"] is True
