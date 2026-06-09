"""
Testes das funções Gold de convênios.

Estratégia: sem banco de dados.
  - Carregamos o CSV Bronze de fixture.
  - Passamos pelo transformar_df() da Silver (mesmo código de produção).
  - Alimentamos as funções Gold com o DataFrame resultante.
  - Verificamos os resultados contra os valores esperados conhecidos.

Isso garante que qualquer mudança acidental na lógica de agregação
ou de transformação quebre imediatamente um teste.
"""

from pathlib import Path

import pandas as pd
import pytest

from core.transform.convenios import transformar_df
from core.gold.convenios import (
    resumo_geral,
    total_por_situacao,
    total_por_ano,
    total_por_concedente,
)

FIXTURE = Path(__file__).parent / "fixtures" / "convenios_exemplo.csv"

# Valores esperados calculados manualmente da fixture (5 registros):
#   123456/2024  Em Execucao     500000,00  2024
#   234567/2024  Aprovado        250000,00  2024
#   345678/2023  Prestacao...    150000,00  2023
#   456789/2022  Encerrado        80000,00  2022
#   567890/2021  Prestacao...    120000,00  2021
VALOR_TOTAL_ESPERADO = 1_100_000.0
TOTAL_REGISTROS = 5


@pytest.fixture(scope="module")
def df_gold():
    """
    DataFrame Silver derivado da fixture Bronze, pronto para as funções Gold.
    scope="module" evita reprocessar o CSV a cada função de teste.
    """
    df_bronze = pd.read_csv(FIXTURE, sep=";", dtype=str, keep_default_na=False)
    return transformar_df(df_bronze)


# =============================================================================
# resumo_geral
# =============================================================================

def test_resumo_geral_total_convenios(df_gold):
    resultado = resumo_geral(df_gold)
    assert resultado["total_convenios"] == TOTAL_REGISTROS


def test_resumo_geral_valor_total(df_gold):
    resultado = resumo_geral(df_gold)
    assert resultado["valor_total"] == pytest.approx(VALOR_TOTAL_ESPERADO)


# =============================================================================
# total_por_situacao
# =============================================================================

def test_total_por_situacao_numero_de_grupos(df_gold):
    """Fixture tem 4 situações únicas."""
    resultado = total_por_situacao(df_gold)
    assert len(resultado) == 4


def test_total_por_situacao_soma_quantidades(df_gold):
    """Soma das quantidades por situação deve ser igual ao total de registros."""
    resultado = total_por_situacao(df_gold)
    assert resultado["quantidade"].sum() == TOTAL_REGISTROS


def test_total_por_situacao_soma_valores(df_gold):
    resultado = total_por_situacao(df_gold)
    assert resultado["valor_total"].sum() == pytest.approx(VALOR_TOTAL_ESPERADO)


def test_total_por_situacao_prestacao_de_contas_tem_dois(df_gold):
    resultado = total_por_situacao(df_gold)
    linha = resultado[resultado["situacao"] == "Prestacao de Contas"]
    assert not linha.empty, "Situacao 'Prestacao de Contas' deve existir"
    assert int(linha["quantidade"].iloc[0]) == 2


# =============================================================================
# total_por_ano
# =============================================================================

def test_total_por_ano_numero_de_anos(df_gold):
    """Fixture abrange 4 anos distintos: 2021, 2022, 2023, 2024."""
    resultado = total_por_ano(df_gold)
    assert len(resultado) == 4


def test_total_por_ano_soma_quantidades(df_gold):
    resultado = total_por_ano(df_gold)
    assert resultado["quantidade"].sum() == TOTAL_REGISTROS


def test_total_por_ano_2024_tem_dois_convenios(df_gold):
    resultado = total_por_ano(df_gold)
    linha = resultado[resultado["ano"] == 2024]
    assert not linha.empty, "Ano 2024 deve estar presente"
    assert int(linha["quantidade"].iloc[0]) == 2


def test_total_por_ano_ordenado_cronologicamente(df_gold):
    resultado = total_por_ano(df_gold)
    anos = resultado["ano"].tolist()
    assert anos == sorted(anos), "Anos devem estar em ordem crescente"


# =============================================================================
# total_por_concedente
# =============================================================================

def test_total_por_concedente_ministerio_educacao_lidera(df_gold):
    """Ministerio da Educacao tem 2 convênios (maior valor total da fixture)."""
    resultado = total_por_concedente(df_gold)
    primeiro = resultado.iloc[0]["concedente"]
    assert primeiro == "Ministerio da Educacao"


def test_total_por_concedente_soma_valores(df_gold):
    resultado = total_por_concedente(df_gold)
    assert resultado["valor_total"].sum() == pytest.approx(VALOR_TOTAL_ESPERADO)
