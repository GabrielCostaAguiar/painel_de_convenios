"""
Camada Gold: indicadores prontos para exibição no painel.

Filosofia desta camada:
  - Recebe um DataFrame (de qualquer origem: banco, CSV Silver, testes).
  - Devolve um DataFrame ou dict pronto para a view renderizar.
  - ZERO side effects: não grava, não lê do banco, não acessa Django.
  - Funções puras → testáveis isoladamente, sem banco e sem servidor.

Por que calcular aqui e não na hora de renderizar a tela?
  Se o cálculo fosse feito dentro da view, CADA requisição de CADA usuário
  repetiria o mesmo groupby/somatório sobre toda a tabela.
  Com a Gold, o dado pesado é calculado uma vez (ou cacheado no services.py)
  e a view apenas formata o resultado pronto.
  Em escala: 1 groupby cacheado vs N groupbys por segundo.
"""

import pandas as pd


# =============================================================================
# Preparação interna — garante que os tipos estejam corretos
# independentemente de o DataFrame vir do banco ou de um CSV de teste.
# =============================================================================

def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza tipos antes de qualquer agregação:
      - valor_global: Decimal do ORM ou string "500000.00" → float
      - data_inicio : date do ORM ou string "2024-01-01" → Timestamp
      - ano         : coluna derivada para agrupamentos temporais
    """
    df = df.copy()
    df["valor_global"] = pd.to_numeric(df["valor_global"], errors="coerce").fillna(0.0)
    df["data_inicio"] = pd.to_datetime(df["data_inicio"], errors="coerce")
    df["ano"] = df["data_inicio"].dt.year.astype("Int64")  # Int64 aceita NaN
    return df


# =============================================================================
# Indicadores
# =============================================================================

def resumo_geral(df: pd.DataFrame) -> dict:
    """
    Painel de controle: números totais de alto nível.
    Retorna dict para facilitar interpolação direta no template.
    """
    df = _preparar(df)
    return {
        "total_convenios": int(len(df)),
        "valor_total": float(df["valor_global"].sum()),
        "total_situacoes": int(df["situacao"].nunique()),
        "total_concedentes": int(df["concedente"].nunique()),
    }


def total_por_situacao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quantidade e valor total por situação/status do convênio.
    Ordenado por valor_total decrescente (mais relevante primeiro).
    """
    df = _preparar(df)
    return (
        df.groupby("situacao", as_index=False)
        .agg(quantidade=("nr_convenio", "count"), valor_total=("valor_global", "sum"))
        .sort_values("valor_total", ascending=False)
        .reset_index(drop=True)
    )


def total_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quantidade e valor total por ano de início do convênio.
    Ordenado cronologicamente (série temporal).
    """
    df = _preparar(df)
    return (
        df.dropna(subset=["ano"])
        .groupby("ano", as_index=False)
        .agg(quantidade=("nr_convenio", "count"), valor_total=("valor_global", "sum"))
        .sort_values("ano")
        .reset_index(drop=True)
    )


def total_por_concedente(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quantidade e valor total por órgão concedente federal.
    Ordenado por valor_total decrescente (top concedentes primeiro).
    """
    df = _preparar(df)
    return (
        df.groupby("concedente", as_index=False)
        .agg(quantidade=("nr_convenio", "count"), valor_total=("valor_global", "sum"))
        .sort_values("valor_total", ascending=False)
        .reset_index(drop=True)
    )
