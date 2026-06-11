"""
Camada Gold — Relacionamento SIGCON ↔ SICONV ↔ SIAFI.

Este módulo implementa o equivalente Python do "miolo" do script QlikView:
  sigcon_chaves1 → G_ fields → A_ fields

Roadmap:
  R2 ✅ montar_sigcon_chaves / preparar_sigcon_convenio
  R3 ✅ aplicar_campos_g / aplicar_campos_a / construir_tabela_integrada
  R4    Conectar ao Django (model + loader idempotente)

Regras de negócio centrais (ver docs/AUDITORIA_RELACIONAMENTO.md):
  - Chave: SIAFI_UO = str(siafi) + str(uo), sem separador, nunca int
  - UOs excluídas: UOS_EXCLUIR (11 UOs não-operacionais)
  - Join SIGCON→SICONV: LEFT JOIN (0 ou 1 SICONV por convênio SIGCON)
  - Fan-out: cada camada de join é validada após a operação

Sobre os campos G_ e A_:
  G_ = coalesce(SICONV, SIGCON)  — melhor informação disponível
  A_ = G_ projetado sobre o SIAFI mais atual (siafi_uo_atual)
       Útil quando um convênio muda de número SIAFI: A_ sempre mostra
       o estado "hoje" da UO que carrega o convênio.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from core.transform.chaves import (
    aplicar_correcoes,
    aplicar_deparas,
    filtrar_uo,
    montar_siafi_uo,
    resolver_siafi_atual,
)
from core.transform.referencias import (
    concedentes_padronizados,
    situacoes_padronizadas,
    uo_descricoes,
    uo_nomes,
    uo_siglas,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------

def _limpar_id(s: pd.Series) -> pd.Series:
    """Remove artefato '.0' de identificadores lidos como float."""
    s = s.astype("string").str.strip()
    mask = s.notna() & s.str.endswith(".0") & s.str[:-2].str.isdigit()
    return s.where(~mask, s.str[:-2])


def _coalesce(
    siconv: pd.Series | None,
    sigcon: pd.Series,
    nome: str = "",
) -> pd.Series:
    """
    Coalesce: retorna siconv se não-nulo/não-vazio, senão sigcon.

    Em pandas: fillna não funciona para StringDtype com strings vazias.
    Então aqui tratamos tanto NA quanto string vazia como "ausente".
    """
    sg = pd.Series(sigcon, dtype="string")

    if siconv is None:
        # Coluna SICONV ausente no DataFrame — usa SIGCON diretamente
        return sg

    sv = pd.Series(siconv, dtype="string")

    # String vazia também é "ausente" — equivalente ao QlikView len(trim(x))=0
    sv_ausente = sv.isna() | (sv.str.strip() == "")
    resultado = sv.where(~sv_ausente, sg)

    if nome:
        n_siconv = int((~sv_ausente).sum())
        n_fallback = int((sv_ausente & sg.notna()).sum())
        logger.debug("G_%-30s  SICONV=%d  SIGCON=%d", nome, n_siconv, n_fallback)

    return resultado.astype("string")


def _coalesce_num(
    siconv: pd.Series | None,
    sigcon: pd.Series | None,
) -> pd.Series:
    """Coalesce para colunas numéricas (float)."""
    if siconv is None:
        return sigcon
    if sigcon is None:
        return siconv
    return siconv.fillna(sigcon)


def _validar_fan_out(df_antes: int, df_depois: int, etapa: str) -> None:
    """Alerta se um join multiplicou linhas (fan-out)."""
    if df_depois > df_antes:
        logger.warning(
            "FAN-OUT em '%s': %d → %d linhas (+%d). "
            "A dimensão do join não estava desduplicada?",
            etapa, df_antes, df_depois, df_depois - df_antes,
        )
    else:
        logger.info("fan-out OK '%s': %d linhas (sem aumento)", etapa, df_depois)


def _col(df: pd.DataFrame, nome: str) -> pd.Series | None:
    """Retorna a coluna se existir; None caso contrário (graceful degradation)."""
    return df[nome] if nome in df.columns else None


# ---------------------------------------------------------------------------
# R2 — preparação do sigcon_convenio antes do join
# ---------------------------------------------------------------------------

def preparar_sigcon_convenio(df_convenio: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica filtro de UO, de-paras e correções ao Silver de dcgce_convenio.

    Produz colunas adicionais: situacao_std, uo_nome_std, uo_sigla_std,
    uo_descricao_std, siafi_uo.
    """
    df = filtrar_uo(df_convenio, coluna_uo="unidade_orcamentaria_codigo")
    df = aplicar_correcoes(df, nome_tabela="sigcon_convenio")
    df = aplicar_deparas(df)
    df["siafi_uo"] = montar_siafi_uo(
        df["convenio_numero_sequencial_siafi"],
        df["unidade_orcamentaria_codigo"],
    )
    return df


