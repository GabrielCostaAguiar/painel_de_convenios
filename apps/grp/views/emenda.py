from apps.grp.services import get_grp_emenda_qs
from apps.grp.views._filtros import _grp_render, _ler_filtros_grp


def grp_emenda(request):
    # GrpEmenda só vai ter registro para instrumentos que tem emenda parlamentar.
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(
        request,
        get_grp_emenda_qs(filtros),
        colunas=["Nº GRP",
                 "Código da proposta",
                  "Nº da emenda",
                  "Ano da emenda",
                  "Nome do parlamentar",
                  "Tipo da emenda",
                  "Situação da emenda"
                  ],
        campos=["nr_grp",
                "cd_proposta",
                "nr_emenda",
                "nr_ano_emenda",
                "nm_parlamentar",
                "tp_transferencia_emenda",
                "ds_situacao_emenda"
                ],
        titulo="Emenda",
        secao_sub="grp_emenda",
        filtros=filtros,
        filtro_nao_aplicavel=True,
        larguras=[90, 
                  120, 
                  120, 
                  120, 
                  200, 
                  200, 
                  120],
    )
