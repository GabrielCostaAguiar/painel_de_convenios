"""
Sub-aba Plano de Aplicação (gold.vw_plano_aplicacao_sigcon).
"""

from apps.sigcon.services import get_plano_aplicacao_qs

from ._filtros import ler_filtros_sigcon, sigcon_render

COLUNAS = [
    "Código SIAFI",
    "Código SIGCON",
    "Código Plano de Trabalho",
    "Ano Exercício",
    "Dotação Orçamentária",
    "UO",
    "Identificador Orçamento",
    "Função",
    "Ação",
    "Categ. Econôm. Despesa",
    "Grupo",
    "Modalidade Aplicação",
    "Fonte",
    "Procedência",
    "Elemento Despesa",
    "Valor Concedente R$",
    "Valor Proponente R$",
]
CAMPOS = [
    "nr_siafi",
    "nr_convenio",
    "cd_plano_trabalho",
    "nr_ano_exercicio",
    "dotacao_orcamentaria",
    "cd_uo_aplicacao",
    "cd_identificador_orcamento",
    "cd_funcao",
    "cd_identificador_projeto_atividade",
    "cd_categoria_economica",
    "cd_grupo_despesa",
    "cd_modalidade_aplicacao",
    "cd_fonte_recurso",
    "cd_procedencia",
    "cd_elemento_despesa",
    "vl_aplicacao_concedente",
    "vl_aplicacao_proponente",
]
LARGURAS = [110, 140, 130, 90, 190, 70, 110, 70, 80, 110, 70, 110, 80, 100, 110, 150, 150]
NOME_EXPORT = "plano_aplicacao"


def consulta(request):
    """QuerySet filtrado da aba — compartilhado por tela e export."""
    return get_plano_aplicacao_qs(ler_filtros_sigcon(request.GET))


def plano_aplicacao(request):
    return sigcon_render(
        request,
        consulta(request),
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Plano de Aplicação",
        secao_sub="plano_aplicacao",
        larguras=LARGURAS,
    )
