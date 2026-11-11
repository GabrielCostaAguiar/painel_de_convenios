"""
Sub-aba Cronograma de Desembolso.
"""

from apps.sigcon.services import anexar_convenio_por_plano, get_cronograma_qs

from ._filtros import sigcon_render

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
    "nr_siafi_ext",            # carimbado por anexar_convenio_por_plano
    "nr_convenio_ext",
    "cd_plano_trabalho",
    "nr_mes_desembolso",
    "nr_ano_desembolso",
    "vl_desembolso_concedente",
    "vl_desembolso_proponente",
]
LARGURAS = [150, 150, 150, 80, 90, 200, 200]
NOME_EXPORT = "cronograma_desembolso"


def consulta(request):
    qs, _ = get_cronograma_qs(
        nr_convenio=request.GET.get("cod_sigcon") or None,
        nr_siafi=request.GET.get("cod_siafi") or None,
        plano=request.GET.get("plano") or None,
    )
    return qs, anexar_convenio_por_plano


def cronograma(request):
    qs, preparar = consulta(request)
    return sigcon_render(
        request, qs,
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Cronograma de Desembolso",
        secao_sub="cronograma",
        larguras=LARGURAS,
        preparar=preparar,
    )
