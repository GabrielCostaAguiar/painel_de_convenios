"""
Views da aba GRP — 7 sub-abas de teste.

Queries em services.py (get_grp_*_qs); os 3 filtros (nr_grp, nr_instrumento,
uo_cod) valem para todas as sub-abas.
"""

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.convenios.models import DadosGrp
from apps.dashboard.services import (
    get_grp_cronograma_qs,
    get_grp_dados_qs,
    get_grp_esfera_qs,
    get_grp_plano_aplicacao_detalhes_qs,
    get_grp_plano_aplicacao_qs,
    get_grp_recursos_concedente_qs,
    get_grp_recursos_contrapartida_qs,
)

from ._helpers import _visible_pages


# ---------------------------------------------------------------------------
# Aba GRP
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Aba GRP — 7 sub-abas de teste. Queries em services.py (get_grp_*_qs);
# os 3 filtros (nr_grp, nr_instrumento, uo_cod) valem para todas as sub-abas.
# ---------------------------------------------------------------------------

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
        "querystring": params.urlencode(), "visible_pages": _visible_pages(page_obj),
        "secao_ativa": "grp", "secao_sub": secao_sub,
        # filtros: mantêm o form preenchido em qualquer sub-aba do GRP
        "nr_grp_sel":         filtros["nr_grp"],
        "nr_instrumento_sel": filtros["nr_instrumento"],
        "uo_cod_sel":         filtros["uo_cod"],
        "filtro_nao_aplicavel": filtro_nao_aplicavel and any(filtros.values()),
    }
    contexto.update(_grp_listas())
    return render(request, "dashboard/grp_generico.html", contexto)

def grp_cronograma(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_cronograma_qs(filtros),
        colunas=["Nº GRP", "Parcela", "Mês", "Ano", "Origem Recurso", "Vlr Desembolso"],
        campos=["nr_grp", "parcela_desembolso", "mes_desembolso", "ano_desembolso", "origem_recurso_parcela", "vl_desembolso"],
        titulo="Cronograma de Desembolso", secao_sub="grp_cronograma", filtros=filtros)

def grp_recursos_contrapartida(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_recursos_contrapartida_qs(filtros),
        colunas=["Nº GRP", "UO", "Fonte", "IPU", "Vlr Contrapartida"],
        campos=["nr_grp", "uo_cod", "fonte", "ipu", "vl_contrapartida_financeira"],
        titulo="Recursos de Contrapartida", secao_sub="grp_recursos_contrapartida", filtros=filtros)

def grp_recursos_concedente(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_recursos_concedente_qs(filtros),
        colunas=["Nº GRP", "UO",  "Fonte", "IPU", "Vlr Concedente"],
        campos=["nr_grp", "uo_cod",  "fonte", "ipu", "vl_concedente"],
        titulo="Recursos do Concedente", secao_sub="grp_recursos_concedente", filtros=filtros)

def grp_plano_aplicacao(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_plano_aplicacao_qs(filtros),
        colunas=["Nº GRP", "Projeto", "Objeto", "Situação", "Tipo", "Responsável", "Atribuição", "CNPJ Convenente"],
        campos=["nr_grp", "nome_projeto", "objeto_projeto", "situacao_instrumento", "tipo_instrumento", "responsavel_nome", "responsavel_atribuicao", "cnpj_convenente"],
        titulo="Plano de Aplicação", secao_sub="grp_plano_aplicacao", filtros=filtros)

def grp_plano_aplicacao_detalhes(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_plano_aplicacao_detalhes_qs(filtros),
        colunas=["Nº GRP", "CATMAS",  "Tipo Despesa", "Categoria", "Grupo", "Modalidade", "Elemento", "CNPJ Benef.", "Descrição", "Origem", "Qtd", "Vlr Unit.", "Vlr Total", "Situação"],
        campos=["nr_grp","nr_catmas",  "tipo_despesa", "categoria_despesa", "grupo_despesa", "modalidade", "elemento_despesa", "beneficiario_cnpj", "descricao_item", "origem_recurso", "qt_item_executar", "vl_uni_item_a_executar", "vl_total_item_a_executar", "situacao_item_a_executar"],
        titulo="Detalhes do Plano de Aplicação", secao_sub="grp_plano_aplicacao_detalhes", filtros=filtros)

def grp_esfera(request):
    # EsferaGrp não tem nr_grp (liga por concedente_cnpj) — o filtro do GRP
    # viaja na URL para não se perder, mas não é aplicado aqui.
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(
        request,
        get_grp_esfera_qs(filtros),
        colunas=["CNPJ", "Nome", "Esfera"],
        campos=["concedente_cnpj", "concedente_nome", "concedente_esfera"],
        titulo="Esfera",
        secao_sub="grp_esfera",
        filtros=filtros,
        filtro_nao_aplicavel=True,
    )


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
    colunas = ["Nº GRP", "UO", "Nº Instrumento",  "Situação", "Vig. Inicial", "Vig. Término", "Vlr Concedente", "Vlr Contrapartida", "Vlr Total"]
    campos = ["nr_grp", "uo_cod", "nr_instrumento",  "situacao", "dt_vigencia_inicial", "dt_vigencia_termino", "vl_instrumento_concedente", "vl_instrumento_contrapartida_fin", "vl_instrumento_total"]
    linhas = [[getattr(obj, c) for c in campos] for obj in page_obj]

    return render(
        request, 
        "dashboard/grp_generico.html", {
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
        "visible_pages":      _visible_pages(page_obj),
        "secao_ativa":        "grp",
        "secao_sub":          "grp_dados",
    })
