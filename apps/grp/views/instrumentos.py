from django.core.paginator import Paginator
from django.shortcuts import render

from core.web import paginas_visiveis
from ._filtros import _ler_filtros_grp

from apps.grp.models import DadosGrp
from apps.grp.services import get_grp_dados_qs

# ---------------------------------------------------------------------------
# GRP — aba teste: lista de instrumentos
# ---------------------------------------------------------------------------

def grp_instrumentos(request):
    filtros = _ler_filtros_grp(request.GET)
    qs = get_grp_dados_qs(filtros)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy(); params.pop("page", None)
    querystring = params.urlencode()

    # listas dos dropdowns/datalists — todas recuadas dentro da função
    uos = (DadosGrp.objects
    .exclude(uo_cod="").exclude(uo_cod=None)
    .values_list("uo_cod", flat=True).distinct().order_by("uo_cod"))
    nr_instrumentos = (DadosGrp.objects
    .exclude(nr_instrumento="").exclude(nr_instrumento=None)
    .values_list("nr_instrumento", flat=True).distinct().order_by("nr_instrumento"))
    nr_grps = (DadosGrp.objects
    .exclude(nr_grp="").exclude(nr_grp=None)
    .values_list("nr_grp", flat=True).distinct().order_by("nr_grp"))

    # monta as linhas da tabela (Opção A) — senão a tabela vem vazia
    colunas = ["Nº GRP", "UO", "Nº Instrumento",  "Concedente CNPJ", "Convenente CNPJ", "Situação", "Vig. Inicial", "Vig. Término", "Vlr Concedente", "Vlr Contrapartida", "Vlr Total"]
    campos = ["nr_grp", "uo_cod", "nr_instrumento",  "concedente_cnpj", "convenente_cnpj", "situacao", "dt_vigencia_inicial", "dt_vigencia_termino", "vl_instrumento_concedente", "vl_instrumento_contrapartida_fin", "vl_instrumento_total"]
    linhas = [[getattr(obj, c) for c in campos] for obj in page_obj]

    return render(
        request, 
        "grp/grp_generico.html", {
        "page_obj":           page_obj,
        "total":              paginator.count,
        "colunas":            colunas,
        "linhas":             linhas,
        "nr_grp_sel":         filtros["nr_grp"],
        "nr_instrumento_sel": filtros["nr_instrumento"],
        "uo_cod_sel":         filtros["uo_cod"],
        "uos":                uos,
        "nr_instrumentos":    nr_instrumentos,
        "nr_grps":            nr_grps,
        "querystring":        querystring,
        "visible_pages":      paginas_visiveis(page_obj),
        "secao_ativa":        "grp",
        "secao_sub":          "grp_dados",
    })
