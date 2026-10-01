from apps.grp.services import get_grp_esfera_qs
from apps.grp.views._filtros import _grp_render, _ler_filtros_grp

def grp_esfera(request):
    # EsferaGrp não tem nr_grp (liga por concedente_cnpj) — o filtro do GRP
    # viaja na URL para não se perder, mas não é aplicado aqui.
    filtros = _ler_filtros_grp(request.GET)
    return _grp_render(
        request,
        get_grp_esfera_qs(filtros),
        colunas=["CNPJ", "Nome", "Esfera"],
        campos=["concedente_cnpj", "concedente_nome", "concedente_esfera"],
        titulo="Esfera",
        secao_sub="grp_esfera",
        filtros=filtros,
        filtro_nao_aplicavel=True,
    )
