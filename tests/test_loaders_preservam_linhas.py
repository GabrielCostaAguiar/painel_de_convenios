"""
Os loaders do SIGCON gravam TODAS as linhas da Silver (regra do dono dos
dados: nenhuma linha com dado é excluída). Contagem do model = contagem do
Parquet de origem.

Dois grupos:
  - Parquet sintético (sempre roda): duplicadas, marcadas e chave nula;
  - Silver real (pula se data/silver não existir): todos os 17 models.
"""

from pathlib import Path

import pandas as pd
import pytest

from apps.sigcon import loader
from apps.sigcon.models import (
    CodigoConvenio,
    CodigoDeclaracaoContrapartida,
    CodigoPlanoTrabalho,
    CodigoTermoAditivo,
    ControleSEI,
    Convenio,
    ConvenioGeral,
    CronogramaDesembolso,
    DeclaracaoContrapartida,
    Esfera,
    NtEmenda,
    PlanoAplicacao,
    PlanoTrabalho,
    ProrrogacaoOficio,
    TermoAditivo,
    UnidadesExecutoras,
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
def test_controle_sei_grava_todas_as_linhas_inclusive_duplicadas_e_sem_siafi(settings, tmp_path):
    _gravar(settings, tmp_path, "controle_sei", {
        "nr_sei": pd.array(["S1", "S2", "S3", "S4", "S4"], dtype="string"),
        "nr_siafi": pd.array(["100", "100", None, None, None], dtype="string"),
        "nr_proposta_siconv": pd.array([None] * 5, dtype="string"),
    })
    resultado = loader.carregar_controle_sei()
    assert resultado["inseridos"] == 5
    assert ControleSEI.objects.count() == 5  # antes: 2 (dedup por SIAFI)


@pytest.mark.django_db
def test_cronograma_grava_linhas_marcadas_e_nao_herda_de_chave_nula(settings, tmp_path):
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
    # Geral com uma linha de plano NULO: o merge não pode casá-la com as linhas
    # do cronograma que também têm plano nulo.
    _gravar(settings, tmp_path, "sigcon_convenio_geral", {
        "cd_plano_trabalho": pd.array(["P1", None], dtype="string"),
        "nr_convenio": pd.array(["CV1", "CV-NULO"], dtype="string"),
        "cd_convenio_sequencial": pd.array(["7", "9"], dtype="string"),
    })
    _gravar(settings, tmp_path, "sigcon_chave_convenio", {
        "cd_convenio_sequencial": pd.array(["7", "9"], dtype="string"),
        "nr_siafi": pd.array(["111", "999"], dtype="string"),
        "cd_uo": pd.array(["1261", "5555"], dtype="string"),
    })

    resultado = loader.carregar_cronograma_desembolso()
    assert resultado["inseridos"] == 3
    linhas = {c.mes_cronograma_desembolso: c for c in CronogramaDesembolso.objects.all()}
    assert linhas["3"].convenio_codigo == "CV1"
    assert linhas["3"].convenio_numero_sequencial_siafi == "111"
    assert linhas["3"].ds_alerta_linha is None
    marcada = linhas["684"]
    assert marcada.ds_alerta_linha == "chave_obrigatoria_vazia:plano_trabalho_codigo"
    assert marcada.convenio_codigo is None  # NÃO "CV-NULO"
    assert marcada.convenio_numero_sequencial_siafi is None
    assert linhas["5"].convenio_codigo is None  # plano sem correspondente


@pytest.mark.django_db
def test_convenio_sem_siafi_nao_herda_dados_de_outro_convenio_sem_siafi(settings, tmp_path):
    _gravar(settings, tmp_path, "sigcon_convenio", {
        "nr_convenio": pd.array(["C1", "C2", "C3"], dtype="string"),
        "nr_siafi": pd.array(["100", None, None], dtype="string"),
        "cd_uo": pd.array(["1261", "1261", "1261"], dtype="string"),
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
        "siafi_uo": pd.array(["1001261", None, None], dtype="string"),
    })
    _gravar(settings, tmp_path, "sigcon_chave_convenio", {
        "nr_convenio": pd.array(["C1", "CX"], dtype="string"),
        "cd_convenio_sequencial": pd.array(["1", "2"], dtype="string"),
        "nr_siafi": pd.array(["100", None], dtype="string"),
        "cd_uo": pd.array(["1261", "1261"], dtype="string"),
        "siafi_uo": pd.array(["1001261", None], dtype="string"),
    })
    _gravar(settings, tmp_path, "sigcon_convenio_geral", {
        "nr_convenio": pd.array(["C1", "CX"], dtype="string"),
        "cd_convenio_sequencial": pd.array(["1", "2"], dtype="string"),
        "cd_plano_trabalho": pd.array(["P1", "PX"], dtype="string"),
        "nr_siafi": pd.array(["100", None], dtype="string"),
        "dt_publicacao": pd.to_datetime(["2020-02-02", "2019-09-09"]),
        "dt_assinatura": pd.to_datetime(["2020-01-15", "2019-08-08"]),
        "nr_ano_convenio": pd.array([2020, 2019], dtype="Int64"),
    })
    _gravar(settings, tmp_path, "sigcon_plano_trabalho", {
        "cd_plano_trabalho": pd.array(["P1", "PX"], dtype="string"),
        "nm_plano_trabalho": pd.array(["titulo 1", "titulo X"], dtype="string"),
        "tx_objeto": pd.array(["obj 1", "obj X"], dtype="string"),
        "nm_concedente": pd.array(["Conc 1", "Conc X"], dtype="string"),
        "nr_cnpj_concedente": pd.array(["11", "99"], dtype="string"),
        "nr_cnpj_proponente": pd.array(["22", "88"], dtype="string"),
        "tp_instrumento_siafi": pd.array(["Convênio", "Portaria"], dtype="string"),
    })
    _gravar(settings, tmp_path, "sigcon_concedente", {
        "nr_cnpj_concedente": pd.array(["11"], dtype="string"),
        "ds_esfera": pd.array(["Federal"], dtype="string"),
    })

    resultado = loader.carregar_convenios()
    assert resultado["inseridos"] == 3
    por_codigo = {c.convenio_codigo: c for c in Convenio.objects.all()}
    assert por_codigo["C1"].titulo == "titulo 1" and por_codigo["C1"].esfera == "Federal"
    # C2 e C3 não têm SIAFI: não herdam o plano PX (que a chave nula casaria)
    assert por_codigo["C2"].titulo is None and por_codigo["C3"].titulo is None
    assert por_codigo["C2"].plano_trabalho_codigo is None


# ---------------------------------------------------------------------------
# Silver real: linhas do model = linhas do Parquet de origem
# ---------------------------------------------------------------------------

_SILVER = Path(__file__).resolve().parent.parent / "data" / "silver"
_TEM_SILVER_NOVA = (_SILVER / "sigcon_convenio.parquet").exists()

_CASOS_REAIS = [
    (loader.carregar_convenios, Convenio, "sigcon_convenio"),
    (loader.carregar_convenio_geral, ConvenioGeral, "sigcon_convenio_geral"),
    (loader.carregar_plano_trabalho, PlanoTrabalho, "sigcon_plano_trabalho"),
    (loader.carregar_cronograma_desembolso, CronogramaDesembolso, "sigcon_cronograma_desembolso"),
    (loader.carregar_plano_aplicacao, PlanoAplicacao, "sigcon_plano_aplicacao"),
    (loader.carregar_termo_aditivo, TermoAditivo, "sigcon_termo_aditivo"),
    (loader.carregar_declaracao_contrapartida, DeclaracaoContrapartida, "sigcon_declaracao_contrapartida"),
    (loader.carregar_prorrogacao_oficio, ProrrogacaoOficio, "sigcon_prorrogacao_oficio"),
    (loader.carregar_nt_emenda, NtEmenda, "sigcon_nt_emenda"),
    (loader.carregar_esfera, Esfera, "sigcon_concedente"),
    (loader.carregar_codigo_convenio, CodigoConvenio, "sigcon_chave_convenio"),
    (loader.carregar_codigo_plano_trabalho, CodigoPlanoTrabalho, "sigcon_chave_plano_trabalho"),
    (loader.carregar_codigo_termo_aditivo, CodigoTermoAditivo, "sigcon_chave_termo_aditivo"),
    (loader.carregar_codigo_declaracao_contrapartida, CodigoDeclaracaoContrapartida, "sigcon_chave_declaracao"),
    (loader.carregar_unidades_executoras, UnidadesExecutoras, "sigcon_unidade_executora"),
    (loader.carregar_controle_sei, ControleSEI, "controle_sei"),
]


@pytest.mark.skipif(not _TEM_SILVER_NOVA, reason="data/silver (Silver nova) não existe neste ambiente")
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


@pytest.mark.skipif(not _TEM_SILVER_NOVA, reason="data/silver (Silver nova) não existe neste ambiente")
@pytest.mark.django_db
def test_cronograma_real_48392_linhas_29992_validas(settings):
    settings.DATA_DIR = _SILVER.parent
    loader.carregar_cronograma_desembolso()
    assert CronogramaDesembolso.objects.count() == 48392
    assert CronogramaDesembolso.objects.filter(ds_alerta_linha__isnull=True).count() == 29992


@pytest.mark.skipif(not _TEM_SILVER_NOVA, reason="data/silver (Silver nova) não existe neste ambiente")
@pytest.mark.django_db
def test_gold_real_grava_todas_as_linhas_inclusive_sem_siafi(settings, tmp_path):
    from apps.sigcon.models import ConvenioIntegrado

    import shutil

    settings.DATA_DIR = tmp_path  # o Gold é gravado aqui, sem mexer em data/gold
    (tmp_path / "silver").mkdir()
    for fonte in ("sigcon_chave_siconv", "depara_siafi", "sigcon_convenio", "sigcon_chave_convenio",
                  "sigcon_convenio_geral", "sigcon_plano_trabalho", "sigcon_concedente", "siconv_convenio"):
        shutil.copy(_SILVER / f"{fonte}.parquet", tmp_path / "silver" / f"{fonte}.parquet")
    resultado = loader.carregar_tabela_integrada()
    n_chaves = len(pd.read_parquet(_SILVER / "sigcon_chave_siconv.parquet"))
    assert resultado["inseridos"] == n_chaves == ConvenioIntegrado.objects.count()
    assert ConvenioIntegrado.objects.filter(siafi_uo__isnull=True).count() == 4
    assert ConvenioIntegrado.objects.filter(fl_uo_excluida=True).count() >= 1
    validas = ConvenioIntegrado.objects.filter(limpeza_g=0, fl_uo_excluida=False).count()
    assert 0 < validas < n_chaves
