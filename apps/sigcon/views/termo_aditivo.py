"""
Sub-aba Termo Aditivo.
"""

from apps.sigcon.services import get_termos_aditivos_qs

from ._filtros import sigcon_render

COLUNAS = [
    "Código SIGCON",
    "Código Plano de Trabalho",
    "Nº Termo Aditivo",
    "Tipo",
    "Data Assinatura",
    "Data Término Vigência",
    "Justificativa",
    "Valor Aditado Concedente R$",
    "Valor Aditado Proponente R$",
]
CAMPOS = [
    "nr_convenio_ext",         # carimbado por preparar
    "cd_plano_trabalho_ext",
    "nr_termo_aditivo",
    "tp_termo_aditivo",
    "dt_assinatura",
    "dt_vigencia_termino",
    "tx_justificativa",
    "vl_aditivo_concedente",
    "vl_aditivo_proponente",
]
LARGURAS = [150, 160, 140, 180, 120, 130, 400, 170, 170]
NOME_EXPORT = "termo_aditivo"


def consulta(request):
    cod_sigcon = request.GET.get("cod_sigcon", "")
    qs, ctx = get_termos_aditivos_qs(cod_sigcon or None, request.GET.get("cod_siafi") or None)
    ta_pt_map = ctx.get("ta_pt_map", {})

    def preparar(objetos):
        for ta in objetos:
            ta.nr_convenio_ext = cod_sigcon
            ta.cd_plano_trabalho_ext = ta_pt_map.get(ta.cd_termo_aditivo, "—")

    return qs, preparar


def termo_aditivo(request):
    qs, preparar = consulta(request)
    return sigcon_render(
        request, qs,
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Termo Aditivo",
        secao_sub="termo_aditivo",
        larguras=LARGURAS,
        preparar=preparar,
    )
