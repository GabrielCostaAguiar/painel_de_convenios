"""
Carregamento das tabelas de referência versionadas em core/referencia/.

Cada função retorna um dict ou pd.DataFrame pronto para uso nos joins Silver/Gold.
Todos os CSVs usam encoding utf-8 e separador vírgula (padrão pandas).

Catálogo:
  situacoes_padronizadas  → Mapa2 do QlikView: situação original → padronizada
  tipos_siafi             → Map_Tipo_SIAFI: código numérico → descrição instrumento
  uo_nomes                → MapaG_UO: código UO → "código - NOME"
  uo_siglas               → Mapa5: nome UO → sigla
  uo_descricoes           → Mapa4: nome UO → "nome - sigla"
  concedentes_padronizados→ Mapa3 (parcial): nome original → nome padronizado
  correcoes               → tabela de exceções de dados hard-coded
"""

from pathlib import Path

import pandas as pd

_REFERENCIA_DIR = Path(__file__).parent.parent / "referencia"


def _carregar(nome_arquivo: str) -> pd.DataFrame:
    caminho = _REFERENCIA_DIR / nome_arquivo
    return pd.read_csv(caminho, dtype=str, keep_default_na=False)


def situacoes_padronizadas() -> dict[str, str]:
    """Retorna {situacao_original: situacao_padronizada} — equivalente ao Mapa2."""
    df = _carregar("situacoes_padronizadas.csv")
    return dict(zip(df["situacao_original"].str.strip(), df["situacao_padronizada"].str.strip()))


def tipos_siafi() -> dict[str, str]:
    """Retorna {codigo_tipo_siafi: descricao_instrumento} — equivalente ao Map_Tipo_SIAFI."""
    df = _carregar("tipos_siafi.csv")
    return dict(zip(df["codigo_tipo_siafi"].str.strip(), df["descricao_instrumento"].str.strip()))


def uo_nomes() -> dict[str, str]:
    """Retorna {codigo_uo: nome_uo} — equivalente ao MapaG_UO."""
    df = _carregar("uo_nomes.csv")
    return dict(zip(df["codigo_uo"].str.strip(), df["nome_uo"].str.strip()))


def uo_siglas() -> dict[str, str]:
    """Retorna {nome_uo: sigla_uo} — equivalente ao Mapa5."""
    df = _carregar("uo_siglas.csv")
    return dict(zip(df["nome_uo"].str.strip(), df["sigla_uo"].str.strip()))


def uo_descricoes() -> dict[str, str]:
    """Retorna {nome_uo: descricao_uo} — equivalente ao Mapa4."""
    df = _carregar("uo_descricoes.csv")
    return dict(zip(df["nome_uo"].str.strip(), df["descricao_uo"].str.strip()))


def concedentes_padronizados() -> dict[str, str]:
    """
    Retorna {nome_original: nome_padronizado} — equivalente ao Mapa3.

    ATENÇÃO: o CSV está parcialmente preenchido (apenas as primeiras 2 entradas do QlikView).
    Para completar: extraia as ~470 linhas do Mapa3 do script QlikView (linhas 2275-2745)
    e adicione ao arquivo core/referencia/concedentes_padronizados.csv.
    """
    df = _carregar("concedentes_padronizados.csv")
    return dict(zip(df["nome_original"].str.strip(), df["nome_padronizado"].str.strip()))


def correcoes() -> pd.DataFrame:
    """
    Retorna a tabela de exceções/correções de dados hard-coded.
    Colunas: tabela, campo_chave, valor_chave, campo_corrigido,
             valor_errado, valor_correto, motivo, qlikview_linha
    """
    return _carregar("correcoes.csv")
