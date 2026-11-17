"""
Aba mestre das Consultas SIGCON: lista de convenios (gold.vw_convenio_sigcon).

Mesmo desenho das views do GRP: `COLUNAS` (rótulo) e `CAMPOS` (atributo do
model gold) andam em paralelo — para trocar o que uma coluna mostra, mude o
campo; para trocar o título, mude a coluna. Tela e export usam as mesmas listas.
"""

from apps.sigcon.services import get_convenios_qs

from ._filtros import ler_filtros_sigcon, sigcon_render

COLUNAS = [
    "Unidade Orçamentária",
    "Código SIGCON",
    # "Código União",
    "Código Plano de Trabalho",
    "Código SIAFI",
    # "SEI",
    "Instrumento",
    "Título",
    "Proponente",
    "Concedente",
    "Esfera Concedente",
    "Objeto",
    "Situação",
    "Característica da Contrapartida",
    "Data de Assinatura",
    "Data de Publicação",
    "Início vigência",
    "Término vigência",
    "Quantidade de dias para termino de vigência",
    "Valor concedente",
    "Valor proponente",
    "Valor total do Convênio",
    "Fim da vigência Inicial",
]

CAMPOS = [
    "cd_uo",
    "nr_convenio",
    # "cd_uniao",                       # fora do modelo SIGCON v1.0
    "cd_plano_trabalho",
    "nr_siafi",
    # "nr_sei",                         # fora do modelo SIGCON v1.0
    "tp_instrumento_siafi",
    "nm_plano_trabalho",
    "nm_uo",
    "nm_concedente",
    "ds_esfera_concedente",
    "tx_objeto",
    "ds_situacao_convenio",
    "ds_caracteristica_contrapartida",
    "dt_assinatura",
    "dt_publicacao",
    "dt_vigencia_inicio",
    "dt_vigencia_termino",
    f"qt_dias_para_vencer {"dias"}",
    "vl_convenio_concedente",
    "vl_convenio_proponente",
    "vl_convenio_total",
    "dt_vigencia_termino_inicial",
]

LARGURAS = [
    120, 150, 120, 110, 160, 280, 240, 240, 110,
    380, 150, 150, 110, 110, 110, 110, 120, 150, 150, 160, 120,
]
NOME_EXPORT = "convenios"


def consulta(request):
    """QuerySet filtrado da aba — compartilhado por tela e export."""
    return get_convenios_qs(ler_filtros_sigcon(request.GET))


def sigcon(request):
    return sigcon_render(
        request,
        consulta(request),
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Convênios",
        secao_sub="sigcon",
        larguras=LARGURAS,
    )
