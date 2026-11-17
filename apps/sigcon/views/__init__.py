"""
Views das Consultas SIGCON — um modulo por sub-aba, mais os exports.

O que urls.py referencia e reexportado aqui, entao `views.<nome>` resolve
igual, independentemente de em qual modulo a funcao mora.
"""

from ._filtros import ler_filtros_sigcon
from .convenios import sigcon
from .cronograma import cronograma
from .plano_aplicacao import plano_aplicacao
from .termo_aditivo import termo_aditivo
from .prorrogacao_oficio import prorrogacao_oficio
from .unidade_executora import unidade_executora
from .exports import (
    cronograma_export_csv,
    cronograma_export_xlsx,
    plano_aplicacao_export_csv,
    plano_aplicacao_export_xlsx,
    sigcon_export_csv,
    sigcon_export_xlsx,
    termo_aditivo_export_csv,
    termo_aditivo_export_xlsx,
    prorrogacao_oficio_export_csv,
    prorrogacao_oficio_export_xlsx,
    unidade_executora_export_csv,
    unidade_executora_export_xlsx,
)


__all__ = [
    # telas
    "sigcon",
    "plano_aplicacao",
    "cronograma",
    "termo_aditivo",
    "prorrogacao_oficio",
    "unidade_executora",
    # exports
    "sigcon_export_csv",
    "sigcon_export_xlsx",
    "plano_aplicacao_export_csv",
    "plano_aplicacao_export_xlsx",
    "cronograma_export_csv",
    "cronograma_export_xlsx",
    "termo_aditivo_export_csv",
    "termo_aditivo_export_xlsx",
    "prorrogacao_oficio_export_csv",
    "prorrogacao_oficio_export_xlsx",
    "unidade_executora_export_csv",
    "unidade_executora_export_xlsx",
    # helper compartilhado entre tela e export
    "ler_filtros_sigcon",
]
