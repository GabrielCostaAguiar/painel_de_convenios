"""
Sub-aba Prorrogacao de Oficio.
"""

from apps.sigcon.services import anexar_convenio_por_sequencial, get_prorrogacao_qs

from ._filtros import sigcon_render

COLUNAS = [
    "Código SIGCON",
    "Código Plano de Trabalho",
    "Código Prorrogação de Ofício",
    "Data de Publicação",
    "Data Vigência Prorrogada",
]
CAMPOS = [
    "nr_convenio_ext",         # carimbado por preparar
    "cd_plano_trabalho_ext",
    "cd_prorrogacao_oficio",
    "dt_publicacao",
    "dt_vigencia_termino",
]
LARGURAS = [160, 170, 200, 150, 170]
NOME_EXPORT = "prorrogacao_oficio"


def consulta(request):
    qs, ctx = get_prorrogacao_qs(
        request.GET.get("cod_sigcon") or None, request.GET.get("cod_siafi") or None,
    )
    plano = ctx.get("cd_plano_trabalho", "")

    def preparar(objetos):
        anexar_convenio_por_sequencial(objetos)
        for obj in objetos:
            obj.cd_plano_trabalho_ext = plano

    return qs, preparar


def prorrogacao(request):
    qs, preparar = consulta(request)
    return sigcon_render(
        request, qs,
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Prorrogação de Ofício",
        secao_sub="prorrogacao",
        larguras=LARGURAS,
        preparar=preparar,
    )
