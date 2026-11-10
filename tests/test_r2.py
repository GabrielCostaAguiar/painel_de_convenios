"""
Testes de R2: resolução de chaves, de-para SIAFI→atual e aplicação de correções.

Todos os testes usam amostras mínimas em memória — sem banco, sem arquivos.
"""

import pandas as pd
import pytest

from core.transform.chaves import (
    UOS_EXCLUIR,
    marcar_uo_excluida,
    montar_siafi_uo,
    resolver_siafi_atual,
    aplicar_correcoes,
    aplicar_deparas,
)


# ---------------------------------------------------------------------------
# Fixtures reutilizáveis
# ---------------------------------------------------------------------------

def _depara(rows: list[tuple], alertas: list | None = None) -> pd.DataFrame:
    """
    Mini depara_siafi (Silver nova). Cada linha:
    (siafi_origem, uo_origem, siafi_atual, uo_atual). siafi_uo_origem/atual já
    montados, como no YAML da fonte.
    """
    df = pd.DataFrame(rows, columns=["nr_siafi_origem", "cd_uo_origem", "nr_siafi_atual", "cd_uo_atual"]).astype("string")
    df["siafi_uo_origem"] = montar_siafi_uo(df["nr_siafi_origem"], df["cd_uo_origem"])
    df["siafi_uo_atual"] = montar_siafi_uo(df["nr_siafi_atual"], df["cd_uo_atual"])
    if alertas is not None:
        df["ds_alerta_linha"] = pd.array(alertas, dtype="string")
    return df


# ---------------------------------------------------------------------------
# montar_siafi_uo
# ---------------------------------------------------------------------------

class TestMontarSiafiUo:
    def test_caso_normal(self):
        siafi = pd.Series(["9309074"], dtype="string")
        uo = pd.Series(["1261"], dtype="string")
        resultado = montar_siafi_uo(siafi, uo)
        assert resultado[0] == "93090741261"

    def test_preserva_zeros_esquerda(self):
        """Zeros à esquerda no UO não devem ser removidos — o tipo string garante isso."""
        siafi = pd.Series(["100"], dtype="string")
        uo = pd.Series(["0042"], dtype="string")
        resultado = montar_siafi_uo(siafi, uo)
        assert resultado[0] == "1000042"

    def test_siafi_nulo_resulta_na(self):
        siafi = pd.Series([pd.NA], dtype="string")
        uo = pd.Series(["1261"], dtype="string")
        resultado = montar_siafi_uo(siafi, uo)
        assert pd.isna(resultado[0])

    def test_uo_nulo_resulta_na(self):
        siafi = pd.Series(["9309074"], dtype="string")
        uo = pd.Series([pd.NA], dtype="string")
        resultado = montar_siafi_uo(siafi, uo)
        assert pd.isna(resultado[0])

    def test_ambos_nulos(self):
        siafi = pd.Series([pd.NA], dtype="string")
        uo = pd.Series([pd.NA], dtype="string")
        resultado = montar_siafi_uo(siafi, uo)
        assert pd.isna(resultado[0])

    def test_strip_em_espacos(self):
        """Espaços laterais devem ser removidos antes de concatenar."""
        siafi = pd.Series([" 9309074 "], dtype="string")
        uo = pd.Series([" 1261 "], dtype="string")
        resultado = montar_siafi_uo(siafi, uo)
        assert resultado[0] == "93090741261"

    def test_multiplos_registros(self):
        siafi = pd.Series(["100", "200", pd.NA], dtype="string")
        uo = pd.Series(["10", "20", "30"], dtype="string")
        resultado = montar_siafi_uo(siafi, uo)
        assert resultado[0] == "10010"
        assert resultado[1] == "20020"
        assert pd.isna(resultado[2])


# ---------------------------------------------------------------------------
# resolver_siafi_atual
# ---------------------------------------------------------------------------

