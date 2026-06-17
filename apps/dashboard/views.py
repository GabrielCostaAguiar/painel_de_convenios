import csv

from django.shortcuts import render
from django.http import HttpResponse
from django.core.paginator import Paginator

from apps.convenios.models import Convenio, CronogramaDesembolso, TermoAditivo
from core.export.xlsx import exportar_xlsx
from core.gold.contrapartida import CATEGORIAS as CATEGORIAS_CONTRAPARTIDA
from apps.dashboard.services import (
    get_anos_disponiveis,
    get_indicadores,
    enrich_convenios_page,
    get_sigcon_qs,
    get_plano_aplicacao_qs,
    get_cronograma_qs,
    get_prorrogacao_qs,
    get_termos_aditivos_qs,
    get_unidades_executoras_qs,
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

def _ler_filtros_sigcon(get_params):
    """Lê os filtros da querystring; usado tanto pela tela quanto pelo export."""
    return {
        "ano": get_params.get("ano", ""),
        "situacao": get_params.get("situacao", ""),
        "cod_sigcon": get_params.get("cod_sigcon", ""),
        "cod_siafi": get_params.get("cod_siafi", ""),
        "instrumento": get_params.get("instrumento", ""),
        "termo_aditivo": get_params.get("termo_aditivo", ""),
        "concedente": get_params.get("concedente", ""),
        "proponente": get_params.get("proponente", ""),
        "tipo_contrapartida": get_params.get("tipo_contrapartida", ""),
    }


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


def sigcon_export_csv(request):
    """Exporta para CSV os Convenio que respeitam os mesmos filtros da tela."""
    filtros = _ler_filtros_sigcon(request.GET)
    qs = get_sigcon_qs(filtros).order_by("convenio_codigo")

    items = list(qs)
    enrichment = enrich_convenios_page(items)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="convenios.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Unidade Orçamentária", "Código SIGCON", "Código União", "Código Plano de Trabalho",
        "Código SIAFI", "SEI", "Instrumento", "Título", "Proponente", "Concedente",
        "Esfera Concedente", "Objeto", "Situação", "Tipo de Contrapartida",
        "Data de Assinatura", "Data de Publicação", "Início vigência", "Término vigência",
        "Valor proponente", "Valor concedente", "Valor total do Convênio",
        "Fim da vigência Inicial",
    ])
    for conv in items:
        extra = enrichment.get(conv.pk, {})
        writer.writerow([
            conv.unidade_orcamentaria_codigo or "",
            conv.convenio_codigo,
            extra.get("codigo_siconv", "—"),
            conv.plano_trabalho_codigo or "",
            conv.convenio_numero_sequencial_siafi or "",
            extra.get("no_sei", "—"),
            conv.instrumento or "",
            conv.titulo or "",
            extra.get("proponente", "—"),
            conv.concedente or "",
            conv.esfera or "",
            conv.objeto or "",
            conv.situacao or "",
            extra.get("tipo_contrapartida", "—"),
            conv.data_assinatura.isoformat() if conv.data_assinatura else "",
            conv.data_publicacao.isoformat() if conv.data_publicacao else "",
            conv.data_inicio_vigencia.isoformat() if conv.data_inicio_vigencia else "",
            conv.data_termino_vigencia.isoformat() if conv.data_termino_vigencia else "",
            conv.valor_proponente if conv.valor_proponente is not None else "",
            conv.valor_concedente if conv.valor_concedente is not None else "",
            conv.valor_total_convenio if conv.valor_total_convenio is not None else "",
            extra.get("fim_vigencia_inicial") or "",
        ])

    return response


_COLUNAS_SIGCON_XLSX = [
    "Unidade Orçamentária", "Código SIGCON", "Código União", "Código Plano de Trabalho",
    "Código SIAFI", "SEI", "Instrumento", "Título", "Proponente", "Concedente",
    "Esfera Concedente", "Objeto", "Situação", "Tipo de Contrapartida",
    "Data de Assinatura", "Data de Publicação", "Início vigência", "Término vigência",
    "Valor proponente", "Valor concedente", "Valor total do Convênio",
    "Fim da vigência Inicial",
]


