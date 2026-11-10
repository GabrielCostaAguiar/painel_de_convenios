"""
O Gold ConvenioIntegrado não exclui linhas: uma linha de saída por linha de
sigcon_chave_siconv. UO excluída -> fl_uo_excluida; sem datas -> limpeza_g=1;
convênio sem SIAFI -> siafi_uo nulo. Chave repetida com conteúdo diferente é
erro (não escolhe em silêncio) e chave nula nunca herda dado de outra linha.

Amostras mínimas em memória, com os nomes de coluna da Silver nova.
"""

import pandas as pd
import pytest

from core.gold.relacionamento import (
    _colapsar_chave_unica,
    _preparar_siconv,
    construir_tabela_integrada,
    montar_sigcon_chaves,
)


def _s(valores):
    return pd.array(valores, dtype="string")


def _chaves(linhas):
    """linhas: (nr_siafi, cd_uo, nr_convenio_siconv)"""
    df = pd.DataFrame(linhas, columns=["nr_siafi", "cd_uo", "nr_convenio_siconv"]).astype("string")
    df["tp_instrumento_siafi"] = _s(["11"] * len(df))
    df["ds_situacao_convenio"] = _s(["VIGENTE"] * len(df))
    df["fl_siconv"] = pd.array([False] * len(df), dtype="boolean")
    df["siafi_uo"] = _s([None] * len(df))
    return df


def _depara():
    return pd.DataFrame({
        "siafi_uo_origem": _s([]), "siafi_uo_atual": _s([]),
        "nr_siafi_atual": _s([]), "cd_uo_atual": _s([]),
        "ds_alerta_linha": _s([]),
    })


def _convenio(linhas):
    """linhas: (nr_siafi, cd_uo, dt_inicio, dt_fim)"""
    df = pd.DataFrame(linhas, columns=["nr_siafi", "cd_uo", "dt_vigencia_inicio", "dt_vigencia_termino"])
    df["nr_siafi"] = df["nr_siafi"].astype("string")
    df["cd_uo"] = df["cd_uo"].astype("string")
    df["dt_vigencia_inicio"] = pd.to_datetime(df["dt_vigencia_inicio"])
    df["dt_vigencia_termino"] = pd.to_datetime(df["dt_vigencia_termino"])
    df["dt_vigencia_termino_inicial"] = df["dt_vigencia_termino"]
    df["nr_convenio"] = _s([f"CV{i}" for i in range(len(df))])
    df["ds_situacao_convenio"] = _s(["VIGENTE"] * len(df))
    for c in ("vl_convenio_concedente_inicial", "vl_convenio_concedente",
              "vl_convenio_proponente", "vl_convenio_total"):
        df[c] = [1.0] * len(df)
    return df


def _satelites(com_chave_nula=False):
    chave_conv = pd.DataFrame({
        "cd_convenio_sequencial": _s(["1", "2"]),
        "nr_siafi": _s(["100", None if com_chave_nula else "200"]),
        "cd_uo": _s(["1261", "5131"]),
    })
    geral = pd.DataFrame({
        "cd_convenio_sequencial": _s(["1", "2"]),
        "cd_plano_trabalho": _s(["P1", None]),
        "nr_siafi": _s(["100", "200"]),
        "dt_assinatura": pd.to_datetime(["2020-01-10", "2020-02-10"]),
    })
    plano = pd.DataFrame({
        "cd_plano_trabalho": _s(["P1"]), "tx_objeto": _s(["objeto 1"]),
        "nm_concedente": _s(["Conc"]), "nr_cnpj_concedente": _s(["11"]),
    })
    concedente = pd.DataFrame({"nr_cnpj_concedente": _s(["11"]), "ds_esfera": _s(["Federal"])})
    return chave_conv, geral, plano, concedente


def _construir(chaves, convenio):
    chave_conv, geral, plano, concedente = _satelites()
    return construir_tabela_integrada(chaves, _depara(), convenio, chave_conv, geral, plano, concedente)


def test_nenhuma_linha_e_excluida_e_flags_marcam():
    chaves = _chaves([
        ("100", "1261", None),   # normal
        ("200", "5131", None),   # UO excluída
        ("300", "1491", None),   # sem nenhuma data
        (None, "1261", "X-1"),   # sem SIAFI
    ])
    convenio = _convenio([
        ("100", "1261", "2020-01-01", "2030-01-01"),
        ("200", "5131", "2020-01-01", "2030-01-01"),
        ("300", "1491", None, None),
    ])
    g = _construir(chaves, convenio)

    assert len(g) == 4  # antes: filtrar_uo e limpeza_g removiam linhas
    por_chave = g.set_index(g["siafi_uo"].fillna("<nulo>"))
    assert bool(por_chave.loc["1001261", "fl_uo_excluida"]) is False
    assert bool(por_chave.loc["2005131", "fl_uo_excluida"]) is True
    assert por_chave.loc["1001261", "limpeza_g"] == 0
    assert por_chave.loc["3001491", "limpeza_g"] == 1
    assert "<nulo>" in por_chave.index  # o convênio sem SIAFI ficou
    assert por_chave.loc["<nulo>", "codigo_siconv"] == "X-1"


def test_chave_nula_nao_herda_dados_de_outra_linha():
    chaves = _chaves([(None, "1261", None), (None, "1491", None), ("100", "1261", None)])
    convenio = _convenio([
        (None, "1261", "2020-01-01", "2030-01-01"),   # convênio sem SIAFI no lado SIGCON
        ("100", "1261", "2021-05-05", "2031-05-05"),
    ])
    g = _construir(chaves, convenio)
    assert len(g) == 3
    nulos = g[g["siafi_uo"].isna()]
    assert len(nulos) == 2
    # as duas linhas sem chave NÃO recebem as datas do convênio sem SIAFI
    assert nulos["g_inicio_vigencia"].isna().all()
    assert (nulos["limpeza_g"] == 1).all()


def test_linhas_100_porcento_identicas_colapsam():
    df = pd.DataFrame({"siafi_uo": _s(["A", "A", None, None]), "x": _s(["1", "1", "2", "2"])})
    r = _colapsar_chave_unica(df, "siafi_uo", "teste")
    # A colapsa; as duas linhas de chave nula ficam (não são duplicatas entre si)
    assert len(r) == 3
    assert r["siafi_uo"].isna().sum() == 2


def test_chave_repetida_com_conteudo_diferente_levanta_erro():
    df = pd.DataFrame({"siafi_uo": _s(["A", "A"]), "x": _s(["1", "2"])})
    with pytest.raises(ValueError, match="conteúdo diferente"):
        _colapsar_chave_unica(df, "siafi_uo", "teste")


def test_montar_sigcon_chaves_nao_perde_linha_de_uo_excluida():
    chaves = _chaves([("100", "1261", None), ("200", "5131", None)])
    r = montar_sigcon_chaves(chaves, _depara())
    assert len(r) == 2
    assert r["fl_uo_excluida"].tolist() == [False, True]


def test_coluna_obrigatoria_ausente_levanta_keyerror():
    siconv = pd.DataFrame({"nr_convenio_siconv": _s(["1"])})
    with pytest.raises(KeyError, match="obrigatória"):
        _preparar_siconv(siconv)


def test_chave_siconv_sem_coluna_obrigatoria_levanta_keyerror():
    with pytest.raises(KeyError, match="obrigatória"):
        montar_sigcon_chaves(pd.DataFrame({"nr_siafi": _s(["1"])}), _depara())