class TestResolverSiafiAtual:
    def _chaves(self, siafi_uo_values: list) -> pd.DataFrame:
        return pd.DataFrame({"siafi_uo": pd.array(siafi_uo_values, dtype="string")})

    def test_match_simples(self):
        """Convênio com substituição SIAFI deve receber o valor atual."""
        chaves = self._chaves(["93090741261"])
        depara = _depara([("9309074", "1261", "9600000", "1300")])
        resultado = resolver_siafi_atual(chaves, depara)
        assert resultado["siafi_uo_atual"][0] == "96000001300"
        assert resultado["siafiatual"][0] == "9600000"
        assert resultado["uo_atual"][0] == "1300"

    def test_sem_match_usa_fallback(self):
        """Convênio sem entrada no depara deve ter siafi_uo_atual = siafi_uo original."""
        chaves = self._chaves(["00000001234"])
        depara = _depara([("9999999", "9999", "8888888", "8888")])
        resultado = resolver_siafi_atual(chaves, depara)
        assert resultado["siafi_uo_atual"][0] == "00000001234"

    def test_fallback_quando_depara_vazio(self):
        chaves = self._chaves(["1001001"])
        resultado = resolver_siafi_atual(chaves, _depara([]))
        assert resultado["siafi_uo_atual"][0] == "1001001"

    def test_origem_repetida_com_mesmo_destino_colapsa_na_consulta(self):
        """Linhas repetidas do depara (as colunas redundantes diferiam) não multiplicam o convênio."""
        chaves = self._chaves(["93090741261"])
        depara = _depara([
            ("9309074", "1261", "9600000", "1300"),
            ("9309074", "1261", "9600000", "1300"),
        ])
        resultado = resolver_siafi_atual(chaves, depara)
        assert len(resultado) == 1
        assert resultado["siafi_uo_atual"][0] == "96000001300"

    def test_multiplos_com_mix_match_e_fallback(self):
        chaves = self._chaves(["93090741261", "11111111111", "22222222222"])
        depara = _depara([
            ("9309074", "1261", "9600000", "1300"),
            ("2222222", "2222", "3333333", "3333"),
        ])
        resultado = resolver_siafi_atual(chaves, depara).set_index("siafi_uo")["siafi_uo_atual"]
        assert resultado["93090741261"] == "96000001300"
        assert resultado["11111111111"] == "11111111111"
        assert resultado["22222222222"] == "33333333333"

    def test_linhas_em_quarentena_sao_ignoradas_na_consulta(self):
        """Origem com destinos divergentes (marcada) não escolhe destino: cai no fallback."""
        chaves = self._chaves(["94277811451"])
        depara = _depara(
            [("9427781", "1451", "9427781", "1451"), ("9427781", "1451", "9433735", "4691")],
            alertas=["quarentena:grao_divergente", "quarentena:grao_divergente"],
        )
        resultado = resolver_siafi_atual(chaves, depara)
        assert len(resultado) == 1
        assert resultado["siafi_uo_atual"][0] == "94277811451"

    def test_chave_nula_nao_casa_com_origem_nula(self):
        """O pandas casaria nulo com nulo: um convênio sem SIAFI não pode herdar destino."""
        chaves = self._chaves([None])
        depara = _depara([(None, "1261", "9600000", "1300")])
        resultado = resolver_siafi_atual(chaves, depara)
        assert len(resultado) == 1
        assert pd.isna(resultado["siafi_uo_atual"][0])

    def test_coluna_ausente_levanta_keyerror(self):
        with pytest.raises(KeyError):
            resolver_siafi_atual(self._chaves(["1"]), pd.DataFrame({"outra": ["x"]}))

    def test_nao_perde_linhas_do_lado_esquerdo(self):
        chaves = self._chaves(["A", "B", None])
        resultado = resolver_siafi_atual(chaves, _depara([("1", "2", "3", "4")]))
        assert len(resultado) == 3


# ---------------------------------------------------------------------------
# aplicar_correcoes
# ---------------------------------------------------------------------------

class TestAplicarCorrecoes:
    def _df_base(self) -> pd.DataFrame:
        return pd.DataFrame({
            "convenio_codigo": pd.array(
                ["CV s/ nº 2020", "CV 98/2020", "OUTRO"], dtype="string"
            ),
            "convenio_codigo_sigcon": pd.array(["", "", ""], dtype="string"),
            "situacao": pd.array(["BLOQUEADO", "VIGENTE", "Em execução"], dtype="string"),
            "convenio_numero_sequencial_siafi": pd.array(
                ["9440702", "9999999", "1111111"], dtype="string"
            ),
        })

    def test_corrige_codigo_sigcon(self):
        df = self._df_base()
        resultado = aplicar_correcoes(df, "sigcon_convenio")
        linha = resultado[resultado["convenio_codigo"] == "CV s/ nº 2020"].iloc[0]
        assert linha["convenio_codigo_sigcon"] == "CV 559/5502"

    def test_corrige_segundo_codigo(self):
        df = self._df_base()
        resultado = aplicar_correcoes(df, "sigcon_convenio")
        linha = resultado[resultado["convenio_codigo"] == "CV 98/2020"].iloc[0]
        assert linha["convenio_codigo_sigcon"] == "CV 10954"

    def test_corrige_situacao_bloqueada(self):
        df = self._df_base()
        resultado = aplicar_correcoes(df, "sigcon_convenio")
        linha = resultado[resultado["convenio_numero_sequencial_siafi"] == "9440702"].iloc[0]
        assert linha["situacao"] == "VIGENTE"

    def test_sem_match_nao_altera(self):
        df = self._df_base()
        resultado = aplicar_correcoes(df, "sigcon_convenio")
        linha = resultado[resultado["convenio_codigo"] == "OUTRO"].iloc[0]
        assert linha["convenio_codigo_sigcon"] == ""

    def test_tabela_desconhecida_retorna_df_inalterado(self):
        df = self._df_base()
        resultado = aplicar_correcoes(df, "tabela_que_nao_existe")
        pd.testing.assert_frame_equal(resultado, df)

    def test_idempotente(self):
        """Rodar duas vezes não aplica a correção duas vezes."""
        df = self._df_base()
        resultado1 = aplicar_correcoes(df, "sigcon_convenio")
        resultado2 = aplicar_correcoes(resultado1, "sigcon_convenio")
        pd.testing.assert_frame_equal(resultado1, resultado2)


