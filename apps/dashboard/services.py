"""
Camada de serviços do dashboard.

Responsabilidade: fazer a ponte entre o banco (ORM Django) e a Gold (core/gold/).
As views NÃO acessam o banco diretamente — elas chamam funções deste módulo.

Separação de responsabilidades:
  - View       → recebe request, escolhe template, passa contexto
  - Services   → busca dados, chama Gold, aplica cache
  - core/gold/ → faz os cálculos (função pura, sem Django)

Onde faz sentido cachear?
  Os dados do banco só mudam quando `carregar_silver` é rodado (tipicamente
  uma vez por dia ou por semana). Portanto:
    - Indicadores históricos (anos anteriores): imutáveis → longa TTL ou infinita.
    - Indicadores do ano corrente: mudam na próxima carga → TTL curta (ex.: 1 hora).
  Por ora usamos uma única chave com TTL configurável em GOLD_CACHE_SECONDS.
  Quando `carregar_silver` rodar, ele deve chamar `invalidar_cache()` para
  forçar recalculo na próxima requisição.

  Em produção, troque o backend de cache para Redis no settings.py:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                          "LOCATION": "redis://127.0.0.1:6379/1"}}
"""

import logging

import pandas as pd
from django.conf import settings
from django.core.cache import cache

from core.gold import convenios as gold

logger = logging.getLogger(__name__)

# TTL padrão em segundos — pode ser sobrescrito em settings.py
_CACHE_TTL = getattr(settings, "GOLD_CACHE_SECONDS", 3600)
_CACHE_KEY = "gold:indicadores:convenios"


# ---------------------------------------------------------------------------
# Carregamento do DataFrame a partir do banco
# ---------------------------------------------------------------------------

def _carregar_df() -> pd.DataFrame:
    """
    Lê todos os convênios do banco como DataFrame.
    Importação lazy do model evita problemas de inicialização circular.
    """
    from apps.convenios.models import Convenio

    qs = Convenio.objects.all().values(
        "nr_convenio",
        "situacao",
        "valor_global",
        "data_inicio",
        "concedente",
        "convenente",
    )
    return pd.DataFrame.from_records(qs)


# ---------------------------------------------------------------------------
# API pública do serviço
# ---------------------------------------------------------------------------

def get_indicadores(usar_cache: bool = True) -> dict:
    """
    Retorna todos os indicadores Gold prontos para as views.

    Retorna um dict com:
      resumo        → dict com totais gerais
      por_situacao  → DataFrame (situacao, quantidade, valor_total)
      por_ano       → DataFrame (ano, quantidade, valor_total)
      por_concedente→ DataFrame (concedente, quantidade, valor_total)

    Se o banco estiver vazio, retorna {'vazio': True} para a view tratar.
    """
    if usar_cache:
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            logger.debug("Cache hit: %s", _CACHE_KEY)
            return cached

    df = _carregar_df()

    if df.empty:
        logger.warning("Banco de convenios vazio — rode carregar_silver primeiro.")
        return {"vazio": True}

    resultado = {
        "vazio": False,
        "resumo": gold.resumo_geral(df),
        "por_situacao": gold.total_por_situacao(df),
        "por_ano": gold.total_por_ano(df),
        "por_concedente": gold.total_por_concedente(df),
    }

    if usar_cache:
        cache.set(_CACHE_KEY, resultado, _CACHE_TTL)
        logger.debug("Cache set: %s (TTL=%ds)", _CACHE_KEY, _CACHE_TTL)

    return resultado


def invalidar_cache() -> None:
    """
    Invalida o cache dos indicadores.
    Chame após rodar carregar_silver para que a próxima requisição
    recalcule os dados com o conteúdo atualizado do banco.
    """
    cache.delete(_CACHE_KEY)
    logger.info("Cache invalidado: %s", _CACHE_KEY)
