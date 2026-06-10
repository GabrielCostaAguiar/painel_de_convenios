"""
Testes de R2: resolução de chaves, de-para SIAFI→atual e aplicação de correções.

Todos os testes usam amostras mínimas em memória — sem banco, sem arquivos.
"""

import pandas as pd
import pytest

from core.transform.chaves import (
    UOS_EXCLUIR,
    filtrar_uo,
    montar_siafi_uo,
    resolver_siafi_atual,
    aplicar_correcoes,
    aplicar_deparas,
)


# ---------------------------------------------------------------------------
# Fixtures reutilizáveis
# ---------------------------------------------------------------------------

def _siafi2(rows: list[tuple]) -> pd.DataFrame:
    """Cria um mini-SIAFI2 com colunas (siafi1, uo1, siafi2, uo2, siafiatual, uoatual)."""
    return pd.DataFrame(rows, columns=["siafi1", "uo1", "siafi2", "uo2", "siafiatual", "uoatual"]).astype("string")


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
    def _chaves(self, siafi_uo_values: list[str]) -> pd.DataFrame:
        return pd.DataFrame({"siafi_uo": pd.array(siafi_uo_values, dtype="string")})

    def test_match_simples(self):
        """Convênio com substituição SIAFI deve receber o valor atual."""
        chaves = self._chaves(["93090741261"])
        siafi2 = _siafi2([("9309074", "1261", "9309074", "1261", "9600000", "1300")])
        resultado = resolver_siafi_atual(chaves, siafi2)
        assert resultado["siafi_uo_atual"][0] == "96000001300"
        assert resultado["siafiatual"][0] == "9600000"
        assert resultado["uo_atual"][0] == "1300"

    def test_sem_match_usa_fallback(self):
        """Convênio sem entrada no SIAFI2 deve ter siafi_uo_atual = siafi_uo original."""
        chaves = self._chaves(["00000001234"])
        siafi2 = _siafi2([("9999999", "9999", "9999999", "9999", "8888888", "8888")])
        resultado = resolver_siafi_atual(chaves, siafi2)
        assert resultado["siafi_uo_atual"][0] == "00000001234"

    def test_fallback_quando_siafi2_vazio(self):
        """SIAFI2 vazio: todos os convênios ficam com siafi_uo_atual = siafi_uo."""
        chaves = self._chaves(["1001001"])
        siafi2 = _siafi2([])
        resultado = resolver_siafi_atual(chaves, siafi2)
        assert resultado["siafi_uo_atual"][0] == "1001001"

    def test_deduplicacao_siafi2(self):
        """Duplicata na dimensão SIAFI2 deve ser removida sem erro."""
        chaves = self._chaves(["93090741261"])
        siafi2 = _siafi2([
            ("9309074", "1261", "9309074", "1261", "9600000", "1300"),
            ("9309074", "1261", "9309074", "1261", "9600000", "1300"),  # duplicata
        ])
        resultado = resolver_siafi_atual(chaves, siafi2)
        assert len(resultado) == 1
        assert resultado["siafi_uo_atual"][0] == "96000001300"

    def test_multiplos_com_mix_match_e_fallback(self):
        """Mix de convênios: alguns com match, outros sem."""
        chaves = self._chaves(["93090741261", "11111111111", "22222222222"])
        siafi2 = _siafi2([
            ("9309074", "1261", "9309074", "1261", "9600000", "1300"),
            ("2222222", "2222", "2222222", "2222", "3333333", "3333"),
        ])
        resultado = resolver_siafi_atual(chaves, siafi2)
        assert resultado.set_index("siafi_uo")["siafi_uo_atual"]["93090741261"] == "96000001300"
        assert resultado.set_index("siafi_uo")["siafi_uo_atual"]["11111111111"] == "11111111111"
        assert resultado.set_index("siafi_uo")["siafi_uo_atual"]["22222222222"] == "33333333333"


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

class TestFiltrarUo:
    def test_remove_uo_excluida(self):
        df = pd.DataFrame({
            "unidade_orcamentaria_codigo": pd.array(
                ["1261", "5131", "9801", "1491"], dtype="string"
            )
        })
        resultado = filtrar_uo(df)
        assert set(resultado["unidade_orcamentaria_codigo"]) == {"1261", "1491"}

    def test_todas_excluidas(self):
        uos = list(UOS_EXCLUIR)
        df = pd.DataFrame({"unidade_orcamentaria_codigo": pd.array(uos, dtype="string")})
        resultado = filtrar_uo(df)
        assert len(resultado) == 0

    def test_nenhuma_excluida(self):
        df = pd.DataFrame({
            "unidade_orcamentaria_codigo": pd.array(["1261", "1491", "2351"], dtype="string")
        })
        resultado = filtrar_uo(df)
        assert len(resultado) == 3

    def test_coluna_ausente_levanta_keyerror(self):
        df = pd.DataFrame({"outra_coluna": [1, 2]})
        with pytest.raises(KeyError):
            filtrar_uo(df)

    def test_coluna_customizada(self):
        df = pd.DataFrame({"uo": pd.array(["5131", "1261"], dtype="string")})
        resultado = filtrar_uo(df, coluna_uo="uo")
        assert len(resultado) == 1


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
