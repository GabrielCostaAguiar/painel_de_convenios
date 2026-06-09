"""
Camada de serviços do dashboard.

Responsabilidade: fazer a ponte entre o banco (ORM Django) e a Gold (core/gold/).
As views NÃO acessam o banco diretamente — elas chamam funções deste módulo.

Separação de responsabilidades:
  - View       → recebe request, escolhe template, passa contexto
  - Services   → busca dados, chama Gold, aplica cache
  - core/gold/ → faz os cálculos (função pura, sem Django)

Sobre o cache:
  Os dados mudam apenas quando `carregar_silver` é executado.
  Ao concluir, ele chama invalidar_cache() automaticamente.
  Em produção, configure Redis em settings.py:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                          "LOCATION": "redis://127.0.0.1:6379/1"}}
"""

import logging

import pandas as pd
from django.conf import settings
from django.core.cache import cache

from core.gold import convenios as gold

logger = logging.getLogger(__name__)

_CACHE_TTL = getattr(settings, "GOLD_CACHE_SECONDS", 3600)
_CACHE_KEY = "gold:indicadores:convenios"


def _carregar_df() -> pd.DataFrame:
    from apps.convenios.models import Convenio
    qs = Convenio.objects.all().values(
        "nr_convenio", "situacao", "valor_global",
        "data_inicio", "concedente", "convenente",
    )
    return pd.DataFrame.from_records(qs)


def get_indicadores(ano: int | None = None, usar_cache: bool = True) -> dict:
    """
    Retorna indicadores Gold prontos para as views.

    Parâmetros
    ----------
    ano         : filtra pelo ano de início do convênio; None = todos os anos
    usar_cache  : False força recalculo (útil após carga ou para filtros)
    """
    cache_key = _CACHE_KEY if ano is None else f"{_CACHE_KEY}:ano:{ano}"

    if usar_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    df = _carregar_df()
    if df.empty:
        return {"vazio": True}

    if ano is not None:
        anos_serie = pd.to_datetime(df["data_inicio"], errors="coerce").dt.year
        df = df[anos_serie == ano]

    if df.empty:
        return {"vazio": True}

    resultado = {
        "vazio": False,
        "resumo": gold.resumo_geral(df),
        "por_situacao": gold.total_por_situacao(df),
        "por_ano": gold.total_por_ano(df),
        "por_concedente": gold.total_por_concedente(df),
    }

    if usar_cache:
        cache.set(cache_key, resultado, _CACHE_TTL)

    return resultado


def get_anos_disponiveis() -> list[int]:
    """Lista de anos com convênios, em ordem decrescente."""
    from apps.convenios.models import Convenio
    from django.db.models.functions import ExtractYear
    return list(
        Convenio.objects
        .exclude(data_inicio=None)
        .annotate(ano=ExtractYear("data_inicio"))
        .values_list("ano", flat=True)
        .distinct()
        .order_by("-ano")
    )


def invalidar_cache() -> None:
    """Limpa o cache principal. Chamado automaticamente por carregar_silver."""
    cache.delete(_CACHE_KEY)
    logger.info("Cache invalidado: %s", _CACHE_KEY)
