"""
Sub-aba Plano de Aplicacao.
"""

from apps.sigcon.services import anexar_convenio_por_plano, get_plano_aplicacao_qs

from ._filtros import sigcon_render

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
    "Fonte nova",
    "Procedência",
    "Elemento Despesa",
    "Valor Concedente R$",
    "Valor Proponente R$",
]
CAMPOS = [
    "nr_siafi_ext",            # carimbado por preparar
    "nr_convenio_ext",
    "cd_plano_trabalho",
    "nr_ano_exercicio",
    "cd_funcional_programatica",
    "cd_uo",
    "cd_identificador_orcamento",
    "cd_funcao",
    "cd_identificador_projeto_atividade",
    "cd_categoria_economica",
    "cd_grupo_despesa",
    "cd_modalidade_aplicacao",
    "cd_fonte_recurso",
    "ds_fonte_nova",           # constante, carimbada por preparar
    "cd_procedencia",
    "cd_elemento_despesa",
    "vl_aplicacao_concedente",
    "vl_aplicacao_proponente",
]
LARGURAS = [110, 140, 130, 90, 190, 70, 110, 70, 80, 110, 70, 110, 80, 110, 100, 110, 150, 150]
NOME_EXPORT = "plano_aplicacao"


def preparar(objetos):
    anexar_convenio_por_plano(objetos)
    for obj in objetos:
        obj.ds_fonte_nova = "— sem fonte —"


def consulta(request):
    qs, _ = get_plano_aplicacao_qs(
        request.GET.get("cod_sigcon") or None, request.GET.get("cod_siafi") or None,
    )
    return qs, preparar


def plano_aplicacao(request):
    qs, prep = consulta(request)
    return sigcon_render(
        request, qs,
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Plano de Aplicação",
        secao_sub="plano_aplicacao",
        larguras=LARGURAS,
        preparar=prep,
    )
