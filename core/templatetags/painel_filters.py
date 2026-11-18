"""
Filtros de template do painel.

Uso no template:
    {% load painel_filters %}
    {{ valor|brl }}       → "R$ 1.100.000,00"
    {{ valor|brl:"0" }}   → "R$ 1.100.000" (sem decimais)
"""

from django import template

from core.web import querystring_de

register = template.Library()

# Filtros globais das abas de Consultas SIGCON — parâmetros propagados
# automaticamente entre as sub-abas pela barra de navegação.
GLOBAL_PARAMS = (
    "ano", "nr_convenio", "nr_siafi", "proponente", "concedente",
    "caracteristica_contrapartida", "situacao", "termo_aditivo", "instrumento",
)


@register.simple_tag(takes_context=True)
def querystring_global(context):
    """
    Querystring contendo só os filtros GLOBAIS (GLOBAL_PARAMS) presentes em
    request.GET — usada para montar os links das sub-abas sem vazar filtros
    locais de uma aba para as outras.
    """
    request = context.get("request")
    if request is None:
        return ""
    return querystring_de(request.GET, GLOBAL_PARAMS)


@register.filter(name="badge_class")
def badge_class(situacao):
    """Maps situação string → CSS badge class for .badge styling."""
    if not situacao:
        return "b-bloq"
    s = str(situacao).upper()
    if any(k in s for k in ("VIG", "EXECU", "ANDAMENTO", "REGULAR")):
        return "b-vig"
    if any(k in s for k in ("VENC", "ENCERR", "INADIMPL", "CONCLU", "PREST")):
        return "b-venc"
    return "b-bloq"


@register.filter(name="brl")
def brl(value, decimais=2):
    """Formata número float/Decimal para padrão monetário brasileiro."""
    try:
        n = float(value)
        decimais = int(decimais)
    except (TypeError, ValueError):
        return value

    # Formata em padrão americano e troca separadores para o padrão BR
    fmt = f"{n:,.{decimais}f}"
    # "1,100,000.00" → "1.100.000,00"
    resultado = fmt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {resultado}"

@register.filter(name="tipo_siafi")
def tipo_siafi(value):
    """Código do Tipo SIAFI -> descrição (core/referencia/tipos_siafi.csv)."""
    from core.tipos_siafi import descricao_tipo_siafi

    return descricao_tipo_siafi(value)
