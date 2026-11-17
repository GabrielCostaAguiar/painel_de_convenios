"""
Sub-aba Cronograma de Desembolso (gold.vw_cronograma_desembolso_sigcon).
"""

from apps.sigcon.services import get_cronograma_qs

from ._filtros import ler_filtros_sigcon, sigcon_render

COLUNAS = [
    "Código SIAFI",
    "Código SIGCON",
    "Código Plano de Trabalho",
    "Mês",
    "Ano",
    "Valor Concedente R$",
    "Valor Proponente R$",
]
CAMPOS = [
    "nr_siafi",
    "nr_convenio",
    "cd_plano_trabalho",
    "nr_mes_desembolso",
    "nr_ano_desembolso",
    "vl_desembolso_concedente",
    "vl_desembolso_proponente",
]
LARGURAS = [150, 150, 150, 80, 90, 200, 200]
NOME_EXPORT = "cronograma_desembolso"


def consulta(request):
    """QuerySet filtrado da aba — compartilhado por tela e export."""
    return get_cronograma_qs(ler_filtros_sigcon(request.GET))


def cronograma(request):
    return sigcon_render(
        request,
        consulta(request),
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Cronograma de Desembolso",
        secao_sub="cronograma",
        larguras=LARGURAS,
    )
