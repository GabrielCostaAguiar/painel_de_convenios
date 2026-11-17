"""
Sub-aba Prorrogação de Ofício (gold.vw_unidade_executora_sigcon).
"""

from apps.sigcon.services import get_unidade_executora_qs

from ._filtros import ler_filtros_sigcon, sigcon_render

COLUNAS = [
    "Código SIGCON",
    "Código SIAFI",
    # "Código União",
    "Unidades Executoras",
    # "SEI",
]
CAMPOS = [
    "nr_convenio",
    "nr_siafi",
    # "Código União",
    "cd_unidade_executora",
    # "SEI",
]
LARGURAS = [150, 160, 140]
NOME_EXPORT = "unidade_executora"


def consulta(request):
    """QuerySet filtrado da aba — compartilhado por tela e export."""
    return get_unidade_executora_qs(ler_filtros_sigcon(request.GET))


def unidade_executora(request):
    return sigcon_render(
        request,
        consulta(request),
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Unidades Executoras",
        secao_sub="unidade_executora",
        larguras=LARGURAS,
    )
