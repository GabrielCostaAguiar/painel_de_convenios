"""
Views do GRP — um modulo por sub-aba, mais os exports.

O que urls.py referencia e reexportado aqui, entao `views.<nome>` resolve
igual, independentemente de em qual modulo a funcao mora.
"""

from ._filtros import _ler_filtros_grp
from .cronograma import grp_cronograma
from .instrumentos import grp_instrumentos
from .plano_aplicacao import grp_plano_aplicacao
from .plano_aplicacao_detalhado import grp_plano_aplicacao_detalhes
from .recursos_concedente import grp_recursos_concedente
from .recursos_contrapartida import grp_recursos_contrapartida
from . esfera import grp_esfera
__all__ = [
    # telas
    "grp_cronograma",
    "grp_instrumentos",
    "grp_plano_aplicacao",
    "grp_plano_aplicacao_detalhes",
    "grp_recursos_concedente",
    "grp_recursos_contrapartida",
    "grp_esfera",
    # helper compartilhado entre tela e export
    "_ler_filtros_grp"
]
