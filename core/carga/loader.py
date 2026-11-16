"""
Carga genérica Silver (Parquet) → tabela do banco, compartilhada pelos apps.

Cada app só registra `partial(carregar_tabela_generica, "<fonte>", Model)` no
seu `loader.py`; a lógica de ler, conferir colunas e fazer o full refresh mora
aqui. `pandas` é importado dentro das funções (CLAUDE.md §4).
"""

import logging
from pathlib import Path

from django.conf import settings

from core.carga.refresh import bulk_refresh

logger = logging.getLogger(__name__)


def silver_path(nome_fonte: str) -> Path:
    return Path(settings.DATA_DIR) / "silver" / f"{nome_fonte}.parquet"


def ler_parquet(caminho: Path):
    import pandas as pd

    if not caminho.exists():
        raise FileNotFoundError(
            f"Parquet Silver não encontrado: {caminho}\n"
            "Rode antes: python manage.py rodar_silver <fonte>"
        )
    df = pd.read_parquet(caminho)
    logger.info("Parquet lido: %s (%d linhas × %d colunas)", caminho.name, *df.shape)
    return df


def carregar_tabela_generica(nome_fonte: str, model) -> dict:
    """
    Carrega uma tabela da silver para o banco, sem de-para manual.
    Funciona porque as colunas do parquet têm os mesmos nomes dos campos do model.

    Args:
        nome_fonte: nome da fonte (ex.: "grp_instrumento")
        model: classe do model Django (ex.: GrpInstrumento)

    Returns:
        {'apagados': int, 'inseridos': int}
    """
    import pandas as pd

    # 1. montar o caminho do parquet a partir do nome da fonte e ler
    df = ler_parquet(silver_path(nome_fonte))
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
    objetos = [model(**row) for row in df.to_dict("records")]

    # 5. full refresh numa transação; devolve as quantidades
    return bulk_refresh(model, objetos)
