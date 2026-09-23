"""Views de secao ainda nao implementada."""

from django.shortcuts import render

TEMPLATE_EM_CONSTRUCAO = "painel/em_construcao.html"


def view_em_construcao(secao_ativa, secao_nome):
    """
    Fabrica uma view que renderiza a tela "Em construcao".

    `secao_ativa` e a chave que a sidebar usa para marcar o item como ativo, e
    vira tambem o __name__ da view — e o que aparece no traceback e no
    inventario de rotas, entao precisa identificar a secao.
    """

    def view(request):
        return render(request, TEMPLATE_EM_CONSTRUCAO, {
            "secao_ativa": secao_ativa,
            "secao_nome": secao_nome,
        })

    view.__name__ = secao_ativa
    return view
