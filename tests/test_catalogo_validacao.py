import pytest

from apps.grp.validacao.catalogo import TESTES


class TestIdUnicos:
    def test_ids_unicos(self):
        ids = [t["id"] for t in TESTES]
        assert len(ids) == len(
            set(ids)
        ), f"IDs repetidos: {[x for x in ids if ids.count(x) > 1]}"


class TestEstrutura:
    @pytest.mark.parametrize("teste", TESTES, ids=lambda t: t["id"])
    def test_campos_obrigatorios(self, teste):
        for campo in ("id", "severidade", "tabela", "descricao"):
            assert campo in teste, f"{teste.get('id', '???')}: falta '{campo}'"

    @pytest.mark.parametrize("teste", TESTES, ids=lambda t: t["id"])
    def test_severidade_valida(self, teste):
        assert teste["severidade"] in (
            "ERRO",
            "ALERTA",
        ), f"{teste['id']}: severidade '{teste['severidade']}' inválida"

    @pytest.mark.parametrize("teste", TESTES, ids=lambda t: t["id"])
    def test_sql_ou_funcao_exclusivo(self, teste):
        tem_sql = "sql" in teste
        tem_funcao = "funcao" in teste
        assert (
            tem_sql ^ tem_funcao
        ), f"{teste['id']}: deve ter exatamente uma de 'sql' ou 'funcao'"

    @pytest.mark.parametrize("teste", TESTES, ids=lambda t: t["id"])
    def test_sql_sem_ponto_virgula(self, teste):
        if "sql" not in teste:
            pytest.skip("teste funcional, sem sql")
        assert (
            not teste["sql"].strip().endswith(";")
        ), f"{teste['id']}: SQL termina com ';' — o motor embrulha numa subconsulta"


class TestSeveridadeVsModel:
    def test_valores_catalogo_pertencem_aos_choices(self):
        from apps.grp.models import ResultadoValidacao

        field = ResultadoValidacao._meta.get_field("severidade")
        if not field.choices:
            pytest.skip("campo sem choices")
        valores_validos = {c[0] for c in field.choices}
        for teste in TESTES:
            assert (
                teste["severidade"] in valores_validos
            ), f"{teste['id']}: '{teste['severidade']}' fora dos choices do model"
