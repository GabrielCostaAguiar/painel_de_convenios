import logging

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

    def test_dayfirst_isolado(self, tmp_path, monkeypatch):
        """Data ambígua como ÚNICA da coluna: sem datas não-ambíguas, o pandas
        não consegue inferir o formato e depende exclusivamente de dayfirst."""
        schema = {
            "fonte": "fonte_dayfirst",
            "gerado_em": "2026-10-26",
            "colunas": {"data": ["col_data"]},
            "duvidoso": [],
            "renomear": {},
        }
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        with (schema_dir / "fonte_dayfirst.yaml").open("w", encoding="utf-8") as f:
            yaml.dump(schema, f, allow_unicode=True)

        csv = tmp_path / "fonte_dayfirst_20261026.csv"
        csv.write_text("col_data\n05/03/2026\n", encoding="utf-8")

        import core.transform.silver as silver_mod

        monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)

        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_dayfirst", bronze_path=csv)
        ts = df["col_data"].iloc[0]
        assert ts.month == 3, f"Esperado março (3), obteve mês {ts.month}"
        assert ts.day == 5, f"Esperado dia 5, obteve dia {ts.day}"


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

    def _fonte_flag(self, tmp_path, monkeypatch, valor):
        """Helper: cria fonte com uma única linha na coluna fl_flag."""
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
        csv.write_text(f"col_flag\n{valor}\n", encoding="utf-8")

        import core.transform.silver as silver_mod

        monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)
        return csv

    def test_valor_inesperado_levanta_erro(self, tmp_path, monkeypatch):
        csv = self._fonte_flag(tmp_path, monkeypatch, "TALVEZ")
        from core.transform.silver import transformar_fonte

        with pytest.raises(ValueError, match="fl_flag"):
            transformar_fonte("fonte_flag", bronze_path=csv)

    def test_minusculo_sim_levanta_erro(self, tmp_path, monkeypatch):
        """'sim' em minúsculo não está no MAPA_BOOLEANO (case-sensitive)."""
        csv = self._fonte_flag(tmp_path, monkeypatch, "sim")
        from core.transform.silver import transformar_fonte

        with pytest.raises(ValueError, match="fl_flag"):
            transformar_fonte("fonte_flag", bronze_path=csv)


# ---------------------------------------------------------------------------
# Blocos novos da Fase 2 (Modelo de Extração das Bases Legadas v1.0):
# sentinelas, booleanos, descartar, descartar_linhas_se_nulo, grao,
# derivadas, desdobrar, quarentena, dedup de linhas idênticas.
# ---------------------------------------------------------------------------


def _criar_fonte(tmp_path, monkeypatch, nome, schema, csv_texto):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir(exist_ok=True)
    with (schema_dir / f"{nome}.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(schema, f, allow_unicode=True)

    csv_file = tmp_path / f"{nome}_20261026.csv"
    csv_file.write_text(csv_texto, encoding="utf-8")

    import core.transform.silver as silver_mod

    monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)
    return csv_file


class TestSentinelas:
    """'sentinelas:' por coluna substitui o conjunto global SENTINELAS."""

    def test_override_anula_valor_que_nao_e_sentinela_global(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_sentinela",
            "colunas": {"identificador": ["col_id"]},
            "sentinelas": {"col_id": ["99999999"]},
            "renomear": {"col_id": "cd_id", "col_outro": "cd_outro"},
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_sentinela", schema,
            "col_id,col_outro\n99999999,a\n102,b\nN/A,c\n",
        )
        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_sentinela", bronze_path=csv)
        # "99999999" é anulado pelo override; "N/A" (sentinela global) NÃO é,
        # porque o override substitui a lista inteira para esta coluna. A
        # 2ª coluna preenchida evita que a linha inteira seja descartada
        # por ficar 100% vazia depois da tipagem.
        assert len(df) == 3
        assert pd.isna(df["cd_id"].iloc[0])
        assert df["cd_id"].iloc[1] == "102"
        assert df["cd_id"].iloc[2] == "N/A"

    def test_sem_override_usa_sentinela_global(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_sem_override",
            "colunas": {"identificador": ["col_id"]},
            "renomear": {"col_id": "cd_id", "col_outro": "cd_outro"},
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_sem_override", schema,
            "col_id,col_outro\nN/A,a\n102,b\n",
        )
        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_sem_override", bronze_path=csv)
        assert len(df) == 2
        assert pd.isna(df["cd_id"].iloc[0])
        assert df["cd_id"].iloc[1] == "102"


