from apps.grp.services import get_municipios_atendidos_qs, get_regioes_atendidas_qs
from apps.grp.views._filtros import _grp_render, _ler_filtros_grp

# Configuração das abas: rótulo, função de queryset, colunas e campos.
# Adicionar uma aba nova = adicionar uma entrada aqui, sem tocar na view.
ABAS_PLANO = {
    "Municípios": {
        "rotulo": "Municípios atendidos",
        "qs": get_municipios_atendidos_qs,
        "colunas": [
            "Nº GRP",
            "Código da propostas",
            "Nome do município",
            "Código do município",
            "Sigla da UF"
        ],
        "campos": [
            "nr_grp",
            "cd_proposta",
            "nm_municipio",
            "sg_uf"
        ],
        "larguras": [90, 120, 200, 120, 90],
    },
    "Regiões": {
        "rotulo": "Regiões atendidas",
        "qs": get_regioes_atendidas_qs,
        "colunas": [
            "Nº GRP",
            "Código da proposta",
            "Nome da região",
            "Sigla da UF do município da região",
            "Nome do município da região",
            "Situação da região"
        ],
        "campos": [
            "nr_grp",
            "cd_proposta",
            "nm_regiao",
            "sg_uf_municipio_regiao",
            "nm_municipio_regiao",
            "ds_situacao_regiao"
        ],
        "larguras": [90, 120, 200, 120, 200, 130],
    },
}
ABA_PADRAO = "Municípios"


def grp_regioes_atendidas(request):
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
        titulo=f"Regiões atendidas — {cfg['rotulo']}",
        secao_sub="grp_regioes_atendidas",
        filtros=filtros,
        larguras=cfg["larguras"],
        abas=[(chave, c["rotulo"]) for chave, c in ABAS_PLANO.items()],
        aba_atual=aba,
        qs_sem_aba=params.urlencode(),
    )