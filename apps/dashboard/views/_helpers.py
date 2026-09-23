"""
Utilitários privados compartilhados pelas views do dashboard.
"""

from django.shortcuts import render


def _visible_pages(page_obj, wing=2):
    """Compact page list; None acts as ellipsis sentinel."""
    n = page_obj.paginator.num_pages
    cur = page_obj.number
    pages = sorted({1, n} | set(range(max(1, cur - wing), min(n + 1, cur + wing + 1))))
    out, prev = [], 0
    for p in pages:
        if p - prev > 1:
            out.append(None)
        out.append(p)
        prev = p
    return out


# ---------------------------------------------------------------------------
# Consultas SIGCON — filtros compartilhados entre a tela e o export
# ---------------------------------------------------------------------------

def _ler_filtros_sigcon(get_params):
    """Lê os filtros da querystring; usado tanto pela tela quanto pelo export."""
    return {
        "ano": get_params.get("ano", ""),
        "situacao": get_params.get("situacao", ""),
        "cod_sigcon": get_params.get("cod_sigcon", ""),
        "cod_siafi": get_params.get("cod_siafi", ""),
        "instrumento": get_params.get("instrumento", ""),
        "termo_aditivo": get_params.get("termo_aditivo", ""),
        "concedente": get_params.get("concedente", ""),
        "proponente": get_params.get("proponente", ""),
        "tipo_contrapartida": get_params.get("tipo_contrapartida", ""),
    }


# ---------------------------------------------------------------------------
# Stubs — "Em construção" para seções ainda não implementadas
# ---------------------------------------------------------------------------

def _stub(secao_ativa, secao_nome):
    def view(request):
        return render(request, "dashboard/em_construcao.html", {
            "secao_ativa": secao_ativa,
            "secao_nome":  secao_nome,
        })
    view.__name__ = secao_ativa
    return view
