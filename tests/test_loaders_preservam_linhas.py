"""
Os loaders do SIGCON gravam TODAS as linhas da Silver (regra do dono dos
dados: nenhuma linha com dado é excluída). Contagem do model = contagem do
Parquet de origem.

Dois grupos:
  - Parquet sintético (sempre roda): linhas marcadas pelo motor Silver chegam
    ao banco, com o motivo, em vez de serem descartadas;
  - Silver real (pula se data/silver não existir): os 16 models Sigcon*.

Antes da refatoração, os loaders enriqueciam o convênio com joins e o teste
cobria "chave nula não herda dado de outra linha". O loader atual é genérico
(Parquet → model, sem join), então esse risco deixou de existir.
"""

from pathlib import Path

import pandas as pd
import pytest

from apps.sigcon import loader
from apps.sigcon.models import (
    SigconChaveConvenio,
    SigconChaveDeclaracao,
    SigconChavePlanoTrabalho,
    SigconChaveTermoAditivo,
    SigconConcedente,
    SigconConvenio,
    SigconConvenioGeral,
    SigconCronogramaDesembolso,
    SigconDeclaracaoContrapartida,
    SigconNtEmenda,
    SigconPlanoAplicacao,
    SigconPlanoTrabalho,
    SigconProrrogacaoOficio,
    SigconTabelaUo,
    SigconTermoAditivo,
    SigconUnidadeExecutora,
)


def _gravar(settings, tmp_path, nome, dados: dict):
    settings.DATA_DIR = tmp_path
    destino = tmp_path / "silver"
    destino.mkdir(exist_ok=True)
    pd.DataFrame(dados).to_parquet(destino / f"{nome}.parquet", index=False)


# ---------------------------------------------------------------------------
# Parquet sintético
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cronograma_grava_linhas_marcadas_com_o_motivo(settings, tmp_path):
    """O bloco desalinhado do BO (sem plano, ano nem valor) fica no banco,
    marcado em ds_alerta_linha; as consultas é que o filtram."""
    _gravar(settings, tmp_path, "sigcon_cronograma_desembolso", {
        "nr_mes_desembolso": pd.array([3, 684, 5], dtype="Int64"),
        "nr_ano_desembolso": pd.array([2024, None, 2025], dtype="Int64"),
        "vl_desembolso_concedente": [10.5, None, 7.0],
        "vl_desembolso_proponente": [1.0, None, 2.0],
        "cd_plano_trabalho": pd.array(["P1", None, "P9"], dtype="string"),
        "ds_alerta_linha": pd.array(
            [None, "chave_obrigatoria_vazia:plano_trabalho_codigo", None], dtype="string",
        ),
        "tx_linha_bruta": pd.array([None, "{}", None], dtype="string"),
    })

    resultado = loader.carregar_sigcon_cronograma_desembolso()

    assert resultado["inseridos"] == 3
    assert SigconCronogramaDesembolso.objects.count() == 3
    marcada = SigconCronogramaDesembolso.objects.get(nr_mes_desembolso=684)
    assert marcada.ds_alerta_linha == "chave_obrigatoria_vazia:plano_trabalho_codigo"
    assert marcada.cd_plano_trabalho is None
    validas = SigconCronogramaDesembolso.objects.filter(ds_alerta_linha__isnull=True)
    assert sorted(validas.values_list("nr_mes_desembolso", flat=True)) == [3, 5]


@pytest.mark.django_db
def test_convenios_sem_siafi_entram_todos_e_sem_chave(settings, tmp_path):
    """Convênios sem SIAFI (siafi_uo nulo) não são descartados nem colapsados
    entre si — com a unique removida de siafi_uo, vários nulos convivem."""
    _gravar(settings, tmp_path, "sigcon_convenio", {
        "nr_convenio": pd.array(["C1", "C2", "C3"], dtype="string"),
        "nr_siafi": pd.array(["100", None, None], dtype="string"),
        "cd_uo": pd.array(["1261", "1261", "1261"], dtype="string"),
        "siafi_uo": pd.array(["1001261", None, None], dtype="string"),
        "ds_situacao_convenio": pd.array(["a", "b", "c"], dtype="string"),
        "dt_vigencia_inicio": pd.to_datetime(["2020-01-01"] * 3),
        "dt_vigencia_termino_inicial": pd.to_datetime(["2021-01-01"] * 3),
        "dt_vigencia_termino": pd.to_datetime(["2021-06-01"] * 3),
        "vl_convenio_concedente_inicial": [1.0] * 3,
        "vl_convenio_concedente_aditado": [0.0] * 3,
        "vl_convenio_concedente": [1.0] * 3,
        "vl_convenio_proponente_inicial": [1.0] * 3,
        "vl_convenio_proponente_aditado": [0.0] * 3,
        "vl_convenio_proponente": [1.0] * 3,
        "vl_convenio_total": [2.0] * 3,
    })

    resultado = loader.carregar_sigcon_convenio()

    assert resultado["inseridos"] == 3
    assert SigconConvenio.objects.filter(siafi_uo__isnull=True).count() == 2


