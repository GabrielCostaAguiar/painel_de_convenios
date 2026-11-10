"""
Loaders full-refresh para os models da app sigcon.

Cada função:
  1. Lê o(s) Parquet(s) Silver via pd.read_parquet
  2. Apaga todos os registros existentes no model
  3. Reconstrói via bulk_create(batch_size=500)
  4. Retorna dict com 'apagados' e 'inseridos'

Os passos 2 e 3 rodam sempre dentro de uma mesma transação (core.db.bulk_refresh):
ou a tabela inteira é substituída, ou nada muda.

Fontes: as chaves novas da Silver (sigcon_*, depara_*, controle_sei — ver
core/ingestion/sources.py e docs/dicionario_dados_legado.md). Os models mantêm
os nomes de campo históricos; cada loader faz o de-para coluna da Silver →
campo do model.

REGRA: nenhuma linha da Silver é perdida na carga (linhas do model = linhas do
Parquet de origem). Joins de enriquecimento são LEFT, com o lado direito
desduplicado e sem chave nula, e conferem que o número de linhas não mudou.
"""
import logging
from decimal import Decimal
from pathlib import Path

import pandas as pd
from django.conf import settings

from core.db import bulk_refresh as _bulk_refresh

from .models import (
    CodigoConvenio,
    CodigoDeclaracaoContrapartida,
    CodigoPlanoTrabalho,
    CodigoTermoAditivo,
    Convenio,
    ConvenioGeral,
    ConvenioIntegrado,
    ControleSEI,
    CronogramaDesembolso,
    DeclaracaoContrapartida,
    Esfera,
    NtEmenda,
    PlanoAplicacao,
    PlanoTrabalho,
    ProrrogacaoOficio,
    TermoAditivo,
    UnidadesExecutoras,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------

def _silver_path(nome_fonte: str) -> Path:
    return Path(settings.DATA_DIR) / "silver" / f"{nome_fonte}.parquet"


def _para_date(val):
    """pd.Timestamp → datetime.date; NaT/None/NA → None."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(val, "date"):
        return val.date()
    return None


def _para_decimal(val):
    """float → Decimal via str(); NaN/NA → None."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _para_str(val):
    """StringDtype <NA> / NaN / vazio → None; caso contrário, strip e retorna str."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    return s or None


def _bool_para_texto(val, verdadeiro: str, falso: str):
    """boolean nullable da Silver → texto original do export; nulo → None."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return verdadeiro if bool(val) else falso


def _ler_parquet(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Parquet Silver não encontrado: {caminho}\n"
            "Rode antes: python manage.py rodar_silver <fonte>"
        )
    df = pd.read_parquet(caminho)
    logger.info("Parquet lido: %s (%d linhas × %d colunas)", caminho.name, *df.shape)
    return df


def _normalizar_chave(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Garante que colunas de chave estão como StringDtype nullable, stripped e sem artefato '.0'.
    Necessário para que os merges entre parquets funcionem corretamente.
    """
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col].astype("string").str.strip()
        mask = s.notna() & s.str.endswith(".0") & s.str[:-2].str.isdigit()
        s = s.where(~mask, s.str[:-2])
        df[col] = s
    return df


# ---------------------------------------------------------------------------
# Piloto — Convenio consolidado
# ---------------------------------------------------------------------------

def carregar_convenios(silver_path: Path | None = None) -> dict:
    """
    Full refresh consolidado do model Convenio.

    Fontes lidas (Silver, na ordem dos joins):
      sigcon_convenio        — chave SIAFI+UO, situação, datas vigência, valores
      sigcon_chave_convenio  — ponte: cd_convenio_sequencial → UO (enriquece Geral)
      sigcon_convenio_geral  — data publicação, assinatura, plano de trabalho
      sigcon_plano_trabalho  — título, objeto, concedente, CNPJs, instrumento
      sigcon_concedente      — esfera via CNPJ concedente

    Joins (todos LEFT: o model recebe uma linha por linha de sigcon_convenio):
      Geral+UO:    geral.cd_convenio_sequencial = chave.cd_convenio_sequencial
      Conv+Geral:  (conv.nr_siafi, conv.cd_uo) = (geral.nr_siafi, geral.cd_uo)
      +Plano:      merged.cd_plano_trabalho = plano.cd_plano_trabalho
      +Esfera:     merged.nr_cnpj_concedente = concedente.nr_cnpj_concedente

    O lado direito de cada join é desduplicado e SEM chave nula: o pandas casa
    nulo com nulo, e um convênio sem SIAFI herdaria dados de outro convênio
    sem SIAFI (a Silver antiga usava '0' como chave e fazia exatamente isso).
    """
    conv = _ler_parquet(silver_path or _silver_path("sigcon_convenio"))
    cod_conv = _ler_parquet(_silver_path("sigcon_chave_convenio"))
    geral = _ler_parquet(_silver_path("sigcon_convenio_geral"))
    plano = _ler_parquet(_silver_path("sigcon_plano_trabalho"))
    concedente = _ler_parquet(_silver_path("sigcon_concedente"))

    # Normaliza todas as chaves de join
    _normalizar_chave(conv, ["nr_siafi", "cd_uo"])
    _normalizar_chave(cod_conv, ["cd_convenio_sequencial", "nr_siafi", "cd_uo"])
    _normalizar_chave(geral, ["nr_siafi", "cd_convenio_sequencial", "cd_plano_trabalho"])
    _normalizar_chave(plano, ["cd_plano_trabalho", "nr_cnpj_concedente"])
    _normalizar_chave(concedente, ["nr_cnpj_concedente"])

    # Step 1: enriquecer Geral com UO (via cd_convenio_sequencial → chave_convenio)
    cod_conv_uo = (
        cod_conv[["cd_convenio_sequencial", "cd_uo"]]
        .dropna(subset=["cd_convenio_sequencial"])
        .drop_duplicates("cd_convenio_sequencial")
    )
    geral = geral.merge(cod_conv_uo, on="cd_convenio_sequencial", how="left")

    # Step 2: merge Convenio + Geral pela chave composta SIAFI+UO
    geral_sub = (
        geral[[
            "nr_siafi", "cd_uo", "cd_plano_trabalho",
            "dt_publicacao", "dt_assinatura", "nr_ano_convenio",
        ]]
        .dropna(subset=["nr_siafi", "cd_uo"])
        .drop_duplicates(["nr_siafi", "cd_uo"])
    )
    merged = conv.merge(geral_sub, on=["nr_siafi", "cd_uo"], how="left")
    assert len(merged) == len(conv), "fan-out inesperado no join Convenio+Geral"

    n_sem_plano = int(merged["cd_plano_trabalho"].isna().sum())
    logger.info(
        "Conv+Geral: %d registros, %d sem cd_plano_trabalho (%.1f%%)",
        len(merged), n_sem_plano, 100 * n_sem_plano / max(len(merged), 1),
    )

    # Step 3: merge + PlanoTrabalho
    plano_sub = (
        plano[[
            "cd_plano_trabalho", "nm_plano_trabalho", "tx_objeto",
            "nm_concedente", "nr_cnpj_concedente",
            "nr_cnpj_proponente", "tp_instrumento_siafi",
        ]]
        .dropna(subset=["cd_plano_trabalho"])
        .drop_duplicates("cd_plano_trabalho")
    )
    merged = merged.merge(plano_sub, on="cd_plano_trabalho", how="left")
    assert len(merged) == len(conv), "fan-out inesperado no join +Plano"

    # Step 4: merge + Esfera via CNPJ concedente
    esfera_sub = (
        concedente[["nr_cnpj_concedente", "ds_esfera"]]
        .dropna(subset=["nr_cnpj_concedente"])
        .drop_duplicates("nr_cnpj_concedente")
    )
    merged = merged.merge(esfera_sub, on="nr_cnpj_concedente", how="left")
    assert len(merged) == len(conv), "fan-out inesperado no join +Esfera"

    n_sem_esfera = int(merged["ds_esfera"].isna().sum())
    logger.info(
        "Conv+Esfera: %d sem esfera (%.1f%%)",
        n_sem_esfera, 100 * n_sem_esfera / max(len(merged), 1),
    )

    objetos = [
        Convenio(
            convenio_codigo=_para_str(row["nr_convenio"]) or "",
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
            situacao=_para_str(row["ds_situacao_convenio"]),
            data_inicio_vigencia=_para_date(row["dt_vigencia_inicio"]),
            data_termino_vigencia=_para_date(row["dt_vigencia_termino_inicial"]),
            data_real_convenio=_para_date(row["dt_vigencia_termino"]),
            valor_inicial_concedente_contratado=_para_decimal(row["vl_convenio_concedente_inicial"]),
            valor_total_aditado_concedente_contratado=_para_decimal(row["vl_convenio_concedente_aditado"]),
            valor_concedente=_para_decimal(row["vl_convenio_concedente"]),
            valor_inicial_proponente_contratado=_para_decimal(row["vl_convenio_proponente_inicial"]),
            valor_total_aditado_proponente_contratado=_para_decimal(row["vl_convenio_proponente_aditado"]),
            valor_proponente=_para_decimal(row["vl_convenio_proponente"]),
            valor_total_convenio=_para_decimal(row["vl_convenio_total"]),
            # de Geral
            plano_trabalho_codigo=_para_str(row["cd_plano_trabalho"]),
            data_publicacao=_para_date(row["dt_publicacao"]),
            data_assinatura=_para_date(row["dt_assinatura"]),
            convenio_ano=_para_str(row["nr_ano_convenio"]),
            # de PlanoTrabalho
            instrumento=_para_str(row["tp_instrumento_siafi"]),
            titulo=_para_str(row["nm_plano_trabalho"]),
            objeto=_para_str(row["tx_objeto"]),
            concedente=_para_str(row["nm_concedente"]),
            cnpj_concedente=_para_str(row["nr_cnpj_concedente"]),
            cnpj_proponente=_para_str(row["nr_cnpj_proponente"]),
            # de Concedente (esfera)
            esfera=_para_str(row["ds_esfera"]),
        )
        for _, row in merged.iterrows()
    ]
    return _bulk_refresh(Convenio, objetos)


# ---------------------------------------------------------------------------
# Piloto — Cronograma com SIAFI+UO carimbados
# ---------------------------------------------------------------------------

def carregar_cronograma_desembolso(silver_path: Path | None = None) -> dict:
    """
    Full refresh do CronogramaDesembolso com SIAFI+UO do convênio.

    TODAS as linhas da Silver entram (hoje 48.392), inclusive as marcadas pelo
    motor (bloco desalinhado do relatório do BO, sem plano de trabalho): o
    motivo vai para `ds_alerta_linha` e as telas filtram
    `ds_alerta_linha__isnull=True`.

    Rota do join:
      cronograma.cd_plano_trabalho
        = geral.cd_plano_trabalho
        → geral.cd_convenio_sequencial
        → chave_convenio.cd_convenio_sequencial
        → chave_convenio.(nr_siafi, cd_uo)

    convenio_codigo (Código SIGCON) é carimbado 1:1 por linha pela mesma
    chave cd_plano_trabalho, reaproveitando sigcon_convenio_geral
    (core/gold/relacionamento.py::carimbar_convenio_codigo) — nunca via SIAFI,
    que é 1:N convênio.
    """
    from core.gold.relacionamento import carimbar_convenio_codigo

    crono = _ler_parquet(silver_path or _silver_path("sigcon_cronograma_desembolso"))
    geral = _ler_parquet(_silver_path("sigcon_convenio_geral"))
    cod_conv = _ler_parquet(_silver_path("sigcon_chave_convenio"))

    _normalizar_chave(crono, ["cd_plano_trabalho"])
    _normalizar_chave(geral, ["cd_plano_trabalho", "cd_convenio_sequencial"])
    _normalizar_chave(cod_conv, ["cd_convenio_sequencial", "nr_siafi", "cd_uo"])
    n_linhas = len(crono)

    # Step 1: cronograma → Geral (cd_plano_trabalho)
    geral_plano = (
        geral[["cd_plano_trabalho", "cd_convenio_sequencial"]]
        .dropna(subset=["cd_plano_trabalho"])
        .drop_duplicates("cd_plano_trabalho")
    )
    crono_enrich = crono.merge(geral_plano, on="cd_plano_trabalho", how="left")
    assert len(crono_enrich) == n_linhas, "fan-out inesperado no join cronograma→Geral"

    # Step 1b: carimba convenio_codigo (Código SIGCON) 1:1 pela mesma chave
    crono_enrich = carimbar_convenio_codigo(crono_enrich, geral, coluna_plano_trabalho="cd_plano_trabalho")

    # Step 2: → chave_convenio (cd_convenio_sequencial → SIAFI+UO)
    cod_conv_sub = (
        cod_conv[["cd_convenio_sequencial", "nr_siafi", "cd_uo"]]
        .dropna(subset=["cd_convenio_sequencial"])
        .drop_duplicates("cd_convenio_sequencial")
    )
    crono_enrich = crono_enrich.merge(cod_conv_sub, on="cd_convenio_sequencial", how="left")
    assert len(crono_enrich) == n_linhas, "fan-out inesperado no join sequencial→SIAFI+UO"

    n_total = len(crono_enrich)
    n_com_siafi = int(crono_enrich["nr_siafi"].notna().sum())
    n_sem_siafi = n_total - n_com_siafi
    n_marcadas = int(crono_enrich["ds_alerta_linha"].notna().sum())
    logger.info(
        "Cronograma: %d total (%d marcadas) | com SIAFI: %d (%.1f%%) | sem SIAFI: %d (%.1f%%)",
        n_total, n_marcadas,
        n_com_siafi, 100 * n_com_siafi / max(n_total, 1),
        n_sem_siafi, 100 * n_sem_siafi / max(n_total, 1),
    )

    objetos = [
        CronogramaDesembolso(
            plano_trabalho_codigo=_para_str(row["cd_plano_trabalho"]),
            convenio_codigo=_para_str(row["convenio_codigo"]),
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
            valor_concedente_cronograma_desembolso=_para_decimal(row["vl_desembolso_concedente"]),
            valor_proponente_cronograma_desembolso=_para_decimal(row["vl_desembolso_proponente"]),
            mes_cronograma_desembolso=_para_str(row["nr_mes_desembolso"]),
            ano_cronograma_desembolso=_para_str(row["nr_ano_desembolso"]),
            ds_alerta_linha=_para_str(row["ds_alerta_linha"]),
        )
        for _, row in crono_enrich.iterrows()
    ]
    return _bulk_refresh(CronogramaDesembolso, objetos)


# ---------------------------------------------------------------------------
# Loaders dos demais models (cada um lê a Silver da sua fonte `sigcon_*`)
# ---------------------------------------------------------------------------

def carregar_convenio_geral(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_convenio_geral.parquet → model ConvenioGeral."""
    caminho = silver_path or _silver_path("sigcon_convenio_geral")
    df = _ler_parquet(caminho)

    objetos = [
        ConvenioGeral(
            convenio_codigo=_para_str(row["nr_convenio"]),
            convenio_codigo_sequencial=_para_str(row["cd_convenio_sequencial"]),
            conveno_codigo_plano_trabalho=_para_str(row["cd_plano_trabalho"]),
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            convenio_codigo_declaracao=_para_str(row["cd_declaracao_contrapartida"]),
            convenio_data_de_publicacao=_para_date(row["dt_publicacao"]),
            convenio_data_alteracao_sccg=_para_date(row["dh_alteracao_sccg"]),
            convenio_data_controle_sccg_convenio=_para_date(row["dt_controle_sccg"]),
            convenio_data_assinatura_convenio=_para_date(row["dt_assinatura"]),
            convenio_data_de_cadastramento=_para_date(row["dh_cadastramento"]),
            convenio_ano=_para_str(row["nr_ano_convenio"]),
            convenio_alteracao=_bool_para_texto(
                row["fl_permite_alteracao"], "Pode sofrer alteração", "Não pode sofrer alteração",
            ),
            convenio_matricula_tecnico_sccg=_para_str(row["cd_matricula_tecnico_sccg"]),
            convenio_justificativa_da_alteracao=_para_str(row["tx_justificativa_alteracao"]),
            convenio_matricula_gestor=_para_str(row["cd_matricula_gestor"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(ConvenioGeral, objetos)


def carregar_plano_trabalho(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_plano_trabalho.parquet → model PlanoTrabalho."""
    caminho = silver_path or _silver_path("sigcon_plano_trabalho")
    df = _ler_parquet(caminho)

    objetos = [
        PlanoTrabalho(
            plano_trabalho_codigo=_para_str(row["cd_plano_trabalho"]),
            plano_trabalho_codigo_execucao_no_exercicio=_para_str(row["cd_execucao_exercicio"]),
            plano_trabalho_tipo_siafi=_para_str(row["tp_instrumento_siafi"]),
            plano_trabalho_cnpj_concedente=_para_str(row["nr_cnpj_concedente"]),
            plano_trabalho_cnpj_proponente=_para_str(row["nr_cnpj_proponente"]),
            plano_trabalho_data_cancelamento_sccg=_para_date(row["dh_cancelamento_sccg"]),
            plano_trabalho_data_cadastro=_para_date(row["dh_cadastro"]),
            plano_trabalho_data_envio_sccg=_para_date(row["dh_envio_sccg"]),
            plano_trabalho_titulo=_para_str(row["nm_plano_trabalho"]),
            plano_trabalho_objeto=_para_str(row["tx_objeto"]),
            plano_trabalho_justificativa=_para_str(row["tx_justificativa"]),
            plano_trabalho_status=_para_str(row["ds_status_plano_trabalho"]),
            plano_trabalho_caracteristica=_para_str(row["ds_caracteristica_contrapartida"]),
            plano_trabalho_tipo=_para_str(row["tp_plano_trabalho"]),
            plano_trabalho_migrado_ou_novo=_para_str(row["ds_origem_cadastro"]),
            plano_trabalho_matricula_sccg_cancelamento=_para_str(row["cd_matricula_cancelamento_sccg"]),
            plano_trabalho_justificativa_sccg_cancelamento=_para_str(row["tx_justificativa_cancelamento"]),
            plano_trabalho_cancelamento_sccg=_para_str(row["ds_cancelamento_sccg"]),
            plano_trabalho_ano=_para_str(row["nr_ano_plano_trabalho"]),
            plano_trabalho_altera_termo_aditivo=_para_str(row["ds_alteracao_termo_aditivo"]),
            plano_trabalho_razao_social_concedente=_para_str(row["nm_concedente"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(PlanoTrabalho, objetos)


def carregar_plano_aplicacao(silver_path: Path | None = None) -> dict:
    """
    Fonte: sigcon_plano_aplicacao.parquet → model PlanoAplicacao.

    convenio_codigo (Código SIGCON) é carimbado 1:1 por linha via
    cd_plano_trabalho, reaproveitando sigcon_convenio_geral
    (core/gold/relacionamento.py::carimbar_convenio_codigo) — nunca via SIAFI,
    que é 1:N convênio.

    convenio_numero_sequencial_siafi é carimbado pela mesma rota usada em
    carregar_cronograma_desembolso: Geral.cd_convenio_sequencial →
    sigcon_chave_convenio.nr_siafi.
    """
    from core.gold.relacionamento import carimbar_convenio_codigo

    caminho = silver_path or _silver_path("sigcon_plano_aplicacao")
    df = _ler_parquet(caminho)
    geral = _ler_parquet(_silver_path("sigcon_convenio_geral"))
    cod_conv = _ler_parquet(_silver_path("sigcon_chave_convenio"))

    _normalizar_chave(df, ["cd_plano_trabalho"])
    _normalizar_chave(geral, ["cd_plano_trabalho", "cd_convenio_sequencial"])
    _normalizar_chave(cod_conv, ["cd_convenio_sequencial", "nr_siafi"])

    # Step 1: plano_aplicacao → Geral (cd_plano_trabalho)
    geral_seq = (
        geral[["cd_plano_trabalho", "cd_convenio_sequencial"]]
        .dropna(subset=["cd_plano_trabalho"])
        .drop_duplicates("cd_plano_trabalho")
    )
    antes = len(df)
    df = df.merge(geral_seq, on="cd_plano_trabalho", how="left")
    assert len(df) == antes, "fan-out inesperado no join Geral->sequencial"

    # Step 1b: carimba convenio_codigo (Código SIGCON) 1:1 pela mesma chave
    df = carimbar_convenio_codigo(df, geral, coluna_plano_trabalho="cd_plano_trabalho")

    # Step 2: → chave_convenio (cd_convenio_sequencial → SIAFI)
    cod_conv_sub = (
        cod_conv[["cd_convenio_sequencial", "nr_siafi"]]
        .dropna(subset=["cd_convenio_sequencial"])
        .drop_duplicates("cd_convenio_sequencial")
    )
    antes = len(df)
    df = df.merge(cod_conv_sub, on="cd_convenio_sequencial", how="left")
    assert len(df) == antes, "fan-out inesperado no join sequencial->SIAFI"

    objetos = [
        PlanoAplicacao(
            codigo_plano_trabalho=_para_str(row["cd_plano_trabalho"]),
            convenio_codigo=_para_str(row["convenio_codigo"]),
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            codigo_unidade_orcamentaria=_para_str(row["cd_uo"]),
            funcao_codigo=_para_str(row["cd_funcao"]),
            subfuncao_codigo=_para_str(row["cd_subfuncao"]),
            programa_codigo=_para_str(row["cd_programa"]),
            identificador_projeto_atividade_codigo=_para_str(row["cd_identificador_projeto_atividade"]),
            projeto_atividade_codigo=_para_str(row["cd_projeto_atividade"]),
            subprojeto_subatividade_codigo=_para_str(row["cd_subprojeto_subatividade"]),
            categoria_economica_despesa_codigo=_para_str(row["cd_categoria_economica"]),
            grupo_despesa_codigo=_para_str(row["cd_grupo_despesa"]),
            modalidade_aplicacao_codigo=_para_str(row["cd_modalidade_aplicacao"]),
            elemento_despesa_codigo=_para_str(row["cd_elemento_despesa"]),
            identificador_orcamento_codigo=_para_str(row["cd_identificador_orcamento"]),
            fonte_recurso_codigo=_para_str(row["cd_fonte_recurso"]),
            procedencia_codigo=_para_str(row["cd_procedencia"]),
            funcional_programatica_formatado=_para_str(row["cd_funcional_programatica"]),
            valor_concedente=_para_decimal(row["vl_aplicacao_concedente"]),
            valor_proponente=_para_decimal(row["vl_aplicacao_proponente"]),
            ano_exercicio_programa_trabalho=_para_str(row["nr_ano_exercicio"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(PlanoAplicacao, objetos)


def carregar_termo_aditivo(silver_path: Path | None = None) -> dict:
    """
    Fonte: sigcon_termo_aditivo.parquet → model TermoAditivo.

    termo_aditivo_alteracao, termo_aditivo_tipo e quantidade_termo_aditivo não
    existem mais na Silver (eram constantes ou vazias nas 7.113 linhas) e ficam
    nulos; a tela já usa tipo_termo_aditivo (← tp_termo_aditivo).
    """
    caminho = silver_path or _silver_path("sigcon_termo_aditivo")
    df = _ler_parquet(caminho)

    objetos = [
        TermoAditivo(
            termo_aditivo_codigo_sequencial=_para_str(row["cd_termo_aditivo"]),
            termo_aditivo_numero_termo_aditivo=_para_str(row["nr_termo_aditivo"]),
            termo_aditivo_data_assinatura=_para_date(row["dt_assinatura"]),
            termo_aditivo_data_inicio_vigencia=_para_date(row["dt_vigencia_inicio"]),
            termo_aditivo_data_termino_vigencia=_para_date(row["dt_vigencia_termino"]),
            data_termo_aditivo=_para_date(row["dh_registro"]),
            valor_aditado_concedente_contratado=_para_decimal(row["vl_aditivo_concedente"]),
            valor_aditado_proponente_contratado=_para_decimal(row["vl_aditivo_proponente"]),
            termo_aditivo_justificativa=_para_str(row["tx_justificativa"]),
            termo_aditivo_ano=_para_str(row["nr_ano_termo_aditivo"]),
            tipo_termo_aditivo=_para_str(row["tp_termo_aditivo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(TermoAditivo, objetos)


def carregar_declaracao_contrapartida(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_declaracao_contrapartida.parquet → model DeclaracaoContrapartida."""
    caminho = silver_path or _silver_path("sigcon_declaracao_contrapartida")
    df = _ler_parquet(caminho)

    objetos = [
        DeclaracaoContrapartida(
            declaracao_contrapartida_codigo=_para_str(row["cd_declaracao_contrapartida"]),
            declaracao_contrapartida_codigo_nota_tecnica=_para_str(row["cd_nota_tecnica"]),
            declaracao_contrapartida_codigo_parecer_aprovacao=_para_str(row["ds_parecer_aprovacao"]),
            declaracao_contrapartida_data_completa_emissao=_para_date(row["dh_emissao"]),
            declaracao_contrapartida_data_emissao=_para_date(row["dt_emissao"]),
            declaracao_contrapartida_data_completa_parecer_aprovacao=_para_date(row["dh_parecer_aprovacao"]),
            declaracao_contrapartida_data_parecer_aprovacao=_para_date(row["dt_parecer_aprovacao"]),
            declaracao_contrapartida_ano=_para_str(row["nr_ano_declaracao"]),
            declaracao_contrapartida_status=_para_str(row["ds_status_declaracao"]),
            declaracao_contrapartida_observacao=_para_str(row["tx_observacao"]),
            declaracao_contrapartida_observacao_aprovacao=_para_str(row["tx_observacao_aprovacao"]),
            declaracao_contrapartida_matricula_aprovacao=_para_str(row["cd_matricula_aprovacao"]),
            declaracao_contrapartida_momento=_para_str(row["ds_momento"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(DeclaracaoContrapartida, objetos)


def carregar_prorrogacao_oficio(silver_path: Path | None = None) -> dict:
    """
    Fonte: sigcon_prorrogacao_oficio.parquet → model ProrrogacaoOficio.

    prorrogacao_oficio_codigo_convenio ← cd_convenio_sequencial: na Silver a
    coluna é o código SEQUENCIAL do convênio, não o número legível.
    """
    caminho = silver_path or _silver_path("sigcon_prorrogacao_oficio")
    df = _ler_parquet(caminho)

    objetos = [
        ProrrogacaoOficio(
            prorrogacao_oficio_codigo=_para_str(row["cd_prorrogacao_oficio"]),
            prorrogacao_oficio_codigo_convenio=_para_str(row["cd_convenio_sequencial"]),
            prorrogacao_oficio_data_inicio_vigencia=_para_date(row["dt_vigencia_inicio"]),
            prorrogacao_oficio_data_termino_vigencia=_para_date(row["dt_vigencia_termino"]),
            prorrogacao_oficio_data_envio=_para_date(row["dt_envio"]),
            prorrogacao_oficio_data_parecer=_para_date(row["dt_parecer"]),
            prorrogacao_oficio_data_publicacao=_para_date(row["dt_publicacao"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(ProrrogacaoOficio, objetos)


def carregar_nt_emenda(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_nt_emenda.parquet → model NtEmenda."""
    caminho = silver_path or _silver_path("sigcon_nt_emenda")
    df = _ler_parquet(caminho)

    objetos = [
        NtEmenda(
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
            plano_trabalho_codigo=_para_str(row["cd_plano_trabalho"]),
            nt_emenda_no=_para_str(row["nr_emenda"]),
            nt_emenda_nome=_para_str(row["nm_parlamentar"]),
            nota_tecnica_emenda_parlamentar_federal_situacao=_bool_para_texto(
                row["fl_emenda_parlamentar_federal"], "Sim", "Não",
            ),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(NtEmenda, objetos)


def carregar_esfera(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_concedente.parquet → model Esfera."""
    caminho = silver_path or _silver_path("sigcon_concedente")
    df = _ler_parquet(caminho)

    objetos = [
        Esfera(
            concedente_cnpj=_para_str(row["nr_cnpj_concedente"]),
            concedente_esfera=_para_str(row["ds_esfera"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(Esfera, objetos)


def carregar_codigo_convenio(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_convenio.parquet → model CodigoConvenio."""
    caminho = silver_path or _silver_path("sigcon_chave_convenio")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoConvenio(
            convenio_codigo=_para_str(row["nr_convenio"]),
            convenio_codigo_sequencial=_para_str(row["cd_convenio_sequencial"]),
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoConvenio, objetos)


def carregar_codigo_plano_trabalho(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_plano_trabalho.parquet → model CodigoPlanoTrabalho."""
    caminho = silver_path or _silver_path("sigcon_chave_plano_trabalho")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoPlanoTrabalho(
            conveno_codigo_plano_trabalho=_para_str(row["cd_plano_trabalho"]),
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoPlanoTrabalho, objetos)


def carregar_codigo_termo_aditivo(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_termo_aditivo.parquet → model CodigoTermoAditivo."""
    caminho = silver_path or _silver_path("sigcon_chave_termo_aditivo")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoTermoAditivo(
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            termo_aditivo_codigo_sequencial=_para_str(row["cd_termo_aditivo"]),
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
            plano_trabalho_codigo=_para_str(row["cd_plano_trabalho"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoTermoAditivo, objetos)


def carregar_codigo_declaracao_contrapartida(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_declaracao.parquet → model CodigoDeclaracaoContrapartida."""
    caminho = silver_path or _silver_path("sigcon_chave_declaracao")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoDeclaracaoContrapartida(
            declaracao_contrapartida_codigo=_para_str(row["cd_declaracao_contrapartida"]),
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoDeclaracaoContrapartida, objetos)


#----- CARREGAR DADOS DO GRP PARA TESTE DAS TABELAS ----------------------


def _str_para_date(val):
    """String ISO / pd.Timestamp / NaT → datetime.date; erro ou NA → None."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    ts = pd.to_datetime(val, errors="coerce")
    if ts is pd.NaT or pd.isna(ts):
        return None
    return ts.date()


def _para_int(val) -> int | None:
    """pandas Int64 / float / None → int ou None."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def carregar_tabela_integrada(gold_path: Path | None = None) -> dict:
    """
    Full refresh do model ConvenioIntegrado a partir do Gold Parquet.

    Se gold_path não fornecido, constrói a tabela chamando
    construir_tabela_integrada() com os Silver files e grava em data/gold/.

    TODAS as linhas do Gold entram (uma por linha de sigcon_chave_siconv): UO
    excluída vai para fl_uo_excluida, linha sem datas para limpeza_g, e
    convênio sem SIAFI fica com siafi_uo nulo. As consultas filtram.

    Parâmetros
    ----------
    gold_path : caminho explícito para o Parquet Gold convenios_integrado.
                Se None, tenta data/gold/convenios_integrado.parquet;
                se não existir, constrói do zero. (O comando
                carregar_relacionamento remove o Gold antigo antes, para
                sempre reconstruir.)
    """
    from core.gold.relacionamento import construir_tabela_integrada, gravar_tabela_integrada

    caminho_gold = gold_path or (Path(settings.DATA_DIR) / "gold" / "convenios_integrado.parquet")

    if caminho_gold.exists():
        logger.info("Lendo Gold Parquet: %s", caminho_gold)
        df = pd.read_parquet(caminho_gold)
    else:
        logger.info("Gold Parquet não encontrado — construindo a partir dos Silver files...")
        df_chaves = _ler_parquet(_silver_path("sigcon_chave_siconv"))
        df_depara = _ler_parquet(_silver_path("depara_siafi"))
        df_conv = _ler_parquet(_silver_path("sigcon_convenio"))
        df_cod = _ler_parquet(_silver_path("sigcon_chave_convenio"))
        df_geral = _ler_parquet(_silver_path("sigcon_convenio_geral"))
        df_plano = _ler_parquet(_silver_path("sigcon_plano_trabalho"))
        df_esfera = _ler_parquet(_silver_path("sigcon_concedente"))

        # siconv_convenio é opcional
        siconv_p = _silver_path("siconv_convenio")
        df_siconv = pd.read_parquet(siconv_p) if siconv_p.exists() else None

        df = construir_tabela_integrada(
            df_chaves, df_depara, df_conv, df_cod, df_geral, df_plano, df_esfera,
            df_siconv=df_siconv,
        )
        gravar_tabela_integrada(df)

    logger.info("Construindo objetos ConvenioIntegrado: %d linhas", len(df))

    def _g(col):
        return row.get(col) if col in df.columns else None

    objetos = []
    for _, row in df.iterrows():
        objetos.append(ConvenioIntegrado(
            # bridge / chaves
            siafi_uo=_para_str(row["siafi_uo"]),  # nulo = convênio sem SIAFI
            siafi_uo_atual=_para_str(_g("siafi_uo_atual")),
            convenio_numero_sequencial_siafi=_para_str(_g("convenio_numero_sequencial_siafi")),
            unidade_orcamentaria_codigo=_para_str(_g("unidade_orcamentaria_codigo")),
            siafiatual=_para_str(_g("siafiatual")),
            uo_atual=_para_str(_g("uo_atual")),
            codigo_siconv=_para_str(_g("codigo_siconv")),
            # de-paras
            instrumento_chaves=_para_str(_g("instrumento_chaves")),
            situacao=_para_str(_g("situacao")),
            situacao_std=_para_str(_g("situacao_std")),
            uo_nome_std=_para_str(_g("uo_nome_std")),
            uo_sigla_std=_para_str(_g("uo_sigla_std")),
            uo_descricao_std=_para_str(_g("uo_descricao_std")),
            # G_ datas
            g_dia_assinatura=_str_para_date(_g("g_dia_assinatura")),
            g_inicio_vigencia=_str_para_date(_g("g_inicio_vigencia")),
            g_fim_vigencia=_str_para_date(_g("g_fim_vigencia")),
            g_fim_vigencia_inicial=_str_para_date(_g("g_fim_vigencia_inicial")),
            # G_ anos
            g_ano_assinatura=_para_int(_g("g_ano_assinatura")),
            g_ano_inicio_vigencia=_para_int(_g("g_ano_inicio_vigencia")),
            g_ano_convenio=_para_int(_g("g_ano_convenio")),
            # G_ texto
            g_situacao_convenio=_para_str(_g("g_situacao_convenio")),
            g_objeto_convenio=_para_str(_g("g_objeto_convenio")),
            g_proponente=_para_str(_g("g_proponente")),
            g_concedente=_para_str(_g("g_concedente")),
            g_instrumento=_para_str(_g("g_instrumento")),
            g_esfera=_para_str(_g("g_esfera")),
            g_uo=_para_str(_g("g_uo")),
            g_vigencia=_para_str(_g("g_vigencia")),
            g_situacao_convenio_categorizado=_para_str(_g("g_situacao_convenio_categorizado")),
            g_concedente_pad=_para_str(_g("g_concedente_pad")),
            g_proponente_pad=_para_str(_g("g_proponente_pad")),
            g_proponente_pad_siglas=_para_str(_g("g_proponente_pad_siglas")),
            g_uo_descricao=_para_str(_g("g_uo_descricao")),
            # G_ valores
            g_valor_concedente=_para_decimal(_g("g_valor_concedente")),
            g_valor_proponente=_para_decimal(_g("g_valor_proponente")),
            g_valor_global=_para_decimal(_g("g_valor_global")),
            # G_ flags
            g_periodo_nao_aditado=_para_int(_g("g_periodo_nao_aditado")),
            g_valor_nao_aditado=_para_int(_g("g_valor_nao_aditado")),
            limpeza_g=_para_int(_g("limpeza_g")),
            fl_uo_excluida=bool(_g("fl_uo_excluida")),
            # A_ datas
            a_dia_assinatura=_str_para_date(_g("a_dia_assinatura")),
            a_inicio_vigencia=_str_para_date(_g("a_inicio_vigencia")),
            a_fim_vigencia=_str_para_date(_g("a_fim_vigencia")),
            a_fim_vigencia_inicial=_str_para_date(_g("a_fim_vigencia_inicial")),
            # A_ anos
            a_ano_assinatura=_para_int(_g("a_ano_assinatura")),
            a_ano_inicio_vigencia=_para_int(_g("a_ano_inicio_vigencia")),
            a_ano_convenio=_para_int(_g("a_ano_convenio")),
            # A_ texto
            a_situacao_convenio=_para_str(_g("a_situacao_convenio")),
            a_objeto_convenio=_para_str(_g("a_objeto_convenio")),
            a_proponente=_para_str(_g("a_proponente")),
            a_concedente=_para_str(_g("a_concedente")),
            a_instrumento=_para_str(_g("a_instrumento")),
            a_esfera=_para_str(_g("a_esfera")),
            a_vigencia=_para_str(_g("a_vigencia")),
            a_situacao_convenio_categorizado=_para_str(_g("a_situacao_convenio_categorizado")),
            a_concedente_pad=_para_str(_g("a_concedente_pad")),
            a_proponente_pad=_para_str(_g("a_proponente_pad")),
            a_proponente_pad_siglas=_para_str(_g("a_proponente_pad_siglas")),
            # A_ valores
            a_valor_concedente=_para_decimal(_g("a_valor_concedente")),
            a_valor_proponente=_para_decimal(_g("a_valor_proponente")),
            a_valor_global=_para_decimal(_g("a_valor_global")),
            # A_ flags
            a_periodo_nao_aditado=_para_int(_g("a_periodo_nao_aditado")),
            a_valor_nao_aditado=_para_int(_g("a_valor_nao_aditado")),
        ))

    return _bulk_refresh(ConvenioIntegrado, objetos)


def carregar_unidades_executoras(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_unidade_executora.parquet → model UnidadesExecutoras."""
    caminho = silver_path or _silver_path("sigcon_unidade_executora")
    df = _ler_parquet(caminho)

    objetos = [
        UnidadesExecutoras(
            unidade_orcamentaria_codigo=_para_str(row["cd_uo"]),
            convenio_numero_sequencial_siafi=_para_str(row["nr_siafi"]),
            unidade_executora=_para_str(row["cd_unidade_executora"]),
            convenio_codigo=_para_str(row["nr_convenio"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(UnidadesExecutoras, objetos)


def carregar_controle_sei(silver_path: Path | None = None) -> dict:
    """
    Full refresh do model ControleSEI a partir do Silver controle_sei.parquet.

    TODAS as linhas entram (hoje 2.834). Antes a carga mantinha só o 1º SEI por
    SIAFI e apagava 334 linhas (326 sem SIAFI + 8 SIAFIs com 2 processos). A
    escolha de "um SEI por SIAFI" para a aba Convênios agora é feita na
    consulta (apps/sigcon/services.py::enrich_convenios_page), não na carga.

    Mapeamento de colunas (Parquet → model):
      nr_sei             → no_sei
      nr_siafi           → no_siafi_sigcon
      nr_proposta_siconv → no_proposta_siconv
    """
    caminho = silver_path or _silver_path("controle_sei")
    df = _ler_parquet(caminho)

    objetos = [
        ControleSEI(
            no_sei=_para_str(row["nr_sei"]),
            no_siafi_sigcon=_para_str(row["nr_siafi"]),
            no_proposta_siconv=_para_str(row["nr_proposta_siconv"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(ControleSEI, objetos)
