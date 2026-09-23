"""Leitura dos filtros das Consultas SIGCON a partir da querystring."""


def ler_filtros_sigcon(get_params):
    """
    Filtros da tela, lidos da querystring.

    Usado pela tela e pelo export correspondente — e por isso que ele vive num
    modulo proprio, e nao dentro da view: os dois precisam ler exatamente os
    mesmos parametros, senao o arquivo baixado nao bate com o que esta em tela.
    """
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
