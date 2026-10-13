"""
Testes de _filtrar_nr_grp_multiplo.

Verificam a construção da query (parsing, dedup, limite, Q objects) sem
precisar de um banco — usam str(qs.query) sobre querysets lazy.
"""

import logging

import pytest
from django.db.models import QuerySet

from apps.grp.models import DadosGrp
from apps.grp.services import _filtrar_nr_grp_multiplo


def _qs() -> QuerySet:
    return DadosGrp.objects.all()


def _sql(qs: QuerySet) -> str:
    return str(qs.query).upper()


class TestSemFiltro:

    def test_vazio(self):
        resultado = _filtrar_nr_grp_multiplo(_qs(), "")
        assert "WHERE" not in _sql(resultado)

    def test_somente_espacos(self):
        resultado = _filtrar_nr_grp_multiplo(_qs(), "   ")
        assert "WHERE" not in _sql(resultado)

    def test_tabs_e_newlines(self):
        resultado = _filtrar_nr_grp_multiplo(_qs(), "\t \n ")
        assert "WHERE" not in _sql(resultado)

    def test_none(self):
        resultado = _filtrar_nr_grp_multiplo(_qs(), None)
        assert "WHERE" not in _sql(resultado)


class TestTermoUnico:

    def test_icontains_gerado(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "1000001"))
        assert "LIKE" in sql
        assert "1000001" in sql

    def test_sem_or(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "1000001"))
        assert sql.count("LIKE") == 1


class TestMultiplosTermos:

    def test_tres_termos(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "1000001 2000001 9999999"))
        assert "1000001" in sql
        assert "2000001" in sql
        assert "9999999" in sql
        assert sql.count("LIKE") == 3

    def test_or_entre_termos(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "AAA BBB"))
        assert " OR " in sql

    def test_espacos_multiplos(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "AAA    BBB"))
        assert "AAA" in sql
        assert "BBB" in sql
        assert sql.count("LIKE") == 2

    def test_tab_e_newline_como_separador(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "AAA\tBBB\nCCC"))
        assert sql.count("LIKE") == 3

    def test_duplicados_removidos(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "AAA AAA AAA"))
        assert sql.count("LIKE") == 1


class TestLimite200:

    def test_acima_do_limite_usa_200(self):
        termos = [f"T{i:04d}" for i in range(250)]
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), " ".join(termos)))
        assert sql.count("LIKE") == 200

    def test_log_aviso(self, caplog):
        termos = [f"T{i:04d}" for i in range(250)]
        with caplog.at_level(logging.WARNING, logger="apps.grp.services"):
            _filtrar_nr_grp_multiplo(_qs(), " ".join(termos))
        assert "250 termos" in caplog.text
        assert "200 primeiros" in caplog.text

    def test_exatamente_200_sem_aviso(self, caplog):
        termos = [f"T{i:04d}" for i in range(200)]
        with caplog.at_level(logging.WARNING, logger="apps.grp.services"):
            _filtrar_nr_grp_multiplo(_qs(), " ".join(termos))
        assert caplog.text == ""


class TestCampoCustomizado:

    def test_campo_nr_instrumento(self):
        sql = _sql(_filtrar_nr_grp_multiplo(_qs(), "INST-100", campo="nr_instrumento"))
        assert "NR_INSTRUMENTO" in sql
        assert "INST-100" in sql
