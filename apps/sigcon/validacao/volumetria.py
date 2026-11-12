"""
Volumetria: o banco tem exatamente as linhas da Silver de cada tabela SIGCON.

A carga é full refresh e nunca descarta linha com dado (Silver = model), então
qualquer diferença entre o Parquet e a tabela indica carga interrompida, Parquet
regerado sem recarregar o banco, ou perda de linha no loader.
"""

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.db import connection
from psycopg import sql

PREFIXO = "sigcon_"


def pasta_silver():
    # Lido a cada chamada (não no import) para respeitar DATA_DIR sobrescrito.
    return Path(settings.DATA_DIR) / "silver"


def tabelas_sigcon():
    """Nomes das tabelas dos models SIGCON — a mesma chave da fonte e do Parquet."""
    return sorted(
        modelo._meta.db_table
        for modelo in apps.get_models()
        if modelo._meta.db_table.startswith(PREFIXO)
    )


def contar_tabela(tabela):
    """Conta o número de linhas da tabela."""
    consulta = sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(tabela))
    with connection.cursor() as cur:
        cur.execute(consulta)
        return cur.fetchone()[0]


def contar_parquet(nome):
    import pandas as pd  # import tardio: evita o erro de OpenBLAS no runserver

    return len(pd.read_parquet(pasta_silver() / f"{nome}.parquet"))


def variacao_percentual(anterior, atual):
    """Variação relativa entre duas cargas (0.05 = 5%). Tabela que estava vazia e
    passou a ter linhas conta como 100%; vazia nas duas, como 0."""
    if anterior == atual:
        return 0.0
    if anterior == 0:
        return 1.0
    return abs(atual - anterior) / anterior


def teste_variacao_volumetria(minimo, maximo=None):
    """
    Devolve (qt, amostra) das tabelas cuja carga mais recente variou em relação à
    anterior mais que `minimo` e, se informado, até `maximo` (frações: 0.05 = 5%).

    Tabela com menos de duas cargas no histórico passa: é a primeira carga, só
    há o que registrar (a gravação é feita por `carregar_sigcon`).
    """
    from apps.sigcon.models import SigconHistoricoCarga

    fora = []
    for tabela in tabelas_sigcon():
        ultimas = list(
            SigconHistoricoCarga.objects.filter(tabela=tabela).order_by("-dt_carga", "-id")[:2]
        )
        if len(ultimas) < 2:
            continue
        atual, anterior = ultimas[0].qt_linhas, ultimas[1].qt_linhas
        variacao = variacao_percentual(anterior, atual)
        if variacao > minimo and (maximo is None or variacao <= maximo):
            fora.append(
                {
                    "fonte": tabela,
                    "linhas_anterior": anterior,
                    "linhas_atual": atual,
                    "variacao_pct": round(variacao * 100, 1),
                }
            )
    return len(fora), fora


def teste_volumetria():
    """Devolve (qt_divergencias, amostra), no mesmo formato dos testes SQL."""
    divergencias = []

    for tabela in tabelas_sigcon():
        try:
            n_parquet = contar_parquet(tabela)
        except FileNotFoundError:
            # Fonte ainda sem Silver: é divergência, não motivo para abortar
            # a validação das demais.
            divergencias.append(
                {
                    "fonte": tabela,
                    "linhas_parquet": None,
                    "linhas_banco": contar_tabela(tabela),
                }
            )
            continue
        n_banco = contar_tabela(tabela)
        if n_parquet != n_banco:
            divergencias.append(
                {"fonte": tabela, "linhas_parquet": n_parquet, "linhas_banco": n_banco}
            )
    return len(divergencias), divergencias