# ---------------------------------------------------------------------------
# R2 — tabela-ponte com chaves resolvidas
# ---------------------------------------------------------------------------

def montar_sigcon_chaves(
    df_chaves: pd.DataFrame,
    df_siafi2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói a tabela-ponte sigcon_chaves com chaves SIAFI_UO resolvidas.

    Equivalente ao bloco QlikView:
      sigcon_chaves1 (FROM Chaves_convenio.csv) + LEFT JOIN SIAFI2

    Passos:
      1. Filtra UOs não-operacionais
      2. Monta siafi_uo = siafi + uo
      3. Aplica de-paras (instrumento, uo_nome_std, situacao_std, etc.)
      4. Resolve siafi_uo_atual via LEFT JOIN com SIAFI2 (fallback = original)
      5. Deduplica por siafi_uo

    Saída: siafi_uo, siafi_uo_atual, siafiatual, uo_atual, codigo_siconv,
           instrumento_chaves, situacao, situacao_std, uo_nome_std, etc.
    """
    df = filtrar_uo(df_chaves, coluna_uo="unidade_orcamentaria_codigo")

    df["siafi_uo"] = montar_siafi_uo(
        df["convenio_numero_sequencial_siafi"],
        df["unidade_orcamentaria_codigo"],
    )
    n_sem_chave = int(df["siafi_uo"].isna().sum())
    if n_sem_chave:
        logger.warning(
            "montar_sigcon_chaves: %d linhas com SIAFI_UO nulo", n_sem_chave
        )

    df = aplicar_deparas(df)
    df = resolver_siafi_atual(df, df_siafi2, coluna_siafi_uo="siafi_uo")

    n_antes = len(df)
    df = df.drop_duplicates(subset=["siafi_uo"], keep="first")
    if len(df) < n_antes:
        logger.warning(
            "montar_sigcon_chaves: %d duplicatas em siafi_uo removidas",
            n_antes - len(df),
        )

    colunas_saida = [
        "siafi_uo", "siafi_uo_atual",
        "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
        "siafiatual", "uo_atual",
        "codigo_siconv", "instrumento_chaves",
        "situacao", "situacao_std",
        "uo_nome_std", "uo_sigla_std", "uo_descricao_std",
    ]
    colunas_saida = [c for c in colunas_saida if c in df.columns]
    df = df[colunas_saida].reset_index(drop=True)

    logger.info("montar_sigcon_chaves: %d linhas, %d colunas", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# R3 — preparação das fontes SIGCON e SICONV
# ---------------------------------------------------------------------------

def _preparar_sigcon_completo(
    df_convenio: pd.DataFrame,
    df_codigo_convenio: pd.DataFrame,
    df_geral: pd.DataFrame,
    df_plano: pd.DataFrame,
    df_esfera: pd.DataFrame,
) -> pd.DataFrame:
    """
    Junta as 5 fontes SIGCON em um único DataFrame por siafi_uo.

    Reproduz a cadeia de joins de carregar_convenios() em loader.py, mas
    retorna o DataFrame em vez de instâncias ORM.

    Colunas de saída (prefixadas com sigcon_ para evitar colisão em joins):
      siafi_uo (chave), sigcon_situacao, sigcon_data_inicio_vigencia,
      sigcon_data_termino_vigencia, sigcon_data_real_convenio,
      sigcon_data_assinatura, sigcon_valor_concedente, sigcon_valor_proponente,
      sigcon_valor_global, sigcon_valor_global_inicial,
      sigcon_concedente, sigcon_objeto, sigcon_cnpj_concedente, sigcon_esfera.
    """
    # Normaliza chaves de join
    for df, cols in [
        (df_convenio, ["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"]),
        (df_codigo_convenio, ["convenio_codigo_sequencial", "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"]),
        (df_geral, ["convenio_numero_sequencial_siafi", "convenio_codigo_sequencial", "conveno_codigo_plano_trabalho"]),
        (df_plano, ["plano_trabalho_codigo", "plano_trabalho_cnpj_concedente"]),
        (df_esfera, ["concedente_cnpj"]),
    ]:
        for col in cols:
            if col in df.columns:
                df[col] = _limpar_id(df[col])

    # Aplica filtro, correções e de-paras ao convenio antes de qualquer join
    convenio = preparar_sigcon_convenio(df_convenio)
    convenio["siafi_uo"] = montar_siafi_uo(
        convenio["convenio_numero_sequencial_siafi"],
        convenio["unidade_orcamentaria_codigo"],
    )

    # Enriquece geral com UO via codigo_convenio
    cod_uo = (
        df_codigo_convenio[["convenio_codigo_sequencial", "unidade_orcamentaria_codigo"]]
        .drop_duplicates("convenio_codigo_sequencial")
    )
    geral = df_geral.merge(cod_uo, on="convenio_codigo_sequencial", how="left")
    geral = geral.rename(columns={"conveno_codigo_plano_trabalho": "plano_trabalho_codigo"})
    if "unidade_orcamentaria_codigo" in geral.columns:
        geral["unidade_orcamentaria_codigo"] = _limpar_id(geral["unidade_orcamentaria_codigo"])

    geral_sub = (
        geral[[
            "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
            "plano_trabalho_codigo", "convenio_data_assinatura_convenio",
        ]]
        .drop_duplicates(["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"])
    )

    merged = convenio.merge(
        geral_sub,
        on=["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"],
        how="left",
    )
    _validar_fan_out(len(convenio), len(merged), "sigcon+geral")

    # Plano trabalho (concedente, objeto, cnpj, instrumento)
    plano_sub = (
        df_plano[[
            "plano_trabalho_codigo", "plano_trabalho_objeto",
            "plano_trabalho_razao_social_concedente", "plano_trabalho_cnpj_concedente",
        ]]
        .drop_duplicates("plano_trabalho_codigo")
    )
    merged = merged.merge(plano_sub, on="plano_trabalho_codigo", how="left")
    _validar_fan_out(len(convenio), len(merged), "sigcon+plano")

    # Esfera via CNPJ concedente
    esfera_sub = (
        df_esfera[["concedente_cnpj", "concedente_esfera"]]
        .drop_duplicates("concedente_cnpj")
    )
    merged = merged.merge(
        esfera_sub,
        left_on="plano_trabalho_cnpj_concedente",
        right_on="concedente_cnpj",
        how="left",
    )

    # Projeta somente as colunas necessárias para G_, com prefixo sigcon_
    colunas = {
        "siafi_uo": "siafi_uo",
        "situacao": "sigcon_situacao",
        "data_inicio_vigencia": "sigcon_data_inicio_vigencia",
        "data_termino_vigencia": "sigcon_data_termino_vigencia",
        "data_real_convenio": "sigcon_data_real_convenio",
        "convenio_data_assinatura_convenio": "sigcon_data_assinatura",
        "valor_concedente": "sigcon_valor_concedente",
        "valor_proponente": "sigcon_valor_proponente",
        "valor_total_convenio": "sigcon_valor_global",
        "valor_inicial_concedente_contratado": "sigcon_valor_global_inicial",
        "plano_trabalho_razao_social_concedente": "sigcon_concedente",
        "plano_trabalho_objeto": "sigcon_objeto",
        "plano_trabalho_cnpj_concedente": "sigcon_cnpj_concedente",
        "concedente_esfera": "sigcon_esfera",
    }
    presentes = {k: v for k, v in colunas.items() if k in merged.columns}
    resultado = merged[list(presentes.keys())].rename(columns=presentes)

    resultado = resultado.drop_duplicates("siafi_uo")
    return resultado


def _preparar_siconv(df_siconv: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza o Silver de siconv_convenio, prefixando colunas com siconv_.

    O arquivo Transferegov pode usar nomes ligeiramente diferentes entre versões.
    Esta função trata os nomes pós-normalização (snake_case do Silver) e mapeia
    para os nomes canônicos usados no coalesce.

    Colunas de saída: nr_convenio (chave), id_proposta,
      siconv_situacao, siconv_data_inicio_vigencia, siconv_data_fim_vigencia,
      siconv_data_fim_vigencia_inicial, siconv_data_assinatura,
      siconv_valor_concedente, siconv_valor_proponente, siconv_valor_global,
      siconv_proponente, siconv_concedente, siconv_objeto.
    """
    # Mapeamento de nomes Transferegov → canônicos (post-Silver normalization)
    mapa = {
        # datas
        "dia_assin_conv": "siconv_data_assinatura",
        "dia_inic_vigenc_conv": "siconv_data_inicio_vigencia",
        "dia_fim_vigenc_conv": "siconv_data_fim_vigencia",
        "dia_fim_vigenc_original_conv": "siconv_data_fim_vigencia_inicial",
        # situação
        "sit_convenio": "siconv_situacao",
        # valores
        "vl_repasse_conv": "siconv_valor_concedente",
        "vl_contrapartida_conv": "siconv_valor_proponente",
        "vl_global_conv": "siconv_valor_global",
        # nomes (podem vir do mesmo CSV ou de siconv_proposta se disponível)
        "nm_proponente": "siconv_proponente",
        "desc_orgao_sup": "siconv_concedente",
        "objeto_proposta": "siconv_objeto",
    }

    df = df_siconv.copy()
    df = df.rename(columns={k: v for k, v in mapa.items() if k in df.columns})

    # Chave: nr_convenio deve ser StringDtype sem artefatos .0
    if "nr_convenio" in df.columns:
        df["nr_convenio"] = _limpar_id(df["nr_convenio"])

    colunas_saida = ["nr_convenio", "id_proposta"] + [
        v for v in mapa.values() if v in df.columns
    ]
    colunas_saida = [c for c in colunas_saida if c in df.columns]

    df = df[colunas_saida].drop_duplicates("nr_convenio")
    return df


# ---------------------------------------------------------------------------
# R3 — campos G_ (coalesce SICONV → SIGCON)
# ---------------------------------------------------------------------------

def aplicar_campos_g(
    df_sigcon_chaves: pd.DataFrame,
    df_sigcon_completo: pd.DataFrame,
    df_siconv: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Constrói os campos G_ pelo padrão coalesce: SICONV se presente, senão SIGCON.

    Equivalente ao bloco 'sigcon_chaves3' do QlikView (linhas 3030-3082).

    Parâmetros
    ----------
    df_sigcon_chaves  : saída de montar_sigcon_chaves() — base da tabela
    df_sigcon_completo: saída de _preparar_sigcon_completo() — SIGCON completo
    df_siconv         : saída de _preparar_siconv() ou None (convênios só-SIGCON)

    Retorna
    -------
    DataFrame enriquecido com colunas G_ e derivadas.
    Fan-out é validado após cada join.

    Campos G_ implementados:
      g_dia_assinatura, g_ano_assinatura
      g_inicio_vigencia, g_ano_inicio_vigencia
      g_fim_vigencia, g_fim_vigencia_inicial
      g_situacao_convenio, g_objeto_convenio
      g_proponente, g_concedente
      g_valor_concedente, g_valor_proponente, g_valor_global
      g_instrumento, g_esfera, g_uo

    Derivados:
      g_vigencia, g_vigencia_siconv, g_vigencia_sigcon
      g_periodo_nao_aditado_sigcon, g_periodo_nao_aditado
      g_valor_nao_aditado_siconv, g_valor_nao_aditado_sigcon, g_valor_nao_aditado
      g_ano_convenio, g_situacao_convenio_categorizado
      g_concedente_pad, g_proponente_pad, g_proponente_pad_siglas
      g_uo_descricao, limpeza_g
    """
    n_base = len(df_sigcon_chaves)

    # --- Join 1: SIGCON completo por siafi_uo ---
    df = df_sigcon_chaves.merge(df_sigcon_completo, on="siafi_uo", how="left")
    _validar_fan_out(n_base, len(df), "G_/sigcon_completo")

    # --- Join 2: SICONV por codigo_siconv = nr_convenio ---
    if df_siconv is not None and "nr_convenio" in df_siconv.columns:
        df = df.merge(
            df_siconv,
            left_on="codigo_siconv",
            right_on="nr_convenio",
            how="left",
        )
        _validar_fan_out(n_base, len(df), "G_/siconv")

    # --- Coalesce: G_ fields ---
    hoje = pd.Timestamp(date.today())

    # datas (coalesce → texto para depois converter)
    df["g_dia_assinatura"] = _coalesce(
        _col(df, "siconv_data_assinatura"),
        _col(df, "sigcon_data_assinatura"),
        "dia_assinatura",
    )
    df["g_inicio_vigencia"] = _coalesce(
        _col(df, "siconv_data_inicio_vigencia"),
        _col(df, "sigcon_data_inicio_vigencia"),
        "inicio_vigencia",
    )
    df["g_fim_vigencia"] = _coalesce(
        _col(df, "siconv_data_fim_vigencia"),
        _col(df, "sigcon_data_real_convenio"),
        "fim_vigencia",
    )
    df["g_fim_vigencia_inicial"] = _coalesce(
        _col(df, "siconv_data_fim_vigencia_inicial"),
        _col(df, "sigcon_data_termino_vigencia"),
        "fim_vigencia_inicial",
    )

    # Converte para datetime para cálculos derivados (mantém original em texto)
    g_assin_dt = pd.to_datetime(df["g_dia_assinatura"], errors="coerce")
    g_ini_dt = pd.to_datetime(df["g_inicio_vigencia"], errors="coerce")
    g_fim_dt = pd.to_datetime(df["g_fim_vigencia"], errors="coerce")
    g_fim_ini_dt = pd.to_datetime(df["g_fim_vigencia_inicial"], errors="coerce")

    # anos derivados
    df["g_ano_assinatura"] = g_assin_dt.dt.year.astype("Int64")
    df["g_ano_inicio_vigencia"] = g_ini_dt.dt.year.astype("Int64")

    # situação
    df["g_situacao_convenio"] = _coalesce(
        _col(df, "siconv_situacao"),
        _col(df, "sigcon_situacao"),
        "situacao",
    )

    # objeto
    df["g_objeto_convenio"] = _coalesce(
        _col(df, "siconv_objeto"),
        _col(df, "sigcon_objeto"),
        "objeto",
    )

    # proponente: SICONV tem nm_proponente; fallback é uo_nome_std da bridge
    sigcon_proponente = _col(df, "uo_nome_std")
    df["g_proponente"] = _coalesce(
        _col(df, "siconv_proponente"),
        sigcon_proponente,
        "proponente",
    )

    # concedente
    df["g_concedente"] = _coalesce(
        _col(df, "siconv_concedente"),
        _col(df, "sigcon_concedente"),
        "concedente",
    )

    # valores (numéricos)
    df["g_valor_concedente"] = _coalesce_num(
        _col(df, "siconv_valor_concedente"),
        _col(df, "sigcon_valor_concedente"),
    )
    df["g_valor_proponente"] = _coalesce_num(
        _col(df, "siconv_valor_proponente"),
        _col(df, "sigcon_valor_proponente"),
    )
    df["g_valor_global"] = _coalesce_num(
        _col(df, "siconv_valor_global"),
        _col(df, "sigcon_valor_global"),
    )

    # instrumento: fallback padrão 'Convênio de Entrada'
    instr = _col(df, "instrumento_chaves")
    if instr is not None:
        instr_vazio = instr.isna() | (instr.str.strip() == "")
        df["g_instrumento"] = instr.where(~instr_vazio, "Convênio de Entrada").astype("string")
    else:
        df["g_instrumento"] = pd.array(["Convênio de Entrada"] * len(df), dtype="string")

    # esfera: fallback padrão 'Federal'
    esf = _col(df, "sigcon_esfera")
    if esf is not None:
        esf_vazio = esf.isna() | (esf.str.strip() == "")
        df["g_esfera"] = esf.where(~esf_vazio, "Federal").astype("string")
    else:
        df["g_esfera"] = pd.array(["Federal"] * len(df), dtype="string")

    # UO: SICONV uo_siconv → fallback unidade_orcamentaria_codigo da bridge
    df["g_uo"] = _coalesce(
        _col(df, "siconv_uo"),  # pode não existir
        _col(df, "unidade_orcamentaria_codigo"),
        "uo",
    )

    # --- Derivados de datas ---
    fim_sig = _col(df, "sigcon_data_real_convenio")
    fim_ini_sig = _col(df, "sigcon_data_termino_vigencia")

    # Período não-aditado SIGCON: fim_vigencia == fim_vigencia_inicial (no SIGCON)
    if fim_sig is not None and fim_ini_sig is not None:
        fim_sig_dt = pd.to_datetime(fim_sig, errors="coerce")
        fim_ini_sig_dt = pd.to_datetime(fim_ini_sig, errors="coerce")
        df["g_periodo_nao_aditado_sigcon"] = (
            (fim_sig_dt == fim_ini_sig_dt).where(fim_sig_dt.notna(), False).astype(int)
        )
    else:
        df["g_periodo_nao_aditado_sigcon"] = 0

    # Período não-aditado (G_): g_fim_vigencia == g_fim_vigencia_inicial
    df["g_periodo_nao_aditado"] = (
        (g_fim_dt == g_fim_ini_dt).where(g_fim_dt.notna() & g_fim_ini_dt.notna(), False).astype(int)
    )

    # Vigência G_
    df["g_vigencia"] = pd.array(
        ["Vigente" if (pd.notna(v) and v >= hoje) else "Vencido" for v in g_fim_dt],
        dtype="string",
    )
    if "siconv_data_fim_vigencia" in df.columns:
        fim_scnv_dt = pd.to_datetime(df["siconv_data_fim_vigencia"], errors="coerce")
        df["g_vigencia_siconv"] = pd.array(
            ["Vigente" if (pd.notna(v) and v >= hoje) else "Vencido" for v in fim_scnv_dt],
            dtype="string",
        )
    if "sigcon_data_real_convenio" in df.columns:
        fim_sgcn_dt = pd.to_datetime(df["sigcon_data_real_convenio"], errors="coerce")
        df["g_vigencia_sigcon"] = pd.array(
            ["Vigente" if (pd.notna(v) and v >= hoje) else "Vencido" for v in fim_sgcn_dt],
            dtype="string",
        )

    # --- Derivados de valores ---
    val_global_adit_scnv = _col(df, "siconv_valor_global_aditado")  # pode não existir
    val_global_ini_sgcn = _col(df, "sigcon_valor_global_inicial")
    val_global_sgcn = _col(df, "sigcon_valor_global")

    if val_global_adit_scnv is not None:
        df["g_valor_nao_aditado_siconv"] = (
            val_global_adit_scnv.isna() | (val_global_adit_scnv == 0)
        ).astype(int)
    else:
        df["g_valor_nao_aditado_siconv"] = 1  # sem info SICONV → considera não-aditado

    if val_global_ini_sgcn is not None and val_global_sgcn is not None:
        df["g_valor_nao_aditado_sigcon"] = (
            (val_global_ini_sgcn == val_global_sgcn) | val_global_sgcn.isna()
        ).astype(int)
    else:
        df["g_valor_nao_aditado_sigcon"] = 1

    df["g_valor_nao_aditado"] = (
        (df["g_valor_nao_aditado_siconv"] == 1) & (df["g_valor_nao_aditado_sigcon"] == 1)
    ).astype(int)

    # --- Derivados de classificação ---
    df["g_ano_convenio"] = df["g_ano_assinatura"].fillna(df["g_ano_inicio_vigencia"])

    # g_situacao_convenio_categorizado: Mapa2 já aplicado em situacao_std
    # Re-aplicamos sobre g_situacao_convenio (que é o coalesce real)
    mapa2 = situacoes_padronizadas()
    df["g_situacao_convenio_categorizado"] = (
        df["g_situacao_convenio"].map(mapa2)
        .fillna(df["g_situacao_convenio"])
        .astype("string")
    )

    # g_concedente_pad: Mapa3 sobre g_concedente
    mapa3 = concedentes_padronizados()
    df["g_concedente_pad"] = (
        df["g_concedente"].map(mapa3)
        .fillna(df["g_concedente"])
        .astype("string")
    )

    # g_proponente_pad: Mapa4 (uo_descricoes)
    mapa4 = uo_descricoes()
    df["g_proponente_pad"] = (
        df["g_proponente"].map(mapa4)
        .fillna(df["g_proponente"])
        .astype("string")
    )

    # g_proponente_pad_siglas: Mapa5 (uo_siglas)
    mapa5 = uo_siglas()
    df["g_proponente_pad_siglas"] = (
        df["g_proponente"].map(mapa5)
        .fillna(pd.NA)
        .astype("string")
    )

    # g_uo_descricao: MapaG_UO
    mapa_uo = uo_nomes()
    df["g_uo_descricao"] = (
        df["g_uo"].map(mapa_uo)
        .fillna(df["g_uo"])
        .astype("string")
    )

    # limpeza_g: 1 se TODOS os campos temporais G_ são nulos (linha sem dados)
    # Equivalente ao filtro where limpeza_g=0 no QlikView final
    df["limpeza_g"] = (
        g_ini_dt.isna() & g_fim_dt.isna() & g_assin_dt.isna()
    ).astype(int)

    n_limpeza = int((df["limpeza_g"] == 1).sum())
    if n_limpeza:
        logger.info(
            "aplicar_campos_g: %d linhas com limpeza_g=1 (sem nenhuma data G_)",
            n_limpeza,
        )

    logger.info(
        "aplicar_campos_g: %d linhas totais, %d colunas G_ adicionadas",
        len(df), len(df.columns),
    )
    return df


# ---------------------------------------------------------------------------
# R3 — campos A_ (projeção sobre SIAFI_atual)
# ---------------------------------------------------------------------------

def aplicar_campos_a(df_com_g: pd.DataFrame) -> pd.DataFrame:
    """
    Produz os campos A_ projetando os G_ sobre o SIAFI mais atual.

    Lógica QlikView (linhas 3119-3175):
      A tabela sigcon_chaves_atual2 é keyed por siafi_uo_atual.
      Para cada siafi_uo_atual, os campos A_ são os campos G_ da linha
      cuja siafi_uo == siafi_uo_atual.

      Em Python: auto-join df_com_g com ele mesmo por (siafi_uo_atual = siafi_uo).
      Se a linha não tem correspondência (siafi_uo_atual já é o próprio siafi_uo,
      ou o siafi atual não existe no dataset), os campos A_ == G_ da própria linha.

    Campos A_ gerados:
      a_vigencia, a_ano_convenio, a_situacao_convenio, a_situacao_convenio_categorizado,
      a_concedente_pad, a_proponente_pad, a_dia_assinatura, a_ano_assinatura,
      a_inicio_vigencia, a_ano_inicio_vigencia, a_fim_vigencia, a_fim_vigencia_inicial,
      a_objeto_convenio, a_proponente, a_concedente, a_valor_concedente,
      a_valor_proponente, a_valor_global, a_instrumento, a_esfera,
      a_periodo_nao_aditado_sigcon, a_periodo_nao_aditado, a_valor_nao_aditado.

    Diferença prática entre G_ e A_:
      G_ = "visão do convênio pelo SIAFI de origem" — cada convênio tem o seu G_
           com o número SIAFI histórico que ainda pode não ser o atual.
      A_ = "visão pelo SIAFI atual" — todos os convênios de uma mesma UO
           que têm o mesmo siafi_uo_atual compartilham os mesmos valores A_.
           Útil para dashboards que mostram o estado "hoje" sem duplicar.
    """
    g_para_a = {
        "g_vigencia": "a_vigencia",
        "g_vigencia_siconv": "a_vigencia_siconv",
        "g_vigencia_sigcon": "a_vigencia_sigcon",
        "g_ano_convenio": "a_ano_convenio",
        "g_situacao_convenio": "a_situacao_convenio",
        "g_situacao_convenio_categorizado": "a_situacao_convenio_categorizado",
        "g_concedente_pad": "a_concedente_pad",
        "g_proponente_pad": "a_proponente_pad",
        "g_proponente_pad_siglas": "a_proponente_pad_siglas",
        "g_dia_assinatura": "a_dia_assinatura",
        "g_ano_assinatura": "a_ano_assinatura",
        "g_inicio_vigencia": "a_inicio_vigencia",
        "g_ano_inicio_vigencia": "a_ano_inicio_vigencia",
        "g_fim_vigencia": "a_fim_vigencia",
        "g_fim_vigencia_inicial": "a_fim_vigencia_inicial",
        "g_objeto_convenio": "a_objeto_convenio",
        "g_proponente": "a_proponente",
        "g_concedente": "a_concedente",
        "g_valor_concedente": "a_valor_concedente",
        "g_valor_proponente": "a_valor_proponente",
        "g_valor_global": "a_valor_global",
        "g_instrumento": "a_instrumento",
        "g_esfera": "a_esfera",
        "g_periodo_nao_aditado_sigcon": "a_periodo_nao_aditado_sigcon",
        "g_periodo_nao_aditado": "a_periodo_nao_aditado",
        "g_valor_nao_aditado": "a_valor_nao_aditado",
    }

    # Colunas G_ que existem no DataFrame
    g_existentes = {g: a for g, a in g_para_a.items() if g in df_com_g.columns}
    if not g_existentes:
        return df_com_g

    # Dimensão A_: uma linha por siafi_uo_atual com os campos G_ correspondentes
    # Selecionamos as colunas G_ da tabela original, keyed por siafi_uo
    dim_a = (
        df_com_g[["siafi_uo"] + list(g_existentes.keys())]
        .drop_duplicates("siafi_uo")
        .rename(columns=g_existentes)
        .rename(columns={"siafi_uo": "siafi_uo_key"})
    )

    n_antes = len(df_com_g)
    resultado = df_com_g.merge(
        dim_a,
        left_on="siafi_uo_atual",
        right_on="siafi_uo_key",
        how="left",
    ).drop(columns=["siafi_uo_key"])
    _validar_fan_out(n_antes, len(resultado), "A_/self-join")

    # Fallback: onde não há match (siafi_uo_atual não tem linha própria), A_ = G_
    for g_col, a_col in g_existentes.items():
        if a_col in resultado.columns:
            resultado[a_col] = resultado[a_col].fillna(resultado[g_col])

    logger.info("aplicar_campos_a: %d campos A_ adicionados", len(g_existentes))
    return resultado


# ---------------------------------------------------------------------------
# R3 — orquestrador principal
# ---------------------------------------------------------------------------

def construir_tabela_integrada(
    df_chaves: pd.DataFrame,
    df_siafi2: pd.DataFrame,
    df_sigcon_convenio: pd.DataFrame,
    df_sigcon_codigo_convenio: pd.DataFrame,
    df_sigcon_geral: pd.DataFrame,
    df_sigcon_plano: pd.DataFrame,
    df_sigcon_esfera: pd.DataFrame,
    df_siconv: pd.DataFrame | None = None,
    filtrar_limpeza_g: bool = True,
) -> pd.DataFrame:
    """
    Constrói a tabela integrada completa (G_ + A_) a partir dos Silver files.

    Passos:
      1. Monta tabela-ponte SIGCON (chaves + SIAFI2)
      2. Prepara lado SIGCON completo (convenio + geral + plano + esfera)
      3. Prepara lado SICONV (se disponível)
      4. Aplica campos G_ (coalesce SICONV → SIGCON)
      5. Aplica campos A_ (projeção sobre siafi_uo_atual)
      6. Filtra limpeza_g == 0 (linhas sem dados temporais) se solicitado

    Parameters
    ----------
    df_chaves          : Silver de chaves_convenio
    df_siafi2          : Silver de siafi2
    df_sigcon_convenio : Silver de dcgce_convenio
    df_sigcon_codigo_convenio : Silver de dcgce_codigo_convenio
    df_sigcon_geral    : Silver de dcgce_geral
    df_sigcon_plano    : Silver de dcgce_plano_trabalho
    df_sigcon_esfera   : Silver de dcgce_esfera
    df_siconv          : Silver de siconv_convenio (opcional)
    filtrar_limpeza_g  : se True, remove linhas sem nenhuma data G_ (default True)

    Returns
    -------
    DataFrame com todas as colunas SIGCON, SICONV, G_ e A_.
    """
    logger.info("construir_tabela_integrada: início")

    # Passo 1: tabela-ponte
    sigcon_chaves = montar_sigcon_chaves(df_chaves, df_siafi2)
    logger.info("  tabela-ponte: %d linhas", len(sigcon_chaves))

    # Passo 2: SIGCON completo
    sigcon_completo = _preparar_sigcon_completo(
        df_sigcon_convenio,
        df_sigcon_codigo_convenio,
        df_sigcon_geral,
        df_sigcon_plano,
        df_sigcon_esfera,
    )
    logger.info("  sigcon_completo: %d linhas", len(sigcon_completo))

    # Passo 3: SICONV (opcional)
    siconv = None
    if df_siconv is not None:
        siconv = _preparar_siconv(df_siconv)
        logger.info("  siconv: %d linhas", len(siconv))
    else:
        logger.info("  siconv: não fornecido — campos G_ usarão somente SIGCON")

    # Passo 4: G_ fields
    integrado = aplicar_campos_g(sigcon_chaves, sigcon_completo, siconv)

    # Passo 5: A_ fields
    integrado = aplicar_campos_a(integrado)

    # Passo 6: limpeza_g
    if filtrar_limpeza_g and "limpeza_g" in integrado.columns:
        n_antes = len(integrado)
        integrado = integrado[integrado["limpeza_g"] == 0].reset_index(drop=True)
        n_removidas = n_antes - len(integrado)
        if n_removidas:
            logger.info("  limpeza_g: %d linhas removidas (sem dados temporais)", n_removidas)

    logger.info(
        "construir_tabela_integrada: concluído — %d linhas × %d colunas",
        len(integrado), len(integrado.columns),
    )
    return integrado


def gravar_tabela_integrada(
    df: pd.DataFrame,
    nome: str = "convenios_integrado",
    destino: Path | None = None,
) -> Path:
    """
    Grava a tabela integrada em Parquet em data/gold/.

    Parameters
    ----------
    df      : DataFrame retornado por construir_tabela_integrada()
    nome    : nome do arquivo (sem extensão)
    destino : caminho explícito; se None usa DATA_DIR/gold/<nome>.parquet
    """
    if destino is None:
        from django.conf import settings
        gold_dir = Path(settings.DATA_DIR) / "gold"
        gold_dir.mkdir(parents=True, exist_ok=True)
        destino = gold_dir / f"{nome}.parquet"

    df.to_parquet(destino, index=False)
    logger.info("tabela integrada gravada: %s (%d linhas)", destino, len(df))
    return Path(destino)


# ---------------------------------------------------------------------------
# Distinct_SIAFI_UO — equivalente QlikView, para métricas sem duplicação
# ---------------------------------------------------------------------------

def deduplicar_por_siafi_atual(df_integrado: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna uma linha por siafi_uo_atual com os campos A_.

    Equivalente à tabela Distinct_SIAFI_UO do QlikView (linhas 3178-3190).

    Use este DataFrame para KPIs que não devem contar o mesmo convênio
    duas vezes quando ele mudou de SIAFI — ex: somas de valores.

    Garante que cada siafi_uo_atual aparece uma única vez (keep='first').
    """
    colunas_a = [c for c in df_integrado.columns if c.startswith("a_")]
    colunas_chave = ["siafi_uo_atual", "siafi_uo", "codigo_siconv"]
    colunas_saida = [c for c in colunas_chave + colunas_a if c in df_integrado.columns]

    return (
        df_integrado[colunas_saida]
        .drop_duplicates("siafi_uo_atual", keep="first")
        .reset_index(drop=True)
    )
