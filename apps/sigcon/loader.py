"""
Loaders full-refresh das tabelas do SIGCON.

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
    SigconChaveConvenio,
    SigconChaveDeclaracao,
    SigconChavePlanoTrabalho,
    SigconChaveTermoAditivo,
    SigconConcedente,
    SigconConvenio,
    SigconConvenioGeral,
    SigconCronogramaDesembolso,
    SigconDeclaracaoContrapartida,
    SigconNtEmenda,
    SigconPlanoAplicacao,
    SigconPlanoTrabalho,
    SigconProrrogacaoOficio,
    SigconTabelaUo,
    SigconTermoAditivo,
    SigconUnidadeExecutora,
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

# ---------------------------------------------------------------------------
# Gold — ConvenioIntegrado (tabela G_/A_ completa)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Loader genérico para todas as tabelas do SIGCON
# ---------------------------------------------------------------------------


def carregar_tabela_generica(nome_fonte: str, model) -> dict:
    """
    Carrega uma tabela da silver para o banco, sem de-para manual.
    Funciona porque as colunas do parquet têm os mesmos nomes dos campos do model.

    Args:
        nome_fonte: nome da fonte (ex.: "sigcon_convenio")
        model: classe do model Django (ex.: SigconConvenio)

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


# ---------------------------------------------------------------------------
# Partial loaders para conveniência (apps/grp/loader.py usa partial para cada tabela)
carregar_sigcon_convenio = partial(
    carregar_tabela_generica, "sigcon_convenio", SigconConvenio
)
carregar_sigcon_convenio_geral = partial(
    carregar_tabela_generica, "sigcon_convenio_geral", SigconConvenioGeral
)
carregar_sigcon_plano_trabalho = partial(
    carregar_tabela_generica, "sigcon_plano_trabalho", SigconPlanoTrabalho
)
carregar_sigcon_termo_aditivo = partial(
    carregar_tabela_generica, "sigcon_termo_aditivo", SigconTermoAditivo
)
carregar_sigcon_prorrogacao_oficio = partial(
    carregar_tabela_generica, "sigcon_prorrogacao_oficio", SigconProrrogacaoOficio
)
carregar_sigcon_declaracao_contrapartida = partial(
    carregar_tabela_generica, "sigcon_declaracao_contrapartida", SigconDeclaracaoContrapartida
)
carregar_sigcon_cronograma_desembolso = partial(
    carregar_tabela_generica, "sigcon_cronograma_desembolso", SigconCronogramaDesembolso
)
carregar_sigcon_plano_aplicacao = partial(
    carregar_tabela_generica, "sigcon_plano_aplicacao", SigconPlanoAplicacao
)   
carregar_sigcon_unidade_executora = partial(
    carregar_tabela_generica, "sigcon_unidade_executora", SigconUnidadeExecutora
)
carregar_sigcon_nt_emenda = partial(
    carregar_tabela_generica, "sigcon_nt_emenda", SigconNtEmenda
)
carregar_sigcon_chave_convenio = partial(
    carregar_tabela_generica, "sigcon_chave_convenio", SigconChaveConvenio
)
carregar_sigcon_chave_termo_aditivo = partial(
    carregar_tabela_generica, "sigcon_chave_termo_aditivo", SigconChaveTermoAditivo
)
carregar_sigcon_chave_plano_trabalho = partial(
    carregar_tabela_generica, "sigcon_chave_plano_trabalho", SigconChavePlanoTrabalho
)
carregar_sigcon_chave_declaracao = partial(
    carregar_tabela_generica, "sigcon_chave_declaracao", SigconChaveDeclaracao
)
carregar_sigcon_concedente = partial(
    carregar_tabela_generica, "sigcon_concedente", SigconConcedente
)
carregar_sigcon_tabela_uo = partial(
    carregar_tabela_generica, "sigcon_tabela_uo", SigconTabelaUo
)