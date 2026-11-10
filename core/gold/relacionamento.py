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
  - UOs de UOS_EXCLUIR (11 UOs não-operacionais): MARCADAS em fl_uo_excluida,
    não removidas — nenhuma linha com dado é excluída em nenhuma camada
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
    marcar_uo_excluida,
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
# Fronteira: Silver nova (nr_/cd_/dt_/...) → nomes internos do Gold
# ---------------------------------------------------------------------------
# O miolo G_/A_ trabalha com os nomes dos campos do model ConvenioIntegrado e
# com os prefixos sigcon_/siconv_. As Silvers novas são renomeadas AQUI, uma
# vez, na entrada de cada função pública. Coluna obrigatória ausente levanta
# KeyError: antes, `if coluna in df.columns` fazia campos (SICONV, de-paras)
# sumirem do Gold sem aviso quando o nome mudava.

_ENTRADA_CHAVE_SICONV = {   # sigcon_chave_siconv
    "tp_instrumento_siafi": "plano_trabalho_tipo_siafi",
    "cd_uo": "unidade_orcamentaria_codigo",
    "nr_siafi": "convenio_numero_sequencial_siafi",
    "ds_situacao_convenio": "situacao",
    "nr_convenio_siconv": "codigo_siconv",
}
_ENTRADA_CONVENIO = {       # sigcon_convenio
    "nr_convenio": "convenio_codigo",
    "nr_siafi": "convenio_numero_sequencial_siafi",
    "cd_uo": "unidade_orcamentaria_codigo",
    "ds_situacao_convenio": "situacao",
    "dt_vigencia_inicio": "data_inicio_vigencia",
    "dt_vigencia_termino_inicial": "data_termino_vigencia",
    "dt_vigencia_termino": "data_real_convenio",
    "vl_convenio_concedente_inicial": "valor_inicial_concedente_contratado",
    "vl_convenio_concedente": "valor_concedente",
    "vl_convenio_proponente": "valor_proponente",
    "vl_convenio_total": "valor_total_convenio",
}
_ENTRADA_CHAVE_CONVENIO = {  # sigcon_chave_convenio
    "cd_convenio_sequencial": "convenio_codigo_sequencial",
    "nr_siafi": "convenio_numero_sequencial_siafi",
    "cd_uo": "unidade_orcamentaria_codigo",
}
_ENTRADA_GERAL = {          # sigcon_convenio_geral
    "cd_convenio_sequencial": "convenio_codigo_sequencial",
    "cd_plano_trabalho": "conveno_codigo_plano_trabalho",
    "nr_siafi": "convenio_numero_sequencial_siafi",
    "dt_assinatura": "convenio_data_assinatura_convenio",
}
_ENTRADA_PLANO = {          # sigcon_plano_trabalho
    "cd_plano_trabalho": "plano_trabalho_codigo",
    "tx_objeto": "plano_trabalho_objeto",
    "nm_concedente": "plano_trabalho_razao_social_concedente",
    "nr_cnpj_concedente": "plano_trabalho_cnpj_concedente",
}
_ENTRADA_CONCEDENTE = {     # sigcon_concedente
    "nr_cnpj_concedente": "concedente_cnpj",
    "ds_esfera": "concedente_esfera",
}
_ENTRADA_SICONV = {         # siconv_convenio
    "nr_convenio_siconv": "nr_convenio",
    "cd_proposta_siconv": "id_proposta",
    "dt_assinatura": "siconv_data_assinatura",
    "dt_vigencia_inicio": "siconv_data_inicio_vigencia",
    "dt_vigencia_termino": "siconv_data_fim_vigencia",
    "dt_vigencia_termino_inicial": "siconv_data_fim_vigencia_inicial",
    "ds_situacao_convenio": "siconv_situacao",
    "vl_repasse": "siconv_valor_concedente",
    "vl_contrapartida": "siconv_valor_proponente",
    "vl_global": "siconv_valor_global",
}
# Opcionais: o Transferegov pode trazê-las, mas siconv_convenio hoje NÃO tem
# nome do proponente, órgão concedente nem objeto (G_proponente cai em
# uo_nome_std; G_concedente e G_objeto vêm só do SIGCON).
_ENTRADA_SICONV_OPCIONAL = {
    "nm_proponente": "siconv_proponente",
    "desc_orgao_sup": "siconv_concedente",
    "objeto_proposta": "siconv_objeto",
}


