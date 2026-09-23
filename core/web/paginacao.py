"""Auxiliares de paginacao para os templates."""


def paginas_visiveis(page_obj, wing=2):
    """
    Lista compacta de paginas para a barra de navegacao.

    Devolve sempre a primeira e a ultima pagina, mais `wing` paginas de cada
    lado da atual. `None` no meio da lista e a sentinela de reticencias — o
    template a renderiza como "...".

    Ex.: pagina 7 de 20 com wing=2 -> [1, None, 5, 6, 7, 8, 9, None, 20]
    """
    total = page_obj.paginator.num_pages
    atual = page_obj.number
    paginas = sorted(
        {1, total} | set(range(max(1, atual - wing), min(total + 1, atual + wing + 1)))
    )

    saida, anterior = [], 0
    for pagina in paginas:
        if pagina - anterior > 1:
            saida.append(None)
        saida.append(pagina)
        anterior = pagina
    return saida
