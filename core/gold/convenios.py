"""
Camada Gold: indicadores calculados via ORM Django.

Cada função faz uma consulta agregada ao banco e retorna estruturas
simples (dict / list[dict]) com valores JSON-safe (float, int, str, None).
Sem DataFrames, sem Decimal, sem objetos date — prontos para template e json_script.
"""

import logging

from django.db.models import Count, Sum
from django.db.models.functions import ExtractYear

from apps.convenios.models import Convenio

logger = logging.getLogger(__name__)


def _qs(ano: int | None = None):
    """QuerySet base, opcionalmente filtrado pelo ano de data_inicio_vigencia."""
    qs = Convenio.objects.all()
    if ano is not None:
        qs = qs.filter(data_inicio_vigencia__year=ano)
    return qs


def kpis(ano: int | None = None) -> dict:
    """
    KPIs de alto nível.

    Retorna: total_convenios (int), valor_total_convenio, valor_concedente,
             valor_proponente (float em reais).
    """
    agg = _qs(ano).aggregate(
        total_convenios=Count("id"),
        valor_total_convenio=Sum("valor_total_convenio"),
        valor_concedente=Sum("valor_concedente"),
        valor_proponente=Sum("valor_proponente"),
    )
    return {
        "total_convenios": agg["total_convenios"] or 0,
        "valor_total_convenio": float(agg["valor_total_convenio"] or 0),
        "valor_concedente": float(agg["valor_concedente"] or 0),
        "valor_proponente": float(agg["valor_proponente"] or 0),
    }


def por_situacao(ano: int | None = None) -> list[dict]:
    """
    Contagem e valor total por situação, ordenados por valor_total decrescente.
    Chaves: situacao, quantidade, valor_total — compatível com graficos.js.
    """
    rows = (
        _qs(ano)
        .values("situacao")
        .annotate(
            quantidade=Count("id"),
            valor_total=Sum("valor_total_convenio"),
        )
        .order_by("-valor_total")
    )
    return [
        {
            "situacao": row["situacao"] or "—",
            "quantidade": row["quantidade"],
            "valor_total": float(row["valor_total"] or 0),
        }
        for row in rows
    ]


def por_ano() -> list[dict]:
    """
    Contagem e valor total por ano de início de vigência — série histórica completa.
    Não filtra por ano: destina-se ao gráfico de linha temporal.
    Chaves: ano, quantidade, valor_total — compatível com graficos.js.
    """
    rows = (
        Convenio.objects
        .exclude(data_inicio_vigencia=None)
        .annotate(ano=ExtractYear("data_inicio_vigencia"))
        .values("ano")
        .annotate(
            quantidade=Count("id"),
            valor_total=Sum("valor_total_convenio"),
        )
        .order_by("ano")
    )
    return [
        {
            "ano": row["ano"],
            "quantidade": row["quantidade"],
            "valor_total": float(row["valor_total"] or 0),
        }
        for row in rows
    ]


def recentes(limite: int = 50, ano: int | None = None) -> list[dict]:
    """
    Os N convênios mais recentes por data_inicio_vigencia.
    Datas retornadas como string ISO 8601; valores como float.
    """
    rows = (
        _qs(ano)
        .exclude(data_inicio_vigencia=None)
        .order_by("-data_inicio_vigencia")
        .values(
            "convenio_codigo",
            "situacao",
            "data_inicio_vigencia",
            "data_termino_vigencia",
            "valor_total_convenio",
        )[:limite]
    )
    return [
        {
            "convenio_codigo": row["convenio_codigo"],
            "situacao": row["situacao"] or "—",
            "data_inicio": row["data_inicio_vigencia"].isoformat(),
            "data_termino": row["data_termino_vigencia"].isoformat() if row["data_termino_vigencia"] else None,
            "valor_total": float(row["valor_total_convenio"]) if row["valor_total_convenio"] is not None else None,
        }
        for row in rows
    ]
