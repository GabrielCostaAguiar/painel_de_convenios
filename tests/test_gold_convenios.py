"""
Testes das funções Gold de convênios.

Estratégia: banco de teste real (pytest-django).
  - Criamos Convenio diretamente via ORM, sem CSV nem DataFrame.
  - Alimentamos as funções Gold (kpis, por_situacao, por_ano, recentes).
  - Verificamos os agregados contra os valores esperados.
"""

from datetime import date

import pytest

from apps.convenios.models import Convenio
from core.gold.convenios import kpis, por_situacao, por_ano, recentes

# Mesma amostra de dados da versão anterior do teste (5 registros):
#   123456/2024  Em Execucao         500000,00  2024
#   234567/2024  Aprovado            250000,00  2024
#   345678/2023  Prestacao de Contas 150000,00  2023
#   456789/2022  Encerrado            80000,00  2022
#   567890/2021  Prestacao de Contas 120000,00  2021
AMOSTRA = [
    ("123456/2024", "Em Execucao", date(2024, 3, 1), 500_000),
    ("234567/2024", "Aprovado", date(2024, 7, 15), 250_000),
    ("345678/2023", "Prestacao de Contas", date(2023, 5, 10), 150_000),
    ("456789/2022", "Encerrado", date(2022, 1, 20), 80_000),
    ("567890/2021", "Prestacao de Contas", date(2021, 11, 30), 120_000),
]
VALOR_TOTAL_ESPERADO = sum(valor for _, _, _, valor in AMOSTRA)
TOTAL_REGISTROS = len(AMOSTRA)


@pytest.fixture
def convenios_amostra(db):
    Convenio.objects.bulk_create(
        Convenio(
            convenio_codigo=codigo,
            situacao=situacao,
            data_inicio_vigencia=data_inicio,
            valor_total_convenio=valor,
            valor_concedente=valor,
            valor_proponente=0,
        )
        for codigo, situacao, data_inicio, valor in AMOSTRA
    )


# =============================================================================
# kpis
# =============================================================================

def test_kpis_total_convenios(convenios_amostra):
    assert kpis()["total_convenios"] == TOTAL_REGISTROS


def test_kpis_valor_total(convenios_amostra):
    assert kpis()["valor_total_convenio"] == pytest.approx(VALOR_TOTAL_ESPERADO)


def test_kpis_filtra_por_ano(convenios_amostra):
    resultado = kpis(ano=2024)
    assert resultado["total_convenios"] == 2
    assert resultado["valor_total_convenio"] == pytest.approx(750_000)


# =============================================================================
# por_situacao
# =============================================================================

def test_por_situacao_numero_de_grupos(convenios_amostra):
    """Amostra tem 4 situações únicas."""
    assert len(por_situacao()) == 4


def test_por_situacao_soma_quantidades(convenios_amostra):
    resultado = por_situacao()
    assert sum(linha["quantidade"] for linha in resultado) == TOTAL_REGISTROS


def test_por_situacao_soma_valores(convenios_amostra):
    resultado = por_situacao()
    assert sum(linha["valor_total"] for linha in resultado) == pytest.approx(VALOR_TOTAL_ESPERADO)


def test_por_situacao_prestacao_de_contas_tem_dois(convenios_amostra):
    resultado = por_situacao()
    linha = next(l for l in resultado if l["situacao"] == "Prestacao de Contas")
    assert linha["quantidade"] == 2


# =============================================================================
# por_ano
# =============================================================================

def test_por_ano_numero_de_anos(convenios_amostra):
    """Amostra abrange 4 anos distintos: 2021, 2022, 2023, 2024."""
    assert len(por_ano()) == 4


def test_por_ano_soma_quantidades(convenios_amostra):
    resultado = por_ano()
    assert sum(linha["quantidade"] for linha in resultado) == TOTAL_REGISTROS


def test_por_ano_2024_tem_dois_convenios(convenios_amostra):
    resultado = por_ano()
    linha = next(l for l in resultado if l["ano"] == 2024)
    assert linha["quantidade"] == 2


def test_por_ano_ordenado_cronologicamente(convenios_amostra):
    anos = [linha["ano"] for linha in por_ano()]
    assert anos == sorted(anos)


# =============================================================================
# recentes
# =============================================================================

def test_recentes_ordenado_por_data_decrescente(convenios_amostra):
    resultado = recentes()
    datas = [linha["data_inicio"] for linha in resultado]
    assert datas == sorted(datas, reverse=True)


def test_recentes_respeita_limite(convenios_amostra):
    assert len(recentes(limite=2)) == 2