def _entrada(df: pd.DataFrame, mapa: dict[str, str], fonte: str) -> pd.DataFrame:
    """Renomeia a Silver nova para os nomes internos; coluna do mapa ausente = KeyError."""
    faltando = [c for c in mapa if c not in df.columns]
    if faltando:
        raise KeyError(f"Silver '{fonte}': coluna(s) obrigatória(s) ausente(s): {faltando}")
    return df.rename(columns=mapa)


def _deduplicar_consulta(df: pd.DataFrame, chaves: list[str], etapa: str) -> pd.DataFrame:
    """
    Subconjunto de CONSULTA para um merge LEFT: uma linha por chave, sem chave nula.

    Chave nula sai porque o pandas casa nulo com nulo — um convênio sem SIAFI
    herdaria dados de outro sem SIAFI. Chave repetida fica com a primeira linha;
    se as linhas repetidas tiverem conteúdo DIFERENTE, registra ALERTA com a
    contagem (nenhuma escolha em silêncio). Só use em dimensões de consulta,
    nunca na tabela que será gravada.
    """
    df = df.dropna(subset=chaves)
    sem_identicas = df.drop_duplicates()
    n_conflito = int(sem_identicas.duplicated(subset=chaves).sum())
    if n_conflito:
        logger.warning(
            "ALERTA '%s': %d linha(s) com a mesma chave %s e conteúdo diferente; vale a primeira",
            etapa, n_conflito, chaves,
        )
    return sem_identicas.drop_duplicates(subset=chaves)


def _colapsar_chave_unica(df: pd.DataFrame, chave: str, etapa: str) -> pd.DataFrame:
    """
    Garante uma linha por `chave` na tabela que será GRAVADA, sem perder dado.

    - Linhas com chave nula ficam todas (não são duplicatas umas das outras).
    - Linhas com a mesma chave e 100% idênticas colapsam numa só.
    - Mesma chave com conteúdo DIFERENTE: ValueError. Quem escolhe qual vale é
      uma pessoa, não o código.
    """
    com_chave = df[chave].notna()
    sub = df[com_chave]
    sem_identicas = sub.drop_duplicates()
    repetidas = int(sem_identicas.duplicated(subset=[chave]).sum())
    if repetidas:
        raise ValueError(
            f"{etapa}: {repetidas} chave(s) '{chave}' repetida(s) com conteúdo diferente "
            "— decisão de negócio, o código não escolhe sozinho"
        )
    n_identicas = len(sub) - len(sem_identicas)
    if n_identicas:
        logger.warning("%s: %d linha(s) 100%% idênticas colapsadas em '%s'", etapa, n_identicas, chave)
        df = df.drop(index=sub.index[sub.duplicated()])
    return df


# ---------------------------------------------------------------------------
# Convenio_codigo (Código SIGCON) 1:1 por linha — Plano de Aplicação / Cronograma
# ---------------------------------------------------------------------------

def carimbar_convenio_codigo(
    df: pd.DataFrame,
    df_geral: pd.DataFrame,
    coluna_plano_trabalho: str,
) -> pd.DataFrame:
    """
    Carimba convenio_codigo (Código SIGCON) 1:1 por linha, via plano de trabalho.

    NUNCA usar SIAFI como chave aqui — SIAFI é 1:N convênio (o mesmo número
    SIAFI pode abrigar convênios diferentes ao longo do tempo, conforme
    diagnóstico do caso SIAFI 9481207). O plano de trabalho identifica o
    convênio EXATO de cada linha — mesma chave que já liga Plano de Aplicação
    e Cronograma ao convênio desde o R0–R4.

    `df_geral` é o Silver `sigcon_convenio_geral`: traz, na mesma linha,
    `cd_plano_trabalho` (a chave) e `nr_convenio` (Código SIGCON) — join
    direto, sem tabela intermediária. Nenhuma linha de `df` é perdida (left
    join) e chave nula nunca casa com chave nula: linha sem plano de trabalho
    fica com convenio_codigo nulo.

    Pré-requisito: chaves já normalizadas pelo chamador (ver
    apps/sigcon/loader.py::_normalizar_chave) — esta função não normaliza.
    """
    geral_codigo = (
        df_geral[["cd_plano_trabalho", "nr_convenio"]]
        .dropna(subset=["cd_plano_trabalho"])
        .drop_duplicates("cd_plano_trabalho")
        .rename(columns={"cd_plano_trabalho": "_plano_geral", "nr_convenio": "convenio_codigo"})
    )
    antes = len(df)
    resultado = df.merge(
        geral_codigo,
        left_on=coluna_plano_trabalho,
        right_on="_plano_geral",
        how="left",
    ).drop(columns=["_plano_geral"])
    _validar_fan_out(antes, len(resultado), "carimbar_convenio_codigo")
    assert len(resultado) == antes, "carimbar_convenio_codigo: o join mudou o número de linhas"
    return resultado


