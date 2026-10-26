import pytest
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError


def _fazer_teste(id_, severidade, qt_falhas):
    return {
        "id": id_,
        "severidade": severidade,
        "tabela": "t_mock",
        "descricao": "teste mock",
        "sql": "SELECT 1",
    }


@pytest.fixture
def mock_portao(monkeypatch):
    mock_modelo = MagicMock()
    monkeypatch.setattr(
        "apps.grp.management.commands.validar_grp.ResultadoValidacao",
        mock_modelo,
    )

    def _setup(testes, resultados):
        monkeypatch.setattr(
            "apps.grp.management.commands.validar_grp.TESTES",
            testes,
        )

        call_count = {"n": 0}
        results_iter = iter(resultados)

        def fake_rodar(self, sql):
            return next(results_iter)

        from apps.grp.management.commands.validar_grp import Command

        monkeypatch.setattr(Command, "_rodar", fake_rodar)
        return mock_modelo

    return _setup


class TestPortaoErroFalha:
    def test_erro_que_falha_levanta_command_error(self, mock_portao):
        testes = [_fazer_teste("T-X01", "ERRO", 0)]
        modelo = mock_portao(testes, [(3, [])])

        with pytest.raises(CommandError, match="T-X01"):
            call_command("validar_grp")

        modelo.objects.create.assert_called_once()
        kwargs = modelo.objects.create.call_args[1]
        assert kwargs["status"] == "FALHOU"


class TestPortaoAlertaFalha:
    def test_alerta_que_falha_nao_levanta_erro(self, mock_portao):
        testes = [_fazer_teste("T-X02", "ALERTA", 0)]
        modelo = mock_portao(testes, [(5, [])])

        call_command("validar_grp")

        modelo.objects.create.assert_called_once()
        kwargs = modelo.objects.create.call_args[1]
        assert kwargs["status"] == "FALHOU"


class TestPortaoErroPassa:
    def test_erro_que_passa_nao_levanta(self, mock_portao):
        testes = [_fazer_teste("T-X03", "ERRO", 0)]
        modelo = mock_portao(testes, [(0, [])])

        call_command("validar_grp")

        kwargs = modelo.objects.create.call_args[1]
        assert kwargs["status"] == "PASSOU"


class TestPortaoMisto:
    def test_mensagem_cita_so_id_do_erro(self, mock_portao):
        testes = [
            _fazer_teste("T-X04", "ERRO", 0),
            _fazer_teste("T-X05", "ALERTA", 0),
        ]
        modelo = mock_portao(testes, [(2, []), (3, [])])

        with pytest.raises(CommandError, match="T-X04") as exc_info:
            call_command("validar_grp")

        assert "T-X05" not in str(exc_info.value)
