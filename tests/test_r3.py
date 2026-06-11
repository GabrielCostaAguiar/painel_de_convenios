"""
Testes de R3: campos G_, campos A_, validação de fan-out.

Todos os testes usam amostras mínimas em memória — sem banco, sem arquivos.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from core.gold.relacionamento import (
    _coalesce,
    _coalesce_num,
    aplicar_campos_a,
    aplicar_campos_g,
)


# ---------------------------------------------------------------------------
# Fixtures reutilizáveis
# ---------------------------------------------------------------------------

_HOJE = pd.Timestamp(date.today())
_VIGENTE = (_HOJE + timedelta(days=30)).strftime("%Y-%m-%d")
_VENCIDO = (_HOJE - timedelta(days=30)).strftime("%Y-%m-%d")


def _chaves(rows: list[dict]) -> pd.DataFrame:
    """Cria mini-sigcon_chaves com as colunas mínimas necessárias para G_."""
    defaults = {
        "siafi_uo": pd.NA,
        "siafi_uo_atual": pd.NA,
        "codigo_siconv": pd.NA,
        "instrumento_chaves": pd.NA,
        "situacao": pd.NA,
        "uo_nome_std": pd.NA,
        "unidade_orcamentaria_codigo": pd.NA,
    }
    for r in rows:
        for k, v in defaults.items():
            r.setdefault(k, v)
    df = pd.DataFrame(rows)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("string")
    return df


def _sigcon(rows: list[dict]) -> pd.DataFrame:
    """Cria mini-sigcon_completo (colunas prefixadas sigcon_)."""
    defaults = {
        "siafi_uo": pd.NA,
        "sigcon_situacao": pd.NA,
        "sigcon_data_inicio_vigencia": pd.NA,
        "sigcon_data_termino_vigencia": pd.NA,
        "sigcon_data_real_convenio": pd.NA,
        "sigcon_data_assinatura": pd.NA,
        "sigcon_valor_concedente": pd.NA,
        "sigcon_valor_proponente": pd.NA,
        "sigcon_valor_global": pd.NA,
        "sigcon_valor_global_inicial": pd.NA,
        "sigcon_concedente": pd.NA,
        "sigcon_objeto": pd.NA,
        "sigcon_esfera": pd.NA,
    }
    for r in rows:
        for k, v in defaults.items():
            r.setdefault(k, v)
    df = pd.DataFrame(rows)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("string")
    return df


def _siconv(rows: list[dict]) -> pd.DataFrame:
    """Cria mini-siconv_convenio (colunas prefixadas siconv_)."""
    defaults = {
        "nr_convenio": pd.NA,
        "id_proposta": pd.NA,
        "siconv_situacao": pd.NA,
        "siconv_data_inicio_vigencia": pd.NA,
        "siconv_data_fim_vigencia": pd.NA,
        "siconv_data_fim_vigencia_inicial": pd.NA,
        "siconv_data_assinatura": pd.NA,
        "siconv_valor_concedente": pd.NA,
        "siconv_valor_proponente": pd.NA,
        "siconv_valor_global": pd.NA,
        "siconv_proponente": pd.NA,
        "siconv_concedente": pd.NA,
        "siconv_objeto": pd.NA,
    }
    for r in rows:
        for k, v in defaults.items():
            r.setdefault(k, v)
    df = pd.DataFrame(rows)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("string")
    return df


# ---------------------------------------------------------------------------
# _coalesce (lógica central do coalesce G_)
# ---------------------------------------------------------------------------

class TestCoalesce:
    def test_siconv_presente_tem_precedencia(self):
        sv = pd.array(["SIT_SICONV"], dtype="string")
        sg = pd.array(["SIT_SIGCON"], dtype="string")
        res = _coalesce(pd.Series(sv), pd.Series(sg))
        assert res[0] == "SIT_SICONV"

    def test_siconv_nulo_usa_sigcon(self):
        sv = pd.array([pd.NA], dtype="string")
        sg = pd.array(["SIT_SIGCON"], dtype="string")
        res = _coalesce(pd.Series(sv), pd.Series(sg))
        assert res[0] == "SIT_SIGCON"

    def test_siconv_vazio_usa_sigcon(self):
        """String vazia deve ser tratada como ausente, igual a NA."""
        sv = pd.array([""], dtype="string")
        sg = pd.array(["SIT_SIGCON"], dtype="string")
        res = _coalesce(pd.Series(sv), pd.Series(sg))
        assert res[0] == "SIT_SIGCON"

    def test_ambos_nulos_resultado_na(self):
        sv = pd.array([pd.NA], dtype="string")
        sg = pd.array([pd.NA], dtype="string")
        res = _coalesce(pd.Series(sv), pd.Series(sg))
        assert pd.isna(res[0])

    def test_siconv_none_usa_sigcon(self):
        """siconv=None indica coluna ausente; deve usar sigcon diretamente."""
        sg = pd.array(["SIT_SIGCON"], dtype="string")
        res = _coalesce(None, pd.Series(sg))
        assert res[0] == "SIT_SIGCON"


class TestCoalesceNum:
    def test_siconv_presente(self):
        sv = pd.Series([100.0])
        sg = pd.Series([200.0])
        res = _coalesce_num(sv, sg)
        assert res[0] == 100.0

    def test_siconv_nan_usa_sigcon(self):
        sv = pd.Series([float("nan")])
        sg = pd.Series([200.0])
        res = _coalesce_num(sv, sg)
        assert res[0] == 200.0

    def test_ambos_nan(self):
        import math
        sv = pd.Series([float("nan")])
        sg = pd.Series([float("nan")])
        res = _coalesce_num(sv, sg)
        assert math.isnan(res[0])


# ---------------------------------------------------------------------------
# G_ fields via aplicar_campos_g
# ---------------------------------------------------------------------------

class TestGFields:
    def _base(self, siafi_uo="100010", codigo_siconv="999", instrumento=None):
        return _chaves([{
            "siafi_uo": siafi_uo,
            "siafi_uo_atual": siafi_uo,
            "codigo_siconv": codigo_siconv,
            "instrumento_chaves": instrumento,
            "situacao": "Em execução",
            "uo_nome_std": "SECRETARIA DE SAUDE",
            "unidade_orcamentaria_codigo": "1001",
        }])

    def _sgcn(self, siafi_uo="100010", **kwargs):
        dados = {"siafi_uo": siafi_uo}
        dados.update(kwargs)
        return _sigcon([dados])

    def _scnv(self, nr_convenio="999", **kwargs):
        dados = {"nr_convenio": nr_convenio}
        dados.update(kwargs)
        return _siconv([dados])

    # g_situacao_convenio
    def test_situacao_usa_siconv_se_presente(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_situacao="VIGENTE")
        scnv = self._scnv(siconv_situacao="ADIMPLENTE")
        res = aplicar_campos_g(base, sgcn, scnv)
        assert res["g_situacao_convenio"][0] == "ADIMPLENTE"

    def test_situacao_fallback_sigcon(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_situacao="VIGENTE")
        # siconv sem situação
        res = aplicar_campos_g(base, sgcn)
        assert res["g_situacao_convenio"][0] == "VIGENTE"

    def test_situacao_ambos_nulos(self):
        base = self._base()
        sgcn = self._sgcn()
        res = aplicar_campos_g(base, sgcn)
        assert pd.isna(res["g_situacao_convenio"][0])

    # g_valor_global (numérico)
    def test_valor_global_usa_siconv(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_valor_global=100_000.0)
        scnv = self._scnv(siconv_valor_global=200_000.0)
        res = aplicar_campos_g(base, sgcn, scnv)
        assert res["g_valor_global"][0] == 200_000.0

    def test_valor_global_fallback_sigcon(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_valor_global=100_000.0)
        res = aplicar_campos_g(base, sgcn)
        assert res["g_valor_global"][0] == 100_000.0

    # g_instrumento: fallback para 'Convênio de Entrada' quando null
    def test_instrumento_default_quando_nulo(self):
        base = self._base(instrumento=None)
        sgcn = self._sgcn()
        res = aplicar_campos_g(base, sgcn)
        assert res["g_instrumento"][0] == "Convênio de Entrada"

    def test_instrumento_preserva_valor_informado(self):
        base = self._base(instrumento="Acordo / Ajuste")
        sgcn = self._sgcn()
        res = aplicar_campos_g(base, sgcn)
        assert res["g_instrumento"][0] == "Acordo / Ajuste"

    # g_esfera: fallback para 'Federal' quando null
    def test_esfera_default_quando_nulo(self):
        base = self._base()
        sgcn = self._sgcn()
        res = aplicar_campos_g(base, sgcn)
        assert res["g_esfera"][0] == "Federal"

    def test_esfera_preserva_valor_informado(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_esfera="Estadual")
        res = aplicar_campos_g(base, sgcn)
        assert res["g_esfera"][0] == "Estadual"

    # g_vigencia (derivado de data)
    def test_vigencia_vigente(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_data_real_convenio=_VIGENTE)
        res = aplicar_campos_g(base, sgcn)
        assert res["g_vigencia"][0] == "Vigente"

    def test_vigencia_vencido(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_data_real_convenio=_VENCIDO)
        res = aplicar_campos_g(base, sgcn)
        assert res["g_vigencia"][0] == "Vencido"

    def test_vigencia_usa_siconv_quando_presente(self):
        """SICONV tem precedência mesmo para a data de fim que rege a vigência."""
        base = self._base()
        sgcn = self._sgcn(sigcon_data_real_convenio=_VENCIDO)
        scnv = self._scnv(siconv_data_fim_vigencia=_VIGENTE)
        res = aplicar_campos_g(base, sgcn, scnv)
        assert res["g_vigencia"][0] == "Vigente"

    # g_proponente: SICONV nm_proponente → fallback uo_nome_std
    def test_proponente_usa_siconv(self):
        base = self._base()
        sgcn = self._sgcn()
        scnv = self._scnv(siconv_proponente="PREFEITURA DE BH")
        res = aplicar_campos_g(base, sgcn, scnv)
        assert res["g_proponente"][0] == "PREFEITURA DE BH"

    def test_proponente_fallback_uo_nome_std(self):
        base = self._base()  # uo_nome_std = "SECRETARIA DE SAUDE"
        sgcn = self._sgcn()
        res = aplicar_campos_g(base, sgcn)
        assert res["g_proponente"][0] == "SECRETARIA DE SAUDE"

    # limpeza_g
    def test_limpeza_g_1_quando_sem_datas(self):
        base = self._base()
        sgcn = self._sgcn()  # sem nenhuma data
        res = aplicar_campos_g(base, sgcn)
        assert res["limpeza_g"][0] == 1

    def test_limpeza_g_0_quando_tem_data_fim(self):
        base = self._base()
        sgcn = self._sgcn(sigcon_data_real_convenio=_VIGENTE)
        res = aplicar_campos_g(base, sgcn)
        assert res["limpeza_g"][0] == 0


# ---------------------------------------------------------------------------
# Anti-fan-out
# ---------------------------------------------------------------------------

class TestFanOut:
    def test_join_sigcon_nao_multiplica_linhas(self):
        """Join com sigcon_completo não deve aumentar nº de linhas."""
        n = 5
        base = _chaves([{
            "siafi_uo": str(i),
            "siafi_uo_atual": str(i),
            "codigo_siconv": str(i),
            "unidade_orcamentaria_codigo": "1001",
        } for i in range(n)])
        # sigcon com uma linha por siafi_uo (deduplicated)
        sgcn = _sigcon([{"siafi_uo": str(i)} for i in range(n)])
        res = aplicar_campos_g(base, sgcn)
        assert len(res) == n, f"Fan-out detectado: {n} → {len(res)} linhas"

    def test_join_siconv_nao_multiplica_linhas(self):
        """Join com siconv também não deve aumentar nº de linhas."""
        n = 3
        base = _chaves([{
            "siafi_uo": str(i),
            "siafi_uo_atual": str(i),
            "codigo_siconv": str(i),
        } for i in range(n)])
        sgcn = _sigcon([{"siafi_uo": str(i)} for i in range(n)])
        scnv = _siconv([{"nr_convenio": str(i)} for i in range(n)])
        res = aplicar_campos_g(base, sgcn, scnv)
        assert len(res) == n


# ---------------------------------------------------------------------------
# A_ fields via aplicar_campos_a
# ---------------------------------------------------------------------------

class TestAFields:
    def _df_com_g(self):
        """Tabela G_ mínima com 2 convênios: um com SIAFI substituído."""
        return pd.DataFrame({
            "siafi_uo": pd.array(["100010", "200020"], dtype="string"),
            "siafi_uo_atual": pd.array(["300030", "200020"], dtype="string"),
            "g_situacao_convenio": pd.array(["VIGENTE", "BLOQUEADO"], dtype="string"),
            "g_valor_global": [100_000.0, 50_000.0],
            "g_fim_vigencia": pd.array([_VIGENTE, _VENCIDO], dtype="string"),
            "g_instrumento": pd.array(["Acordo / Ajuste", "Convênio de Entrada"], dtype="string"),
        })

    def test_a_situacao_copiada_de_g(self):
        """Convênio sem substituição de SIAFI: A_ == G_."""
        df = self._df_com_g()
        res = aplicar_campos_a(df)
        # Linha 2 (200020→200020): A_ = G_ do próprio registro
        linha = res[res["siafi_uo"] == "200020"].iloc[0]
        assert linha["a_situacao_convenio"] == "BLOQUEADO"

    def test_a_valor_copiado_de_g(self):
        """A_valor_global deve vir da linha cuja siafi_uo == siafi_uo_atual."""
        df = self._df_com_g()
        res = aplicar_campos_a(df)
        # Linha 2 (200020→200020): A_valor = 50_000
        linha = res[res["siafi_uo"] == "200020"].iloc[0]
        assert linha["a_valor_global"] == 50_000.0

    def test_a_fallback_quando_atual_nao_existe(self):
        """
        Se siafi_uo_atual não existe no dataset (ex.: SIAFI substituído e o
        novo não tem linha própria), A_ fica com o valor G_ da própria linha.
        """
        df = self._df_com_g()
        res = aplicar_campos_a(df)
        # Linha 1 (100010→300030): 300030 não existe como siafi_uo no dataset
        # → A_ = G_ da própria linha
        linha = res[res["siafi_uo"] == "100010"].iloc[0]
        assert linha["a_situacao_convenio"] == "VIGENTE"
        assert linha["a_valor_global"] == 100_000.0

    def test_a_fan_out_nao_ocorre(self):
        """aplicar_campos_a não deve multiplicar linhas."""
        df = self._df_com_g()
        res = aplicar_campos_a(df)
        assert len(res) == len(df)

    def test_df_sem_g_passa_inalterado(self):
        """Se não há colunas G_, retorna o DataFrame sem alteração."""
        df = pd.DataFrame({"siafi_uo": pd.array(["1"], dtype="string"), "outra": ["x"]})
        res = aplicar_campos_a(df)
        assert list(res.columns) == list(df.columns)
