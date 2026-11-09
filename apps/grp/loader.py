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
    GrpInstrumento,
    GrpConcedente,
    GrpPrestacaoContas,
    GrpPlanejamentoObras,
    GrpPropostaMarcoLogico,
    GrpEmenda,
    GrpInterveniente,
    GrpUnidadeExecutora,
    GrpMunicipioAtendido,
    GrpRegiaoAtendida,
    GrpRecursoConcedente,
    GrpRecursoContrapartida,
    GrpDotacaoContrapartida,
    GrpAcaoOrcamentaria,
    GrpInstrumentoFinanciado,
    GrpItemExecutar,
    GrpCronogramaDesembolso,
    GrpCronogramaFisico,
    GrpEntregaProjeto,
    GrpAtividadeProjeto,
    GrpMatrizResponsabilidade,
    GrpTabelaUo,
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


# ---------------------------------------------------------------------------
# Gold — ConvenioIntegrado (tabela G_/A_ completa)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Loader genérico para todas as tabelas do GRP
# ---------------------------------------------------------------------------


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
        field.name for field in model._meta.concrete_fields if field.name != "id"
    }

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


carregar_grp_instrumento = partial(
    carregar_tabela_generica, "grp_instrumento", GrpInstrumento
)
carregar_grp_concedente = partial(
    carregar_tabela_generica, "grp_concedente", GrpConcedente
)
carregar_grp_prestacao_contas = partial(
    carregar_tabela_generica, "grp_prestacao_contas", GrpPrestacaoContas
)
carregar_grp_planejamento_obras = partial(
    carregar_tabela_generica, "grp_planejamento_obras", GrpPlanejamentoObras
)
carregar_grp_proposta_marco_logico = partial(
    carregar_tabela_generica, "grp_proposta_marco_logico", GrpPropostaMarcoLogico
)
carregar_grp_emenda = partial(carregar_tabela_generica, "grp_emenda", GrpEmenda)
carregar_grp_interveniente = partial(
    carregar_tabela_generica, "grp_interveniente", GrpInterveniente
)
carregar_grp_unidade_executora = partial(
    carregar_tabela_generica, "grp_unidade_executora", GrpUnidadeExecutora
)
carregar_grp_municipio_atendido = partial(
    carregar_tabela_generica, "grp_municipio_atendido", GrpMunicipioAtendido
)
carregar_grp_regiao_atendida = partial(
    carregar_tabela_generica, "grp_regiao_atendida", GrpRegiaoAtendida
)
carregar_grp_recurso_concedente = partial(
    carregar_tabela_generica, "grp_recurso_concedente", GrpRecursoConcedente
)
carregar_grp_recurso_contrapartida = partial(
    carregar_tabela_generica, "grp_recurso_contrapartida", GrpRecursoContrapartida
)
carregar_grp_dotacao_contrapartida = partial(
    carregar_tabela_generica, "grp_dotacao_contrapartida", GrpDotacaoContrapartida
)
carregar_grp_acao_orcamentaria = partial(
    carregar_tabela_generica, "grp_acao_orcamentaria", GrpAcaoOrcamentaria
)
carregar_grp_instrumento_financiado = partial(
    carregar_tabela_generica, "grp_instrumento_financiado", GrpInstrumentoFinanciado
)
carregar_grp_item_executar = partial(
    carregar_tabela_generica, "grp_item_executar", GrpItemExecutar
)
carregar_grp_cronograma_desembolso = partial(
    carregar_tabela_generica, "grp_cronograma_desembolso", GrpCronogramaDesembolso
)
carregar_grp_cronograma_fisico = partial(
    carregar_tabela_generica, "grp_cronograma_fisico", GrpCronogramaFisico
)
carregar_grp_entrega_projeto = partial(
    carregar_tabela_generica, "grp_entrega_projeto", GrpEntregaProjeto
)
carregar_grp_atividade_projeto = partial(
    carregar_tabela_generica, "grp_atividade_projeto", GrpAtividadeProjeto
)
carregar_grp_matriz_responsabilidade = partial(
    carregar_tabela_generica, "grp_matriz_responsabilidade", GrpMatrizResponsabilidade
)
carregar_grp_tabela_uo = partial(carregar_tabela_generica, "grp_tabela_uo", GrpTabelaUo)
