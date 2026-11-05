"""
Views do GRP — um modulo por sub-aba, mais os exports.

O que urls.py referencia e reexportado aqui, entao `views.<nome>` resolve
igual, independentemente de em qual modulo a funcao mora.
"""

from ._filtros import _ler_filtros_grp
from .cronograma import grp_cronograma
from .instrumentos import grp_instrumentos
from .plano_aplicacao import grp_plano_aplicacao
from .emenda import grp_emenda
from .regioes_municipios_atendidos import grp_regioes_atendidas
from .prestacao_contas import grp_prestacao_contas
__all__ = [
    # telas
    "grp_cronograma",
    "grp_instrumentos",
    "grp_plano_aplicacao",
    "grp_emenda",
    "grp_regioes_atendidas",
    "grp_prestacao_contas",
    # helper compartilhado entre tela e export
    "_ler_filtros_grp",
]
