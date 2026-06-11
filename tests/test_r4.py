"""
Testes de R4: carga idempotente e leitura básica do model ConvenioIntegrado.

Usam um Gold Parquet mínimo em memória (via arquivo temporário) para não
depender dos Silver files nem do pipeline completo.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from apps.convenios.loader import carregar_tabela_integrada
from apps.convenios.models import ConvenioIntegrado


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gold_minimo(tmp_path: Path) -> Path:
    """Cria um Parquet Gold mínimo com 3 convênios e retorna o caminho."""
    df = pd.DataFrame({
        "siafi_uo": pd.array(["100011001", "200022002", "300033003"], dtype="string"),
        "siafi_uo_atual": pd.array(["100011001", "200022002", "300033003"], dtype="string"),
        "convenio_numero_sequencial_siafi": pd.array(["10001", "20002", "30003"], dtype="string"),
        "unidade_orcamentaria_codigo": pd.array(["1001", "2002", "3003"], dtype="string"),
        "siafiatual": pd.array(["10001", "20002", "30003"], dtype="string"),
        "uo_atual": pd.array(["1001", "2002", "3003"], dtype="string"),
        "codigo_siconv": pd.array(["C001", "C002", pd.NA], dtype="string"),
        "instrumento_chaves": pd.array(["Convênio de Entrada", "Acordo / Ajuste", pd.NA], dtype="string"),
        "situacao": pd.array(["Em execução", "Concluído", "Vigente"], dtype="string"),
        "situacao_std": pd.array(["Em execução", "Concluído", "Vigente"], dtype="string"),
        "uo_nome_std": pd.array(["SECRETARIA A", "SECRETARIA B", "FUNDO X"], dtype="string"),
        "uo_sigla_std": pd.array(["SA", "SB", "FX"], dtype="string"),
        "uo_descricao_std": pd.array(["Desc A", "Desc B", "Desc X"], dtype="string"),
        # G_ datas
        "g_dia_assinatura": pd.array(["2020-01-15", "2019-06-01", pd.NA], dtype="string"),
        "g_inicio_vigencia": pd.array(["2020-02-01", "2019-07-01", "2021-01-01"], dtype="string"),
        "g_fim_vigencia": pd.array(["2025-01-31", "2022-06-30", "2027-12-31"], dtype="string"),
        "g_fim_vigencia_inicial": pd.array(["2023-01-31", "2022-06-30", "2024-12-31"], dtype="string"),
        "g_ano_assinatura": pd.array([2020, 2019, pd.NA], dtype="Int64"),
        "g_ano_inicio_vigencia": pd.array([2020, 2019, 2021], dtype="Int64"),
        "g_ano_convenio": pd.array([2020, 2019, 2021], dtype="Int64"),
        "g_situacao_convenio": pd.array(["VIGENTE", "CONCLUÍDO", "VIGENTE"], dtype="string"),
        "g_objeto_convenio": pd.array(["Objeto A", "Objeto B", "Objeto C"], dtype="string"),
        "g_proponente": pd.array(["SECRETARIA A", "SECRETARIA B", "FUNDO X"], dtype="string"),
        "g_concedente": pd.array(["UNIAO", "UNIAO", "ESTADO"], dtype="string"),
        "g_instrumento": pd.array(["Convênio de Entrada", "Acordo / Ajuste", "Convênio de Entrada"], dtype="string"),
        "g_esfera": pd.array(["Federal", "Federal", "Estadual"], dtype="string"),
        "g_uo": pd.array(["1001", "2002", "3003"], dtype="string"),
        "g_vigencia": pd.array(["Vigente", "Vencido", "Vigente"], dtype="string"),
        "g_situacao_convenio_categorizado": pd.array(["Vigente", "Concluído", "Vigente"], dtype="string"),
        "g_concedente_pad": pd.array(["UNIAO", "UNIAO", "ESTADO"], dtype="string"),
        "g_proponente_pad": pd.array(["Secretaria A", "Secretaria B", "Fundo X"], dtype="string"),
        "g_proponente_pad_siglas": pd.array(["SA", "SB", pd.NA], dtype="string"),
        "g_uo_descricao": pd.array(["Descrição A", "Descrição B", "Descrição X"], dtype="string"),
        "g_valor_concedente": [500_000.0, 300_000.0, 1_200_000.0],
        "g_valor_proponente": [50_000.0, 30_000.0, 120_000.0],
        "g_valor_global": [550_000.0, 330_000.0, 1_320_000.0],
        "g_periodo_nao_aditado": [0, 1, 0],
        "g_valor_nao_aditado": [0, 1, 0],
        "limpeza_g": [0, 0, 0],
        # A_ (mesmos valores para simplificar — sem troca de SIAFI nesta fixture)
        "a_dia_assinatura": pd.array(["2020-01-15", "2019-06-01", pd.NA], dtype="string"),
        "a_inicio_vigencia": pd.array(["2020-02-01", "2019-07-01", "2021-01-01"], dtype="string"),
        "a_fim_vigencia": pd.array(["2025-01-31", "2022-06-30", "2027-12-31"], dtype="string"),
        "a_fim_vigencia_inicial": pd.array(["2023-01-31", "2022-06-30", "2024-12-31"], dtype="string"),
        "a_ano_assinatura": pd.array([2020, 2019, pd.NA], dtype="Int64"),
        "a_ano_inicio_vigencia": pd.array([2020, 2019, 2021], dtype="Int64"),
        "a_ano_convenio": pd.array([2020, 2019, 2021], dtype="Int64"),
        "a_situacao_convenio": pd.array(["VIGENTE", "CONCLUÍDO", "VIGENTE"], dtype="string"),
        "a_objeto_convenio": pd.array(["Objeto A", "Objeto B", "Objeto C"], dtype="string"),
        "a_proponente": pd.array(["SECRETARIA A", "SECRETARIA B", "FUNDO X"], dtype="string"),
        "a_concedente": pd.array(["UNIAO", "UNIAO", "ESTADO"], dtype="string"),
        "a_instrumento": pd.array(["Convênio de Entrada", "Acordo / Ajuste", "Convênio de Entrada"], dtype="string"),
        "a_esfera": pd.array(["Federal", "Federal", "Estadual"], dtype="string"),
        "a_vigencia": pd.array(["Vigente", "Vencido", "Vigente"], dtype="string"),
        "a_situacao_convenio_categorizado": pd.array(["Vigente", "Concluído", "Vigente"], dtype="string"),
        "a_concedente_pad": pd.array(["UNIAO", "UNIAO", "ESTADO"], dtype="string"),
        "a_proponente_pad": pd.array(["Secretaria A", "Secretaria B", "Fundo X"], dtype="string"),
        "a_proponente_pad_siglas": pd.array(["SA", "SB", pd.NA], dtype="string"),
        "a_valor_concedente": [500_000.0, 300_000.0, 1_200_000.0],
        "a_valor_proponente": [50_000.0, 30_000.0, 120_000.0],
        "a_valor_global": [550_000.0, 330_000.0, 1_320_000.0],
        "a_periodo_nao_aditado": [0, 1, 0],
        "a_valor_nao_aditado": [0, 1, 0],
    })

    caminho = tmp_path / "convenios_integrado.parquet"
    df.to_parquet(caminho, index=False)
    return caminho


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_carga_idempotente(tmp_path):
    """Rodar carregar_tabela_integrada duas vezes não cria duplicatas."""
    gold = _gold_minimo(tmp_path)

    resultado1 = carregar_tabela_integrada(gold)
    assert resultado1["inseridos"] == 3
    assert ConvenioIntegrado.objects.count() == 3

    resultado2 = carregar_tabela_integrada(gold)
    assert resultado2["inseridos"] == 3
    # Após o segundo carregamento o total ainda deve ser 3 (apagou e reinseriu)
    assert ConvenioIntegrado.objects.count() == 3


@pytest.mark.django_db
def test_leitura_basica_modelo(tmp_path):
    """Após a carga, campos G_ e A_ são recuperados corretamente pelo ORM."""
    gold = _gold_minimo(tmp_path)
    carregar_tabela_integrada(gold)

    obj = ConvenioIntegrado.objects.get(siafi_uo="100011001")

    assert obj.g_situacao_convenio == "VIGENTE"
    assert obj.g_vigencia == "Vigente"
    assert obj.g_esfera == "Federal"
    assert obj.g_ano_convenio == 2020
    assert obj.a_situacao_convenio == "VIGENTE"
    # data armazenada como DateField
    from datetime import date
    assert obj.g_fim_vigencia == date(2025, 1, 31)
    assert obj.a_fim_vigencia == date(2025, 1, 31)
