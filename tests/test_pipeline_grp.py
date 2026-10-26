import pytest
from unittest.mock import call as mock_call

from django.core.management.base import CommandError


class TestPipelineTudoPassa:
    def test_todas_etapas_chamadas_em_ordem(self, monkeypatch):
        chamadas = []

        def fake_call_command(nome, *args, **kwargs):
            chamadas.append(nome)

        monkeypatch.setattr(
            "apps.grp.management.commands.pipeline_grp.call_command",
            fake_call_command,
        )
        monkeypatch.setattr(
            "apps.grp.management.commands.pipeline_grp.ETAPAS",
            ["carregar_grp", "validar_grp", "etapa_depois"],
        )

        from django.core.management import call_command

        call_command("pipeline_grp")

        assert chamadas == ["carregar_grp", "validar_grp", "etapa_depois"]


class TestPipelineErro:
    def test_erro_propaga_e_para(self, monkeypatch):
        chamadas = []

        def fake_call_command(nome, *args, **kwargs):
            chamadas.append(nome)
            if nome == "validar_grp":
                raise CommandError("falha no validar")

        monkeypatch.setattr(
            "apps.grp.management.commands.pipeline_grp.call_command",
            fake_call_command,
        )
        monkeypatch.setattr(
            "apps.grp.management.commands.pipeline_grp.ETAPAS",
            ["carregar_grp", "validar_grp", "etapa_depois"],
        )

        from django.core.management import call_command

        with pytest.raises(CommandError, match="falha no validar"):
            call_command("pipeline_grp")

        assert "etapa_depois" not in chamadas
        assert chamadas == ["carregar_grp", "validar_grp"]
