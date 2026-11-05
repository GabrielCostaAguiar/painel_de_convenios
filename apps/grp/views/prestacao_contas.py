from apps.grp.services import get_grp_prestacao_contas_qs
from apps.grp.views._filtros import _grp_render, _ler_filtros_grp

def grp_prestacao_contas(request):
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(
        request,
        get_grp_prestacao_contas_qs(filtros),
        colunas=[
            "Nº GRP",
            "Código da proposta",
            "Prestação de Contas obrigatória",
            "Justificativa da não obrigatoriedade",
            "Prazo Prestação de Contas",
            "Data limite da Prestação de Contas",
            "Data limite inicial da Prestação de Contas",
            "Tipo final da Prestação de Contas",
            "Data de envio da Prestação de Contas",
            "Conclusão do objeto",
            "Justificativa da conclusão",
            "Prestação de Contas finalizada",
            "Pendência Contabilização S/N",
            "Data de finalização",
            "Justificativa da aprovação",
            "Situação da aprovação"
        ],
        campos=[
            "nr_grp", 
            "cd_proposta", 
            "fl_pc_obrigatoria", 
            "tx_pc_justificativa_nao_obrigatoriedade", 
            "qt_pc_prazo",
            "dt_pc_limite",
            "dt_pc_limite_inicial",
            "tp_pc_final",
            "dt_pc_envio",
            "fl_conclusao_objeto",
            "tx_pc_justificativa_conclusao",
            "fl_pc_finalizada",
            "fl_pendencia_contabilizacao", 
            "dt_pc_finalizacao", 
            "tx_pc_justificativa_aprovacao", 
            "ds_pc_situacao_aprovacao"
        ],
        titulo="Prestação de Contas do GRP",
        secao_sub="grp_prestacao_contas",
        filtros=filtros,
        larguras=[90, 120, 150, 200, 120, 120, 130, 100, 120, 130, 200, 130, 150, 120, 200, 180],
    )