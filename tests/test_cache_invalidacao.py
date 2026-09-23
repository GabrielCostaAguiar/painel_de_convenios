"""
Testes da invalidação centralizada do cache de indicadores (core/cache.py).

O risco coberto: antes, invalidar_cache() apagava só a chave base
"gold:indicadores:convenios" e deixava intactas as variantes por ano
("...:ano:2024", "...:ano:2023"). Depois de uma carga, o painel continuava
servindo indicadores velhos por ano até o TTL expirar — até uma hora.
"""
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings

from core.cache import (
    CHAVE_INDICADORES,
    chave_indicadores,
    invalidar_cache_indicadores,
    versao_indicadores,
)

# LocMemCache isolado por módulo: evita que estes testes enxerguem (ou deixem)
# entradas de outros testes que também mexem no cache default.
CACHE_ISOLADO = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache-invalidacao",
    }
}



@pytest.fixture(autouse=True)
def _cache_isolado_e_limpo():
    """
    Cada teste roda com um LocMemCache próprio e vazio.

    override_settings entra como context manager (e não como pytestmark, que o
    pytest não aceita) para valer também nas fixtures do pytest-django.
    """
    with override_settings(CACHES=CACHE_ISOLADO):
        cache.clear()
        yield
        cache.clear()


def test_chave_base_e_por_ano_compartilham_a_versao():
    base = chave_indicadores()
    por_ano = chave_indicadores(2024)

    assert base.startswith(CHAVE_INDICADORES)
    assert por_ano == f"{base}:ano:2024"


def test_invalidar_muda_todas_as_chaves_de_uma_vez():
    """Chave base + duas por ano populadas → invalidar → nenhuma é mais servida."""
    chaves_antigas = {
        "base": chave_indicadores(),
        "2024": chave_indicadores(2024),
        "2023": chave_indicadores(2023),
    }
    for nome, chave in chaves_antigas.items():
        cache.set(chave, f"valor-velho-{nome}", 3600)

    # sanidade: antes de invalidar, tudo é servido
    for chave in chaves_antigas.values():
        assert cache.get(chave) is not None

    invalidar_cache_indicadores()

    # as chaves que o código passa a consultar são outras, e estão vazias
    assert cache.get(chave_indicadores()) is None
    assert cache.get(chave_indicadores(2024)) is None
    assert cache.get(chave_indicadores(2023)) is None


def test_invalidar_incrementa_a_versao_mesmo_sem_contador_previo():
    """cache.incr estoura em chave inexistente; a função trata e segue."""
    assert versao_indicadores() == 1

    primeira = invalidar_cache_indicadores()
    segunda = invalidar_cache_indicadores()

    assert primeira == 2
    assert segunda == 3
    assert versao_indicadores() == 3


@pytest.mark.django_db
def test_get_indicadores_recalcula_apos_invalidacao():
    """
    Popula o cache pela própria get_indicadores, invalida e confirma que a
    camada Gold é consultada de novo em vez de devolver o valor cacheado.
    """
    from apps.dashboard import services

    with mock.patch.object(services.gold, "kpis", return_value={"total_convenios": 1}) as kpis, \
         mock.patch.object(services.gold, "por_situacao", return_value=[]), \
         mock.patch.object(services.gold, "por_ano", return_value=[]), \
         mock.patch.object(services.gold, "recentes", return_value=[]):

        services.get_indicadores(ano=2024)
        services.get_indicadores(ano=2024)
        assert kpis.call_count == 1, "segunda chamada deveria vir do cache"

        invalidar_cache_indicadores()

        services.get_indicadores(ano=2024)
        assert kpis.call_count == 2, "após invalidar, deveria recalcular"


def test_invalidar_cache_do_services_delega_para_core():
    """O nome antigo continua exportado em services e faz a mesma coisa."""
    from apps.dashboard.services import invalidar_cache

    cache.set(chave_indicadores(2024), "velho", 3600)
    invalidar_cache()

    assert cache.get(chave_indicadores(2024)) is None


# ---------------------------------------------------------------------------
# atualizar_painel(): quando o pipeline deve (e não deve) invalidar
# ---------------------------------------------------------------------------

def _etapa(nome, sucesso, contagens):
    return {"nome": nome, "sucesso": sucesso, "contagens": contagens, "erros": []}


def test_atualizar_painel_invalida_quando_houve_carga():
    from core import pipeline

    with mock.patch.object(pipeline, "_etapa_extracao_bronze",
                           return_value=_etapa("extracao_bronze", True, {})), \
         mock.patch.object(pipeline, "_etapa_silver",
                           return_value=_etapa("silver", True, {"gerados": 3})), \
         mock.patch.object(pipeline, "_etapa_gold_orm",
                           return_value=_etapa("gold_orm", True,
                                               {"carregar_convenios": {"inseridos": 10}})), \
         mock.patch.object(pipeline, "invalidar_cache_indicadores") as invalidar:

        resultado = pipeline.atualizar_painel()

    assert resultado["sucesso"] is True
    invalidar.assert_called_once()


def test_atualizar_painel_invalida_quando_so_alguns_loaders_passaram():
    """
    A etapa gold_orm falhou (carregar_convenios estourou), mas outros loaders
    gravaram no banco — os dados em tela mudaram, então o cache tem que cair.
    """
    from core import pipeline

    with mock.patch.object(pipeline, "_etapa_extracao_bronze",
                           return_value=_etapa("extracao_bronze", True, {})), \
         mock.patch.object(pipeline, "_etapa_silver",
                           return_value=_etapa("silver", True, {"gerados": 3})), \
         mock.patch.object(pipeline, "_etapa_gold_orm",
                           return_value=_etapa("gold_orm", False,
                                               {"carregar_cronograma": {"inseridos": 4}})), \
         mock.patch.object(pipeline, "invalidar_cache_indicadores") as invalidar:

        resultado = pipeline.atualizar_painel()

    assert resultado["sucesso"] is False
    invalidar.assert_called_once()


def test_atualizar_painel_nao_invalida_quando_nenhuma_carga_rodou():
    """Pipeline parou no Bronze: o banco não foi tocado, o cache continua válido."""
    from core import pipeline

    with mock.patch.object(pipeline, "_etapa_extracao_bronze",
                           return_value=_etapa("extracao_bronze", False, {})), \
         mock.patch.object(pipeline, "_etapa_silver") as silver, \
         mock.patch.object(pipeline, "_etapa_gold_orm") as gold, \
         mock.patch.object(pipeline, "invalidar_cache_indicadores") as invalidar:

        resultado = pipeline.atualizar_painel()

    assert resultado["sucesso"] is False
    silver.assert_not_called()
    gold.assert_not_called()
    invalidar.assert_not_called()


def test_atualizar_painel_nao_invalida_quando_gold_rodou_sem_nenhum_sucesso():
    """Etapa gold_orm rodou mas todos os loaders falharam: nada mudou no banco."""
    from core import pipeline

    with mock.patch.object(pipeline, "_etapa_extracao_bronze",
                           return_value=_etapa("extracao_bronze", True, {})), \
         mock.patch.object(pipeline, "_etapa_silver",
                           return_value=_etapa("silver", True, {"gerados": 1})), \
         mock.patch.object(pipeline, "_etapa_gold_orm",
                           return_value=_etapa("gold_orm", False, {})), \
         mock.patch.object(pipeline, "invalidar_cache_indicadores") as invalidar:

        pipeline.atualizar_painel()

    invalidar.assert_not_called()
