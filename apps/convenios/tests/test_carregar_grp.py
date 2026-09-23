"""
Comando `carregar_grp` e a etapa opcional do GRP no pipeline.

Os loaders GRP existiam mas nenhum comando os chamava — só dava para popular
as telas GRP abrindo um shell. Estes testes fixam o comando e, principalmente,
a regra de que o GRP fica **fora** do `rodar_pipeline` por padrão: ele está em
teste e não pode derrubar a atualização diária do painel SIGCON.

Os Parquets são sintéticos e mínimos, escritos em tmp_path com DATA_DIR
sobrescrito — nenhum dado real é tocado.
"""
import inspect
import logging
import re
from unittest import mock

import pandas as pd
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.convenios.management.commands.carregar_grp import _LOADERS_GRP, FONTES_GRP
from apps.convenios.models import (
    CronogramaDesembolsoGrp,
    DadosGrp,
    EsferaGrp,
    PlanoAplicacaoGrp,
    PlanoAplicacaoGrpDetalhes,
    RecursosConcedenteGrp,
    RecursosContrapartidaGrp,
)

# fonte → (model, colunas mínimas que o loader lê)
FONTE_PARA_MODEL = {
    "dcgce_dados_grp": DadosGrp,
    "dcgce_cronograma_desembolso_grp": CronogramaDesembolsoGrp,
    "dcgce_recursos_contrapartida_grp": RecursosContrapartidaGrp,
    "dcgce_recursos_concedente_grp": RecursosConcedenteGrp,
    "dcgce_plano_aplicacao_grp": PlanoAplicacaoGrp,
    "dcgce_plano_aplicacao_grp_detalhes": PlanoAplicacaoGrpDetalhes,
    "dcgce_esfera_grp": EsferaGrp,
}


_ACESSO_A_COLUNA = re.compile(r"""row\[(["'])(.*?)\1\]""")


def _colunas_do_loader(fonte: str) -> list[str]:
    """
    Colunas que o loader daquela fonte lê do Parquet.

    Extraídas do código do próprio loader (os `row["..."]`), e não dos campos
    do model: no GRP os nomes não coincidem — o campo `concedente_nome` vem da
    coluna `concedente_-_nome`. Derivar do loader mantém a fixture sincronizada
    sozinha se uma coluna mudar de nome.
    """
    fonte_do_loader = inspect.getsource(_LOADERS_GRP[fonte])
    return [coluna for _, coluna in _ACESSO_A_COLUNA.findall(fonte_do_loader)]


def _gravar_silver_sintetico(diretorio, fonte: str, linhas: int = 2):
    """Escreve um Parquet mínimo com as colunas que o loader espera."""
    colunas = _colunas_do_loader(fonte)
    dados = {
        coluna: [f"{coluna[:12]}-{i}" for i in range(linhas)]
        for coluna in colunas
    }
    destino = diretorio / "silver" / f"{fonte}.parquet"
    destino.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(dados).to_parquet(destino, index=False)
    return destino


@pytest.fixture
def data_dir_sintetico(tmp_path):
    """DATA_DIR isolado com os 7 Parquets Silver do GRP."""
    for fonte in FONTES_GRP:
        _gravar_silver_sintetico(tmp_path, fonte)
    with override_settings(DATA_DIR=str(tmp_path)):
        yield tmp_path


# ---------------------------------------------------------------------------
# O comando
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_sem_argumentos_carrega_as_sete_tabelas(data_dir_sintetico):
    call_command("carregar_grp")

    for fonte, model in FONTE_PARA_MODEL.items():
        assert model.objects.count() == 2, f"{fonte} não foi carregada"


@pytest.mark.django_db
def test_fonte_unica_carrega_so_aquela(data_dir_sintetico):
    call_command("carregar_grp", "--fonte", "dcgce_esfera_grp")

    assert EsferaGrp.objects.count() == 2
    assert DadosGrp.objects.count() == 0
    assert CronogramaDesembolsoGrp.objects.count() == 0


@pytest.mark.django_db
def test_fonte_repetida_carrega_as_indicadas(data_dir_sintetico):
    call_command(
        "carregar_grp",
        "--fonte", "dcgce_esfera_grp",
        "--fonte", "dcgce_dados_grp",
    )

    assert EsferaGrp.objects.count() == 2
    assert DadosGrp.objects.count() == 2
    assert PlanoAplicacaoGrp.objects.count() == 0


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
    (data_dir_sintetico / "silver" / "dcgce_esfera_grp.parquet").unlink()

    with pytest.raises(CommandError) as excinfo:
        call_command("carregar_grp")

    assert "dcgce_esfera_grp" in str(excinfo.value)
    assert EsferaGrp.objects.count() == 0
    # as outras seis entraram mesmo assim
    for fonte, model in FONTE_PARA_MODEL.items():
        if fonte != "dcgce_esfera_grp":
            assert model.objects.count() == 2, f"{fonte} deveria ter carregado"


@pytest.mark.django_db
def test_erro_inesperado_registra_traceback_e_segue(data_dir_sintetico, caplog):
    from apps.convenios.management.commands import carregar_grp as cmd

    loaders_com_falha = dict(cmd._LOADERS_GRP)
    loaders_com_falha["dcgce_dados_grp"] = mock.Mock(
        side_effect=ValueError("parquet corrompido")
    )

    with mock.patch.object(cmd, "_LOADERS_GRP", loaders_com_falha):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(CommandError):
                call_command("carregar_grp")

    assert DadosGrp.objects.count() == 0
    assert EsferaGrp.objects.count() == 2, "as demais deveriam carregar"
    assert any(r.exc_info for r in caplog.records if r.levelno >= logging.ERROR)


@pytest.mark.django_db
def test_carga_bem_sucedida_invalida_o_cache(data_dir_sintetico):
    from apps.convenios.management.commands import carregar_grp as cmd

    with mock.patch.object(cmd, "invalidar_cache_indicadores") as invalidar:
        call_command("carregar_grp", "--fonte", "dcgce_esfera_grp")

    invalidar.assert_called_once()


@pytest.mark.django_db
def test_sem_nenhuma_carga_bem_sucedida_nao_invalida(data_dir_sintetico):
    from apps.convenios.management.commands import carregar_grp as cmd

    for fonte in FONTES_GRP:
        (data_dir_sintetico / "silver" / f"{fonte}.parquet").unlink()

    with mock.patch.object(cmd, "invalidar_cache_indicadores") as invalidar:
        with pytest.raises(CommandError):
            call_command("carregar_grp")

    invalidar.assert_not_called()


@pytest.mark.django_db
def test_carga_e_idempotente(data_dir_sintetico):
    """Full refresh: rodar duas vezes não duplica."""
    call_command("carregar_grp", "--fonte", "dcgce_esfera_grp")
    call_command("carregar_grp", "--fonte", "dcgce_esfera_grp")

    assert EsferaGrp.objects.count() == 2


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
    assert not any(f.endswith("_grp") for f in pipeline._fontes_silver())
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


def test_comando_pertence_ao_app_convenios():
    from django.core.management import get_commands

    assert get_commands()["carregar_grp"] == "apps.convenios"
