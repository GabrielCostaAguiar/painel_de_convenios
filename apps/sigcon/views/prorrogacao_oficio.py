"""
Sub-aba Prorrogação de Ofício (gold.vw_prorrogacao_oficio_sigcon).
"""

from apps.sigcon.services import get_prorrogacao_oficio_qs

from ._filtros import ler_filtros_sigcon, sigcon_render

COLUNAS = [
    "Código SIGCON",
    "Código Prorrogação de Ofício",
    "Data de publicação",
    "Data de vigência prorrogada",
]
CAMPOS = [
    "nr_convenio",
    "cd_prorrogacao_oficio",
    "dt_publicacao",
    "dt_vigencia_termino",
]
LARGURAS = [150, 160, 140, 180]
NOME_EXPORT = "prorrogacao_oficio"


def consulta(request):
    """QuerySet filtrado da aba — compartilhado por tela e export."""
    return get_prorrogacao_oficio_qs(ler_filtros_sigcon(request.GET))


def prorrogacao_oficio(request):
    return sigcon_render(
        request,
        consulta(request),
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Prorrogação de Ofício",
        secao_sub="prorrogacao_oficio",
        larguras=LARGURAS,
    )
