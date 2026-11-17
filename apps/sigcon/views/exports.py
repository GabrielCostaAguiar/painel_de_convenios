"""
Views de export CSV/XLSX das abas de Consultas SIGCON.

Cada export usa a mesma consulta, as mesmas colunas e os mesmos campos da tela
correspondente (módulo da sub-aba), para que o arquivo baixado tenha exatamente
as linhas — e na mesma ordem — que o usuário está vendo.

Atenção: core.web.exportacao não pode importar pandas/numpy (erro de OpenBLAS com
múltiplos workers em produção) — não introduza esse import neste caminho.
"""

from importlib import import_module

from ._filtros import sigcon_exportar

# import_module, e não `from . import cronograma`: views/__init__.py reexporta a
# FUNÇÃO `cronograma` (...), que oculta o módulo de mesmo nome
# no atributo do pacote.
convenios = import_module("apps.sigcon.views.convenios")
cronograma = import_module("apps.sigcon.views.cronograma")
plano_aplicacao = import_module("apps.sigcon.views.plano_aplicacao")
termo_aditivo = import_module("apps.sigcon.views.termo_aditivo")
prorrogacao_oficio = import_module("apps.sigcon.views.prorrogacao_oficio")
unidade_executora = import_module("apps.sigcon.views.unidade_executora")


def _exportar(request, modulo, nome, formato):
    return sigcon_exportar(modulo.consulta(request), modulo.COLUNAS, modulo.CAMPOS, nome, formato)


def sigcon_export_csv(request):
    return _exportar(request, convenios, convenios.NOME_EXPORT, "csv")


def sigcon_export_xlsx(request):
    return _exportar(request, convenios, convenios.NOME_EXPORT, "xlsx")


def plano_aplicacao_export_csv(request):
    return _exportar(request, plano_aplicacao, plano_aplicacao.NOME_EXPORT, "csv")


def plano_aplicacao_export_xlsx(request):
    return _exportar(request, plano_aplicacao, plano_aplicacao.NOME_EXPORT, "xlsx")


def cronograma_export_csv(request):
    return _exportar(request, cronograma, cronograma.NOME_EXPORT, "csv")


def cronograma_export_xlsx(request):
    return _exportar(request, cronograma, cronograma.NOME_EXPORT, "xlsx")


def termo_aditivo_export_csv(request):
    return _exportar(request, termo_aditivo, termo_aditivo.NOME_EXPORT, "csv")


def termo_aditivo_export_xlsx(request):
    return _exportar(request, termo_aditivo, termo_aditivo.NOME_EXPORT, "xlsx")

def prorrogacao_oficio_export_csv(request):
    return _exportar(request, prorrogacao_oficio, prorrogacao_oficio.NOME_EXPORT, "csv")


def prorrogacao_oficio_export_xlsx(request):
    return _exportar(request, prorrogacao_oficio, prorrogacao_oficio.NOME_EXPORT, "xlsx")

def unidade_executora_export_csv(request):
    return _exportar(request, unidade_executora, unidade_executora.NOME_EXPORT, "csv")


def unidade_executora_export_xlsx(request):
    return _exportar(request, unidade_executora, unidade_executora.NOME_EXPORT, "xlsx")
