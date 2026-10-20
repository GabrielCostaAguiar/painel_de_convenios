from pathlib import Path

from django.conf import settings
from django.db import connection
from psycopg import sql

PASTA_SILVER = Path(settings.BASE_DIR) / "data" / "silver"


def contar_tabela(tabela):
    """
    Conta o número de linhas da tabela
    """
    consulta = sql.SQL("SELECT COUNT(*) FROM {}").format(
        sql.Identifier(tabela)
    )  # COUNT(*) montado com sql.Identifier
    with connection.cursor() as cur:
        cur.execute(consulta)
        qt = cur.fetchone()[0]

        return qt


def contar_parquet(nome):
    import pandas as pd  # import dentro da função: lembra do erro de OpenBLAS no runserver?

    return len(pd.read_parquet(PASTA_SILVER / f"{nome}.parquet"))


def teste_volumetria():
    """Devolve (qt_divergencias, amostra), no mesmo formato dos testes SQL."""
    from core.ingestion.sources import FONTES

    divergencias = []

    for nome in FONTES:  # as fontes grp_* do seu sources.py
        if not nome.startswith("grp_"):
            continue
        tabela = nome
        n_parquet = contar_parquet(nome)
        n_banco = contar_tabela(tabela)
        if n_parquet != n_banco:
            divergencias.append(
                {"fonte": nome, "linhas_parquet": n_parquet, "linhas_banco": n_banco}
            )
    return len(divergencias), divergencias
