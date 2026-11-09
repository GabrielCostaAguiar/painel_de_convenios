"""
Comando `carregar_grp`: full refresh das tabelas do GRP a partir da Silver.

Os Parquets são sintéticos e mínimos, escritos em tmp_path com DATA_DIR
sobrescrito — nenhum dado real é tocado. Só duas fontes reais (grp_concedente
e grp_tabela_uo) ganham Parquet sintético; as demais, quando o teste precisa
rodar "todas", são substituídas por dublês que não tocam disco — gerar 21
Parquets sintéticos a cada teste não traria nenhuma garantia adicional.
"""
import logging
from unittest import mock

import pandas as pd
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.grp.management.commands import carregar_grp as cmd
from apps.grp.management.commands.carregar_grp import _LOADERS_GRP, FONTES_GRP
from apps.grp.models import GrpConcedente, GrpTabelaUo

_FONTES_REAIS = {"grp_concedente": GrpConcedente, "grp_tabela_uo": GrpTabelaUo}


def _gravar_silver_sintetico(diretorio, fonte: str, model, linhas: int = 2):
    """Parquet mínimo cujas colunas são os campos do model (loader genérico:
    carregar_tabela_generica exige que parquet e model tenham os mesmos nomes)."""
    campos = [f.name for f in model._meta.concrete_fields if f.name != "id"]
    dados = {campo: [f"{campo[:12]}-{i}" for i in range(linhas)] for campo in campos}
    destino = diretorio / "silver" / f"{fonte}.parquet"
    destino.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(dados).to_parquet(destino, index=False)
    return destino


