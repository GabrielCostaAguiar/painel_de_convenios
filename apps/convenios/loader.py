"""
Loaders full-refresh para os models da app convenios.

Cada função:
  1. Lê o(s) Parquet(s) Silver via pd.read_parquet
  2. Apaga todos os registros existentes no model
  3. Reconstrói via bulk_create(batch_size=500)
  4. Retorna dict com 'apagados' e 'inseridos'

Funções do piloto (Convenio consolidado + Cronograma com SIAFI):
  carregar_convenios()          — full-refresh do Convenio consolidado
  carregar_cronograma_desembolso() — full-refresh do CronogramaDesembolso com SIAFI

As demais funções carregam os outros models da app (PlanoTrabalho, TermoAditivo, etc.)
e ainda usam os Silver dos nomes antigos (dcgce_plano.trabalho.parquet, etc.) enquanto
não forem re-ingeridos com os novos nomes.
"""
import logging
from decimal import Decimal
from pathlib import Path

import pandas as pd
from django.conf import settings

from .models import (
    CodigoConvenio,
    CodigoDeclaracaoContrapartida,
    CodigoPlanoTrabalho,
    CodigoTermoAditivo,
    Convenio,
    ConvenioGeral,
    ConvenioIntegrado,
    CronogramaDesembolso,
    DeclaracaoContrapartida,
    Esfera,
    NtEmenda,
    PlanoAplicacao,
    PlanoTrabalho,
    ProrrogacaoOficio,
    TermoAditivo,
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


def _ler_parquet(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Parquet Silver não encontrado: {caminho}\n"
            "Rode antes: python manage.py rodar_silver <fonte>"
        )
    df = pd.read_parquet(caminho)
    logger.info("Parquet lido: %s (%d linhas × %d colunas)", caminho.name, *df.shape)
    return df


def _bulk_refresh(model, objetos: list) -> dict:
    apagados, _ = model.objects.all().delete()
    model.objects.bulk_create(objetos, batch_size=500)
    logger.info("%s: %d apagados, %d inseridos", model.__name__, apagados, len(objetos))
    return {"apagados": apagados, "inseridos": len(objetos)}


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

    Fontes lidas (na ordem dos joins):
      dcgce_convenio         — chave SIAFI+UO, situação, datas vigência, valores
      dcgce_codigo_convenio  — ponte: convenio_codigo_sequencial → UO (enriquece Geral)
      dcgce_geral            — data publicação, assinatura, plano_trabalho_codigo
      dcgce_plano_trabalho   — título, objeto, concedente, CNPJs, instrumento
      dcgce_esfera           — esfera via CNPJ concedente

    Joins:
      Geral+UO:    geral.convenio_codigo_sequencial = cod_conv.convenio_codigo_sequencial
      Conv+Geral:  (conv.siafi, conv.uo) = (geral_enriquecido.siafi, geral_enriquecido.uo)
      +Plano:      merged.plano_trabalho_codigo = plano.plano_trabalho_codigo
      +Esfera:     merged.cnpj_concedente = esfera.concedente_cnpj
    """
    conv = _ler_parquet(silver_path or _silver_path("dcgce_convenio"))
    cod_conv = _ler_parquet(_silver_path("dcgce_codigo_convenio"))
    geral = _ler_parquet(_silver_path("dcgce_geral"))
    plano = _ler_parquet(_silver_path("dcgce_plano_trabalho"))
    esfera = _ler_parquet(_silver_path("dcgce_esfera"))

    # Normaliza todas as chaves de join
    _normalizar_chave(conv, ["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"])
    _normalizar_chave(cod_conv, [
        "convenio_codigo_sequencial", "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
    ])
    _normalizar_chave(geral, [
        "convenio_numero_sequencial_siafi", "convenio_codigo_sequencial", "conveno_codigo_plano_trabalho",
    ])
    _normalizar_chave(plano, ["plano_trabalho_codigo", "plano_trabalho_cnpj_concedente"])
    _normalizar_chave(esfera, ["concedente_cnpj"])

    # Step 1: enriquecer Geral com UO (via convenio_codigo_sequencial → cod_conv)
    cod_conv_uo = (
        cod_conv[["convenio_codigo_sequencial", "unidade_orcamentaria_codigo"]]
        .drop_duplicates("convenio_codigo_sequencial")
    )
    geral = geral.merge(cod_conv_uo, on="convenio_codigo_sequencial", how="left")
    # renomeia coluna com typo para nome canônico
    geral = geral.rename(columns={"conveno_codigo_plano_trabalho": "plano_trabalho_codigo"})
    _normalizar_chave(geral, ["unidade_orcamentaria_codigo"])

    # Step 2: merge Convenio + Geral pela chave composta SIAFI+UO
    geral_sub = (
        geral[[
            "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
            "plano_trabalho_codigo",
            "convenio_data_de_publicacao", "convenio_data_assinatura_convenio", "convenio_ano",
        ]]
        .drop_duplicates(["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"])
    )
    merged = conv.merge(
        geral_sub,
        on=["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"],
        how="left",
    )

    n_sem_plano = int(merged["plano_trabalho_codigo"].isna().sum())
    logger.info(
        "Conv+Geral: %d registros, %d sem plano_trabalho_codigo (%.1f%%)",
        len(merged), n_sem_plano, 100 * n_sem_plano / max(len(merged), 1),
    )

    # Step 3: merge + PlanoTrabalho
    plano_sub = (
        plano[[
            "plano_trabalho_codigo", "plano_trabalho_titulo", "plano_trabalho_objeto",
            "plano_trabalho_razao_social_concedente", "plano_trabalho_cnpj_concedente",
            "plano_trabalho_cnpj_proponente", "plano_trabalho_tipo_siafi",
        ]]
        .drop_duplicates("plano_trabalho_codigo")
    )
    merged = merged.merge(plano_sub, on="plano_trabalho_codigo", how="left")

    # Step 4: merge + Esfera via CNPJ concedente
    esfera_sub = esfera[["concedente_cnpj", "concedente_esfera"]].drop_duplicates("concedente_cnpj")
    merged = merged.merge(
        esfera_sub,
        left_on="plano_trabalho_cnpj_concedente",
        right_on="concedente_cnpj",
        how="left",
    )

    n_sem_esfera = int(merged["concedente_esfera"].isna().sum())
    logger.info(
        "Conv+Esfera: %d sem esfera (%.1f%%)",
        n_sem_esfera, 100 * n_sem_esfera / max(len(merged), 1),
    )

    objetos = [
        Convenio(
            convenio_codigo=_para_str(row["convenio_codigo"]) or "",
            convenio_numero_sequencial_siafi=_para_str(row["convenio_numero_sequencial_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["unidade_orcamentaria_codigo"]),
            situacao=_para_str(row["situacao"]),
            data_inicio_vigencia=_para_date(row["data_inicio_vigencia"]),
            data_termino_vigencia=_para_date(row["data_termino_vigencia"]),
            data_real_convenio=_para_date(row["data_real_convenio"]),
            valor_inicial_concedente_contratado=_para_decimal(row["valor_inicial_concedente_contratado"]),
            valor_total_aditado_concedente_contratado=_para_decimal(row["valor_total_aditado_concedente_contratado"]),
            valor_concedente=_para_decimal(row["valor_concedente"]),
            valor_inicial_proponente_contratado=_para_decimal(row["valor_inicial_proponente_contratado"]),
            valor_total_aditado_proponente_contratado=_para_decimal(row["valor_total_aditado_proponente_contratado"]),
            valor_proponente=_para_decimal(row["valor_proponente"]),
            valor_total_convenio=_para_decimal(row["valor_total_convenio"]),
            # de Geral
            plano_trabalho_codigo=_para_str(row.get("plano_trabalho_codigo")),
            data_publicacao=_para_date(row.get("convenio_data_de_publicacao")),
            data_assinatura=_para_date(row.get("convenio_data_assinatura_convenio")),
            convenio_ano=_para_str(row.get("convenio_ano")),
            # de PlanoTrabalho
            instrumento=_para_str(row.get("plano_trabalho_tipo_siafi")),
            titulo=_para_str(row.get("plano_trabalho_titulo")),
            objeto=_para_str(row.get("plano_trabalho_objeto")),
            concedente=_para_str(row.get("plano_trabalho_razao_social_concedente")),
            cnpj_concedente=_para_str(row.get("plano_trabalho_cnpj_concedente")),
            cnpj_proponente=_para_str(row.get("plano_trabalho_cnpj_proponente")),
            # de Esfera
            esfera=_para_str(row.get("concedente_esfera")),
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

    Rota do join:
      cronograma.plano_trabalho_codigo
        = geral.conveno_codigo_plano_trabalho  (campo com typo na fonte)
        → geral.convenio_codigo_sequencial
        → cod_conv.convenio_codigo_sequencial
        → cod_conv.(convenio_numero_sequencial_siafi, unidade_orcamentaria_codigo)
    """
    crono = _ler_parquet(silver_path or _silver_path("dcgce_cronograma_desembolso"))
    geral = _ler_parquet(_silver_path("dcgce_geral"))
    cod_conv = _ler_parquet(_silver_path("dcgce_codigo_convenio"))

    _normalizar_chave(crono, ["plano_trabalho_codigo"])
    _normalizar_chave(geral, ["conveno_codigo_plano_trabalho", "convenio_codigo_sequencial"])
    _normalizar_chave(cod_conv, [
        "convenio_codigo_sequencial", "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
    ])

    # Step 1: cronograma → Geral (plano_trabalho_codigo = conveno_codigo_plano_trabalho)
    geral_plano = (
        geral[["conveno_codigo_plano_trabalho", "convenio_codigo_sequencial"]]
        .drop_duplicates("conveno_codigo_plano_trabalho")
    )
    crono_enrich = crono.merge(
        geral_plano,
        left_on="plano_trabalho_codigo",
        right_on="conveno_codigo_plano_trabalho",
        how="left",
    )

    # Step 2: → CodigoConvenio (convenio_codigo_sequencial → SIAFI+UO)
    cod_conv_sub = (
        cod_conv[[
            "convenio_codigo_sequencial",
            "convenio_numero_sequencial_siafi",
            "unidade_orcamentaria_codigo",
        ]]
        .drop_duplicates("convenio_codigo_sequencial")
    )
    crono_enrich = crono_enrich.merge(cod_conv_sub, on="convenio_codigo_sequencial", how="left")

    n_total = len(crono_enrich)
    n_com_siafi = int(crono_enrich["convenio_numero_sequencial_siafi"].notna().sum())
    n_sem_siafi = n_total - n_com_siafi
    logger.info(
        "Cronograma: %d total | com SIAFI: %d (%.1f%%) | sem SIAFI: %d (%.1f%%)",
        n_total,
        n_com_siafi, 100 * n_com_siafi / max(n_total, 1),
        n_sem_siafi, 100 * n_sem_siafi / max(n_total, 1),
    )

    objetos = [
        CronogramaDesembolso(
            plano_trabalho_codigo=_para_str(row["plano_trabalho_codigo"]),
            convenio_numero_sequencial_siafi=_para_str(row.get("convenio_numero_sequencial_siafi")),
            unidade_orcamentaria_codigo=_para_str(row.get("unidade_orcamentaria_codigo")),
            valor_concedente_cronograma_desembolso=_para_decimal(row["valor_concedente_cronograma_desembolso"]),
            valor_proponente_cronograma_desembolso=_para_decimal(row["valor_proponente_cronograma_desembolso"]),
            mes_cronograma_desembolso=_para_str(row["mes_cronograma_desembolso"]),
            ano_cronograma_desembolso=_para_str(row["ano_cronograma_desembolso"]),
        )
        for _, row in crono_enrich.iterrows()
    ]
    return _bulk_refresh(CronogramaDesembolso, objetos)


# ---------------------------------------------------------------------------
# Loaders dos demais models
# (ainda referenciam os nomes antigos dos Parquets Silver até re-ingestão)
# ---------------------------------------------------------------------------

def carregar_convenio_geral(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_geral.parquet → model ConvenioGeral."""
    caminho = silver_path or _silver_path("dcgce_geral")
    df = _ler_parquet(caminho)

    objetos = [
        ConvenioGeral(
            convenio_codigo=_para_str(row["convenio_codigo"]),
            convenio_codigo_sequencial=_para_str(row["convenio_codigo_sequencial"]),
            conveno_codigo_plano_trabalho=_para_str(row["conveno_codigo_plano_trabalho"]),
            convenio_numero_sequencial_siafi=_para_str(row["convenio_numero_sequencial_siafi"]),
            convenio_codigo_declaracao=_para_str(row["convenio_codigo_declaracao"]),
            convenio_data_de_publicacao=_para_date(row["convenio_data_de_publicacao"]),
            convenio_data_alteracao_sccg=_para_date(row["convenio_data_alteracao_sccg"]),
            convenio_data_controle_sccg_convenio=_para_date(row["convenio_data_controle_sccg_convenio"]),
            convenio_data_assinatura_convenio=_para_date(row["convenio_data_assinatura_convenio"]),
            convenio_data_de_cadastramento=_para_date(row["convenio_data_de_cadastramento"]),
            convenio_ano=_para_str(row["convenio_ano"]),
            convenio_alteracao=_para_str(row["convenio_alteracao"]),
            convenio_matricula_tecnico_sccg=_para_str(row["convenio_matricula_tecnico_sccg"]),
            convenio_justificativa_da_alteracao=_para_str(row["convenio_justificativa_da_alteracao"]),
            convenio_matricula_gestor=_para_str(row["convenio_matricula_gestor"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(ConvenioGeral, objetos)


def carregar_plano_trabalho(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_plano_trabalho.parquet (ou dcgce_plano.trabalho.parquet legado)."""
    caminho = silver_path or _silver_path("dcgce_plano_trabalho")
    if not caminho.exists():
        caminho = _silver_path("dcgce_plano.trabalho")
    df = _ler_parquet(caminho)

    objetos = [
        PlanoTrabalho(
            plano_trabalho_codigo=_para_str(row["plano_trabalho_codigo"]),
            plano_trabalho_codigo_execucao_no_exercicio=_para_str(row["plano_trabalho_codigo_execucao_no_exercicio"]),
            plano_trabalho_tipo_siafi=_para_str(row["plano_trabalho_tipo_siafi"]),
            plano_trabalho_cnpj_concedente=_para_str(row["plano_trabalho_cnpj_concedente"]),
            plano_trabalho_cnpj_proponente=_para_str(row["plano_trabalho_cnpj_proponente"]),
            plano_trabalho_data_cancelamento_sccg=_para_date(row["plano_trabalho_data_cancelamento_sccg"]),
            plano_trabalho_data_cadastro=_para_date(row["plano_trabalho_data_cadastro"]),
            plano_trabalho_data_envio_sccg=_para_date(row["plano_trabalho_data_envio_sccg"]),
            plano_trabalho_titulo=_para_str(row["plano_trabalho_titulo"]),
            plano_trabalho_objeto=_para_str(row["plano_trabalho_objeto"]),
            plano_trabalho_justificativa=_para_str(row["plano_trabalho_justificativa"]),
            plano_trabalho_status=_para_str(row["plano_trabalho_status"]),
            plano_trabalho_caracteristica=_para_str(row["plano_trabalho_caracteristica"]),
            plano_trabalho_tipo=_para_str(row["plano_trabalho_tipo"]),
            plano_trabalho_migrado_ou_novo=_para_str(row["plano_trabalho_migrado_ou_novo"]),
            plano_trabalho_matricula_sccg_cancelamento=_para_str(row["plano_trabalho_matricula_sccg_cancelamento"]),
            plano_trabalho_justificativa_sccg_cancelamento=_para_str(row["plano_trabalho_justificativa_sccg_cancelamento"]),
            plano_trabalho_cancelamento_sccg=_para_str(row["plano_trabalho_cancelamento_sccg"]),
            plano_trabalho_ano=_para_str(row["plano_trabalho_ano"]),
            plano_trabalho_altera_termo_aditivo=_para_str(row["plano_trabalho_altera_termo_aditivo"]),
            plano_trabalho_razao_social_concedente=_para_str(row["plano_trabalho_razao_social_concedente"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(PlanoTrabalho, objetos)


def carregar_plano_aplicacao(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_plano_aplicacao.parquet → model PlanoAplicacao."""
    caminho = silver_path or _silver_path("dcgce_plano_aplicacao")
    df = _ler_parquet(caminho)

    objetos = [
        PlanoAplicacao(
            codigo_plano_trabalho=_para_str(row["codigo_plano_trabalho"]),
            codigo_unidade_orcamentaria=_para_str(row["codigo_unidade_orcamentaria"]),
            funcao_codigo=_para_str(row["funcao_codigo"]),
            subfuncao_codigo=_para_str(row["subfuncao_codigo"]),
            programa_codigo=_para_str(row["programa_codigo"]),
            identificador_projeto_atividade_codigo=_para_str(row["identificador_projeto_atividade_codigo"]),
            projeto_atividade_codigo=_para_str(row["projeto_atividade_codigo"]),
            subprojeto_subatividade_codigo=_para_str(row["subprojeto_subatividade_codigo"]),
            categoria_economica_despesa_codigo=_para_str(row["categoria_economica_despesa_codigo"]),
            grupo_despesa_codigo=_para_str(row["grupo_despesa_codigo"]),
            modalidade_aplicacao_codigo=_para_str(row["modalidade_aplicacao_codigo"]),
            elemento_despesa_codigo=_para_str(row["elemento_despesa_codigo"]),
            identificador_orcamento_codigo=_para_str(row["identificador_orcamento_codigo"]),
            fonte_recurso_codigo=_para_str(row["fonte_recurso_codigo"]),
            procedencia_codigo=_para_str(row["procedencia_codigo"]),
            funcional_programatica_formatado=_para_str(row["funcional_programatica_formatado"]),
            valor_concedente=_para_decimal(row["valor_concedente"]),
            valor_proponente=_para_decimal(row["valor_proponente"]),
            ano_exercicio_programa_trabalho=_para_str(row["ano_exercicio_programa_trabalho"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(PlanoAplicacao, objetos)


def carregar_termo_aditivo(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_termo_aditivo.parquet (ou dcgce_termo.aditivo.parquet legado)."""
    caminho = silver_path or _silver_path("dcgce_termo_aditivo")
    if not caminho.exists():
        caminho = _silver_path("dcgce_termo.aditivo")
    df = _ler_parquet(caminho)

    objetos = [
        TermoAditivo(
            termo_aditivo_codigo_sequencial=_para_str(row["termo_aditivo_codigo_sequencial"]),
            termo_aditivo_numero_termo_aditivo=_para_str(row["termo_aditivo_numero_termo_aditivo"]),
            termo_aditivo_data_assinatura=_para_date(row["termo_aditivo_data_assinatura"]),
            termo_aditivo_data_inicio_vigencia=_para_date(row["termo_aditivo_data_inicio_vigencia"]),
            termo_aditivo_data_termino_vigencia=_para_date(row["termo_aditivo_data_termino_vigencia"]),
            data_termo_aditivo=_para_date(row["data_termo_aditivo"]),
            valor_aditado_concedente_contratado=_para_decimal(row["valor_aditado_concedente_contratado"]),
            valor_aditado_proponente_contratado=_para_decimal(row["valor_aditado_proponente_contratado"]),
            termo_aditivo_justificativa=_para_str(row["termo_aditivo_justificativa"]),
            termo_aditivo_ano=_para_str(row["termo_aditivo_ano"]),
            termo_aditivo_alteracao=_para_str(row["termo_aditivo_alteracao"]),
            termo_aditivo_tipo=_para_str(row["termo_aditivo_tipo"]),
            tipo_termo_aditivo=_para_str(row["tipo_termo_aditivo"]),
            quantidade_termo_aditivo=_para_str(row["quantidade_termo_aditivo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(TermoAditivo, objetos)


def carregar_declaracao_contrapartida(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_declaracao_contrapartida.parquet → model DeclaracaoContrapartida."""
    caminho = silver_path or _silver_path("dcgce_declaracao_contrapartida")
    df = _ler_parquet(caminho)

    objetos = [
        DeclaracaoContrapartida(
            declaracao_contrapartida_codigo=_para_str(row["declaracao_contrapartida_codigo"]),
            declaracao_contrapartida_codigo_nota_tecnica=_para_str(row["declaracao_contrapartida_codigo_nota_tecnica"]),
            declaracao_contrapartida_codigo_parecer_aprovacao=_para_str(row["declaracao_contrapartida_codigo_parecer_aprovacao"]),
            declaracao_contrapartida_data_completa_emissao=_para_date(row["declaracao_contrapartida_data_completa_emissao"]),
            declaracao_contrapartida_data_emissao=_para_date(row["declaracao_contrapartida_data_emissao"]),
            declaracao_contrapartida_data_completa_parecer_aprovacao=_para_date(row["declaracao_contrapartida_data_completa_parecer_aprovacao"]),
            declaracao_contrapartida_data_parecer_aprovacao=_para_date(row["declaracao_contrapartida_data_parecer_aprovacao"]),
            declaracao_contrapartida_ano=_para_str(row["declaracao_contrapartida_ano"]),
            declaracao_contrapartida_status=_para_str(row["declaracao_contrapartida_status"]),
            declaracao_contrapartida_observacao=_para_str(row["declaracao_contrapartida_observacao"]),
            declaracao_contrapartida_observacao_aprovacao=_para_str(row["declaracao_contrapartida_observacao_aprovacao"]),
            declaracao_contrapartida_matricula_aprovacao=_para_str(row["declaracao_contrapartida_matricula_aprovacao"]),
            declaracao_contrapartida_momento=_para_str(row["declaracao_contrapartida_momento"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(DeclaracaoContrapartida, objetos)


def carregar_prorrogacao_oficio(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_prorrogacao_oficio.parquet → model ProrrogacaoOficio."""
    caminho = silver_path or _silver_path("dcgce_prorrogacao_oficio")
    df = _ler_parquet(caminho)

    objetos = [
        ProrrogacaoOficio(
            prorrogacao_oficio_codigo=_para_str(row["prorrogacao_oficio_codigo"]),
            prorrogacao_oficio_codigo_convenio=_para_str(row["prorrogacao_oficio_codigo_convenio"]),
            prorrogacao_oficio_data_inicio_vigencia=_para_date(row["prorrogacao_oficio_data_inicio_vigencia"]),
            prorrogacao_oficio_data_termino_vigencia=_para_date(row["prorrogacao_oficio_data_termino_vigencia"]),
            prorrogacao_oficio_data_envio=_para_date(row["prorrogacao_oficio_data_envio"]),
            prorrogacao_oficio_data_parecer=_para_date(row["prorrogacao_oficio_data_parecer"]),
            prorrogacao_oficio_data_publicacao=_para_date(row["prorrogacao_oficio_data_publicacao"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(ProrrogacaoOficio, objetos)


def carregar_nt_emenda(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_sigcon_nt_emenda.parquet → model NtEmenda."""
    caminho = silver_path or _silver_path("dcgce_sigcon_nt_emenda")
    df = _ler_parquet(caminho)

    objetos = [
        NtEmenda(
            unidade_orcamentaria_codigo=_para_str(row["unidade_orcamentaria_codigo"]),
            plano_trabalho_codigo=_para_str(row["plano_trabalho_codigo"]),
            nt_emenda_no=_para_str(row["nt_emenda_no"]),
            nt_emenda_nome=_para_str(row["nt_emenda_nome"]),
            nota_tecnica_emenda_parlamentar_federal_situacao=_para_str(row["nota_tecnica_emenda_parlamentar_federal_situacao"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(NtEmenda, objetos)


def carregar_esfera(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_esfera.parquet → model Esfera."""
    caminho = silver_path or _silver_path("dcgce_esfera")
    df = _ler_parquet(caminho)

    objetos = [
        Esfera(
            concedente_cnpj=_para_str(row["concedente_cnpj"]),
            concedente_esfera=_para_str(row["concedente_esfera"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(Esfera, objetos)


def carregar_codigo_convenio(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_codigo_convenio.parquet → model CodigoConvenio."""
    caminho = silver_path or _silver_path("dcgce_codigo_convenio")
    if not caminho.exists():
        caminho = _silver_path("dcgce_Codigo_convenio")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoConvenio(
            convenio_codigo=_para_str(row["convenio_codigo"]),
            convenio_codigo_sequencial=_para_str(row["convenio_codigo_sequencial"]),
            convenio_numero_sequencial_siafi=_para_str(row["convenio_numero_sequencial_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["unidade_orcamentaria_codigo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoConvenio, objetos)


def carregar_codigo_plano_trabalho(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_Codigo_plano_de_trabalho.parquet → model CodigoPlanoTrabalho (legado)."""
    caminho = silver_path or _silver_path("dcgce_Codigo_plano_de_trabalho")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoPlanoTrabalho(
            conveno_codigo_plano_trabalho=_para_str(row["conveno_codigo_plano_trabalho"]),
            convenio_numero_sequencial_siafi=_para_str(row["convenio_numero_sequencial_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["unidade_orcamentaria_codigo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoPlanoTrabalho, objetos)


def carregar_codigo_termo_aditivo(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_codigo_ta.parquet → model CodigoTermoAditivo."""
    caminho = silver_path or _silver_path("dcgce_codigo_ta")
    if not caminho.exists():
        caminho = _silver_path("dcgce_Codigo_ta")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoTermoAditivo(
            convenio_numero_sequencial_siafi=_para_str(row["convenio_numero_sequencial_siafi"]),
            termo_aditivo_codigo_sequencial=_para_str(row["termo_aditivo_codigo_sequencial"]),
            unidade_orcamentaria_codigo=_para_str(row["unidade_orcamentaria_codigo"]),
            plano_trabalho_codigo=_para_str(row["plano_trabalho_codigo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoTermoAditivo, objetos)


def carregar_codigo_declaracao_contrapartida(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_codigo_dec_contrap.parquet → model CodigoDeclaracaoContrapartida."""
    caminho = silver_path or _silver_path("dcgce_codigo_dec_contrap")
    if not caminho.exists():
        caminho = _silver_path("dcgce_Codigo_dec_contrap")
    df = _ler_parquet(caminho)

    objetos = [
        CodigoDeclaracaoContrapartida(
            declaracao_contrapartida_codigo=_para_str(row["declaracao_contrapartida_codigo"]),
            convenio_numero_sequencial_siafi=_para_str(row["convenio_numero_sequencial_siafi"]),
            unidade_orcamentaria_codigo=_para_str(row["unidade_orcamentaria_codigo"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CodigoDeclaracaoContrapartida, objetos)


# ---------------------------------------------------------------------------
# Gold — ConvenioIntegrado (tabela G_/A_ completa)
# ---------------------------------------------------------------------------

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

    Parâmetros
    ----------
    gold_path : caminho explícito para o Parquet Gold convenios_integrado.
                Se None, tenta data/gold/convenios_integrado.parquet;
                se não existir, constrói do zero.
    """
    from core.gold.relacionamento import construir_tabela_integrada, gravar_tabela_integrada

    caminho_gold = gold_path or (Path(settings.DATA_DIR) / "gold" / "convenios_integrado.parquet")

    if caminho_gold.exists():
        logger.info("Lendo Gold Parquet: %s", caminho_gold)
        df = pd.read_parquet(caminho_gold)
    else:
        logger.info("Gold Parquet não encontrado — construindo a partir dos Silver files...")
        df_chaves = _ler_parquet(_silver_path("chaves_convenio"))
        df_siafi2 = _ler_parquet(_silver_path("siafi2"))
        df_conv = _ler_parquet(_silver_path("dcgce_convenio"))
        df_cod = _ler_parquet(_silver_path("dcgce_codigo_convenio"))
        df_geral = _ler_parquet(_silver_path("dcgce_geral"))
        df_plano = _ler_parquet(_silver_path("dcgce_plano_trabalho"))
        df_esfera = _ler_parquet(_silver_path("dcgce_esfera"))

        # siconv_convenio é opcional
        siconv_p = _silver_path("siconv_convenio")
        df_siconv = pd.read_parquet(siconv_p) if siconv_p.exists() else None

        df = construir_tabela_integrada(
            df_chaves, df_siafi2, df_conv, df_cod, df_geral, df_plano, df_esfera,
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
            siafi_uo=_para_str(row["siafi_uo"]) or "",
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
