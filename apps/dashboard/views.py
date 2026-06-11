from django.shortcuts import render
from django.core.paginator import Paginator

from apps.convenios.models import Convenio, CronogramaDesembolso
from apps.dashboard.services import (
    get_anos_disponiveis,
    get_indicadores,
    enrich_convenios_page,
    get_plano_aplicacao_qs,
    get_cronograma_qs,
    get_prorrogacao_qs,
    get_termos_aditivos_qs,
)


def _visible_pages(page_obj, wing=2):
    """Compact page list; None acts as ellipsis sentinel."""
    n = page_obj.paginator.num_pages
    cur = page_obj.number
    pages = sorted({1, n} | set(range(max(1, cur - wing), min(n + 1, cur + wing + 1))))
    out, prev = [], 0
    for p in pages:
        if p - prev > 1:
            out.append(None)
        out.append(p)
        prev = p
    return out


# ---------------------------------------------------------------------------
# Consultas SIGCON — aba mestre: lista de convênios
# ---------------------------------------------------------------------------

def sigcon(request):
    ano_str    = request.GET.get("ano", "")
    situacao   = request.GET.get("situacao", "")
    uo         = request.GET.get("uo", "")
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")

    qs = Convenio.objects.all()
    if ano_str.isdigit():
        qs = qs.filter(data_inicio_vigencia__year=int(ano_str))
    if situacao:
        qs = qs.filter(situacao=situacao)
    if uo:
        qs = qs.filter(unidade_orcamentaria_codigo=uo)
    if cod_sigcon:
        qs = qs.filter(convenio_codigo__icontains=cod_sigcon)
    if cod_siafi:
        qs = qs.filter(convenio_numero_sequencial_siafi__icontains=cod_siafi)

    anos = get_anos_disponiveis()
    situacoes = (
        Convenio.objects
        .exclude(situacao=None).exclude(situacao="")
        .values_list("situacao", flat=True)
        .distinct().order_by("situacao")
    )
    uos = (
        Convenio.objects
        .exclude(unidade_orcamentaria_codigo=None).exclude(unidade_orcamentaria_codigo="")
        .values_list("unidade_orcamentaria_codigo", flat=True)
        .distinct().order_by("unidade_orcamentaria_codigo")
    )

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    # Enriquecer cada conv na página com campos de ConvenioIntegrado
    page_items = list(page_obj)
    enrichment = enrich_convenios_page(page_items)
    for conv in page_items:
        extra = enrichment.get(conv.pk, {})
        conv.codigo_siconv_ext       = extra.get("codigo_siconv", "—")
        conv.proponente_ext          = extra.get("proponente", "—")
        conv.fim_vigencia_inicial_ext = extra.get("fim_vigencia_inicial")

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "dashboard/painel.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "anos":           anos,
        "situacoes":      situacoes,
        "uos":            uos,
        "ano_sel":        ano_str,
        "situacao_sel":   situacao,
        "uo_sel":         uo,
        "cod_sigcon_sel": cod_sigcon,
        "cod_siafi_sel":  cod_siafi,
        "querystring":    querystring,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
    })


# ---------------------------------------------------------------------------
# Indicadores — KPIs e tabela por situação
# ---------------------------------------------------------------------------

def indicadores(request):
    ano_str = request.GET.get("ano", "")
    ano = int(ano_str) if ano_str.isdigit() else None

    dados = get_indicadores(ano=ano)
    anos  = get_anos_disponiveis()

    if dados.get("vazio"):
        return render(request, "dashboard/indicadores.html", {
            "vazio": True,
            "anos":  anos,
            "ano_selecionado": ano,
            "secao_ativa": "indicadores",
        })

    return render(request, "dashboard/indicadores.html", {
        "vazio":        False,
        "anos":         anos,
        "ano_selecionado": ano,
        "resumo":       dados["resumo"],
        "por_situacao": dados["por_situacao"],
        "secao_ativa":  "indicadores",
    })


# ---------------------------------------------------------------------------
# Gráficos — dois painéis Chart.js
# ---------------------------------------------------------------------------

def graficos(request):
    ano_str = request.GET.get("ano", "")
    ano = int(ano_str) if ano_str.isdigit() else None

    dados = get_indicadores(ano=ano)

    if dados.get("vazio"):
        return render(request, "dashboard/graficos.html", {
            "vazio": True,
            "secao_ativa": "graficos",
        })

    return render(request, "dashboard/graficos.html", {
        "vazio":        False,
        "por_ano":      dados["por_ano"],
        "por_situacao": dados["por_situacao"],
        "secao_ativa":  "graficos",
    })


# ---------------------------------------------------------------------------
# Aba Plano de Aplicação — detalhe do convênio selecionado
# ---------------------------------------------------------------------------

def plano_aplicacao(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    qs, ctx = get_plano_aplicacao_qs(cod_sigcon or None)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "dashboard/plano_aplicacao.html", {
        "page_obj":       page_obj,
        "total":          paginator.count,
        "cod_sigcon_sel": cod_sigcon,
        "siafi_sel":      ctx.get("siafi", ""),
        "uo_sel":         ctx.get("uo", ""),
        "plano_sel":      ctx.get("plano_trabalho_codigo", ""),
        "querystring":    querystring,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
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
    })


# ---------------------------------------------------------------------------
# Aba Prorrogação de Ofício
# ---------------------------------------------------------------------------

def prorrogacao(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    qs, ctx = get_prorrogacao_qs(cod_sigcon or None)

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "dashboard/prorrogacao.html", {
        "page_obj":         page_obj,
        "total":            paginator.count,
        "cod_sigcon_sel":   cod_sigcon,
        "plano_sel":        ctx.get("plano_trabalho_codigo", ""),
        "querystring":      querystring,
        "visible_pages":    _visible_pages(page_obj),
        "secao_ativa":      "sigcon",
    })


# ---------------------------------------------------------------------------
# Aba Termo Aditivo
# ---------------------------------------------------------------------------

def termo_aditivo(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    qs, ctx = get_termos_aditivos_qs(cod_sigcon or None)

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
        "plano_sel":      ctx.get("plano_trabalho_codigo", ""),
        "querystring":    querystring,
        "visible_pages":  _visible_pages(page_obj),
        "secao_ativa":    "sigcon",
    })


# ---------------------------------------------------------------------------
# Aba Unidades Executoras — sem model (pendência de fonte)
# ---------------------------------------------------------------------------

def unidades_executoras(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    return render(request, "dashboard/unidades_executoras.html", {
        "cod_sigcon_sel": cod_sigcon,
        "secao_ativa":   "sigcon",
    })


# ---------------------------------------------------------------------------
# Stubs — "Em construção" para seções ainda não implementadas
# ---------------------------------------------------------------------------

def _stub(secao_ativa, secao_nome):
    def view(request):
        return render(request, "dashboard/em_construcao.html", {
            "secao_ativa": secao_ativa,
            "secao_nome":  secao_nome,
        })
    view.__name__ = secao_ativa
    return view


uniao         = _stub("uniao",         "Consultas União")
execucao      = _stub("execucao",      "Execução Estadual")
monitoramento = _stub("monitoramento", "Monitoramento")
relatorio     = _stub("relatorio",     "Relatório Individual")
alertas       = _stub("alertas",       "Alertas")
emendas       = _stub("emendas",       "Painel de Emendas")
