"""
Camada Gold — Relacionamento SIGCON ↔ SICONV ↔ SIAFI.

Este módulo implementa o equivalente Python do "miolo" do script QlikView:
  sigcon_chaves1 → G_ fields → A_ fields

Roadmap:
  R2 ✅ montar_sigcon_chaves: base SIGCON + join SIAFI2 → chaves resolvidas + de-paras
  R3    aplicar_campos_g: coalesce SICONV+SIGCON nos 21 campos padronizados
  R4    aplicar_campos_a: projeção G_ sobre SIAFI_atual

Regras de negócio centrais (ver docs/AUDITORIA_RELACIONAMENTO.md):
  - Chave: SIAFI_UO = str(siafi) + str(uo), sem separador, nunca int
  - UOs excluídas: UOS_EXCLUIR (11 UOs não-operacionais)
  - Join SIGCON→SICONV: LEFT JOIN (0 ou 1 SICONV por convênio SIGCON)
  - Fan-out: dimensão SIAFI2 é deduplicada antes do merge
"""

from __future__ import annotations

import logging

import pandas as pd

from core.transform.chaves import (
    filtrar_uo,
    montar_siafi_uo,
    resolver_siafi_atual,
    aplicar_deparas,
    aplicar_correcoes,
)

# ---------------------------------------------------------------------------
# R2 — preparação do sigcon_convenio (dcgce_convenio) antes do join
# ---------------------------------------------------------------------------

