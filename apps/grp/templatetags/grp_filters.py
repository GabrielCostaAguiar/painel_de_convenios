"""
Tags de template do GRP.

Uso no template:
    {% load grp_filters %}
    {% querystring_grp as qs_grp %}
"""

from urllib.parse import urlencode

from django import template

register = template.Library()

# Filtros globais da aba GRP, propagados entre as 7 sub-abas do GRP.
# Lista própria (não reaproveita GLOBAL_PARAMS do core) para que mexer no GRP
# nunca altere o que as abas do SIGCON propagam entre si.
GRP_PARAMS = ("nr_grp", "nr_instrumento", "cd_uo")


@register.simple_tag(takes_context=True)
def querystring_grp(context):
    """
    Querystring com os filtros do GRP (GRP_PARAMS) presentes em request.GET —
    usada para montar os links das sub-abas do GRP preservando o filtro.
    """
    request = context.get("request")
    if request is None:
        return ""
    params = {k: v for k, v in request.GET.items() if k in GRP_PARAMS and v}
    return urlencode(params)
