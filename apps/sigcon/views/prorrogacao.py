"""
Sub-aba Prorrogacao de Oficio.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.sigcon.services import get_prorrogacao_qs
from core.web import paginas_visiveis

def prorrogacao(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_prorrogacao_qs(cod_sigcon or None, cod_siafi or None)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "sigcon/prorrogacao.html", {
        "page_obj":         page_obj,
        "total":            paginator.count,
        "cod_sigcon_sel":   cod_sigcon,
        "cod_siafi_sel":    cod_siafi,
        "plano_sel":        ctx.get("plano_trabalho_codigo", ""),
        "querystring":      querystring,
        "visible_pages":    paginas_visiveis(page_obj),
        "secao_ativa":      "sigcon",
        "secao_sub":        "prorrogacao",
    })