@pytest.fixture
def data_dir_sintetico(tmp_path):
    """DATA_DIR isolado com Parquet sintético para as 2 fontes reais do teste."""
    for fonte, model in _FONTES_REAIS.items():
        _gravar_silver_sintetico(tmp_path, fonte, model)
    with override_settings(DATA_DIR=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def loaders_rapidos():
    """Troca os loaders das fontes sem Parquet sintético por dublês que
    retornam 'nada carregado' sem tocar disco — só grp_concedente e
    grp_tabela_uo usam o loader real nos testes que chamam o comando inteiro."""
    substitutos = {
        fonte: (
            loader
            if fonte in _FONTES_REAIS
            else mock.Mock(return_value={"apagados": 0, "inseridos": 0})
        )
        for fonte, loader in _LOADERS_GRP.items()
    }
    with mock.patch.object(cmd, "_LOADERS_GRP", substitutos):
        yield substitutos


# ---------------------------------------------------------------------------
# O comando
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sem_argumentos_carrega_todas_as_fontes(data_dir_sintetico, loaders_rapidos):
    call_command("carregar_grp")

    assert GrpConcedente.objects.count() == 2
    assert GrpTabelaUo.objects.count() == 2


@pytest.mark.django_db
def test_fonte_unica_carrega_so_aquela(data_dir_sintetico):
    call_command("carregar_grp", "--fonte", "grp_tabela_uo")

    assert GrpTabelaUo.objects.count() == 2
    assert GrpConcedente.objects.count() == 0


@pytest.mark.django_db
def test_fonte_repetida_carrega_as_indicadas(data_dir_sintetico):
    call_command(
        "carregar_grp",
        "--fonte", "grp_tabela_uo",
        "--fonte", "grp_concedente",
    )

    assert GrpTabelaUo.objects.count() == 2
    assert GrpConcedente.objects.count() == 2


@pytest.mark.django_db
def test_fonte_invalida_lista_as_validas(data_dir_sintetico):
    with pytest.raises(CommandError) as excinfo:
        call_command("carregar_grp", "--fonte", "fonte_inexistente")

    mensagem = str(excinfo.value)
    assert "fonte_inexistente" in mensagem
    for fonte in FONTES_GRP:
        assert fonte in mensagem


@pytest.mark.django_db
def test_fonte_sem_arquivo_nao_impede_as_outras(data_dir_sintetico):
    """
    Mesma semântica do pipeline: a falha de uma fonte é registrada, as demais
    carregam, e o comando sai com erro para o agendador perceber.
    """
    (data_dir_sintetico / "silver" / "grp_tabela_uo.parquet").unlink()

    with pytest.raises(CommandError) as excinfo:
        call_command("carregar_grp", "--fonte", "grp_concedente", "--fonte", "grp_tabela_uo")

    assert "grp_tabela_uo" in str(excinfo.value)
    assert GrpTabelaUo.objects.count() == 0
    assert GrpConcedente.objects.count() == 2, "grp_concedente deveria ter carregado"


@pytest.mark.django_db
def test_erro_inesperado_registra_traceback_e_segue(data_dir_sintetico, caplog):
    loaders_com_falha = dict(cmd._LOADERS_GRP)
    loaders_com_falha["grp_concedente"] = mock.Mock(
        side_effect=ValueError("parquet corrompido")
    )

    with mock.patch.object(cmd, "_LOADERS_GRP", loaders_com_falha):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(CommandError):
                call_command(
                    "carregar_grp",
                    "--fonte", "grp_concedente",
                    "--fonte", "grp_tabela_uo",
                )

    assert GrpConcedente.objects.count() == 0
    assert GrpTabelaUo.objects.count() == 2, "grp_tabela_uo deveria ter carregado"
    assert any(r.exc_info for r in caplog.records if r.levelno >= logging.ERROR)


@pytest.mark.django_db
def test_carga_bem_sucedida_invalida_o_cache(data_dir_sintetico):
    with mock.patch.object(cmd, "invalidar_cache_indicadores") as invalidar:
        call_command("carregar_grp", "--fonte", "grp_tabela_uo")

    invalidar.assert_called_once()


@pytest.mark.django_db
def test_sem_nenhuma_carga_bem_sucedida_nao_invalida(data_dir_sintetico):
    (data_dir_sintetico / "silver" / "grp_concedente.parquet").unlink()
    (data_dir_sintetico / "silver" / "grp_tabela_uo.parquet").unlink()

    with mock.patch.object(cmd, "invalidar_cache_indicadores") as invalidar:
        with pytest.raises(CommandError):
            call_command("carregar_grp", "--fonte", "grp_concedente", "--fonte", "grp_tabela_uo")

    invalidar.assert_not_called()


@pytest.mark.django_db
def test_carga_e_idempotente(data_dir_sintetico):
    """Full refresh: rodar duas vezes não duplica."""
    call_command("carregar_grp", "--fonte", "grp_tabela_uo")
    call_command("carregar_grp", "--fonte", "grp_tabela_uo")

    assert GrpTabelaUo.objects.count() == 2


# ---------------------------------------------------------------------------
# Etapa opcional no pipeline
# ---------------------------------------------------------------------------

@override_settings(PIPELINE_INCLUIR_GRP=False)
def test_pipeline_nao_chama_o_grp_por_padrao():
    """
    Com o default, `rodar_pipeline` se comporta exatamente como antes de o GRP
    existir — nem a etapa Silver nem a carga incluem as fontes GRP.
    """
    from core import pipeline

    assert pipeline._incluir_grp() is False
    assert not any(f.startswith("grp_") for f in pipeline._fontes_silver())
    assert "carregar_grp" not in [c for c, _, _ in pipeline._cargas_orm()]


@override_settings(PIPELINE_INCLUIR_GRP=True)
def test_pipeline_chama_o_grp_quando_ligado():
    from core import pipeline

    assert pipeline._incluir_grp() is True
    fontes = pipeline._fontes_silver()
    for fonte in FONTES_GRP:
        assert fonte in fontes
    assert "carregar_grp" in [c for c, _, _ in pipeline._cargas_orm()]


@override_settings(PIPELINE_INCLUIR_GRP=False)
def test_etapa_gold_nao_executa_carregar_grp_por_padrao():
    from core import pipeline

    chamados = []

    def fake_call_command(comando, *args, **kwargs):
        chamados.append(comando)
        buffer = kwargs.get("stdout")
        if buffer is not None:
            buffer.write("Concluído! Apagados: 0 | Inseridos: 0\n")

    with mock.patch.object(pipeline, "call_command", side_effect=fake_call_command):
        pipeline._etapa_gold_orm()

    assert "carregar_grp" not in chamados


@override_settings(PIPELINE_INCLUIR_GRP=True)
def test_etapa_gold_executa_carregar_grp_quando_ligado():
    from core import pipeline

    chamados = []

    def fake_call_command(comando, *args, **kwargs):
        chamados.append(comando)
        buffer = kwargs.get("stdout")
        if buffer is not None:
            buffer.write("Concluído! Apagados: 0 | Inseridos: 0\n")

    with mock.patch.object(pipeline, "call_command", side_effect=fake_call_command):
        pipeline._etapa_gold_orm()

    assert "carregar_grp" in chamados


def test_comando_pertence_ao_app_grp():
    from django.core.management import get_commands

    assert get_commands()["carregar_grp"] == "apps.grp"
