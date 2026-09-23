"""
Sub-aba Cronograma de Desembolso.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.sigcon.models import CronogramaDesembolso
from apps.sigcon.services import get_cronograma_qs
from core.web import paginas_visiveis

def cronograma(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    plano      = request.GET.get("plano", "")

    qs, ctx = get_cronograma_qs(
        cod_sigcon=cod_sigcon or None,
        cod_siafi=cod_siafi or None,
        plano=plano or None,
    )

    anos = (
        CronogramaDesembolso.objects
        .exclude(ano_cronograma_desembolso=None)
        .exclude(ano_cronograma_desembolso="")
        .values_list("ano_cronograma_desembolso", flat=True)
        .distinct()
        .order_by("-ano_cronograma_desembolso")
    )

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "sigcon/cronograma.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "anos":           anos,
        "cod_sigcon_sel": cod_sigcon,
        "cod_siafi_sel":  ctx.get("siafi", cod_siafi),
        "plano_sel":      ctx.get("plano_trabalho_codigo", plano),
        "querystring":    querystring,
        "visible_pages":  paginas_visiveis(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "cronograma",
    })