def sigcon_export_xlsx(request):
    """Exporta para XLSX os Convenio que respeitam os mesmos filtros e ordem da tela."""
    filtros = _ler_filtros_sigcon(request.GET)
    items = list(get_sigcon_qs(filtros))
    enrichment = enrich_convenios_page(items)

    linhas = [
        [
            conv.unidade_orcamentaria_codigo or "",
            conv.convenio_codigo,
            enrichment.get(conv.pk, {}).get("codigo_siconv", "—"),
            conv.plano_trabalho_codigo or "",
            conv.convenio_numero_sequencial_siafi or "",
            enrichment.get(conv.pk, {}).get("no_sei", "—"),
            conv.instrumento or "",
            conv.titulo or "",
            enrichment.get(conv.pk, {}).get("proponente", "—"),
            conv.concedente or "",
            conv.esfera or "",
            conv.objeto or "",
            conv.situacao or "",
            enrichment.get(conv.pk, {}).get("tipo_contrapartida", "—"),
            conv.data_assinatura,
            conv.data_publicacao,
            conv.data_inicio_vigencia,
            conv.data_termino_vigencia,
            conv.valor_proponente,
            conv.valor_concedente,
            conv.valor_total_convenio,
            enrichment.get(conv.pk, {}).get("fim_vigencia_inicial"),
        ]
        for conv in items
    ]
    return exportar_xlsx(linhas, _COLUNAS_SIGCON_XLSX, "convenios")


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


def plano_aplicacao_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Plano de Aplicação."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_plano_aplicacao_qs(cod_sigcon or None, cod_siafi or None)

    siafi_sel = ctx.get("siafi", "")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="plano_aplicacao.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Ano Exercício",
        "Dotação Orçamentária", "UO", "Identificador Orçamento", "Função", "Ação",
        "Categ. Econôm. Despesa", "Grupo", "Modalidade Aplicação", "Fonte", "Fonte nova",
        "Procedência", "Elemento Despesa", "Valor Concedente R$", "Valor Proponente R$",
    ])
    for pa in qs:
        writer.writerow([
            siafi_sel,
            cod_sigcon,
            pa.codigo_plano_trabalho or "",
            pa.ano_exercicio_programa_trabalho or "",
            pa.funcional_programatica_formatado or "",
            pa.codigo_unidade_orcamentaria or "",
            pa.identificador_orcamento_codigo or "",
            pa.funcao_codigo or "",
            pa.identificador_projeto_atividade_codigo or "",
            pa.categoria_economica_despesa_codigo or "",
            pa.grupo_despesa_codigo or "",
            pa.modalidade_aplicacao_codigo or "",
            pa.fonte_recurso_codigo or "",
            "— sem fonte —",
            pa.procedencia_codigo or "",
            pa.elemento_despesa_codigo or "",
            pa.valor_concedente if pa.valor_concedente is not None else "",
            pa.valor_proponente if pa.valor_proponente is not None else "",
        ])

    return response


