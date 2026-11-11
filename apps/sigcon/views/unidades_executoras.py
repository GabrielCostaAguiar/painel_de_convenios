"""
Sub-aba Unidades Executoras.
"""

from apps.sigcon.services import get_unidades_executoras_qs

from ._filtros import sigcon_render

COLUNAS = ["Código SIGCON", "Código SIAFI", "Cód. UO", "Unidade Executora"]
CAMPOS = ["nr_convenio", "nr_siafi", "cd_uo", "cd_unidade_executora"]
LARGURAS = [200, 150, 120, 300]
NOME_EXPORT = "unidades_executoras"


def consulta(request):
    qs, _ = get_unidades_executoras_qs(
        request.GET.get("cod_sigcon") or None, request.GET.get("cod_siafi") or None,
    )
    return qs, None


def unidades_executoras(request):
    qs, preparar = consulta(request)
    return sigcon_render(
        request, qs,
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Unidades Executoras",
        secao_sub="unidades_executoras",
        larguras=LARGURAS,
        preparar=preparar,
    )
