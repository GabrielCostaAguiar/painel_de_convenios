"""Leitura dos filtros das Consultas SIGCON a partir da querystring."""

def _ler_filtros_grp(get_params):
    """
    Lê os filtros do GRP da querystring; usado por TODAS as sub-abas do GRP
    (e pelo export). As chaves são as mesmas do name= dos campos do form e
    das chaves lidas em services.py — não renomear em um lugar só.
    """
    return {
        "nr_grp": get_params.get("nr_grp", ""),
        "nr_instrumento": get_params.get("nr_instrumento", ""),
        "uo_cod": get_params.get("uo_cod", ""),
    }

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.grp.models import DadosGrp
from core.web import paginas_visiveis

def _grp_listas():
    """Opções dos campos de filtro do GRP — sempre vindas de DadosGrp."""
    return {
        "uos": (DadosGrp.objects
                .exclude(uo_cod="").exclude(uo_cod=None)
                .values_list("uo_cod", flat=True).distinct().order_by("uo_cod")),
        "nr_instrumentos": (DadosGrp.objects
                            .exclude(nr_instrumento="").exclude(nr_instrumento=None)
                            .values_list("nr_instrumento", flat=True).distinct()
                            .order_by("nr_instrumento")),
        "nr_grps": (DadosGrp.objects
                    .exclude(nr_grp="").exclude(nr_grp=None)
                    .values_list("nr_grp", flat=True).distinct().order_by("nr_grp")),
    }

def _grp_render(request, qs, colunas, campos, titulo, secao_sub,
                filtros=None, filtro_nao_aplicavel=False):
    filtros = filtros if filtros is not None else _ler_filtros_grp(request.GET)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))
    linhas = [[getattr(obj, c) for c in campos] for obj in page_obj]

    params = request.GET.copy(); params.pop("page", None)
    contexto = {
        "titulo": titulo, "colunas": colunas, "linhas": linhas,
        "page_obj": page_obj, "total": paginator.count,
        "querystring": params.urlencode(), "visible_pages": paginas_visiveis(page_obj),
        "secao_ativa": "grp", "secao_sub": secao_sub,
        # filtros: mantêm o form preenchido em qualquer sub-aba do GRP
        "nr_grp_sel":         filtros["nr_grp"],
        "nr_instrumento_sel": filtros["nr_instrumento"],
        "uo_cod_sel":         filtros["uo_cod"],
        "filtro_nao_aplicavel": filtro_nao_aplicavel and any(filtros.values()),
    }
    contexto.update(_grp_listas())
    return render(request, "grp/grp_generico.html", contexto)