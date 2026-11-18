"""Leitura dos filtros das Consultas SIGCON a partir da querystring."""


def _ler_filtros_grp(get_params):
    """
    Lê os filtros do GRP da querystring ({chave: [valores]}); usado por TODAS as
    sub-abas do GRP (e pelo export). As chaves são as do name= do formulário e
    as da SPEC_FILTROS_GRP em services.py — não renomear em um lugar só.
    """
    return ler_filtros(get_params, SPEC_FILTROS_GRP)


def _grp_selecionados(filtros):
    """Valores atuais dos filtros para o template (texto junto por '; ', UO em lista)."""
    return {
        "nr_grp_sel": "; ".join(filtros["nr_grp"]),
        "nr_instrumento_sel": "; ".join(filtros["nr_instrumento"]),
        "cd_uo_sel": filtros["cd_uo"],
    }


from django.core.paginator import Paginator
from django.shortcuts import render

from apps.grp.models import GrpInstrumento, GrpTabelaUo
from apps.grp.services import SPEC_FILTROS_GRP
from core.web import (
    calcular_totais,
    cards_totais,
    exportar_objetos,
    filtros_ativos,
    formatar_celula,
    ler_filtros,
    paginas_visiveis,
)


def _grp_contexto_pagina(request, qs, colunas, campos):
    """
    Pedaço do contexto comum às telas GRP: totais (soma no banco sobre o queryset
    filtrado inteiro), filtros_ativos e as URLs de exportação (mesma tela com
    ?export=csv|xlsx, que reusa o MESMO queryset).
    """
    totais = calcular_totais(qs, campos)
    params = request.GET.copy()
    params.pop("page", None)
    params.pop("export", None)
    base = params.urlencode()
    sep = "&" if base else ""
    return {
        "totais": totais,
        "totais_cards": cards_totais(totais, colunas, campos),
        "filtros_ativos": filtros_ativos(request.GET),
        "querystring": base,
        "url_export_csv": f"?{base}{sep}export=csv",
        "url_export_xlsx": f"?{base}{sep}export=xlsx",
    }


def _grp_exportar(request, qs, colunas, campos, secao_sub):
    """Resposta de download se a querystring pedir ?export=csv|xlsx; senão None."""
    formato = request.GET.get("export")
    if formato in ("csv", "xlsx"):
        return exportar_objetos(qs, colunas, campos, secao_sub, formato)
    return None


def _grp_listas():
    """Opções dos campos de filtro do GRP — cd_uo vem de GrpTabelaUo (cd_uo),
    nr_instrumento/nr_grp vêm de GrpInstrumento."""
    return {
        "uos": (
            GrpTabelaUo.objects.exclude(cd_uo="")
            .exclude(cd_uo=None)
            .values_list("cd_uo", flat=True)
            .distinct()
            .order_by("cd_uo")
        ),
        "nr_instrumentos": (
            GrpInstrumento.objects.exclude(nr_instrumento="")
            .exclude(nr_instrumento=None)
            .values_list("nr_instrumento", flat=True)
            .distinct()
            .order_by("nr_instrumento")
        ),
        "nr_grps": (
            GrpInstrumento.objects.exclude(nr_grp="")
            .exclude(nr_grp=None)
            .values_list("nr_grp", flat=True)
            .distinct()
            .order_by("nr_grp")
        ),
    }


def _grp_render(
    request,
    qs,
    colunas,
    campos,
    titulo,
    secao_sub,
    filtros=None,
    filtro_nao_aplicavel=False,
    larguras=None,
    **kwargs,
):
    filtros = filtros if filtros is not None else _ler_filtros_grp(request.GET)

    if larguras is not None and len(larguras) != len(colunas):
        import logging

        logging.getLogger(__name__).warning(
            "larguras (%d) != colunas (%d) na sub-aba '%s'",
            len(larguras),
            len(colunas),
            secao_sub,
        )
        larguras = None

    largura_total = sum(larguras) if larguras else None

    download = _grp_exportar(request, qs, colunas, campos, secao_sub)
    if download is not None:
        return download

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    linhas = [
        [formatar_celula(c, getattr(obj, c)) for c in campos] for obj in page_obj
    ]

    contexto = {
        "titulo": titulo,
        "colunas": colunas,
        "linhas": linhas,
        "page_obj": page_obj,
        "total": paginator.count,
        **_grp_contexto_pagina(request, qs, colunas, campos),
        "visible_pages": paginas_visiveis(page_obj),
        "secao_ativa": "grp",
        "secao_sub": secao_sub,
        **_grp_selecionados(filtros),
        "filtro_nao_aplicavel": filtro_nao_aplicavel and any(filtros.values()),
        "larguras": larguras,
        "largura_total": largura_total,
    }
    contexto.update(_grp_listas())
    contexto.update(kwargs)
    return render(request, "grp/grp_generico.html", contexto)