# ---------------------------------------------------------------------------
# R2 — preparação do sigcon_convenio antes do join
# ---------------------------------------------------------------------------

def preparar_sigcon_convenio(df_convenio: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica correções e de-paras ao Silver `sigcon_convenio` (lado de consulta).

    Entrada com os nomes da Silver nova; a saída usa os nomes internos do Gold.
    Produz colunas adicionais: situacao_std, uo_nome_std, uo_sigla_std,
    uo_descricao_std, siafi_uo. Nenhuma linha é removida (a marcação de UO
    excluída é feita na tabela-ponte, em montar_sigcon_chaves).
    """
    df = _entrada(df_convenio, _ENTRADA_CONVENIO, "sigcon_convenio")
    df = aplicar_correcoes(df, nome_tabela="sigcon_convenio")
    df = aplicar_deparas(df, obrigatorias=("situacao", "unidade_orcamentaria_codigo"))
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
    df_depara: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói a tabela-ponte sigcon_chaves com chaves SIAFI_UO resolvidas.

    Equivalente ao bloco QlikView:
      sigcon_chaves1 (FROM Chaves_convenio.csv) + LEFT JOIN SIAFI2

    Entrada: Silver `sigcon_chave_siconv` e `depara_siafi` (nomes novos).

    Passos (nenhuma linha é removida):
      1. Marca fl_uo_excluida (UO em UOS_EXCLUIR) — a linha fica
      2. Monta siafi_uo = siafi + uo (nulo se faltar SIAFI ou UO)
      3. Aplica de-paras (instrumento, uo_nome_std, situacao_std, etc.)
      4. Resolve siafi_uo_atual via depara_siafi (fallback = original)
      5. Colapsa só linhas 100% idênticas; chave repetida com conteúdo
         diferente levanta ValueError

    Linhas sem siafi_uo (convênio sem SIAFI) ficam, com chave nula.

    Saída: siafi_uo, siafi_uo_atual, siafiatual, uo_atual, codigo_siconv,
           instrumento_chaves, situacao, situacao_std, uo_nome_std, etc.,
           fl_uo_excluida.
    """
    df = _entrada(df_chaves, _ENTRADA_CHAVE_SICONV, "sigcon_chave_siconv")
    df["fl_uo_excluida"] = marcar_uo_excluida(df, coluna_uo="unidade_orcamentaria_codigo")

    df["siafi_uo"] = montar_siafi_uo(
        df["convenio_numero_sequencial_siafi"],
        df["unidade_orcamentaria_codigo"],
    )
    n_sem_chave = int(df["siafi_uo"].isna().sum())
    if n_sem_chave:
        logger.warning(
            "montar_sigcon_chaves: %d linha(s) com SIAFI_UO nulo (mantidas, sem SIAFI)", n_sem_chave
        )

    df = aplicar_deparas(
        df,
        obrigatorias=("situacao", "plano_trabalho_tipo_siafi", "unidade_orcamentaria_codigo"),
    )
    df = resolver_siafi_atual(df, df_depara, coluna_siafi_uo="siafi_uo")
    df = _colapsar_chave_unica(df, "siafi_uo", "montar_sigcon_chaves")

    colunas_saida = [
        "siafi_uo", "siafi_uo_atual",
        "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
        "siafiatual", "uo_atual",
        "codigo_siconv", "instrumento_chaves",
        "situacao", "situacao_std",
        "uo_nome_std", "uo_sigla_std", "uo_descricao_std",
        "fl_uo_excluida",
    ]
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
    Junta as 5 fontes SIGCON em um único DataFrame por siafi_uo (lado de
    consulta do Gold: uma linha por chave, sem chave nula).

    Entrada: Silvers novas (sigcon_convenio, sigcon_chave_convenio,
    sigcon_convenio_geral, sigcon_plano_trabalho, sigcon_concedente).

    Reproduz a cadeia de joins de carregar_convenios() em loader.py, mas
    retorna o DataFrame em vez de instâncias ORM.

    Colunas de saída (prefixadas com sigcon_ para evitar colisão em joins):
      siafi_uo (chave), sigcon_situacao, sigcon_data_inicio_vigencia,
      sigcon_data_termino_vigencia, sigcon_data_real_convenio,
      sigcon_data_assinatura, sigcon_valor_concedente, sigcon_valor_proponente,
      sigcon_valor_global, sigcon_valor_global_inicial,
      sigcon_concedente, sigcon_objeto, sigcon_cnpj_concedente, sigcon_esfera.
    """
    df_codigo_convenio = _entrada(df_codigo_convenio, _ENTRADA_CHAVE_CONVENIO, "sigcon_chave_convenio")
    df_geral = _entrada(df_geral, _ENTRADA_GERAL, "sigcon_convenio_geral")
    df_plano = _entrada(df_plano, _ENTRADA_PLANO, "sigcon_plano_trabalho")
    df_esfera = _entrada(df_esfera, _ENTRADA_CONCEDENTE, "sigcon_concedente")

    # Normaliza chaves de join
    for df, cols in [
        (df_codigo_convenio, ["convenio_codigo_sequencial", "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"]),
        (df_geral, ["convenio_numero_sequencial_siafi", "convenio_codigo_sequencial", "conveno_codigo_plano_trabalho"]),
        (df_plano, ["plano_trabalho_codigo", "plano_trabalho_cnpj_concedente"]),
        (df_esfera, ["concedente_cnpj"]),
    ]:
        for col in cols:
            df[col] = _limpar_id(df[col])

    # Correções e de-paras no convênio (preparar_sigcon_convenio recebe a Silver
    # nova e renomeia sozinha); nenhuma linha sai.
    convenio = preparar_sigcon_convenio(df_convenio)
    for col in ["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"]:
        convenio[col] = _limpar_id(convenio[col])
    convenio["siafi_uo"] = montar_siafi_uo(
        convenio["convenio_numero_sequencial_siafi"],
        convenio["unidade_orcamentaria_codigo"],
    )

    # Enriquece geral com UO via codigo_convenio
    cod_uo = _deduplicar_consulta(
        df_codigo_convenio[["convenio_codigo_sequencial", "unidade_orcamentaria_codigo"]],
        ["convenio_codigo_sequencial"], "sigcon_completo/cod_uo",
    )
    geral = df_geral.merge(cod_uo, on="convenio_codigo_sequencial", how="left")
    geral = geral.rename(columns={"conveno_codigo_plano_trabalho": "plano_trabalho_codigo"})
    geral["unidade_orcamentaria_codigo"] = _limpar_id(geral["unidade_orcamentaria_codigo"])

    geral_sub = _deduplicar_consulta(
        geral[[
            "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
            "plano_trabalho_codigo", "convenio_data_assinatura_convenio",
        ]],
        ["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"],
        "sigcon_completo/geral",
    )

    merged = convenio.merge(
        geral_sub,
        on=["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"],
        how="left",
    )
    _validar_fan_out(len(convenio), len(merged), "sigcon+geral")

    # Plano trabalho (concedente, objeto, cnpj, instrumento)
    plano_sub = _deduplicar_consulta(
        df_plano[[
            "plano_trabalho_codigo", "plano_trabalho_objeto",
            "plano_trabalho_razao_social_concedente", "plano_trabalho_cnpj_concedente",
        ]],
        ["plano_trabalho_codigo"], "sigcon_completo/plano",
    )
    merged = merged.merge(plano_sub, on="plano_trabalho_codigo", how="left")
    _validar_fan_out(len(convenio), len(merged), "sigcon+plano")

    # Esfera via CNPJ concedente
    esfera_sub = _deduplicar_consulta(
        df_esfera[["concedente_cnpj", "concedente_esfera"]],
        ["concedente_cnpj"], "sigcon_completo/esfera",
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
    faltando = [c for c in colunas if c not in merged.columns]
    if faltando:
        raise KeyError(f"_preparar_sigcon_completo: coluna(s) esperada(s) ausente(s): {faltando}")
    resultado = merged[list(colunas)].rename(columns=colunas)

    # Lado de consulta: uma linha por siafi_uo, sem chave nula
    return _deduplicar_consulta(resultado, ["siafi_uo"], "sigcon_completo")


def _preparar_siconv(df_siconv: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara o Silver `siconv_convenio` (nomes novos) para o coalesce G_,
    prefixando as colunas com siconv_ (lado de consulta: uma linha por convênio
    federal, sem chave nula).

    Colunas de saída: nr_convenio (chave), id_proposta,
      siconv_situacao, siconv_data_inicio_vigencia, siconv_data_fim_vigencia,
      siconv_data_fim_vigencia_inicial, siconv_data_assinatura,
      siconv_valor_concedente, siconv_valor_proponente, siconv_valor_global
      (+ siconv_proponente, siconv_concedente, siconv_objeto SE a fonte as trouxer).
    """
    df = _entrada(df_siconv, _ENTRADA_SICONV, "siconv_convenio")
    df = df.rename(columns={k: v for k, v in _ENTRADA_SICONV_OPCIONAL.items() if k in df.columns})

    # Chave: nr_convenio deve ser StringDtype sem artefatos .0
    df["nr_convenio"] = _limpar_id(df["nr_convenio"])

    colunas_saida = ["nr_convenio", "id_proposta"] + [
        v for v in (*_ENTRADA_SICONV.values(), *_ENTRADA_SICONV_OPCIONAL.values())
        if v in df.columns and v not in ("nr_convenio", "id_proposta")
    ]
    return _deduplicar_consulta(df[colunas_saida], ["nr_convenio"], "siconv")


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
        _deduplicar_consulta(
            df_com_g[["siafi_uo"] + list(g_existentes.keys())], ["siafi_uo"], "A_/dimensão",
        )
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
    df_depara: pd.DataFrame,
    df_sigcon_convenio: pd.DataFrame,
    df_sigcon_codigo_convenio: pd.DataFrame,
    df_sigcon_geral: pd.DataFrame,
    df_sigcon_plano: pd.DataFrame,
    df_sigcon_esfera: pd.DataFrame,
    df_siconv: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Constrói a tabela integrada completa (G_ + A_) a partir dos Silver files.

    NENHUMA linha da ponte é excluída: o resultado tem uma linha por linha de
    `sigcon_chave_siconv` (com as repetidas 100% idênticas colapsadas). UO
    excluída → fl_uo_excluida; linha sem datas → limpeza_g = 1. Quem não quer
    essas linhas numa tela filtra na consulta (apps/sigcon/services.py).

    Passos:
      1. Monta tabela-ponte SIGCON (chaves + depara_siafi)
      2. Prepara lado SIGCON completo (convenio + geral + plano + esfera)
      3. Prepara lado SICONV (se disponível)
      4. Aplica campos G_ (coalesce SICONV → SIGCON)
      5. Aplica campos A_ (projeção sobre siafi_uo_atual)

    Parameters (todos com os nomes de coluna da Silver nova)
    ----------
    df_chaves          : Silver de sigcon_chave_siconv
    df_depara          : Silver de depara_siafi
    df_sigcon_convenio : Silver de sigcon_convenio
    df_sigcon_codigo_convenio : Silver de sigcon_chave_convenio
    df_sigcon_geral    : Silver de sigcon_convenio_geral
    df_sigcon_plano    : Silver de sigcon_plano_trabalho
    df_sigcon_esfera   : Silver de sigcon_concedente
    df_siconv          : Silver de siconv_convenio (opcional)

    Returns
    -------
    DataFrame com todas as colunas SIGCON, SICONV, G_ e A_.
    """
    logger.info("construir_tabela_integrada: início")

    # Passo 1: tabela-ponte
    sigcon_chaves = montar_sigcon_chaves(df_chaves, df_depara)
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

    assert len(integrado) == len(sigcon_chaves), (
        f"construir_tabela_integrada: a tabela-ponte tinha {len(sigcon_chaves)} linhas e o "
        f"resultado {len(integrado)} — linha perdida ou multiplicada"
    )
    n_limpeza = int((integrado["limpeza_g"] == 1).sum())
    if n_limpeza:
        logger.info("  limpeza_g=1: %d linha(s) sem nenhuma data G_ (mantidas, marcadas)", n_limpeza)

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
