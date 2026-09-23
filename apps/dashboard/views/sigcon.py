"""
Views das 6 sub-abas de Consultas SIGCON (telas).

Os exports CSV/XLSX das mesmas abas ficam em exports.py.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.convenios.models import Convenio, CronogramaDesembolso, TermoAditivo
from apps.dashboard.services import (
    enrich_convenios_page,
    get_anos_disponiveis,
    get_cronograma_qs,
    get_plano_aplicacao_qs,
    get_prorrogacao_qs,
    get_sigcon_qs,
    get_termos_aditivos_qs,
    get_unidades_executoras_qs,
)
from core.gold.contrapartida import CATEGORIAS as CATEGORIAS_CONTRAPARTIDA

from ._helpers import _ler_filtros_sigcon, _visible_pages


def sigcon(request):
    filtros = _ler_filtros_sigcon(request.GET)
    qs = get_sigcon_qs(filtros)

    anos = get_anos_disponiveis()
    situacoes = (
        Convenio.objects
        .exclude(situacao=None).exclude(situacao="")
        .values_list("situacao", flat=True)
        .distinct().order_by("situacao")
    )
    lista_siafi = (
        Convenio.objects
        .values_list("convenio_numero_sequencial_siafi", flat=True)
        .distinct()
        .order_by("convenio_numero_sequencial_siafi")
    )
    lista_sigcon = (
        Convenio.objects
        .values_list("convenio_codigo", flat=True)
        .distinct()
        .order_by("convenio_codigo")
    )
    lista_instrumentos = (
        Convenio.objects
        .values_list("instrumento", flat=True)
        .distinct()
        .order_by("instrumento")
    )
    lista_termos_aditivo = (
        TermoAditivo.objects
        .values_list("tipo_termo_aditivo", flat=True)
        .distinct()
        .order_by("tipo_termo_aditivo")
    )


    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    # Enriquecer cada conv na página com campos de ConvenioIntegrado
    page_items = list(page_obj)
    enrichment = enrich_convenios_page(page_items)
    for conv in page_items:
        extra = enrichment.get(conv.pk, {})
        conv.codigo_siconv_ext        = extra.get("codigo_siconv", "—")
        conv.proponente_ext           = extra.get("proponente", "—")
        conv.fim_vigencia_inicial_ext = extra.get("fim_vigencia_inicial")
        conv.no_sei_ext               = extra.get("no_sei", "—")
        conv.tipo_contrapartida_ext   = extra.get("tipo_contrapartida", "—")

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "dashboard/convenios.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "anos":           anos,
        "situacoes":      situacoes,
        "ano_sel":             filtros["ano"],
        "situacao_sel":        filtros["situacao"],
        "cod_sigcon_sel":      filtros["cod_sigcon"],
        "cod_siafi_sel":       filtros["cod_siafi"],
        "instrumento_sel":     filtros["instrumento"],
        "termo_aditivo_sel":   filtros["termo_aditivo"],
        "concedente_sel":      filtros["concedente"],
        "proponente_sel":      filtros["proponente"],
        "tipo_contrapartida_sel": filtros["tipo_contrapartida"],
        "querystring":    querystring,
        "siafis":         lista_siafi,
        "sigcons":        lista_sigcon,
        "instrumentos":   lista_instrumentos,
        "termos_aditivo": lista_termos_aditivo,
        "tipos_contrapartida": CATEGORIAS_CONTRAPARTIDA,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "sigcon",
    })


# ---------------------------------------------------------------------------
# Aba Plano de Aplicação — detalhe do convênio selecionado
# ---------------------------------------------------------------------------

def plano_aplicacao(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_plano_aplicacao_qs(cod_sigcon or None, cod_siafi or None)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "dashboard/plano_aplicacao.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "cod_sigcon_sel": cod_sigcon,
        "cod_siafi_sel":  cod_siafi,
        "siafi_sel":      ctx.get("siafi", ""),
        "uo_sel":         ctx.get("uo", ""),
        "plano_sel":      ctx.get("plano_trabalho_codigo", ""),
        "querystring":    querystring,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "plano_aplicacao",
    })


# ---------------------------------------------------------------------------
# Aba Cronograma de Desembolso — suporta modo detalhe (cod_sigcon) e standalone
# ---------------------------------------------------------------------------

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

    return render(request, "dashboard/cronograma.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "anos":           anos,
        "cod_sigcon_sel": cod_sigcon,
        "cod_siafi_sel":  ctx.get("siafi", cod_siafi),
        "plano_sel":      ctx.get("plano_trabalho_codigo", plano),
        "querystring":    querystring,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "cronograma",
    })


# ---------------------------------------------------------------------------
# Aba Prorrogação de Ofício
# ---------------------------------------------------------------------------

def prorrogacao(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_prorrogacao_qs(cod_sigcon or None, cod_siafi or None)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "dashboard/prorrogacao.html", {
        "page_obj":         page_obj,
        "total":            paginator.count,
        "cod_sigcon_sel":   cod_sigcon,
        "cod_siafi_sel":    cod_siafi,
        "plano_sel":        ctx.get("plano_trabalho_codigo", ""),
        "querystring":      querystring,
        "visible_pages":    _visible_pages(page_obj),
        "secao_ativa":      "sigcon",
        "secao_sub":        "prorrogacao",
    })


# ---------------------------------------------------------------------------
# Aba Termo Aditivo
# ---------------------------------------------------------------------------

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

    return render(request, "dashboard/termo_aditivo.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "cod_sigcon_sel": cod_sigcon,
        "cod_siafi_sel":  cod_siafi,
        "plano_sel":      ctx.get("plano_trabalho_codigo", ""),
        "querystring":    querystring,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "termo_aditivo",
    })


# ---------------------------------------------------------------------------
# Aba Unidades Executoras
# ---------------------------------------------------------------------------

def unidades_executoras(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, _ = get_unidades_executoras_qs(cod_sigcon or None, cod_siafi or None)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "dashboard/unidades_executoras.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "cod_sigcon_sel": cod_sigcon,
        "cod_siafi_sel":  cod_siafi,
        "querystring":    querystring,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "unidades_executoras",
    })
