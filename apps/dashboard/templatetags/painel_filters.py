"""
Filtros de template do painel.

Uso no template:
    {% load painel_filters %}
    {{ valor|brl }}       → "R$ 1.100.000,00"
    {{ valor|brl:"0" }}   → "R$ 1.100.000" (sem decimais)
"""

from django import template

register = template.Library()


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
