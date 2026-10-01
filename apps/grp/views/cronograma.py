from apps.grp.services import (
    get_grp_cronograma_qs
)
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render

def grp_cronograma(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_cronograma_qs(filtros),
        colunas=["Nº GRP", "Parcela", "Mês", "Ano", "Origem Recurso", "Vlr Desembolso"],
        campos=["nr_grp", "parcela_desembolso", "mes_desembolso", "ano_desembolso", "origem_recurso_parcela", "vl_desembolso"],
        titulo="Cronograma de Desembolso", secao_sub="grp_cronograma", filtros=filtros)