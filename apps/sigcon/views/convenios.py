"""
Aba mestre das Consultas SIGCON: lista de convenios.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.sigcon.models import Convenio, TermoAditivo
from apps.sigcon.services import (
    enrich_convenios_page,
    get_anos_disponiveis,
    get_sigcon_qs,
)
from core.gold.contrapartida import CATEGORIAS as CATEGORIAS_CONTRAPARTIDA
from core.web import paginas_visiveis

from ._filtros import ler_filtros_sigcon

def sigcon(request):
    filtros = ler_filtros_sigcon(request.GET)
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

    return render(request, "sigcon/convenios.html", {
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
        "visible_pages":  paginas_visiveis(page_obj),
        "secao_ativa":    "sigcon",
        "secao_sub":      "sigcon",
    })