def preparar_sigcon_convenio(df_convenio: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica filtro de UO, de-paras e correções data-driven ao Silver de
    dcgce_convenio, preparando-o para o join em R3.

    Passos:
      1. Filtra UOs não-operacionais (UOS_EXCLUIR)
      2. Aplica correções de dados da tabela core/referencia/correcoes.csv
         (substitui as correções hard-coded do QlikView, linhas 1601-1616)
      3. Aplica de-paras: situacao_std, uo_nome_std, uo_sigla_std, uo_descricao_std
      4. Monta siafi_uo para servir como chave de join em R3

    Parameters
    ----------
    df_convenio : Silver de dcgce_convenio (já com tipos convertidos)

    Returns
    -------
    DataFrame pronto para join, com colunas originais preservadas + _std e siafi_uo.
    """
    df = filtrar_uo(df_convenio, coluna_uo="unidade_orcamentaria_codigo")
    df = aplicar_correcoes(df, nome_tabela="sigcon_convenio")
    df = aplicar_deparas(df)
    df["siafi_uo"] = montar_siafi_uo(
        df["convenio_numero_sequencial_siafi"],
        df["unidade_orcamentaria_codigo"],
    )
    return df

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# R2 — tabela-ponte com chaves resolvidas
# ---------------------------------------------------------------------------

def montar_sigcon_chaves(
    df_chaves: pd.DataFrame,
    df_siafi2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói a tabela-ponte sigcon_chaves com chaves SIAFI_UO resolvidas
    e de-paras aplicados.

    Equivalente ao bloco QlikView:
      sigcon_chaves1 (FROM Chaves_convenio.csv)
      LEFT JOIN SIAFI2 (FROM SIAFI2.csv, chave = SIAFI2 & UO2)

    Passos:
      1. Filtra UOs não-operacionais (UOS_EXCLUIR)
      2. Monta siafi_uo = siafi + uo (concatenação direta, sem separador)
      3. Aplica de-para Map_Tipo_SIAFI → instrumento_chaves
      4. Aplica de-para MapaG_UO → uo_nome_std, uo_sigla_std, uo_descricao_std
      5. Resolve siafi_uo_atual via LEFT JOIN com SIAFI2
         — se não há match, siafi_uo_atual = siafi_uo (fallback)
      6. Deduplica: a tabela-ponte não deve ter linhas duplicadas
         por (siafi_uo); se houver, log de aviso

    Parameters
    ----------
    df_chaves : Silver de chaves_convenio
                Colunas esperadas: convenio_numero_sequencial_siafi,
                unidade_orcamentaria_codigo, codigo_siconv,
                plano_trabalho_tipo_siafi, situacao, siconv
    df_siafi2 : Silver de siafi2
                Colunas esperadas: siafi1, uo1, siafi2, uo2, siafiatual, uoatual

    Returns
    -------
    DataFrame com colunas:
      siafi_uo             — chave original (siafi + uo, sem separador)
      siafi_uo_atual       — chave atual (siafiatual + uoatual); fallback = siafi_uo
      convenio_numero_sequencial_siafi
      unidade_orcamentaria_codigo
      siafiatual           — número SIAFI atual (nulo se sem substituição)
      uo_atual             — código UO atual (nulo se sem substituição)
      codigo_siconv        — NR_CONVENIO para join com SICONV
      instrumento_chaves   — tipo do instrumento (Map_Tipo_SIAFI aplicado)
      situacao             — situação original
      situacao_std         — situação padronizada (Mapa2)
      uo_nome_std          — nome padronizado da UO (MapaG_UO)
      uo_sigla_std         — sigla da UO (Mapa5)
      uo_descricao_std     — descrição da UO (Mapa4)
    """
    # --- 1. Filtro de UOs ---
    df = filtrar_uo(df_chaves, coluna_uo="unidade_orcamentaria_codigo")

    # --- 2. Chave SIAFI_UO ---
    df["siafi_uo"] = montar_siafi_uo(
        df["convenio_numero_sequencial_siafi"],
        df["unidade_orcamentaria_codigo"],
    )
    n_sem_chave = int(df["siafi_uo"].isna().sum())
    if n_sem_chave:
        logger.warning(
            "montar_sigcon_chaves: %d linhas com SIAFI_UO nulo "
            "(siafi ou uo ausente) — serão mantidas mas não vão fazer join",
            n_sem_chave,
        )

    # --- 3 & 4. De-paras ---
    df = aplicar_deparas(df)

    # --- 5. Resolve SIAFI_UO atual ---
    df = resolver_siafi_atual(df, df_siafi2, coluna_siafi_uo="siafi_uo")

    # --- 6. Deduplicação da tabela-ponte ---
    # Cada (siafi_uo) deve aparecer no máximo uma vez. Duplicatas indicam
    # que Chaves_convenio tem o mesmo par SIAFI+UO com NR_CONVENIO diferente
    # (não deve acontecer, mas protegemos aqui).
    n_antes = len(df)
    df = df.drop_duplicates(subset=["siafi_uo"], keep="first")
    n_depois = len(df)
    if n_depois < n_antes:
        logger.warning(
            "montar_sigcon_chaves: %d linhas duplicadas em siafi_uo removidas "
            "(Chaves_convenio tem mais de um NR_CONVENIO para o mesmo par SIAFI+UO)",
            n_antes - n_depois,
        )

    colunas_saida = [
        "siafi_uo",
        "siafi_uo_atual",
        "convenio_numero_sequencial_siafi",
        "unidade_orcamentaria_codigo",
        "siafiatual",
        "uo_atual",
        "codigo_siconv",
        "instrumento_chaves",
        "situacao",
        "situacao_std",
        "uo_nome_std",
        "uo_sigla_std",
        "uo_descricao_std",
    ]
    # Mantém só as colunas de saída que existem
    colunas_saida = [c for c in colunas_saida if c in df.columns]
    df = df[colunas_saida].reset_index(drop=True)

    logger.info(
        "montar_sigcon_chaves: %d linhas, %d colunas", len(df), len(df.columns)
    )
    return df


# ---------------------------------------------------------------------------
# R3 — placeholder
# ---------------------------------------------------------------------------

def aplicar_campos_g(
    df_sigcon: pd.DataFrame,
    df_siconv: pd.DataFrame,
    df_sigcon_chaves: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói os 21 campos G_ pelo padrão coalesce: SICONV se presente, senão SIGCON.

    TODO (R3): implementar.
    """
    raise NotImplementedError("aplicar_campos_g será implementado em R3")


# ---------------------------------------------------------------------------
# R4 — placeholder
# ---------------------------------------------------------------------------

def aplicar_campos_a(df_com_g: pd.DataFrame) -> pd.DataFrame:
    """
    Projeta os campos G_ sobre a UO atual (SIAFI_atual) para os campos A_.

    TODO (R4): implementar.
    """
    raise NotImplementedError("aplicar_campos_a será implementado em R4")
