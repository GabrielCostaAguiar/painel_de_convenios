"""
Views de export CSV/XLSX das abas de Consultas SIGCON.

Cada export usa a mesma consulta, as mesmas colunas e os mesmos campos da tela
correspondente (módulo da sub-aba), para que o arquivo baixado tenha exatamente
as linhas — e na mesma ordem — que o usuário está vendo.

Atenção: core.export.xlsx não pode importar pandas/numpy (erro de OpenBLAS com
múltiplos workers em produção) — não introduza esse import neste caminho.
"""

from importlib import import_module

from ._filtros import sigcon_exportar

# import_module, e não `from . import cronograma`: views/__init__.py reexporta a
# FUNÇÃO `cronograma` (e `prorrogacao`, ...), que oculta o módulo de mesmo nome
# no atributo do pacote.
convenios = import_module("apps.sigcon.views.convenios")
cronograma = import_module("apps.sigcon.views.cronograma")
plano_aplicacao = import_module("apps.sigcon.views.plano_aplicacao")
prorrogacao = import_module("apps.sigcon.views.prorrogacao")
termo_aditivo = import_module("apps.sigcon.views.termo_aditivo")
unidades_executoras = import_module("apps.sigcon.views.unidades_executoras")


def _exportar(request, modulo, nome, formato):
    resultado = modulo.consulta(request)
    # convenios.consulta devolve só o queryset; as demais, (queryset, preparar)
    if isinstance(resultado, tuple):
        qs, preparar = resultado
    else:
        qs, preparar = resultado, getattr(modulo, "preparar", None)
    return sigcon_exportar(qs, modulo.COLUNAS, modulo.CAMPOS, nome, formato, preparar)


def sigcon_export_csv(request):
    return _exportar(request, convenios, "convenios", "csv")


def sigcon_export_xlsx(request):
    return _exportar(request, convenios, "convenios", "xlsx")


def plano_aplicacao_export_csv(request):
    return _exportar(request, plano_aplicacao, plano_aplicacao.NOME_EXPORT, "csv")


def plano_aplicacao_export_xlsx(request):
    return _exportar(request, plano_aplicacao, plano_aplicacao.NOME_EXPORT, "xlsx")


def cronograma_export_csv(request):
    return _exportar(request, cronograma, cronograma.NOME_EXPORT, "csv")


def cronograma_export_xlsx(request):
    return _exportar(request, cronograma, cronograma.NOME_EXPORT, "xlsx")


def prorrogacao_export_csv(request):
    return _exportar(request, prorrogacao, prorrogacao.NOME_EXPORT, "csv")


def prorrogacao_export_xlsx(request):
    return _exportar(request, prorrogacao, prorrogacao.NOME_EXPORT, "xlsx")


def termo_aditivo_export_csv(request):
    return _exportar(request, termo_aditivo, termo_aditivo.NOME_EXPORT, "csv")


def termo_aditivo_export_xlsx(request):
    return _exportar(request, termo_aditivo, termo_aditivo.NOME_EXPORT, "xlsx")


def unidades_executoras_export_csv(request):
    return _exportar(request, unidades_executoras, unidades_executoras.NOME_EXPORT, "csv")


def unidades_executoras_export_xlsx(request):
    return _exportar(request, unidades_executoras, unidades_executoras.NOME_EXPORT, "xlsx")
