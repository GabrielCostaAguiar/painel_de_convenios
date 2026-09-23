"""
Sub-aba Termo Aditivo.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.sigcon.services import get_termos_aditivos_qs
from core.web import paginas_visiveis

def termo_aditivo(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_termos_aditivos_qs(cod_sigcon or None, cod_siafi or None)

    ta_pt_map = ctx.get("ta_pt_map", {})

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    # Attach plano_trabalho_codigo from bridge table to each TA object
    for ta in list(page_obj):
        ta.plano_trabalho_codigo_ext = ta_pt_map.get(ta.termo_aditivo_codigo_sequencial, "—")

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "sigcon/termo_aditivo.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "cod_sigcon_sel": cod_sigcon,
        "cod_siafi_sel":  cod_siafi,
        "plano_sel":      ctx.get("plano_trabalho_codigo", ""),
        "querystring":    querystring,
        "visible_pages":  paginas_visiveis(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "termo_aditivo",
    })
