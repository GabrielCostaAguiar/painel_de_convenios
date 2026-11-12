"""
Comando `carregar_sigcon`: full refresh das tabelas do SIGCON a partir da Silver.

Os Parquets são sintéticos e mínimos, escritos em tmp_path com DATA_DIR
sobrescrito — nenhum dado real é tocado. Só duas fontes reais
(sigcon_concedente e sigcon_tabela_uo) ganham Parquet sintético; as demais,
quando o teste precisa rodar "todas", são substituídas por dublês que não tocam
disco — gerar 16 Parquets sintéticos a cada teste não traria nenhuma garantia
adicional.
"""

import datetime
import logging
from decimal import Decimal
from unittest import mock

import pandas as pd
import pytest
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError
from django.db import models as dj_models
from django.test import override_settings

from apps.sigcon.management.commands import carregar_sigcon as cmd
from apps.sigcon.management.commands.carregar_sigcon import (
    _LOADERS_SIGCON,
    FONTES_SIGCON,
)
from apps.sigcon.models import SigconConcedente, SigconTabelaUo

_FONTES_REAIS = {
    "sigcon_concedente": SigconConcedente,
    "sigcon_tabela_uo": SigconTabelaUo,
}


def _valor_sintetico(campo, i: int):
    """Valor do tipo certo para o campo: o loader genérico não converte nada,
    então inteiro/data/decimal precisam chegar ao banco já no tipo do model."""
    if isinstance(campo, dj_models.IntegerField):
        return 2020 + i
    if isinstance(campo, dj_models.DateField):
        return datetime.date(2024, 1, 1 + i)
    if isinstance(campo, dj_models.DecimalField):
        return Decimal(i + 1)
    if isinstance(campo, dj_models.BooleanField):
        return bool(i % 2)
    return f"{campo.name[:6]}{i}"  # curto: cabe em CharField(max_length=10)


