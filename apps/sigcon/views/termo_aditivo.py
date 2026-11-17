"""
Sub-aba Termo Aditivo (gold.vw_termo_aditivo_sigcon).
"""

from apps.sigcon.services import get_termos_aditivos_qs

from ._filtros import ler_filtros_sigcon, sigcon_render

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
    "nr_convenio",
    "cd_plano_trabalho",
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
    """QuerySet filtrado da aba — compartilhado por tela e export."""
    return get_termos_aditivos_qs(ler_filtros_sigcon(request.GET))


def termo_aditivo(request):
    return sigcon_render(
        request,
        consulta(request),
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Termo Aditivo",
        secao_sub="termo_aditivo",
        larguras=LARGURAS,
    )
