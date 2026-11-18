"""
Consultas das telas SIGCON.

Mesmo desenho do apps/grp/services.py: cada aba tem um `get_*_qs(filtros)` que
parte da sua view gold, aplica os filtros e devolve o queryset ORDENADO. Nenhuma
ligacao entre tabelas e feita aqui — elas ja vem prontas da gold (SQL).

As views nao acessam o ORM direto: tela, export CSV e export XLSX chamam estas
funcoes, entao o arquivo baixado sai com as mesmas linhas, na mesma ordem.

Filtros (todos valem para TODAS as golds do SIGCON; "" = sem filtro):
    ano, nr_convenio, nr_siafi, proponente, concedente,
    caracteristica_contrapartida, situacao, termo_aditivo, instrumento

Como o filtro chega a cada gold:
  - os 9 filtros sao resolvidos em GoldSigconConvenio (a gold mestre);
  - nas demais golds entram como `siafi_uo IN (subquery)`, ja que todas
    carregam siafi_uo (chave do convenio). Mesmo desenho do `nr_grp` no GRP.
"""

from django.db import models

from core.web import Filtro, aplicar_filtros, como_lista

from .models import (
    GoldSigconConvenio,
    GoldSigconCronogramaDesembolso,
    GoldSigconPlanoAplicacao,
    GoldSigconTermoAditivo,
    GoldSigconProrrogacaoOficio,
    GoldSigconUnidadeExecutora
)

# ---------------------------------------------------------------------------
# Ordenacao das telas paginadas
# ---------------------------------------------------------------------------
# Paginar sem order_by deixa o banco devolver ordens diferentes a cada pagina
# (o usuario ve um registro duas vezes e outro nunca). Cada ORDENACAO_* segue as
# colunas da tela e TERMINA em "pk", porque as chaves de negocio admitem empate.
# A ordenacao fica aqui, e nao em Meta.ordering do model, para nao encarecer as
# agregacoes que nao paginam.

ORDENACAO_CONVENIO = ("nr_convenio", "pk")

ORDENACAO_PLANO_APLICACAO = (
    "cd_plano_trabalho",
    "nr_ano_exercicio",
    "dotacao_orcamentaria",
    "pk",
)

ORDENACAO_CRONOGRAMA = (
    "cd_plano_trabalho",
    "nr_ano_desembolso",
    "nr_mes_desembolso",
    "pk",
)

ORDENACAO_TERMO_ADITIVO = (
    "cd_termo_aditivo",
    "nr_termo_aditivo",
    "pk",
)

ORDENACAO_PRORROGACAO_OFICIO = (
    "cd_prorrogacao_oficio",
    "cd_uo",
    "nr_siafi",
    "pk",
)

ORDENACAO_UNIDADE_EXECUTORA = (
    "cd_unidade_executora",
    "nr_siafi",
    "nr_convenio",
    "pk",
)


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

# Cada filtro aceita VÁRIOS valores (OR dentro do campo, AND entre campos) —
# ver core/web/filtros.py. nr_convenio/nr_siafi são exatos (IN); proponente e
# concedente, "contém". termo_aditivo (campo=None) entra por subquery, abaixo.
SPEC_FILTROS = (
    Filtro("ano", "nr_ano_convenio", "inteiro"),
    Filtro("nr_convenio", "nr_convenio", texto=True),
    Filtro("nr_siafi", "nr_siafi", texto=True),
    Filtro("proponente", "nm_uo", "contem", texto=True),
    Filtro("concedente", "nm_concedente", "contem", texto=True),
    Filtro("caracteristica_contrapartida", "ds_caracteristica_contrapartida"),
    Filtro("situacao", "ds_situacao_convenio"),
    Filtro("instrumento", "tp_instrumento_siafi"),
    Filtro("termo_aditivo"),
)
FILTROS = tuple(f.chave for f in SPEC_FILTROS)

_SPEC_TERMO = (Filtro("termo_aditivo", "tp_termo_aditivo"),)


def _filtrar_convenios(qs, filtros: dict):
    """Aplica os 9 filtros a um QuerySet[GoldSigconConvenio]."""
    qs = aplicar_filtros(qs, filtros, SPEC_FILTROS)
    if como_lista(filtros.get("termo_aditivo")):
        termos = aplicar_filtros(GoldSigconTermoAditivo.objects.all(), filtros, _SPEC_TERMO)
        qs = qs.filter(siafi_uo__in=termos.values("siafi_uo"))
    return qs


