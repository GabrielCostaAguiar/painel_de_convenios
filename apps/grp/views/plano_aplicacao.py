from apps.grp.services import (
    get_grp_plano_aplicacao_qs
)
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render

def grp_plano_aplicacao(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(request,
        get_grp_plano_aplicacao_qs(filtros),
        colunas=["Nº GRP", "Projeto", "Objeto", "Situação", "Tipo", "Responsável", "Atribuição", "CNPJ Convenente"],
        campos=["nr_grp", "nome_projeto", "objeto_projeto", "situacao_instrumento", "tipo_instrumento", "responsavel_nome", "responsavel_atribuicao", "cnpj_convenente"],
        titulo="Plano de Aplicação", secao_sub="grp_plano_aplicacao", filtros=filtros)