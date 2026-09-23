"""
Smoke test das rotas do dashboard, com banco vazio.

Serve de rede de segurança para refatorações que mexem em views.py/urls.py:
se uma view some, muda de assinatura ou passa a estourar sem dados, aqui
aparece. Não valida conteúdo renderizado — só que a rota resolve e responde.

O inventário de URLs (nome → caminho) também é comparado com a lista fixada
abaixo, para pegar rota removida, renomeada ou com caminho alterado.
"""
import pytest
from django.urls import get_resolver
from django.urls.resolvers import URLResolver

# Gabarito: nome da URL → caminho, levantado antes da divisão de views.py
# em pacote. Qualquer divergência aqui é mudança de contrato de rota.
ROTAS_ESPERADAS = {
    "sigcon": "",
    "sigcon_export_csv": "export.csv",
    "sigcon_export_xlsx": "export.xlsx",
    "indicadores": "indicadores/",
    "graficos": "graficos/",
    "plano_aplicacao": "plano_aplicacao/",
    "plano_aplicacao_export_csv": "plano_aplicacao/export.csv",
    "plano_aplicacao_export_xlsx": "plano_aplicacao/export.xlsx",
    "cronograma": "cronograma/",
    "cronograma_export_csv": "cronograma/export.csv",
    "cronograma_export_xlsx": "cronograma/export.xlsx",
    "prorrogacao": "prorrogacao/",
    "prorrogacao_export_csv": "prorrogacao/export.csv",
    "prorrogacao_export_xlsx": "prorrogacao/export.xlsx",
    "termo_aditivo": "termo_aditivo/",
    "termo_aditivo_export_csv": "termo_aditivo/export.csv",
    "termo_aditivo_export_xlsx": "termo_aditivo/export.xlsx",
    "unidades_executoras": "unidades_executoras/",
    "unidades_executoras_export_csv": "unidades_executoras/export.csv",
    "unidades_executoras_export_xlsx": "unidades_executoras/export.xlsx",
    "uniao": "uniao/",
    "execucao": "execucao/",
    "monitoramento": "monitoramento/",
    "relatorio": "relatorio/",
    "alertas": "alertas/",
    "emendas": "emendas/",
    "grp_dados": "grp/dados/",
    "grp_cronograma": "grp/cronograma/",
    "grp_recursos_contrapartida": "grp/recursos_contrapartida/",
    "grp_recursos_concedente": "grp/recursos_concedente/",
    "grp_plano_aplicacao": "grp/plano_aplicacao/",
    "grp_plano_aplicacao_detalhes": "grp/plano_aplicacao_detalhes/",
    "grp_esfera": "grp/esfera/",
}

EXPORTS_CSV = [n for n in ROTAS_ESPERADAS if n.endswith("_export_csv")]
EXPORTS_XLSX = [n for n in ROTAS_ESPERADAS if n.endswith("_export_xlsx")]
TELAS = [n for n in ROTAS_ESPERADAS if not n.endswith(("_export_csv", "_export_xlsx"))]


def _inventario_dashboard():
    """nome da URL → caminho, para os patterns servidos por apps.dashboard."""
    def walk(res, prefixo=""):
        for p in res.url_patterns:
            if isinstance(p, URLResolver):
                yield from walk(p, prefixo + str(p.pattern))
            else:
                modulo = getattr(p.callback, "__module__", "")
                if modulo.startswith("apps.dashboard"):
                    yield p.name, prefixo + str(p.pattern)

    return dict(walk(get_resolver()))


def test_inventario_de_rotas_bate_com_o_gabarito():
    assert _inventario_dashboard() == ROTAS_ESPERADAS


@pytest.mark.django_db
@pytest.mark.parametrize("nome", TELAS)
def test_telas_respondem_com_banco_vazio(client, nome):
    resposta = client.get("/" + ROTAS_ESPERADAS[nome])
    assert resposta.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("nome", EXPORTS_CSV)
def test_export_csv_responde_com_banco_vazio(client, nome):
    resposta = client.get("/" + ROTAS_ESPERADAS[nome])
    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "text/csv; charset=utf-8"


@pytest.mark.django_db
@pytest.mark.parametrize("nome", EXPORTS_XLSX)
def test_export_xlsx_responde_com_banco_vazio(client, nome):
    resposta = client.get("/" + ROTAS_ESPERADAS[nome])
    assert resposta.status_code == 200
    assert resposta["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