def _filtrar_por_convenio(qs, filtros: dict):
    """Aplica os filtros a qualquer gold que tenha siafi_uo (via a gold mestre)."""
    if any(como_lista(filtros.get(chave)) for chave in FILTROS):
        convenios = _filtrar_convenios(GoldSigconConvenio.objects.all(), filtros)
        qs = qs.filter(siafi_uo__in=convenios.values("siafi_uo"))
    return qs


# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------

def get_convenios_qs(filtros: dict):
    """QuerySet[GoldSigconConvenio] filtrado para a aba Convênios."""
    qs = _filtrar_convenios(GoldSigconConvenio.objects.all(), filtros)
    return qs.order_by(*ORDENACAO_CONVENIO)


def get_plano_aplicacao_qs(filtros: dict):
    """QuerySet[GoldSigconPlanoAplicacao] filtrado pelos filtros do SIGCON."""
    qs = _filtrar_por_convenio(GoldSigconPlanoAplicacao.objects.all(), filtros)
    return qs.order_by(*ORDENACAO_PLANO_APLICACAO)


def get_cronograma_qs(filtros: dict):
    """QuerySet[GoldSigconCronogramaDesembolso] filtrado pelos filtros do SIGCON."""
    qs = _filtrar_por_convenio(GoldSigconCronogramaDesembolso.objects.all(), filtros)
    return qs.order_by(*ORDENACAO_CRONOGRAMA)


def get_termos_aditivos_qs(filtros: dict):
    """
    QuerySet[GoldSigconTermoAditivo] filtrado pelos filtros do SIGCON.

    Com `termo_aditivo` informado, a aba mostra só os termos daquele tipo (e não
    todos os termos dos convênios que têm um termo daquele tipo).
    """
    qs = _filtrar_por_convenio(GoldSigconTermoAditivo.objects.all(), filtros)
    qs = aplicar_filtros(qs, filtros, _SPEC_TERMO)
    return qs.order_by(*ORDENACAO_TERMO_ADITIVO)

def get_prorrogacao_oficio_qs(filtros: dict):
    """QuerySet[GoldSigconProrrogacaoOficio] filtrado pelos filtros do SIGCON."""
    qs = _filtrar_por_convenio(GoldSigconProrrogacaoOficio.objects.all(), filtros)
    return qs.order_by(*ORDENACAO_PRORROGACAO_OFICIO)

def get_unidade_executora_qs(filtros: dict):
    """QuerySet[GoldSigconUnidadeExecutora] filtrado pelos filtros do SIGCON."""
    qs = _filtrar_por_convenio(GoldSigconUnidadeExecutora.objects.all(), filtros)
    return qs.order_by(*ORDENACAO_UNIDADE_EXECUTORA)


# ---------------------------------------------------------------------------
# Opções dos campos de filtro
# ---------------------------------------------------------------------------

def _distintos(qs, campo: str):
    qs = qs.exclude(**{f"{campo}__isnull": True})
    if not isinstance(qs.model._meta.get_field(campo), models.IntegerField):
        qs = qs.exclude(**{campo: ""})  # "" só existe em campo de texto
    return list(qs.values_list(campo, flat=True).distinct().order_by(campo))


def get_anos_disponiveis() -> list[int]:
    """Anos dos instrumentos, em ordem decrescente (também usado pelo dashboard)."""
    anos = _distintos(GoldSigconConvenio.objects.all(), "nr_ano_convenio")
    return sorted(anos, reverse=True)


def get_opcoes_filtros() -> dict:
    """Listas que alimentam os campos de filtro (selects e datalists)."""
    convenios = GoldSigconConvenio.objects.all()
    return {
        "anos": get_anos_disponiveis(),
        "situacoes": _distintos(convenios, "ds_situacao_convenio"),
        "siafis": _distintos(convenios, "nr_siafi"),
        "sigcons": _distintos(convenios, "nr_convenio"),
        "instrumentos": _distintos(convenios, "tp_instrumento_siafi"),
        "caracteristicas_contrapartida": _distintos(convenios, "ds_caracteristica_contrapartida"),
        "termos_aditivo": _distintos(GoldSigconTermoAditivo.objects.all(), "tp_termo_aditivo"),
    }
