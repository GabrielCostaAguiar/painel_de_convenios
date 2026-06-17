"""
Testes de core/transform/referencias.py — de-paras tipos_receita e tipos_instrumento_entrada.
Sem banco, sem arquivos externos além dos CSVs versionados em core/referencia/.
"""

import pandas as pd

from core.transform.referencias import (
    aplicar_depara,
    tipos_instrumento_entrada,
    tipos_receita,
)


def test_tipos_receita_mapeamentos():
    mapa = tipos_receita()
    assert mapa["13"] == "Rendimento"
    assert mapa["24"] == "Receita de Capital"


def test_tipos_instrumento_entrada_mapeamentos():
    mapa = tipos_instrumento_entrada()
    assert mapa["5"] == "Convênio"
    assert mapa["11"] == "Acordo/Ajuste"


def test_instrumento_entrada_codigo_11_independente_de_tipos_siafi():
    """Garante que os dois de-paras com código 11 são domínios separados e não interferem."""
    from core.transform.referencias import tipos_siafi

    entrada = tipos_instrumento_entrada()
    siafi = tipos_siafi()
    # ambos têm código 11, mas os dicts são independentes e os rótulos podem diferir levemente
    assert "11" in entrada
    assert "11" in siafi
    assert set(entrada.keys()) != set(siafi.keys())


def test_aplicar_depara_preserva_nao_mapeados():
    mapa = tipos_receita()
    s = pd.Series(["13", "99", "17"])
    resultado = aplicar_depara(s, mapa, manter_original=True)
    assert resultado[0] == "Rendimento"
    assert resultado[1] == "99"       # código desconhecido: mantém original
    assert resultado[2] == "Receita Corrente"


def test_aplicar_depara_nan_sem_manter_original():
    mapa = tipos_instrumento_entrada()
    s = pd.Series(["4", "99"])
    resultado = aplicar_depara(s, mapa, manter_original=False)
    assert resultado[0] == "Contrato"
    assert pd.isna(resultado[1])
