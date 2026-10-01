from apps.grp.services import (
    get_grp_plano_aplicacao_detalhes_qs
)
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render

def grp_plano_aplicacao_detalhes(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_plano_aplicacao_detalhes_qs(filtros),
        colunas=["Nº GRP", "CATMAS",  "Tipo Despesa", "Categoria", "Grupo", "Modalidade", "Elemento", "CNPJ Benef.", "Descrição", "Origem", "Qtd", "Vlr Unit.", "Vlr Total", "Situação"],
        campos=["nr_grp","nr_catmas",  "tipo_despesa", "categoria_despesa", "grupo_despesa", "modalidade", "elemento_despesa", "beneficiario_cnpj", "descricao_item", "origem_recurso", "qt_item_executar", "vl_uni_item_a_executar", "vl_total_item_a_executar", "situacao_item_a_executar"],
        titulo="Detalhes do Plano de Aplicação", secao_sub="grp_plano_aplicacao_detalhes", filtros=filtros)