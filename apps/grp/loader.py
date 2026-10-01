"""
Loaders full-refresh das tabelas do GRP.

Cada funcao le o Parquet Silver da fonte e substitui a tabela inteira via
core.db.bulk_refresh — delete e insert na mesma transacao.

Os helpers de conversao sao os mesmos do loader do SIGCON, repetidos aqui em
vez de importados: apps de aba nao importam uns dos outros. Se um terceiro app
precisar deles, o lugar e core/.
"""

import logging
from decimal import Decimal
from pathlib import Path

import pandas as pd
from django.conf import settings

from core.db import bulk_refresh as _bulk_refresh

from functools import partial

from .models import (
    CronogramaDesembolsoGrp,
    DadosGrp,
    EsferaGrp,
    PlanoAplicacaoGrp,
    PlanoAplicacaoGrpDetalhes,
    RecursosConcedenteGrp,
    RecursosContrapartidaGrp,
    TabelaUoGrp,
    GrpInstrumento,
)

logger = logging.getLogger(__name__)


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


def carregar_dados_grp(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_dados_grp.parquet → model DadosGrp."""
    caminho = silver_path or _silver_path("dcgce_dados_grp")
    df = _ler_parquet(caminho)

    objetos = [
        DadosGrp(
            nr_grp=_para_str(row["numero_instrumentogrp"]),
            nr_instrumento=_para_str(row["numero_instrumento"]),
            uo_cod=_para_str(row["unidadeorcam_-_codigo"]),
            concedente_cnpj=_para_str(row["concedente_-_cnpj-capj"]),
            convenente_cnpj=_para_str(row["convenenteinstrumento_-_cnpj-capj"]),
            situacao=_para_str(row["situacao_instrumento"]),
            dt_vigencia_inicial=_para_date(row["data_vigencia_instrumento_-_inicio"]),
            dt_vigencia_termino=_para_date(row["data_vigencia_instrumento_-_termino"]),
            dt_vigenciainicial_termino=_para_date(row["data_vigenciainicial_instrumento_-_termino"]),
            vl_instrumento_concedente_inicial=_para_decimal(row["valor_instrumento_-_concedente_inicial"]),
            vl_instrumento_concedente=_para_decimal(row["valor_instrumento_-_concedente"]),
            vl_instrumento_contrapartida_fin_inicial=_para_decimal(row["valor_instrumento_-_contrapartida_financeira_inicial"]),
            vl_instrumento_contrapartida_fin=_para_decimal(row["valor_instrumento_-_contrapartida_financeira"]),
            vl_instrumento_total=_para_decimal(row["valor_instrumento_-_total"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(DadosGrp, objetos)

def carregar_cronograma_desembolso_grp(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_cronograma_desembolso_grp.parquet → model CronogramaDesembolsoGrp."""
    caminho = silver_path or _silver_path("dcgce_cronograma_desembolso_grp")
    df = _ler_parquet(caminho)

    objetos = [
        CronogramaDesembolsoGrp(
            nr_grp=_para_str(row["numero_instrumentogrp"]),
            parcela_desembolso=_para_str(row["parcela_desembolso"]),
            mes_desembolso=_para_str(row["desembolso_-_mes"]),
            ano_desembolso=_para_str(row["desembolso_-_ano"]),
            origem_recurso_parcela=_para_str(row["origem_recurso_parcela"]),
            vl_desembolso=_para_decimal(row["valor_desembolso"])
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(CronogramaDesembolsoGrp, objetos)
def carregar_recurso_contrapartida_grp(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_recurso_contrapartida_grp.parquet → model RecursoContrapartidaGrp."""
    caminho = silver_path or _silver_path("dcgce_recursos_contrapartida_grp")
    df = _ler_parquet(caminho)

    objetos = [
        RecursosContrapartidaGrp(
            uo_cod=_para_str(row["unidorcamentaria_financiadora_-_codigo"]),
            fonte=_para_str(row["fonterecurso_-_codigo"]),
            nr_grp=_para_str(row["numero_instrumentogrp"]),
            ipu=_para_str(row["ipu_-_codigo"]),
            vl_contrapartida_financeira=_para_decimal(row["valor_contrapartida_financeira"])
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(RecursosContrapartidaGrp, objetos)

def carregar_recurso_concedente_grp(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_recurso_concedente_grp.parquet → model RecursoConcedenteGrp."""
    caminho = silver_path or _silver_path("dcgce_recursos_concedente_grp")
    df = _ler_parquet(caminho)

    objetos = [
        RecursosConcedenteGrp(
            uo_cod=_para_str(row["unidorcamentaria_arrecadacao_-_codigo"]),
            nr_grp=_para_str(row["numero_instrumentogrp"]),
            fonte=_para_str(row["fonterecurso_-_codigo"]),
            ipu=_para_str(row["ipu_-_codigo"]),
            vl_concedente=_para_decimal(row["valor_recurso_concedente"])
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(RecursosConcedenteGrp, objetos)

def carregar_plano_aplicacao_grp(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_plano_aplicacao_grp.parquet → model PlanoAplicacaoGrp."""
    caminho = silver_path or _silver_path("dcgce_plano_aplicacao_grp")
    df = _ler_parquet(caminho)

    objetos = [
        PlanoAplicacaoGrp(
            nr_grp=_para_str(row["numero_instrumentogrp"]),
            nome_projeto=_para_str(row["nome_projeto"]),
            objeto_projeto=_para_str(row["objeto_projeto"]),
            situacao_instrumento=_para_str(row["situacao_instrumento"]),
            tipo_instrumento=_para_str(row["tipo_proposta/instrumento"]),
            responsavel_nome=_para_str(row["responsavel_-_nome"]),
            responsavel_atribuicao=_para_str(row["responsavel_-_atribuicao"]),
            cnpj_convenente=_para_str(row["convenenteinstrumento_-_cnpj-capj"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(PlanoAplicacaoGrp, objetos)

def carregar_plano_aplicacao_grp_detalhes(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_plano_aplicacao_grp_detalhes.parquet → model PlanoAplicacaoGrpDetalhes."""
    caminho = silver_path or _silver_path("dcgce_plano_aplicacao_grp_detalhes")
    df = _ler_parquet(caminho)

    objetos = [
        PlanoAplicacaoGrpDetalhes(
            nr_catmas=_para_str(row["numero_catmas"]),
            nr_grp=_para_str(row["numero_instrumentogrp"]),
            tipo_despesa=_para_str(row["tipo_despesa_aexecutar"]),
            categoria_despesa=_para_str(row["categoriaeconomica_-_codigo"]),
            grupo_despesa=_para_str(row["grupodespesa_-_codigo"]),
            modalidade=_para_str(row["modalidade_-_codigo"]),
            elemento_despesa=_para_str(row["elementodespesa_-_codigo"]),
            beneficiario_cnpj=_para_str(row["beneficiario_-_cnpj-capj"]),
            descricao_item=_para_str(row["descricao_item_aexecutar"]),
            origem_recurso=_para_str(row["origem_recurso"]),
            qt_item_executar=_para_decimal(row["quantidade_item_aexecutar"]),
            vl_uni_item_a_executar=_para_decimal(row["valor_unitario_item_aexecutar"]),
            vl_total_item_a_executar=_para_decimal(row["valor_total_item_aexecutar"]),
            situacao_item_a_executar=_para_str(row["situacao_item_aexecutar"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(PlanoAplicacaoGrpDetalhes, objetos)

def carregar_esfera_grp(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_esfera_grp.parquet → model EsferaGrp."""
    caminho = silver_path or _silver_path("dcgce_esfera_grp")
    df = _ler_parquet(caminho)

    objetos = [
        EsferaGrp(
            concedente_nome=_para_str(row["concedente_-_nome"]),
            concedente_cnpj=_para_str(row["concedente_-_cnpj-capj"]),
            concedente_esfera=_para_str(row["concedente_-_esferaatuacao"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(EsferaGrp, objetos)

def carregar_tabela_uo_grp(silver_path: Path | None = None) -> dict:
    """Fonte: dcgce_tabela_uo_grp.xlsx → model EsferaGrp."""
    caminho = silver_path or _silver_path("dcgce_tabela_uo_grp")
    df = _ler_parquet(caminho)

    objetos = [
        TabelaUoGrp(
            uo_cod=_para_str(row["unidadeorcam_-_codigo"]),
            uo_nome=_para_str(row["unidadeorcam_-_nome"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(TabelaUoGrp, objetos)

# ---------------------------------------------------------------------------
# Gold — ConvenioIntegrado (tabela G_/A_ completa)
# ---------------------------------------------------------------------------


#---------------------------------------------------------------------------
# Loader genérico para todas as tabelas do GRP
#---------------------------------------------------------------------------

def carregar_tabela_generica(nome_fonte: str, model) -> dict:
    """
    Carrega uma tabela da silver para o banco, sem de-para manual.
    Funciona porque as colunas do parquet têm os mesmos nomes dos campos do model.

    Args:
        nome_fonte: nome da fonte (ex.: "grp_instrumento")
        model: classe do model Django (ex.: GrpInstrumento)

    Returns:
        dicionário com a quantidade de linhas inseridas e outras informações
    """
    # 1. montar o caminho do parquet a partir do nome da fonte e ler
    caminho = _silver_path(nome_fonte)

    df = _ler_parquet(caminho)
    colunas_parquet = set(df.columns)
    campos_model = {
        field.name for field in model._meta.concrete_fields 
        if field.name != "id"}
    
    # 2. conferir: colunas do parquet == campos do model (sem o "id")
    sobra_parquet = colunas_parquet - campos_model
    sobra_model = campos_model - colunas_parquet

    if sobra_parquet or sobra_model:
        raise ValueError(
            "Colunas do parquet e campos do model não batem:\n"
            f"  no parquet mas não no model: {sobra_parquet}\n"
            f"  no model mas não no parquet: {sobra_model}"
        )
    
    # 3. trocar os nulos do pandas por None
    df = df.astype(object).where(pd.notna(df), None)

    # 4. transformar cada linha num objeto do model
    df_lista = df.to_dict("records")
    
    objetos = [model(**row) for row in df_lista]

    # 5. apagar o conteúdo atual e inserir os objetos (full refresh, numa transação) e devolver a quantidade inserida
    return _bulk_refresh(model, objetos)


carregar_grp_instrumento = partial(carregar_tabela_generica, "grp_instrumento", GrpInstrumento)