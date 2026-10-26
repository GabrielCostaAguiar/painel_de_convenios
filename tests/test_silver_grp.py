import pytest
import pandas as pd
import yaml

from core.transform.silver import _para_numero

# ---------------------------------------------------------------------------
# Testes existentes: _para_numero (12 casos)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("1.234,56", "1234.56"),
        ("78.320.050", "78320050"),
        ("744684.0", "744684.0"),
        ("1.827", "1.827"),
        ("1,5", "1.5"),
        ("0,00", "0.00"),
        ("-3", "-3"),
        ("N/A", "N/A"),
        ("", ""),
        (" 10,00 ", " 10.00 "),
        (None, None),
    ],
)
def test_para_numero(entrada, esperado):
    assert _para_numero(entrada) == esperado


def test_para_numero_vira_numero():
    assert float(_para_numero("1.234,56")) == pytest.approx(1234.56)


# ---------------------------------------------------------------------------
# Fixture: fonte fictícia com schema YAML + CSV bronze em tmp_path
# ---------------------------------------------------------------------------
#
# CSV layout (6 colunas):
#   row 0: datas/valor/milhar/id-zeros/texto/SIM
#   row 1: dayfirst/simples/simples-int/id-.0/texto/NÃO
#   row 2: data-inválida/zero/milhar2/id-vazio/texto/NAO
#   row 3: tudo vazio (descartada pelo dropna)
#   row 4: N/A em vários / flag vazio
#   row 5: data vazia / 2020.0 / id com espaços / SIM
#
# Após dropna (row 3 removida) os iloc ficam [0,1,2,3→row4,4→row5]

_SCHEMA_YAML = {
    "fonte": "fonte_teste",
    "gerado_em": "2026-10-26",
    "colunas": {
        "data": ["col_data"],
        "valor": ["col_valor"],
        "inteiro": ["col_inteiro"],
        "identificador": ["col_id"],
    },
    "duvidoso": [],
    "renomear": {
        "col_data": "dt_teste",
        "col_valor": "vl_teste",
        "col_inteiro": "nr_teste",
        "col_id": "cd_teste",
        "col_texto": "ds_teste",
        "col_flag": "fl_teste",
    },
}

_CSV = """\
col_data,col_valor,col_inteiro,col_id,col_texto,col_flag
25/03/2026,"1.234,56",1.827,0000102,abc,SIM
05/03/2026,999,2020,102.0,def,NÃO
31/02/2026,0,24.866, ,ghi,NAO
,,,,,
N/A,100,N/A,,jkl,
,200,2020.0, 0000103 ,mno,SIM"""


@pytest.fixture
def fonte_teste(tmp_path, monkeypatch):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    with (schema_dir / "fonte_teste.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(_SCHEMA_YAML, f, allow_unicode=True)

    csv_file = tmp_path / "fonte_teste_20261026.csv"
    csv_file.write_text(_CSV, encoding="utf-8")

    import core.transform.silver as silver_mod

    monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)

    return csv_file


def _transformar(bronze_path):
    from core.transform.silver import transformar_fonte

    return transformar_fonte("fonte_teste", bronze_path=bronze_path)


# --- Datas (5 casos) ---


