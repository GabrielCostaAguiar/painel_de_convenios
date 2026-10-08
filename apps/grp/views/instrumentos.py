from django.core.paginator import Paginator
from django.shortcuts import render

from core.web import paginas_visiveis
from ._filtros import _ler_filtros_grp

from apps.grp.models import GrpGoldInstrumento
from apps.grp.services import get_grp_dados_qs

from django.template.defaultfilters import date as format_date

from django.contrib.humanize.templatetags.humanize import intcomma
from decimal import Decimal

# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------

def _fmt_data(v):
    """Data → dd/mm/aaaa ou —"""
    return format_date(v, "d/m/Y") if v else None

def _fmt_valor(v):
    """Decimal → 50.000,00 (formato brasileiro) ou —"""
    if v is None:
        return None
    formatado = f"{v:,.2f}"
    return formatado.replace(",", "X").replace(".", ",").replace("X", ".")

# Campos que recebem formatação especial (nome do campo → função)
_FORMATADORES = {
    "dt_assinatura": _fmt_data,
    "dt_publicacao": _fmt_data,
    "dt_vigencia_inicio": _fmt_data,
    "dt_vigencia_termino": _fmt_data,
    "dt_vigencia_termino_inicial": _fmt_data,
    "vl_rendimento_autorizado": _fmt_valor,
    "vl_instrumento_concedente": _fmt_valor,
    "vl_instrumento_contrapartida_fin": _fmt_valor,
    "vl_instrumento_total": _fmt_valor,
}


def _formatar_celula(campo, valor):
    """Aplica o formatador se existir, senão devolve o valor cru."""
    fmt = _FORMATADORES.get(campo)
    return fmt(valor) if fmt else valor

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
    # uos = (DadosGrp.objects
    # .exclude(uo_cod="").exclude(uo_cod=None)
    # .values_list("uo_cod", flat=True).distinct().order_by("uo_cod"))
    nr_instrumento = (GrpGoldInstrumento.objects
    .exclude(nr_instrumento="").exclude(nr_instrumento=None)
    .values_list("nr_instrumento", flat=True).distinct().order_by("nr_instrumento"))
    nr_grp = (GrpGoldInstrumento.objects
    .exclude(nr_grp="").exclude(nr_grp=None)
    .values_list("nr_grp", flat=True).distinct().order_by("nr_grp"))

    # monta as linhas da tabela (Opção A) — senão a tabela vem vazia
    colunas = ["Origem do Instrumento", "Nº GRP", "Tipo do Instrumento", "Nº Instrumento", "Nº União", "Nome do Projeto", "Objeto", "Convenente", "Concedente", "Esfera", "Situação", "Status do Instrumento", "Data de assinatura", "Data de publicação", "Inicio de vigência", "Término de vigência", "Rendimento (R$)", "Valor concedente (R$)", "Valor contrapartida (R$)", "Valor Total (R$)", "Término de vigência inicial"]
    campos = ["ds_origem_instrumento", "nr_grp", "ds_tipo_instrumento_juridico", "nr_instrumento",  "nr_instrumento_transferegov", "nm_projeto", "tx_objeto_projeto", "nm_convenente", "nm_concedente", "ds_esfera_atuacao", "ds_situacao_instrumento", "ds_status_instrumento", "dt_assinatura", "dt_publicacao", "dt_vigencia_inicio", "dt_vigencia_termino", "vl_rendimento_autorizado", "vl_instrumento_concedente", "vl_instrumento_contrapartida_fin", "vl_instrumento_total", "dt_vigencia_termino_inicial"]
    linhas = [
        [_formatar_celula(c, getattr(obj, c)) for c in campos]
        for obj in page_obj
    ]


    return render(
        request, 
        "grp/grp_generico.html", {
        "page_obj":           page_obj,
        "total":              paginator.count,
        "colunas":            colunas,
        "linhas":             linhas,
        "nr_grp_sel":         filtros["nr_grp"],
        "nr_instrumento_sel": filtros["nr_instrumento"],
        "nr_instrumento":    nr_instrumento,
        "nr_grp":            nr_grp,
        "querystring":        querystring,
        "visible_pages":      paginas_visiveis(page_obj),
        "secao_ativa":        "grp",
        "secao_sub":          "grp_dados",
    })
