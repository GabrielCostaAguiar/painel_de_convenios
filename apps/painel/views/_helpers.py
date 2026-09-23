"""
Utilitarios privados das views do painel.

`paginas_visiveis` e `view_em_construcao` moravam aqui; foram para core/web/
porque passaram a ser usados por mais de um app.
"""


# ---------------------------------------------------------------------------
# Consultas SIGCON — filtros compartilhados entre a tela e o export
# ---------------------------------------------------------------------------

def _ler_filtros_sigcon(get_params):
    """Le os filtros da querystring; usado tanto pela tela quanto pelo export."""
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