class TestBooleanos:
    """'booleanos:' por coluna substitui o de-para MAPA_BOOLEANO para a coluna."""

    def test_override_aceita_vocabulario_diferente(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_bool_override",
            "colunas": {"identificador": ["col_id"]},
            "booleanos": {"fl_siconv": {"Sim": True, "Nao": False, "Não": False}},
            "renomear": {"col_id": "cd_id", "col_flag": "fl_siconv"},
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_bool_override", schema,
            "col_id,col_flag\n1,Sim\n2,Nao\n3,Não\n",
        )
        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_bool_override", bronze_path=csv)
        assert list(df["fl_siconv"]) == [True, False, False]

    def test_valor_fora_do_override_levanta_erro(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_bool_erro",
            "colunas": {},
            "booleanos": {"fl_siconv": {"Sim": True, "Nao": False}},
            "renomear": {"col_flag": "fl_siconv"},
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_bool_erro", schema, "col_flag\nSIM\n",
        )
        from core.transform.silver import transformar_fonte

        with pytest.raises(ValueError, match="fl_siconv"):
            transformar_fonte("fonte_bool_erro", bronze_path=csv)


class TestDescartar:
    def test_coluna_listada_e_removida(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_descartar",
            "colunas": {},
            "renomear": {"col_a": "cd_a", "col_b": "cd_b"},
            "descartar": ["cd_b"],
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_descartar", schema, "col_a,col_b\n1,2\n",
        )
        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_descartar", bronze_path=csv)
        assert "cd_b" not in df.columns
        assert "cd_a" in df.columns

    def test_coluna_ausente_so_gera_warning(self, tmp_path, monkeypatch, caplog):
        schema = {
            "fonte": "fonte_descartar_ausente",
            "colunas": {},
            "renomear": {"col_a": "cd_a"},
            "descartar": ["nao_existe"],
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_descartar_ausente", schema, "col_a\n1\n",
        )
        from core.transform.silver import transformar_fonte

        with caplog.at_level(logging.WARNING):
            df = transformar_fonte("fonte_descartar_ausente", bronze_path=csv)
        assert "cd_a" in df.columns
        assert "nao_existe" in caplog.text


class TestDescartarLinhasSeNulo:
    def test_linha_com_nulo_na_coluna_e_removida(self, tmp_path, monkeypatch):
        # Chave BRUTA (pré-renomear): o bloco roda antes da tipagem — ver
        # core/transform/silver.py.
        schema = {
            "fonte": "fonte_obrigatoria",
            "colunas": {"identificador": ["col_chave"]},
            "renomear": {"col_chave": "cd_chave", "col_outro": "cd_outro"},
            "descartar_linhas_se_nulo": ["col_chave"],
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_obrigatoria", schema,
            "col_chave,col_outro\n1,a\n,b\n2,c\n",
        )
        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_obrigatoria", bronze_path=csv)
        assert len(df) == 2
        assert set(df["cd_chave"]) == {"1", "2"}


class TestGrao:
    def test_chave_repetida_gera_alerta_mas_nao_remove(self, tmp_path, monkeypatch, caplog):
        schema = {
            "fonte": "fonte_grao",
            "colunas": {"identificador": ["col_chave", "col_extra"]},
            "renomear": {"col_chave": "cd_chave", "col_extra": "cd_extra"},
            "grao": ["cd_chave"],
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_grao", schema,
            "col_chave,col_extra\n1,a\n1,b\n2,c\n",
        )
        from core.transform.silver import transformar_fonte

        with caplog.at_level(logging.WARNING):
            df = transformar_fonte("fonte_grao", bronze_path=csv)
        assert len(df) == 3  # nada foi removido
        assert "ALERTA" in caplog.text

    def test_chave_unica_nao_gera_alerta(self, tmp_path, monkeypatch, caplog):
        schema = {
            "fonte": "fonte_grao_ok",
            "colunas": {"identificador": ["col_chave"]},
            "renomear": {"col_chave": "cd_chave"},
            "grao": ["cd_chave"],
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_grao_ok", schema, "col_chave\n1\n2\n",
        )
        from core.transform.silver import transformar_fonte

        with caplog.at_level(logging.WARNING):
            transformar_fonte("fonte_grao_ok", bronze_path=csv)
        assert "ALERTA" not in caplog.text


