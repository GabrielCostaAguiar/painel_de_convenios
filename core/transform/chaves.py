"""
Ponto central de verdade para filtros e chaves de relacionamento SIGCON↔SICONV.

Responsabilidades:
  - UOS_EXCLUIR: frozenset de UOs administrativas/não-operacionais a ignorar
  - filtrar_uo: aplica o filtro a qualquer DataFrame que tenha a coluna uo
  - montar_siafi_uo: constrói a chave composta SIAFI+UO (sem separador, conforme SIGCON)

Nota sobre UOS_EXCLUIR:
  Lista definida pela equipe DCGCE — equivalente ao `not match(...)` do QlikView.
  Inclui UOs de encargos gerais, transferências intragovernamentais e fundos
  que não representam convênios operacionais do Estado.
  Fonte: QlikView script lines 1627, 1785, 1825 (três pontos de aplicação idênticos).
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Filtro de UOs não-operacionais
# ---------------------------------------------------------------------------

UOS_EXCLUIR: frozenset[str] = frozenset({
    "5131",  # FUNDO ESPECIAL DE CREDITOS INADIMPLIDOS E DIVIDA ATIVA
    "9801",  # RESERVA DE CONTINGENCIA (conta contábil genérica)
    "4611",  # FUNDO DE GARANTIAS DE PARCERIAS PUBLICO-PRIVADAS
    "4441",  # FUNDO DE PREVIDENCIA DO ESTADO DE MINAS GERAIS
    "4451",  # FUNDO FINANCEIRO DE PREVIDENCIA
    "2361",  # AGENCIA REGULADORA DE ABASTECIMENTO DE AGUA E ESGOTO
    "4121",  # FUNDO DE PREVIDENCIA - exclusão por encargo previdenciário
    "1041",  # encargo geral
    "1031",  # encargo geral
    "1051",  # encargo geral
    "4031",  # encargo geral
})


def filtrar_uo(df: pd.DataFrame, coluna_uo: str = "unidade_orcamentaria_codigo") -> pd.DataFrame:
    """
    Remove linhas cujo código de UO pertence a UOS_EXCLUIR.

    O QlikView aplica este filtro com `not match(UO, '5131', ...)`.
    Aqui usamos `~isin(UOS_EXCLUIR)` após normalizar o valor da coluna.
    """
    if coluna_uo not in df.columns:
        raise KeyError(f"Coluna '{coluna_uo}' não encontrada no DataFrame. Colunas disponíveis: {list(df.columns)}")
    mascara = ~df[coluna_uo].astype(str).str.strip().isin(UOS_EXCLUIR)
    return df.loc[mascara].copy()


def montar_siafi_uo(siafi: "pd.Series", uo: "pd.Series") -> "pd.Series":
    """
    Monta a chave composta SIAFI_UO = siafi + uo (concatenação direta, sem separador).

    Exemplo: siafi='9309074', uo='1261' → '93090741261'

    Esta é a chave primária para todos os joins com SIAFI2.csv e sigcon_chaves.
    ATENÇÃO: qualquer espaço nos valores de origem corrompe a chave — use após strip().
    """
    return siafi.astype(str).str.strip() + uo.astype(str).str.strip()
