from apps.grp.services import get_grp_cronograma_qs
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render
from django.db.models import Sum

def grp_cronograma(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(
        request,
        get_grp_cronograma_qs(filtros),
        colunas=["Nº GRP", 
                 "Parcela", 
                 "Mês", 
                 "Ano", 
                 "Origem Recurso", 
                 "Valor Desembolso"],
        campos=[
            "nr_grp", 
            "nr_parcela", 
            "ds_mes_desembolso", 
            "nr_ano_desembolso", 
            "ds_origem_recurso_parcela", 
            "vl_desembolso"
        ],
        titulo="Cronograma de Desembolso",
        secao_sub="grp_cronograma",
        filtros=filtros,
        larguras=[90, 80, 150, 70, 200, 140],
    )