class TestDerivadas:
    def test_siafi_uo_concatena_nr_siafi_e_cd_uo(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_derivada",
            "colunas": {"identificador": ["col_siafi", "col_uo"]},
            "renomear": {"col_siafi": "nr_siafi", "col_uo": "cd_uo"},
            "derivadas": {
                "siafi_uo": {"funcao": "montar_siafi_uo", "args": ["nr_siafi", "cd_uo"]},
            },
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_derivada", schema,
            "col_siafi,col_uo\n9309074,1261\n,1261\n",
        )
        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_derivada", bronze_path=csv)
        assert df["siafi_uo"].iloc[0] == "93090741261"
        assert pd.isna(df["siafi_uo"].iloc[1])


class TestDedupLinhasIdenticas:
    def test_linhas_100_porcento_iguais_colapsam_em_uma(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_dedup",
            "colunas": {"identificador": ["col_a"]},
            "renomear": {"col_a": "cd_a", "col_b": "cd_b"},
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_dedup", schema,
            "col_a,col_b\n1,x\n1,x\n2,y\n",
        )
        from core.transform.silver import transformar_fonte

        df = transformar_fonte("fonte_dedup", bronze_path=csv)
        assert len(df) == 2


class TestQuarentena:
    def test_grao_com_destino_divergente_vai_pra_quarentena(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_quarentena",
            "colunas": {"identificador": ["col_origem", "col_destino"]},
            "renomear": {"col_origem": "siafi_uo_origem", "col_destino": "siafi_uo_atual"},
            "quarentena": {"grao": ["siafi_uo_origem"], "destino": ["siafi_uo_atual"]},
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_quarentena", schema,
            # "A" aponta pra "X" e "Y" (divergente) -> quarentena
            # "B" aponta sempre pra "Z" (mesmo destino, linhas idênticas -> dedup, não quarentena)
            "col_origem,col_destino\nA,X\nA,Y\nB,Z\nB,Z\n",
        )
        from core.transform.silver import transformar_fonte_completo

        resultado = transformar_fonte_completo("fonte_quarentena", bronze_path=csv)
        principal, quarentena = resultado["principal"], resultado["quarentena"]

        assert len(principal) == 1
        assert principal["siafi_uo_origem"].iloc[0] == "B"
        assert quarentena is not None
        assert len(quarentena) == 2
        assert set(quarentena["siafi_uo_origem"]) == {"A"}

    def test_sem_divergencia_quarentena_fica_none(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_sem_quarentena",
            "colunas": {"identificador": ["col_origem", "col_destino"]},
            "renomear": {"col_origem": "siafi_uo_origem", "col_destino": "siafi_uo_atual"},
            "quarentena": {"grao": ["siafi_uo_origem"], "destino": ["siafi_uo_atual"]},
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_sem_quarentena", schema,
            "col_origem,col_destino\nA,X\nB,Z\n",
        )
        from core.transform.silver import transformar_fonte_completo

        resultado = transformar_fonte_completo("fonte_sem_quarentena", bronze_path=csv)
        assert resultado["quarentena"] is None
        assert len(resultado["principal"]) == 2


class TestDesdobrar:
    def test_gera_uma_linha_por_celula_preenchida(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "fonte_desdobrar",
            "colunas": {"identificador": ["col_chave"]},
            "renomear": {"col_chave": "nr_sei"},
            "desdobrar": {
                "chave": ["nr_sei"],
                "valor": "nr_documento_sei",
                "mapa": [
                    {"coluna": "instrumento", "tp_documento": "Instrumento", "nr_ordem": 1},
                    {"coluna": "instrumento_2", "tp_documento": "Instrumento", "nr_ordem": 2},
                ],
            },
        }
        csv = _criar_fonte(
            tmp_path, monkeypatch, "fonte_desdobrar", schema,
            "col_chave,instrumento,instrumento_2\n1,PT 12767,\n2,ABC,DEF\n",
        )
        from core.transform.silver import transformar_fonte_completo

        resultado = transformar_fonte_completo("fonte_desdobrar", bronze_path=csv)
        desdobrado = resultado["desdobrado"]

        assert desdobrado is not None
        # linha 1 só preenche "instrumento" (1 linha); linha 2 preenche os dois (2 linhas) = 3
        assert len(desdobrado) == 3
        assert set(desdobrado["tp_documento"]) == {"Instrumento"}
        linha_pt = desdobrado[desdobrado["nr_documento_sei"] == "PT 12767"]
        assert linha_pt["nr_ordem"].iloc[0] == 1

    def test_fonte_sem_desdobrar_devolve_none(self, fonte_teste):
        from core.transform.silver import transformar_fonte_completo

        resultado = transformar_fonte_completo("fonte_teste", bronze_path=fonte_teste)
        assert resultado["desdobrado"] is None
