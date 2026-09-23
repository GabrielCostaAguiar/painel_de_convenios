"""
Views das Consultas SIGCON — um modulo por sub-aba, mais os exports.

O que urls.py referencia e reexportado aqui, entao `views.<nome>` resolve
igual, independentemente de em qual modulo a funcao mora.
"""

from ._filtros import ler_filtros_sigcon
from .convenios import sigcon
from .cronograma import cronograma
from .exports import (
    cronograma_export_csv,
    cronograma_export_xlsx,
    plano_aplicacao_export_csv,
    plano_aplicacao_export_xlsx,
    prorrogacao_export_csv,
    prorrogacao_export_xlsx,
    sigcon_export_csv,
    sigcon_export_xlsx,
    termo_aditivo_export_csv,
    termo_aditivo_export_xlsx,
    unidades_executoras_export_csv,
    unidades_executoras_export_xlsx,
)
from .plano_aplicacao import plano_aplicacao
from .prorrogacao import prorrogacao
from .termo_aditivo import termo_aditivo
from .unidades_executoras import unidades_executoras

__all__ = [
    # telas
    "sigcon",
    "plano_aplicacao",
    "cronograma",
    "prorrogacao",
    "termo_aditivo",
    "unidades_executoras",
    # exports
    "sigcon_export_csv",
    "sigcon_export_xlsx",
    "plano_aplicacao_export_csv",
    "plano_aplicacao_export_xlsx",
    "cronograma_export_csv",
    "cronograma_export_xlsx",
    "prorrogacao_export_csv",
    "prorrogacao_export_xlsx",
    "termo_aditivo_export_csv",
    "termo_aditivo_export_xlsx",
    "unidades_executoras_export_csv",
    "unidades_executoras_export_xlsx",
    # helper compartilhado entre tela e export
    "ler_filtros_sigcon",
]
