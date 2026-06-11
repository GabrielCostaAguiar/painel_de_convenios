"""
Carregamento das tabelas de referência versionadas em core/referencia/.

Cada função retorna um dict ou pd.DataFrame pronto para uso nos joins Silver/Gold.
Todos os CSVs usam encoding utf-8 e separador vírgula (padrão pandas).

Catálogo:
  situacoes_padronizadas       → Mapa2 do QlikView: situação original → padronizada
  tipos_siafi                  → Map_Tipo_SIAFI: código numérico → descrição instrumento
  tipos_receita                → Mapareceita: código tipo receita → descrição (13→Rendimento…)
  tipos_instrumento_entrada    → Mapa1: código tipo contrato/convênio entrada → descrição
  uo_nomes                     → MapaG_UO: código UO → "código - NOME"
  uo_siglas                    → Mapa5: nome UO → sigla
  uo_descricoes                → Mapa4: nome UO → "nome - sigla"
  concedentes_padronizados     → Mapa3 (parcial): nome original → nome padronizado
  correcoes                    → tabela de exceções de dados hard-coded

Utilitário:
  aplicar_depara(series, mapa, manter_original) → aplica um dict de de-para a uma Series pandas.
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


def tipos_receita() -> dict[str, str]:
    """
    Retorna {codigo_tipo_receita: descricao_receita} — equivalente ao Mapareceita do QlikView.

    Domínio: coluna de tipo de receita (13→Rendimento, 17→Receita Corrente,
    19→Restituição, 24→Receita de Capital).
    Atenção: a base de receita ainda não foi ingerida; esta função existe para quando ela chegar.
    """
    df = _carregar("tipos_receita.csv")
    return dict(zip(df["codigo_tipo_receita"].str.strip(), df["descricao_receita"].str.strip()))


def tipos_instrumento_entrada() -> dict[str, str]:
    """
    Retorna {codigo_tipo_instrumento_entrada: descricao_instrumento_entrada} — equivalente ao Mapa1.

    Domínio: coluna "tipo contrato/convênio entrada" usada em receita/despesa
    (4→Contrato, 5→Convênio, 8→Portaria, 11→Acordo/Ajuste).
    NÃO confundir com tipos_siafi: ambos têm código 11, mas mapeiam domínios distintos.
    """
    df = _carregar("tipos_instrumento_entrada.csv")
    return dict(zip(
        df["codigo_tipo_instrumento_entrada"].str.strip(),
        df["descricao_instrumento_entrada"].str.strip(),
    ))


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


def aplicar_depara(
    series: "pd.Series",
    mapa: dict[str, str],
    manter_original: bool = True,
) -> "pd.Series":
    """
    Aplica um de-para (dict {codigo: rotulo}) a uma coluna de um DataFrame.

    Parâmetros
    ----------
    series          : coluna pandas com os códigos de origem (dtype str/object).
    mapa            : dict retornado por tipos_receita(), tipos_instrumento_entrada(), etc.
    manter_original : se True (padrão), códigos sem mapeamento ficam com o valor original;
                      se False, viram NaN.

    Exemplo
    -------
    df["tipo_receita_desc"] = aplicar_depara(df["tipo_receita_cod"], tipos_receita())

    Nota: a base de receita ainda não foi ingerida. Esta função está pronta para quando
    dcgce_receita (ou fonte equivalente) for carregada via rodar_silver.
    """
    resultado = series.map(mapa)
    if manter_original:
        resultado = resultado.where(resultado.notna(), series)
    return resultado


def correcoes() -> pd.DataFrame:
    """
    Retorna a tabela de exceções/correções de dados hard-coded.
    Colunas: tabela, campo_chave, valor_chave, campo_corrigido,
             valor_errado, valor_correto, motivo, qlikview_linha
    """
    return _carregar("correcoes.csv")
