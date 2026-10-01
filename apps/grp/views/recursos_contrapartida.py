from apps.grp.services import (
    get_grp_recursos_contrapartida_qs
)
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render


def grp_recursos_contrapartida(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_recursos_contrapartida_qs(filtros),
        colunas=["Nº GRP", "UO", "Fonte", "IPU", "Vlr Contrapartida"],
        campos=[ "nr_grp", "uo_cod", "fonte", "ipu", "vl_contrapartida_financeira"],
        titulo="Recursos de Contrapartida", secao_sub="grp_recursos_contrapartida", filtros=filtros)