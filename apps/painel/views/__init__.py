"""
Views do painel: indicadores, graficos e as telas de Acompanhamento.

As telas das abas moram no app de cada aba (apps.sigcon, apps.grp, apps.uniao,
apps.execucao).
"""

from .painel import graficos, indicadores
from .stubs import alertas, emendas, monitoramento, relatorio

__all__ = [
    "indicadores",
    "graficos",
    "monitoramento",
    "relatorio",
    "alertas",
    "emendas",
]
