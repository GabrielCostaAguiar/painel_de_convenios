from apps.grp.services import (
    get_grp_gold_plano_itens_qs, get_grp_gold_recurso_concedente_qs,
    get_grp_gold_recurso_contrapartida_qs, get_grp_gold_acao_orcamentaria_qs,
)
from apps.grp.views._filtros import _ler_filtros_grp, _grp_render

# Configuração das abas: rótulo, função de queryset, colunas e campos.
# Adicionar uma aba nova = adicionar uma entrada aqui, sem tocar na view.
ABAS_PLANO = {
    "itens": {
        "rotulo": "Itens a executar",
        "qs": get_grp_gold_plano_itens_qs,
        "colunas": ["Nº GRP", "CATMAS", "Tipo Despesa", "C", "G", "M", "ED", "EI", "Descrição Item", "Origem do Recurso", "Situação",
                    "Quantidade", "Valor Unitário (R$)", "Valor Total (R$)"],
        "campos": ["nr_grp", "cd_catmas", "tp_despesa", "cd_categoria_economica", "cd_grupo_despesa", "cd_modalidade_aplicacao", "cd_elemento_despesa", "cd_elemento_item",
                   "ds_item", "ds_origem_recurso", "ds_situacao_item", "qt_item",  "vl_unitario_item", "vl_total_item"],
        "larguras": [90, 100, 130, 45, 45, 45, 55, 75, 320, 150, 110, 140, 150, 130],
    },
    "concedente": {
        "rotulo": "Recursos do concedente",
        "qs": get_grp_gold_recurso_concedente_qs,
        "colunas": ["Nº GRP", "Concedente", "CNPJ", "UO Arrecadação", "Nome UO", "Fonte", "IPU",
                    "Situação", "Valor (R$)"],
        "campos": ["nr_grp", "nm_concedente", "nr_cnpj_concedente", "cd_uo_arrecadacao", "nm_uo_arrecadacao",
                   "cd_fonte_recurso", "cd_ipu", "ds_situacao_recurso_concedente", "vl_recurso_concedente"],
        "larguras": [90, 200, 160, 130, 200, 80, 80, 130, 130],
    },
    "contrapartida": {
        "rotulo": "Contrapartida",
        "qs": get_grp_gold_recurso_contrapartida_qs,
        "colunas": ["Nº GRP", "UO Financiadora", "Nome UO", "Fonte", "IPU", "Situação", "Valor (R$)"],
        "campos": ["nr_grp", "cd_uo_financiadora", "nm_uo_financiadora", "cd_fonte_recurso_contrapartida",
                   "cd_ipu_contrapartida", "ds_situacao_contrapartida", "vl_contrapartida_financeira"],
        "larguras": [90, 140, 200, 80, 80, 130, 130],
    },
    "acao": {
        "rotulo": "Ações orçamentárias",
        "qs": get_grp_gold_acao_orcamentaria_qs,
        "colunas": ["Nº GRP", "Ação", "UO Execução", "Nome UO", "Situação", "Valor (R$)"],
        "campos": ["nr_grp", "cd_acao", "cd_uo_execucao", "nm_uo_execucao", "ds_situacao_acao",
                   "vl_execucao_orcamentaria"],
        "larguras": [90, 100, 130, 200, 130, 130],
    },
}
ABA_PADRAO = "itens"


def grp_plano_aplicacao(request):
    filtros = _ler_filtros_grp(request.GET)

    # Aba vem da URL; valor inválido cai na padrão (nunca confie no GET)
    aba = request.GET.get("aba", ABA_PADRAO)
    if aba not in ABAS_PLANO:
        aba = ABA_PADRAO
    cfg = ABAS_PLANO[aba]

    # Querystring sem 'aba' e 'page', para os links das abas manterem os filtros
    params = request.GET.copy()
    params.pop("aba", None)
    params.pop("page", None)

    return _grp_render(
        request,
        cfg["qs"](filtros),
        colunas=cfg["colunas"],
        campos=cfg["campos"],
        titulo=f"Plano de Aplicação — {cfg['rotulo']}",
        secao_sub="grp_plano_aplicacao",
        filtros=filtros,
        larguras=cfg["larguras"],
        abas=[(chave, c["rotulo"]) for chave, c in ABAS_PLANO.items()],
        aba_atual=aba,
        qs_sem_aba=params.urlencode(),
    )