@pytest.mark.django_db
def test_linhas_identicas_sao_todas_gravadas(settings, tmp_path):
    """A Silver só alerta sobre linhas idênticas; o loader não as colapsa."""
    _gravar(settings, tmp_path, "sigcon_tabela_uo", {
        "cd_uo": ["1261", "1261", "1261"],
        "nm_uo": ["SEPLAG", "SEPLAG", "SEPLAG"],
        "nr_ano_exercicio": [2024, 2024, 2024],
    })

    resultado = loader.carregar_sigcon_tabela_uo()

    assert resultado["inseridos"] == 3 == SigconTabelaUo.objects.count()


# ---------------------------------------------------------------------------
# Silver real: linhas do model = linhas do Parquet de origem
# ---------------------------------------------------------------------------

_SILVER = Path(__file__).resolve().parent.parent / "data" / "silver"
_TEM_SILVER = all(
    (_SILVER / f"{fonte}.parquet").exists()
    for fonte in (
        "sigcon_convenio",
        "sigcon_cronograma_desembolso",
        "sigcon_tabela_uo",
    )
)

_CASOS_REAIS = [
    (loader.carregar_sigcon_convenio, SigconConvenio, "sigcon_convenio"),
    (loader.carregar_sigcon_convenio_geral, SigconConvenioGeral, "sigcon_convenio_geral"),
    (loader.carregar_sigcon_plano_trabalho, SigconPlanoTrabalho, "sigcon_plano_trabalho"),
    (loader.carregar_sigcon_termo_aditivo, SigconTermoAditivo, "sigcon_termo_aditivo"),
    (loader.carregar_sigcon_prorrogacao_oficio, SigconProrrogacaoOficio, "sigcon_prorrogacao_oficio"),
    (loader.carregar_sigcon_declaracao_contrapartida, SigconDeclaracaoContrapartida,
     "sigcon_declaracao_contrapartida"),
    (loader.carregar_sigcon_cronograma_desembolso, SigconCronogramaDesembolso,
     "sigcon_cronograma_desembolso"),
    (loader.carregar_sigcon_plano_aplicacao, SigconPlanoAplicacao, "sigcon_plano_aplicacao"),
    (loader.carregar_sigcon_unidade_executora, SigconUnidadeExecutora, "sigcon_unidade_executora"),
    (loader.carregar_sigcon_nt_emenda, SigconNtEmenda, "sigcon_nt_emenda"),
    (loader.carregar_sigcon_chave_convenio, SigconChaveConvenio, "sigcon_chave_convenio"),
    (loader.carregar_sigcon_chave_termo_aditivo, SigconChaveTermoAditivo,
     "sigcon_chave_termo_aditivo"),
    (loader.carregar_sigcon_chave_plano_trabalho, SigconChavePlanoTrabalho,
     "sigcon_chave_plano_trabalho"),
    (loader.carregar_sigcon_chave_declaracao, SigconChaveDeclaracao, "sigcon_chave_declaracao"),
    (loader.carregar_sigcon_concedente, SigconConcedente, "sigcon_concedente"),
    (loader.carregar_sigcon_tabela_uo, SigconTabelaUo, "sigcon_tabela_uo"),
]


@pytest.mark.skipif(not _TEM_SILVER, reason="data/silver não existe neste ambiente")
@pytest.mark.django_db
@pytest.mark.parametrize(
    "funcao,modelo,fonte", _CASOS_REAIS, ids=[c[1].__name__ for c in _CASOS_REAIS],
)
def test_model_tem_todas_as_linhas_da_silver(settings, funcao, modelo, fonte):
    settings.DATA_DIR = _SILVER.parent
    esperado = len(pd.read_parquet(_SILVER / f"{fonte}.parquet"))

    resultado = funcao()

    assert resultado["inseridos"] == esperado
    assert modelo.objects.count() == esperado, (
        f"{modelo.__name__}: {modelo.objects.count()} no banco, {esperado} na Silver ({fonte})"
    )


@pytest.mark.skipif(not _TEM_SILVER, reason="data/silver não existe neste ambiente")
@pytest.mark.django_db
def test_cronograma_real_preserva_o_bloco_desalinhado(settings):
    """O arquivo do BO tem ~38% de linhas de um bloco desalinhado: todas entram
    no banco, e só as válidas (sem ds_alerta_linha) formam o grão do cronograma."""
    settings.DATA_DIR = _SILVER.parent
    loader.carregar_sigcon_cronograma_desembolso()

    total = SigconCronogramaDesembolso.objects.count()
    validas = SigconCronogramaDesembolso.objects.filter(ds_alerta_linha__isnull=True).count()

    assert total == len(pd.read_parquet(_SILVER / "sigcon_cronograma_desembolso.parquet"))
    assert 0 < validas < total
