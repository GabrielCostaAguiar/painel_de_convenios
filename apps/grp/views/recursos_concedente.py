from apps.grp.services import (
    get_grp_recursos_concedente_qs
)
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render

def grp_recursos_concedente(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_recursos_concedente_qs(filtros),
        colunas=["Nº GRP", "UO",  "Fonte", "IPU", "Vlr Concedente"],
        campos=["nr_grp", "uo_cod",  "fonte", "ipu", "vl_concedente"],
        titulo="Recursos do Concedente", secao_sub="grp_recursos_concedente", filtros=filtros)