import pytest

from apps.grp.validacao.generico import (
    sql_formato,
    sql_valores_aceitos,
    sql_orfaos,
    sql_sem_chave,
    sql_unicidade,
)


class TestSqlFormato:
    def test_regex_cnpj_uma_barra(self):
        sql = sql_formato("t", "c", r"^\d{14}$")
        assert r"^\d{14}$" in sql
        assert r"\\d" not in sql


class TestSqlValoresAceitos:
    def test_strings_com_aspas(self):
        sql = sql_valores_aceitos("t", "c", ["MG", "SP"])
        assert "('MG'" in sql or "'MG'" in sql
        assert "('SP'" in sql or "'SP'" in sql

    def test_range_numeros_sem_aspas(self):
        sql = sql_valores_aceitos("t", "c", range(0, 13))
        for i in range(0, 13):
            assert str(i) in sql
        assert "'" not in sql or sql.count("'") == 0


class TestSqlOrfaos:
    def test_contem_not_exists(self):
        sql = sql_orfaos(filha="f", col_filha="cf", pai="p", col_pai="cp")
        assert "NOT EXISTS" in sql

    def test_condicao_ligacao(self):
        sql = sql_orfaos(filha="f", col_filha="cf", pai="p", col_pai="cp")
        assert "p.cp = f.cf" in sql.replace(" ", "").replace("\n", "") or (
            "p.cp" in sql and "f.cf" in sql
        )

    def test_filtra_not_null_filha(self):
        sql = sql_orfaos(filha="f", col_filha="cf", pai="p", col_pai="cp")
        assert "cf IS NOT NULL" in sql


class TestSqlSemChave:
    def test_contem_coalesce(self):
        sql = sql_sem_chave("t")
        assert "COALESCE(nr_grp, cd_proposta) IS NULL" in sql


class TestSqlUnicidade:
    def test_mesmas_colunas_select_e_group_by(self):
        colunas = ["nr_grp", "cd_proposta", "nr_parcela"]
        sql = sql_unicidade("t", colunas)
        cols_str = "nr_grp, cd_proposta, nr_parcela"
        assert sql.count(cols_str) == 2

    def test_having_count(self):
        sql = sql_unicidade("t", ["a", "b"])
        assert "HAVING COUNT(*) > 1" in sql