# ---------------------------------------------------------------------------
# filtrar_uo
# ---------------------------------------------------------------------------

class TestMarcarUoExcluida:
    def test_marca_uo_excluida_sem_remover_linha(self):
        df = pd.DataFrame({
            "unidade_orcamentaria_codigo": pd.array(["1261", "5131", "9801", "1491"], dtype="string")
        })
        mascara = marcar_uo_excluida(df)
        assert mascara.tolist() == [False, True, True, False]
        assert len(df) == 4  # a função não mexe no DataFrame

    def test_todas_excluidas(self):
        df = pd.DataFrame({"unidade_orcamentaria_codigo": pd.array(list(UOS_EXCLUIR), dtype="string")})
        assert marcar_uo_excluida(df).all()

    def test_nenhuma_excluida(self):
        df = pd.DataFrame({
            "unidade_orcamentaria_codigo": pd.array(["1261", "1491", "2351"], dtype="string")
        })
        assert not marcar_uo_excluida(df).any()

    def test_uo_nula_nao_e_excluida(self):
        df = pd.DataFrame({"unidade_orcamentaria_codigo": pd.array([None, "5131"], dtype="string")})
        assert marcar_uo_excluida(df).tolist() == [False, True]

    def test_coluna_ausente_levanta_keyerror(self):
        with pytest.raises(KeyError):
            marcar_uo_excluida(pd.DataFrame({"outra_coluna": [1, 2]}))

    def test_coluna_customizada(self):
        df = pd.DataFrame({"uo": pd.array(["5131", "1261"], dtype="string")})
        assert marcar_uo_excluida(df, coluna_uo="uo").tolist() == [True, False]


# ---------------------------------------------------------------------------
# aplicar_deparas
# ---------------------------------------------------------------------------

class TestAplicarDeparas:
    def test_padroniza_situacao(self):
        df = pd.DataFrame({"situacao": pd.array(["BLOQUEADO", "VIGENTE", "Em execução"], dtype="string")})
        resultado = aplicar_deparas(df)
        assert "situacao_std" in resultado.columns
        assert resultado["situacao_std"][0] == "Bloqueado"
        assert resultado["situacao_std"][1] == "Vigente"
        assert resultado["situacao_std"][2] == "Em execução"

    def test_situacao_sem_match_fica_original(self):
        df = pd.DataFrame({"situacao": pd.array(["STATUS DESCONHECIDO"], dtype="string")})
        resultado = aplicar_deparas(df)
        assert resultado["situacao_std"][0] == "STATUS DESCONHECIDO"

    def test_tipo_siafi(self):
        df = pd.DataFrame({"plano_trabalho_tipo_siafi": pd.array(["11", "15", "99"], dtype="string")})
        resultado = aplicar_deparas(df)
        assert resultado["instrumento_chaves"][0] == "Acordo / Ajuste"
        assert resultado["instrumento_chaves"][1] == "Transferências Especiais"
        assert resultado["instrumento_chaves"][2] == "99"  # sem match → original

    def test_nao_sobrescreve_original(self):
        df = pd.DataFrame({"situacao": pd.array(["BLOQUEADO"], dtype="string")})
        resultado = aplicar_deparas(df)
        assert resultado["situacao"][0] == "BLOQUEADO"
        assert resultado["situacao_std"][0] == "Bloqueado"

    def test_sem_colunas_pertinentes_nao_falha(self):
        df = pd.DataFrame({"col_irrelevante": ["a", "b"]})
        resultado = aplicar_deparas(df)
        assert "situacao_std" not in resultado.columns
        assert "instrumento_chaves" not in resultado.columns
