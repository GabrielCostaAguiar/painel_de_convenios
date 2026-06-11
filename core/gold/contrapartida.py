"""
Gold complementar: tipo de contrapartida por SIAFI_UO.

Equivale ao campo Conv_Caract_Contrapartida do QlikView.
NÃO altera a camada de relacionamento R1–R4.

Cadeia de joins:
  PlanoTrabalho.plano_trabalho_caracteristica
    + PlanoTrabalho.plano_trabalho_codigo
    → CodigoPlanoTrabalho.conveno_codigo_plano_trabalho
    → (convenio_numero_sequencial_siafi, unidade_orcamentaria_codigo)
    → siafi_uo = siafi + uo  (concatenação direta, sem separador)

Arquitetura:
  _computar()       — pura, recebe DataFrames; testável sem banco.
  tipo_por_siafi_uo() — ORM wrapper que carrega os DFs e delega para _computar().
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tabela-verdade de classificação
#
# Chave (financeira_bin, nao_financeira_bin) cobre os 3 casos com >=1 em fin ou nao_fin.
# Quando ambas são 0, o flag "sem" desempata os 2 casos restantes.
# ---------------------------------------------------------------------------

_TABELA: dict[tuple[int, int], str] = {
    (1, 1): "Contrapartida financeira e não financeira",
    (1, 0): "Contrapartida financeira",
    (0, 1): "Contrapartida não financeira",
}
_SEM: dict[int, str] = {
    1: "Sem contrapartida",
    0: "Sem informação",
}


def _classificar(fin: int, nao_fin: int, sem: int) -> str:
    """
    Classifica via tabela-verdade de 5 saídas.
    Entradas devem ser 0 ou 1 (resultado de max() sobre flags binárias).
    """
    return _TABELA.get((fin, nao_fin)) or _SEM[sem]


# ---------------------------------------------------------------------------
# Derivação de flags por linha de plano de trabalho
# ---------------------------------------------------------------------------

_CARACT_FIN     = "Contrapartida"
_CARACT_NAO_FIN = "Contrapartida não financeira"
_CARACT_SEM     = "Sem contrapartida"


def _derivar_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona colunas binárias fin / nao_fin / sem ao DataFrame.
    Recebe coluna 'plano_trabalho_caracteristica' (string nullable).
    """
    caract = df["plano_trabalho_caracteristica"].fillna("").astype(str)
    df = df.copy()
    df["fin"]     = (caract == _CARACT_FIN).astype(int)
    df["nao_fin"] = (caract == _CARACT_NAO_FIN).astype(int)
    df["sem"]     = (caract == _CARACT_SEM).astype(int)
    return df


# ---------------------------------------------------------------------------
# Função pura: testável sem banco
# ---------------------------------------------------------------------------

def _computar(
    df_plano: pd.DataFrame,
    df_bridge: pd.DataFrame,
    siafi_uos: list[str] | None = None,
) -> dict[str, str]:
    """
    Deriva tipo de contrapartida para cada SIAFI_UO.

    Parâmetros
    ----------
    df_plano  : colunas plano_trabalho_codigo, plano_trabalho_caracteristica
    df_bridge : colunas conveno_codigo_plano_trabalho,
                         convenio_numero_sequencial_siafi,
                         unidade_orcamentaria_codigo
    siafi_uos : lista de chaves a retornar; None = todas

    Retorna
    -------
    dict[siafi_uo → tipo_contrapartida]
    """
    if df_plano.empty or df_bridge.empty:
        return {}

    # Renomeia para o join
    bridge = df_bridge.rename(
        columns={"conveno_codigo_plano_trabalho": "plano_trabalho_codigo"}
    )

    # Join: plano → bridge → siafi_uo
    merged = df_plano.merge(bridge, on="plano_trabalho_codigo", how="inner")

    siafi = merged["convenio_numero_sequencial_siafi"].fillna("").astype(str)
    uo    = merged["unidade_orcamentaria_codigo"].fillna("").astype(str)
    merged = merged.copy()
    merged["siafi_uo"] = siafi + uo

    if siafi_uos is not None:
        merged = merged[merged["siafi_uo"].isin(siafi_uos)]
        if merged.empty:
            return {}

    # Flags binárias por linha
    merged = _derivar_flags(merged)

    # Agrega por siafi_uo: max() de cada flag
    agg = (
        merged.groupby("siafi_uo")[["fin", "nao_fin", "sem"]]
        .max()
        .reset_index()
    )

    n_total = len(agg)
    logger.info("Contrapartida: %d SIAFI_UO classificados", n_total)

    return {
        row["siafi_uo"]: _classificar(
            int(row["fin"]), int(row["nao_fin"]), int(row["sem"])
        )
        for _, row in agg.iterrows()
    }


# ---------------------------------------------------------------------------
# ORM wrapper — chamado pelo service
# ---------------------------------------------------------------------------

def tipo_por_siafi_uo(siafi_uos: list[str] | None = None) -> dict[str, str]:
    """
    Carrega PlanoTrabalho e CodigoPlanoTrabalho via ORM e delega para _computar().

    siafi_uos : lista de chaves SIAFI_UO a resolver; None = todas.
    Retorna {siafi_uo: tipo_contrapartida}.
    """
    from apps.convenios.models import CodigoPlanoTrabalho, PlanoTrabalho

    planos_qs = PlanoTrabalho.objects.values(
        "plano_trabalho_codigo",
        "plano_trabalho_caracteristica",
    )
    bridge_qs = CodigoPlanoTrabalho.objects.values(
        "conveno_codigo_plano_trabalho",
        "convenio_numero_sequencial_siafi",
        "unidade_orcamentaria_codigo",
    )

    if not planos_qs.exists() or not bridge_qs.exists():
        logger.warning(
            "Contrapartida: PlanoTrabalho ou CodigoPlanoTrabalho vazio — "
            "rode carregar_plano_trabalho e carregar_codigo_plano_trabalho."
        )
        return {}

    df_plano  = pd.DataFrame(list(planos_qs))
    df_bridge = pd.DataFrame(list(bridge_qs))

    return _computar(df_plano, df_bridge, siafi_uos)
