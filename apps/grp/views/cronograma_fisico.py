from apps.grp.services import get_grp_cronograma_fisico_qs
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render
from django.db.models import Sum

def grp_cronograma_fisico(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(
        request,
        get_grp_cronograma_fisico_qs(filtros),
        colunas=["Nº GRP", 
                 "Código da proposta", 
                 "Tipo da meta/etapa", 
                 "Especificação", 
                 "Valor", 
                 "Data de início",
                 "Data de término",
                 "Duração (dias)"
                 ],
        campos=[
            "nr_grp", 
            "cod_proposta", 
            "tp_meta_etapa", 
            "tx_meta_especificacao", 
            "vl_meta", 
            "dt_meta_inicio"
        ],
        titulo="Cronograma Físico",
        secao_sub="grp_cronograma_fisico",
        filtros=filtros,
        larguras=[90, 80, 150, 70, 200, 140],
    )
