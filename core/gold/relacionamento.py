"""
Camada Gold — Relacionamento SIGCON ↔ SICONV ↔ SIAFI.

Este módulo implementa o equivalente Python do "miolo" do script QlikView:
  sigcon_chaves1 → G_ fields → A_ fields

Etapas (R1→R4):
  R1  — estrutura e de-paras (este arquivo, apenas esqueleto)
  R2  — montar_sigcon_chaves: base SIGCON + join SIAFI2 → chave SIAFI_UO atual
  R3  — campos G_: coalesce SICONV+SIGCON para os 21 campos padronizados
  R4  — campos A_: projeção dos campos G_ sobre a UO atual (SIAFI_atual)

Regras de negócio centrais (ver docs/AUDITORIA_RELACIONAMENTO.md):
  - Chave de join: SIAFI_UO = str(siafi) + str(uo)  (sem separador)
  - UOs excluídas: ver core/transform/chaves.UOS_EXCLUIR
  - Join SIGCON→SICONV é LEFT JOIN (0 ou 1 registro SICONV por convênio SIGCON)
  - Fan-out: sempre deduplicar a dimensão antes de fazer join para evitar linhas multiplicadas
"""

from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
# R2 — placeholder
# ---------------------------------------------------------------------------

def montar_sigcon_chaves(
    df_chaves: pd.DataFrame,
    df_siafi2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói a tabela-ponte sigcon_chaves com a chave SIAFI_UO atual.

    Recebe:
      df_chaves  — Silver de sigcon/Chaves_convenio.csv (já filtrada por UOS_EXCLUIR)
      df_siafi2  — Silver de SIAFI2.csv

    Devolve DataFrame com colunas mínimas:
      siafi_uo          — chave original (SIAFI2 & UO2, sem separador)
      siafi_uo_atual    — chave atual (SIAFIATUAL & UOATUAL)
      nr_convenio       — código SICONV (pode ser nulo para convênios só-SIGCON)
      instrumento_chaves— tipo do instrumento (Map_Tipo_SIAFI aplicado)

    TODO (R2): implementar.
    """
    raise NotImplementedError("montar_sigcon_chaves será implementado em R2")


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
