"""
Testes da camada Gold de contrapartida.
Cobrem os 5 resultados possíveis usando amostras em memória — sem banco.
Testam _computar() diretamente (função pura) para isolar de ORM e fixtures.
"""

import pandas as pd

from core.gold.contrapartida import _computar


def _plano(codigo: str, caract: str | None) -> dict:
    return {"plano_trabalho_codigo": codigo, "plano_trabalho_caracteristica": caract}


def _bridge(plano_cod: str, siafi: str, uo: str) -> dict:
    return {
        "conveno_codigo_plano_trabalho": plano_cod,
        "convenio_numero_sequencial_siafi": siafi,
        "unidade_orcamentaria_codigo": uo,
    }


# siafi+uo da amostra
_SIAFI, _UO = "9001", "1001"
_SIAFI_UO = _SIAFI + _UO


def _resultado(caract: str | None) -> str:
    df_p = pd.DataFrame([_plano("PT001", caract)])
    df_b = pd.DataFrame([_bridge("PT001", _SIAFI, _UO)])
    r = _computar(df_p, df_b)
    return r.get(_SIAFI_UO, "NÃO ENCONTRADO")


def test_contrapartida_financeira():
    assert _resultado("Contrapartida") == "Contrapartida financeira"


def test_contrapartida_nao_financeira():
    assert _resultado("Contrapartida não financeira") == "Contrapartida não financeira"


def test_sem_contrapartida():
    assert _resultado("Sem contrapartida") == "Sem contrapartida"


def test_sem_informacao_quando_nao_informado():
    assert _resultado("Não Informado") == "Sem informação"


def test_sem_informacao_quando_nulo():
    assert _resultado(None) == "Sem informação"


def test_financeira_e_nao_financeira_quando_dois_planos():
    """Mesmo SIAFI_UO com dois planos distintos → max() resulta em ambos = 1."""
    df_p = pd.DataFrame([
        _plano("PT001", "Contrapartida"),
        _plano("PT002", "Contrapartida não financeira"),
    ])
    df_b = pd.DataFrame([
        _bridge("PT001", _SIAFI, _UO),
        _bridge("PT002", _SIAFI, _UO),
    ])
    r = _computar(df_p, df_b)
    assert r[_SIAFI_UO] == "Contrapartida financeira e não financeira"


def test_filtro_siafi_uo_exclui_outros():
    """siafi_uos filtra corretamente — SIAFI_UO ausente da lista não aparece no resultado."""
    df_p = pd.DataFrame([_plano("PT001", "Contrapartida")])
    df_b = pd.DataFrame([_bridge("PT001", _SIAFI, _UO)])
    r = _computar(df_p, df_b, siafi_uos=["99999999"])
    assert _SIAFI_UO not in r


def test_bridge_vazio_retorna_dict_vazio():
    df_p = pd.DataFrame([_plano("PT001", "Contrapartida")])
    df_b = pd.DataFrame(columns=["conveno_codigo_plano_trabalho",
                                  "convenio_numero_sequencial_siafi",
                                  "unidade_orcamentaria_codigo"])
    assert _computar(df_p, df_b) == {}