def _gravar_silver_sintetico(diretorio, fonte: str, model, linhas: int = 2):
    """Parquet mínimo cujas colunas são os campos do model (loader genérico:
    carregar_tabela_generica exige que parquet e model tenham os mesmos nomes)."""
    campos = [f for f in model._meta.concrete_fields if f.name != "id"]
    dados = {c.name: [_valor_sintetico(c, i) for i in range(linhas)] for c in campos}
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
    retornam 'nada carregado' sem tocar disco — só sigcon_concedente e
    sigcon_tabela_uo usam o loader real nos testes que chamam o comando inteiro."""
    substitutos = {
        fonte: (
            loader
            if fonte in _FONTES_REAIS
            else mock.Mock(return_value={"apagados": 0, "inseridos": 0})
        )
        for fonte, loader in _LOADERS_SIGCON.items()
    }
    with mock.patch.object(cmd, "_LOADERS_SIGCON", substitutos):
        yield substitutos


# ---------------------------------------------------------------------------
# O comando
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sem_argumentos_carrega_todas_as_fontes(data_dir_sintetico, loaders_rapidos):
    call_command("carregar_sigcon")

    assert SigconConcedente.objects.count() == 2
    assert SigconTabelaUo.objects.count() == 2
    for fonte, loader in loaders_rapidos.items():
        if fonte not in _FONTES_REAIS:
            loader.assert_called_once_with()


@pytest.mark.django_db
def test_fonte_unica_carrega_so_aquela(data_dir_sintetico):
    call_command("carregar_sigcon", "--fonte", "sigcon_tabela_uo")

    assert SigconTabelaUo.objects.count() == 2
    assert SigconConcedente.objects.count() == 0


@pytest.mark.django_db
def test_fonte_repetida_carrega_as_indicadas(data_dir_sintetico):
    call_command(
        "carregar_sigcon",
        "--fonte", "sigcon_tabela_uo",
        "--fonte", "sigcon_concedente",
    )

    assert SigconTabelaUo.objects.count() == 2
    assert SigconConcedente.objects.count() == 2


@pytest.mark.django_db
def test_fonte_invalida_lista_as_validas(data_dir_sintetico):
    with pytest.raises(CommandError) as excinfo:
        call_command("carregar_sigcon", "--fonte", "fonte_inexistente")

    mensagem = str(excinfo.value)
    assert "fonte_inexistente" in mensagem
    for fonte in FONTES_SIGCON:
        assert fonte in mensagem


@pytest.mark.django_db
def test_fonte_invalida_nao_carrega_nada(data_dir_sintetico):
    """Nome errado entre nomes certos aborta antes de tocar em qualquer tabela."""
    with pytest.raises(CommandError):
        call_command(
            "carregar_sigcon", "--fonte", "sigcon_tabela_uo", "--fonte", "nao_existe"
        )

    assert SigconTabelaUo.objects.count() == 0


@pytest.mark.django_db
def test_fonte_sem_arquivo_nao_impede_as_outras(data_dir_sintetico):
    """
    Mesma semântica do pipeline: a falha de uma fonte é registrada, as demais
    carregam, e o comando sai com erro para o agendador perceber.
    """
    (data_dir_sintetico / "silver" / "sigcon_tabela_uo.parquet").unlink()

    with pytest.raises(CommandError) as excinfo:
        call_command(
            "carregar_sigcon", "--fonte", "sigcon_concedente", "--fonte", "sigcon_tabela_uo"
        )

    assert "sigcon_tabela_uo" in str(excinfo.value)
    assert SigconTabelaUo.objects.count() == 0
    assert SigconConcedente.objects.count() == 2, "sigcon_concedente deveria ter carregado"


@pytest.mark.django_db
def test_erro_inesperado_registra_traceback_e_segue(data_dir_sintetico, caplog):
    loaders_com_falha = dict(cmd._LOADERS_SIGCON)
    loaders_com_falha["sigcon_concedente"] = mock.Mock(
        side_effect=ValueError("parquet corrompido")
    )

    with mock.patch.object(cmd, "_LOADERS_SIGCON", loaders_com_falha):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(CommandError):
                call_command(
                    "carregar_sigcon",
                    "--fonte", "sigcon_concedente",
                    "--fonte", "sigcon_tabela_uo",
                )

    assert SigconConcedente.objects.count() == 0
    assert SigconTabelaUo.objects.count() == 2, "sigcon_tabela_uo deveria ter carregado"
    assert any(r.exc_info for r in caplog.records if r.levelno >= logging.ERROR)


@pytest.mark.django_db
def test_parquet_com_colunas_erradas_nao_apaga_a_tabela(data_dir_sintetico):
    """Silver com esquema diferente do model é erro: a carga anterior permanece."""
    call_command("carregar_sigcon", "--fonte", "sigcon_tabela_uo")
    pd.DataFrame({"coluna_estranha": ["x"]}).to_parquet(
        data_dir_sintetico / "silver" / "sigcon_tabela_uo.parquet", index=False
    )

    with pytest.raises(CommandError):
        call_command("carregar_sigcon", "--fonte", "sigcon_tabela_uo")

    assert SigconTabelaUo.objects.count() == 2


@pytest.mark.django_db
def test_carga_bem_sucedida_invalida_o_cache(data_dir_sintetico):
    with mock.patch.object(cmd, "invalidar_cache_indicadores") as invalidar:
        call_command("carregar_sigcon", "--fonte", "sigcon_tabela_uo")

    invalidar.assert_called_once()


@pytest.mark.django_db
def test_sem_nenhuma_carga_bem_sucedida_nao_invalida(data_dir_sintetico):
    (data_dir_sintetico / "silver" / "sigcon_concedente.parquet").unlink()
    (data_dir_sintetico / "silver" / "sigcon_tabela_uo.parquet").unlink()

    with mock.patch.object(cmd, "invalidar_cache_indicadores") as invalidar:
        with pytest.raises(CommandError):
            call_command(
                "carregar_sigcon",
                "--fonte", "sigcon_concedente",
                "--fonte", "sigcon_tabela_uo",
            )

    invalidar.assert_not_called()


@pytest.mark.django_db
def test_carga_e_idempotente(data_dir_sintetico):
    """Full refresh: rodar duas vezes não duplica."""
    call_command("carregar_sigcon", "--fonte", "sigcon_tabela_uo")
    call_command("carregar_sigcon", "--fonte", "sigcon_tabela_uo")

    assert SigconTabelaUo.objects.count() == 2


# ---------------------------------------------------------------------------
# Registro das fontes
# ---------------------------------------------------------------------------


def test_comandos_pertencem_ao_app_sigcon():
    assert get_commands()["carregar_sigcon"] == "apps.sigcon"
    assert get_commands()["validar_sigcon"] == "apps.sigcon"


def test_toda_fonte_carregada_existe_em_fontes():
    """Um nome digitado errado em _LOADERS_SIGCON só apareceria na primeira carga."""
    from core.ingestion.sources import FONTES

    assert set(FONTES_SIGCON) <= set(FONTES)


def test_cada_fonte_tem_um_model_com_o_mesmo_nome_de_tabela():
    """O loader genérico e a volumetria assumem fonte == db_table."""
    from apps.sigcon.validacao.volumetria import tabelas_sigcon

    # ResultadoValidacao não começa com o prefixo sigcon_, então não entra.
    assert sorted(FONTES_SIGCON) == tabelas_sigcon()