class TestDatas:
    def test_data_dia_maior_que_12(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["dt_teste"].iloc[0] == pd.Timestamp("2026-03-25")

    def test_data_dayfirst(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["dt_teste"].iloc[1] == pd.Timestamp("2026-03-05")

    def test_data_invalida_vira_nat(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert pd.isna(df["dt_teste"].iloc[2])

    def test_data_na_vira_nat(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert pd.isna(df["dt_teste"].iloc[3])

    def test_data_vazia_vira_nat(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert pd.isna(df["dt_teste"].iloc[4])


# --- Inteiros (7 casos, dtype Int64) ---


class TestInteiros:
    def test_milhar_1827(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["nr_teste"].iloc[0] == 1827
        assert df["nr_teste"].dtype == pd.Int64Dtype()

    def test_milhar_24866(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["nr_teste"].iloc[2] == 24866

    def test_inteiro_simples(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["nr_teste"].iloc[1] == 2020

    def test_na_vira_nulo(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert pd.isna(df["nr_teste"].iloc[3])

    def test_2020_ponto_zero(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["nr_teste"].iloc[4] == 2020

    def test_1_5_levanta_erro(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_erro",
            "gerado_em": "2026-10-26",
            "colunas": {"inteiro": ["col_int"]},
            "duvidoso": [],
            "renomear": {},
        }
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        with (schema_dir / "fonte_erro.yaml").open("w", encoding="utf-8") as f:
            yaml.dump(schema, f, allow_unicode=True)

        csv = tmp_path / "fonte_erro_20261026.csv"
        csv.write_text("col_int\n1.5\n", encoding="utf-8")

        import core.transform.silver as silver_mod

        monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)

        from core.transform.silver import transformar_fonte

        with pytest.raises(Exception):
            transformar_fonte("fonte_erro", bronze_path=csv)

    def test_vazio_vira_nulo(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_vazio",
            "gerado_em": "2026-10-26",
            "colunas": {"inteiro": ["col_int"]},
            "duvidoso": [],
            "renomear": {},
        }
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        with (schema_dir / "fonte_vazio.yaml").open("w", encoding="utf-8") as f:
            yaml.dump(schema, f, allow_unicode=True)

        csv = tmp_path / "fonte_vazio_20261026.csv"
        csv.write_text("col_int,col_extra\n,abc\n2020,def\n", encoding="utf-8")

        import core.transform.silver as silver_mod

        monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)

        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_vazio", bronze_path=csv)
        assert pd.isna(df["col_int"].iloc[0])
        assert df["col_int"].iloc[1] == 2020


# --- Valores (1 caso) ---


class TestValores:
    def test_valor_brasileiro(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["vl_teste"].iloc[0] == pytest.approx(1234.56)
        assert df["vl_teste"].dtype == "float64"


# --- Identificadores (4 casos) ---


class TestIdentificadores:
    def test_preserva_zeros(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["cd_teste"].iloc[0] == "0000102"

    def test_remove_ponto_zero(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["cd_teste"].iloc[1] == "102"

    def test_vazio_vira_nulo(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert pd.isna(df["cd_teste"].iloc[3])

    def test_strip_espacos(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["cd_teste"].iloc[4] == "0000103"


# --- Linhas 100% vazias ---


class TestLinhasVazias:
    def test_linha_vazia_descartada(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert len(df) == 5


# --- Renomeação ---


class TestRenomeacao:
    def test_colunas_renomeadas(self, fonte_teste):
        df = _transformar(fonte_teste)
        esperadas = {
            "dt_teste",
            "vl_teste",
            "nr_teste",
            "cd_teste",
            "ds_teste",
            "fl_teste",
        }
        assert esperadas.issubset(set(df.columns))


# --- Flags SIM/NÃO (6 casos) ---
# MAPA_BOOLEANO = {"SIM": True, "NÃO": False, "NAO": False}
# Valores inesperados levantam ValueError (não silenciam como True/False).
# Comparações usam == porque o dtype "boolean" devolve np.True_/np.False_.


class TestFlags:
    def test_sim_vira_true(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["fl_teste"].iloc[0] == True  # noqa: E712

    def test_nao_com_acento_vira_false(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["fl_teste"].iloc[1] == False  # noqa: E712

    def test_nao_sem_acento_vira_false(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["fl_teste"].iloc[2] == False  # noqa: E712

    def test_vazio_vira_nulo(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert pd.isna(df["fl_teste"].iloc[3])

    def test_sim_ultima_linha(self, fonte_teste):
        df = _transformar(fonte_teste)
        assert df["fl_teste"].iloc[4] == True  # noqa: E712

    @pytest.mark.xfail(
        reason="Valor inesperado em fl_ levanta ValueError (correto — não silencia lixo). "
        "O teste documenta que a validação acontece.",
        strict=True,
    )
    def test_valor_inesperado_levanta_erro(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_flag",
            "gerado_em": "2026-10-26",
            "colunas": {},
            "duvidoso": [],
            "renomear": {"col_flag": "fl_flag"},
        }
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        with (schema_dir / "fonte_flag.yaml").open("w", encoding="utf-8") as f:
            yaml.dump(schema, f, allow_unicode=True)

        csv = tmp_path / "fonte_flag_20261026.csv"
        csv.write_text("col_flag\nTALVEZ\n", encoding="utf-8")

        import core.transform.silver as silver_mod

        monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)

        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_flag", bronze_path=csv)
        assert df["fl_flag"].iloc[0] == True  # noqa: E712