def plano_aplicacao_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Plano de Aplicação."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_plano_aplicacao_qs(cod_sigcon or None, cod_siafi or None)

    siafi_sel = ctx.get("siafi", "")
    colunas = [
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Ano Exercício",
        "Dotação Orçamentária", "UO", "Identificador Orçamento", "Função", "Ação",
        "Categ. Econôm. Despesa", "Grupo", "Modalidade Aplicação", "Fonte", "Fonte nova",
        "Procedência", "Elemento Despesa", "Valor Concedente R$", "Valor Proponente R$",
    ]
    linhas = [
        [
            siafi_sel,
            cod_sigcon,
            pa.codigo_plano_trabalho or "",
            pa.ano_exercicio_programa_trabalho or "",
            pa.funcional_programatica_formatado or "",
            pa.codigo_unidade_orcamentaria or "",
            pa.identificador_orcamento_codigo or "",
            pa.funcao_codigo or "",
            pa.identificador_projeto_atividade_codigo or "",
            pa.categoria_economica_despesa_codigo or "",
            pa.grupo_despesa_codigo or "",
            pa.modalidade_aplicacao_codigo or "",
            pa.fonte_recurso_codigo or "",
            "— sem fonte —",
            pa.procedencia_codigo or "",
            pa.elemento_despesa_codigo or "",
            pa.valor_concedente,
            pa.valor_proponente,
        ]
        for pa in qs
    ]
    return exportar_xlsx(linhas, colunas, "plano_aplicacao")


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


def cronograma_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Cronograma de Desembolso."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    plano      = request.GET.get("plano", "")

    qs, _ = get_cronograma_qs(
        cod_sigcon=cod_sigcon or None,
        cod_siafi=cod_siafi or None,
        plano=plano or None,
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="cronograma_desembolso.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Mês", "Ano",
        "Valor Concedente R$", "Valor Proponente R$",
    ])
    for item in qs:
        writer.writerow([
            item.convenio_numero_sequencial_siafi or "",
            cod_sigcon,
            item.plano_trabalho_codigo or "",
            item.mes_cronograma_desembolso or "",
            item.ano_cronograma_desembolso or "",
            item.valor_concedente_cronograma_desembolso if item.valor_concedente_cronograma_desembolso is not None else "",
            item.valor_proponente_cronograma_desembolso if item.valor_proponente_cronograma_desembolso is not None else "",
        ])

    return response


def cronograma_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Cronograma de Desembolso."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    plano      = request.GET.get("plano", "")

    qs, _ = get_cronograma_qs(
        cod_sigcon=cod_sigcon or None,
        cod_siafi=cod_siafi or None,
        plano=plano or None,
    )

    colunas = [
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Mês", "Ano",
        "Valor Concedente R$", "Valor Proponente R$",
    ]
    linhas = [
        [
            item.convenio_numero_sequencial_siafi or "",
            cod_sigcon,
            item.plano_trabalho_codigo or "",
            item.mes_cronograma_desembolso or "",
            item.ano_cronograma_desembolso or "",
            item.valor_concedente_cronograma_desembolso,
            item.valor_proponente_cronograma_desembolso,
        ]
        for item in qs
    ]
    return exportar_xlsx(linhas, colunas, "cronograma_desembolso")


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


def prorrogacao_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Prorrogação de Ofício."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_prorrogacao_qs(cod_sigcon or None, cod_siafi or None)

    plano_sel = ctx.get("plano_trabalho_codigo", "")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="prorrogacao_oficio.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIGCON", "Código Plano de Trabalho", "Código Prorrogação de Ofício",
        "Data de Publicação", "Data Vigência Prorrogada",
    ])
    for po in qs:
        writer.writerow([
            po.prorrogacao_oficio_codigo_convenio or "",
            plano_sel,
            po.prorrogacao_oficio_codigo or "",
            po.prorrogacao_oficio_data_publicacao.isoformat() if po.prorrogacao_oficio_data_publicacao else "",
            po.prorrogacao_oficio_data_termino_vigencia.isoformat() if po.prorrogacao_oficio_data_termino_vigencia else "",
        ])

    return response


def prorrogacao_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Prorrogação de Ofício."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_prorrogacao_qs(cod_sigcon or None, cod_siafi or None)

    plano_sel = ctx.get("plano_trabalho_codigo", "")
    colunas = [
        "Código SIGCON", "Código Plano de Trabalho", "Código Prorrogação de Ofício",
        "Data de Publicação", "Data Vigência Prorrogada",
    ]
    linhas = [
        [
            po.prorrogacao_oficio_codigo_convenio or "",
            plano_sel,
            po.prorrogacao_oficio_codigo or "",
            po.prorrogacao_oficio_data_publicacao,
            po.prorrogacao_oficio_data_termino_vigencia,
        ]
        for po in qs
    ]
    return exportar_xlsx(linhas, colunas, "prorrogacao_oficio")


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


