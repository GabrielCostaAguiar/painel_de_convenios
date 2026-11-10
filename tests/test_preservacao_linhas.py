"""
Regra do dono dos dados: NENHUMA linha pode ser excluída em nenhuma camada, a
não ser a linha que não tem NENHUM dado em NENHUMA coluna.

"Linha 100% vazia" = todas as células do Bronze, inclusive as colunas Unnamed,
"" ou "N/A" depois de strip(), avaliadas no texto bruto antes de
sentinela/tipagem. Linha com qualquer outro texto (0, 9999, 99999999) fica.

Estes testes protegem a regra contra regressão. Diagnóstico e números:
docs/auditoria_exclusao_linhas.md.
"""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from core.transform import silver as silver_mod
from core.transform.silver import _SEM_DADO, transformar_fonte, transformar_fonte_completo


def _fonte(tmp_path, monkeypatch, nome, schema, csv_texto):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir(exist_ok=True)
    with (schema_dir / f"{nome}.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(schema, f, allow_unicode=True)
    csv = tmp_path / f"{nome}_20261026.csv"
    csv.write_text(csv_texto, encoding="utf-8")
    monkeypatch.setattr(silver_mod, "SCHEMAS_DIR", schema_dir)
    return csv


_SCHEMA = {
    "colunas": {"identificador": ["col_a"]},
    "renomear": {"col_a": "cd_a", "col_b": "cd_b"},
}


class TestLinhaVazia:
    def test_linha_vazia_e_removida(self, tmp_path, monkeypatch):
        csv = _fonte(
            tmp_path, monkeypatch, "f1", {"fonte": "f1", **_SCHEMA},
            "col_a,col_b\n1,x\n,\n2,y\n",
        )
        assert len(transformar_fonte("f1", bronze_path=csv)) == 2

    def test_linha_so_com_espacos_e_vazia(self, tmp_path, monkeypatch):
        csv = _fonte(
            tmp_path, monkeypatch, "f2", {"fonte": "f2", **_SCHEMA},
            "col_a,col_b\n1,x\n  ,\t\n2,y\n",
        )
        assert len(transformar_fonte("f2", bronze_path=csv)) == 2

    def test_dado_so_na_coluna_unnamed_nao_e_vazia(self, tmp_path, monkeypatch):
        csv = _fonte(
            tmp_path, monkeypatch, "f3", {"fonte": "f3", **_SCHEMA},
            "col_a,col_b,Unnamed: 0\n1,x,\n,,so-aqui\n,,\n",
        )
        df = transformar_fonte("f3", bronze_path=csv)
        # a linha só com a coluna Unnamed preenchida fica (toda nula nas colunas
        # reais); a 100% vazia sai
        assert len(df) == 2
        assert df["cd_a"].isna().iloc[1] and df["cd_b"].isna().iloc[1]


class TestLinhaSoComMarcadores:
    def test_linha_com_na_em_todas_as_colunas_e_vazia(self, tmp_path, monkeypatch):
        csv = _fonte(
            tmp_path, monkeypatch, "f4", {"fonte": "f4", **_SCHEMA},
            "col_a,col_b\n1,x\nN/A,N/A\n2,y\n",
        )
        assert len(transformar_fonte("f4", bronze_path=csv)) == 2

    def test_na_em_so_uma_coluna_nao_e_vazia(self, tmp_path, monkeypatch):
        csv = _fonte(
            tmp_path, monkeypatch, "f4b", {"fonte": "f4b", **_SCHEMA},
            "col_a,col_b\nN/A,x\n,N/A\n",
        )
        df = transformar_fonte("f4b", bronze_path=csv)
        assert len(df) == 1  # a 2ª (",N/A") é vazia; a 1ª tem "x"
        assert df["cd_b"].iloc[0] == "x"

    def test_9999_e_zero_ficam_toda_nulas_depois_da_sentinela(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "f5",
            "colunas": {"identificador": ["col_a", "col_b"]},
            "sentinelas": {"col_a": ["9999"], "col_b": ["99999999", "0"]},
            "renomear": {"col_a": "cd_a", "col_b": "cd_b"},
        }
        csv = _fonte(tmp_path, monkeypatch, "f5", schema, "col_a,col_b\n9999,99999999\n1,0\n")
        df = transformar_fonte("f5", bronze_path=csv)
        assert len(df) == 2
        assert df["cd_a"].isna().iloc[0] and df["cd_b"].isna().iloc[0]


class TestDuplicadas:
    def test_linhas_identicas_ficam_todas(self, tmp_path, monkeypatch):
        csv = _fonte(
            tmp_path, monkeypatch, "f6", {"fonte": "f6", **_SCHEMA},
            "col_a,col_b\n1,x\n1,x\n1,x\n2,y\n",
        )
        assert len(transformar_fonte("f6", bronze_path=csv)) == 4


class TestCabecalhoRepetido:
    def test_linha_que_repete_o_cabecalho_fica_marcada(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "f7",
            "colunas": {"identificador": ["col_chave"]},
            "renomear": {"col_chave": "cd_chave", "col_outro": "cd_outro"},
            "marcar_linhas_se_nulo": ["col_chave"],
        }
        csv = _fonte(
            tmp_path, monkeypatch, "f7", schema,
            "col_chave,col_outro\n1,a\nCol Chave,Col Outro\n2,b\n",
        )
        df = transformar_fonte("f7", bronze_path=csv)
        assert len(df) == 3
        assert df["ds_alerta_linha"].iloc[1] == "cabecalho_repetido"
        assert "Col Chave" in df["tx_linha_bruta"].iloc[1]
        assert df["ds_alerta_linha"].iloc[0] is pd.NA or pd.isna(df["ds_alerta_linha"].iloc[0])

    def test_sem_marcacao_declarada_so_gera_alerta_e_mantem(self, tmp_path, monkeypatch, caplog):
        import logging

        csv = _fonte(
            tmp_path, monkeypatch, "f8", {"fonte": "f8", **_SCHEMA},
            "col_a,col_b\n1,x\nCol A,Col B\n2,y\n",
        )
        with caplog.at_level(logging.WARNING):
            df = transformar_fonte("f8", bronze_path=csv)
        assert len(df) == 3
        assert "repetem o cabeçalho" in caplog.text
        assert "ds_alerta_linha" not in df.columns  # schema só muda com marcação declarada


class TestMultiplosMotivos:
    def test_motivos_se_acumulam_com_ponto_e_virgula(self, tmp_path, monkeypatch):
        schema = {
            "fonte": "f9",
            "colunas": {"identificador": ["col_chave", "col_x"]},
            "renomear": {"col_chave": "cd_chave", "col_x": "cd_x", "col_o": "cd_o"},
            "marcar_linhas_se_nulo": ["col_chave", "col_x"],
        }
        csv = _fonte(tmp_path, monkeypatch, "f9", schema, "col_chave,col_x,col_o\n,,z\n1,2,w\n")
        df = transformar_fonte("f9", bronze_path=csv)
        assert len(df) == 2
        assert df["ds_alerta_linha"].iloc[0] == (
            "chave_obrigatoria_vazia:col_chave;chave_obrigatoria_vazia:col_x"
        )


# ---------------------------------------------------------------------------
# Invariante com dado real: linhas(Silver) = linhas(Bronze) - linhas 100% vazias
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FONTES_COM_BRONZE = sorted(
    p.name
    for p in (_DATA_DIR / "bronze").glob("*")
    if p.is_dir()
    and (silver_mod.SCHEMAS_DIR / f"{p.name}.yaml").exists()
    and list(p.glob(f"{p.name}_*.csv"))
) if (_DATA_DIR / "bronze").exists() else []


@pytest.mark.skipif(not _FONTES_COM_BRONZE, reason="data/bronze/ não existe neste ambiente")
@pytest.mark.parametrize("nome", _FONTES_COM_BRONZE)
def test_silver_tem_todas_as_linhas_do_bronze_menos_as_vazias(nome, settings):
    settings.DATA_DIR = _DATA_DIR
    csv = sorted((_DATA_DIR / "bronze" / nome).glob(f"{nome}_*.csv"))[-1]
    bronze = pd.read_csv(csv, dtype=str, keep_default_na=False)
    vazias = int(bronze.apply(lambda c: c.str.strip().isin(_SEM_DADO)).all(axis=1).sum())

    resultado = transformar_fonte_completo(nome, bronze_path=csv)
    assert len(resultado["principal"]) == len(bronze) - vazias, (
        f"{nome}: o motor excluiu linhas com dado "
        f"(bronze {len(bronze)}, vazias {vazias}, silver {len(resultado['principal'])})"
    )
