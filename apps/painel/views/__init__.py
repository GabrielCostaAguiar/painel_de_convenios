"""
Views do painel: indicadores, graficos e as telas de Acompanhamento.

As telas das Consultas SIGCON ja moram em apps.sigcon. As do GRP ainda estao
aqui — vao para apps.grp na proxima etapa desta reorganizacao.
"""

from .grp import (
    grp_cronograma,
    grp_esfera,
    grp_instrumentos,
    grp_plano_aplicacao,
    grp_plano_aplicacao_detalhes,
    grp_recursos_concedente,
    grp_recursos_contrapartida,
)
from .painel import graficos, indicadores
from .stubs import alertas, emendas, monitoramento, relatorio

__all__ = [
    "indicadores",
    "graficos",
    "monitoramento",
    "relatorio",
    "alertas",
    "emendas",
    # GRP (em teste) — migra para apps.grp
    "grp_instrumentos",
    "grp_cronograma",
    "grp_recursos_contrapartida",
    "grp_recursos_concedente",
    "grp_plano_aplicacao",
    "grp_plano_aplicacao_detalhes",
    "grp_esfera",
]