def termo_aditivo_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Termo Aditivo."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_termos_aditivos_qs(cod_sigcon or None, cod_siafi or None)
    ta_pt_map = ctx.get("ta_pt_map", {})

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="termo_aditivo.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIGCON", "Código Plano de Trabalho", "Nº Termo Aditivo", "Tipo",
        "Data Assinatura", "Data Término Vigência", "Justificativa",
        "Valor Aditado Concedente R$", "Valor Aditado Proponente R$",
    ])
    for ta in qs:
        writer.writerow([
            cod_sigcon,
            ta_pt_map.get(ta.termo_aditivo_codigo_sequencial, "—"),
            ta.termo_aditivo_numero_termo_aditivo or "",
            ta.termo_aditivo_tipo or ta.tipo_termo_aditivo or "",
            ta.termo_aditivo_data_assinatura.isoformat() if ta.termo_aditivo_data_assinatura else "",
            ta.termo_aditivo_data_termino_vigencia.isoformat() if ta.termo_aditivo_data_termino_vigencia else "",
            ta.termo_aditivo_justificativa or "",
            ta.valor_aditado_concedente_contratado if ta.valor_aditado_concedente_contratado is not None else "",
            ta.valor_aditado_proponente_contratado if ta.valor_aditado_proponente_contratado is not None else "",
        ])

    return response


def termo_aditivo_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Termo Aditivo."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_termos_aditivos_qs(cod_sigcon or None, cod_siafi or None)
    ta_pt_map = ctx.get("ta_pt_map", {})

    colunas = [
        "Código SIGCON", "Código Plano de Trabalho", "Nº Termo Aditivo", "Tipo",
        "Data Assinatura", "Data Término Vigência", "Justificativa",
        "Valor Aditado Concedente R$", "Valor Aditado Proponente R$",
    ]
    linhas = [
        [
            cod_sigcon,
            ta_pt_map.get(ta.termo_aditivo_codigo_sequencial, "—"),
            ta.termo_aditivo_numero_termo_aditivo or "",
            ta.termo_aditivo_tipo or ta.tipo_termo_aditivo or "",
            ta.termo_aditivo_data_assinatura,
            ta.termo_aditivo_data_termino_vigencia,
            ta.termo_aditivo_justificativa or "",
            ta.valor_aditado_concedente_contratado,
            ta.valor_aditado_proponente_contratado,
        ]
        for ta in qs
    ]
    return exportar_xlsx(linhas, colunas, "termo_aditivo")


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


def unidades_executoras_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Unidades Executoras."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, _ = get_unidades_executoras_qs(cod_sigcon or None, cod_siafi or None)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="unidades_executoras.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Código SIGCON", "Código SIAFI", "Cód. UO", "Unidade Executora"])
    for ue in qs:
        writer.writerow([
            ue.convenio_codigo or "",
            ue.convenio_numero_sequencial_siafi or "",
            ue.unidade_orcamentaria_codigo or "",
            ue.unidade_executora or "",
        ])

    return response


def unidades_executoras_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Unidades Executoras."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, _ = get_unidades_executoras_qs(cod_sigcon or None, cod_siafi or None)

    colunas = ["Código SIGCON", "Código SIAFI", "Cód. UO", "Unidade Executora"]
    linhas = [
        [
            ue.convenio_codigo or "",
            ue.convenio_numero_sequencial_siafi or "",
            ue.unidade_orcamentaria_codigo or "",
            ue.unidade_executora or "",
        ]
        for ue in qs
    ]
    return exportar_xlsx(linhas, colunas, "unidades_executoras")


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
