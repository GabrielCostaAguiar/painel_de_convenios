"""
Testes da função enrich_convenios_page — cobertura do campo no_sei.
Usa banco SQLite de teste (pytest-django); sem arquivos externos.
"""

import pytest

from apps.convenios.models import ControleSEI, Convenio


@pytest.mark.django_db
def test_enrich_convenios_page_retorna_sei_pelo_siafi():
    """Para um SIAFI com SEI cadastrado, enrich devolve o nº SEI correto."""
    from apps.dashboard.services import enrich_convenios_page

    ControleSEI.objects.create(
        no_sei="1250.01.0000041/2018-13",
        no_siafi_sigcon="9179282",
        no_proposta_siconv="20496/2017",
    )
    conv = Convenio.objects.create(
        convenio_codigo="CONV-001",
        convenio_numero_sequencial_siafi="9179282",
        unidade_orcamentaria_codigo="1261",
    )

    resultado = enrich_convenios_page([conv])
    assert resultado[conv.pk]["no_sei"] == "1250.01.0000041/2018-13"


@pytest.mark.django_db
def test_enrich_convenios_page_sei_ausente_retorna_tracinho():
    """Convênio sem SEI correspondente recebe '—'."""
    from apps.dashboard.services import enrich_convenios_page

    conv = Convenio.objects.create(
        convenio_codigo="CONV-002",
        convenio_numero_sequencial_siafi="9999999",
        unidade_orcamentaria_codigo="1261",
    )

    resultado = enrich_convenios_page([conv])
    assert resultado[conv.pk]["no_sei"] == "—"


@pytest.mark.django_db
def test_enrich_convenios_page_nao_join_por_siafi_uo():
    """
    Garante que o join usa SIAFI puro, não siafi_uo.
    Se o join fosse por siafi_uo (ex: '91792821261'), o SEI não seria encontrado
    mesmo com SIAFI correto — a chave errada faria o SEI 'sumir' silenciosamente.
    """
    from apps.dashboard.services import enrich_convenios_page

    ControleSEI.objects.create(
        no_sei="1250.01.0000041/2018-13",
        no_siafi_sigcon="9179282",   # SIAFI puro
        no_proposta_siconv=None,
    )
    # Convênio com UO diferente mas mesmo SIAFI — deve encontrar o SEI
    conv = Convenio.objects.create(
        convenio_codigo="CONV-003",
        convenio_numero_sequencial_siafi="9179282",
        unidade_orcamentaria_codigo="9999",   # UO diferente da planilha SEI
    )

    resultado = enrich_convenios_page([conv])
    assert resultado[conv.pk]["no_sei"] == "1250.01.0000041/2018-13"
