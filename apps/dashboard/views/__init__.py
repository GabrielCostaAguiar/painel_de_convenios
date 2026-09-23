"""
Views do dashboard, agrupadas por tela.

Era um único views.py de ~968 linhas. Views são funções comuns: o Django não
liga para o arquivo em que moram, só para o que urls.py referencia.

Os arquivos:
  _helpers.py  — utilitários privados compartilhados
  painel.py    — indicadores (KPIs) e gráficos
  sigcon.py    — as 6 sub-abas de Consultas SIGCON (telas)
  exports.py   — os exports CSV/XLSX dessas abas
  grp.py       — as 7 sub-abas do GRP (em teste)
  stubs.py     — seções ainda em construção

Tudo que urls.py referencia é reexportado aqui, então `views.<nome>` continua
resolvendo igual e urls.py não precisou mudar.
"""

from ._helpers import _ler_filtros_sigcon, _stub, _visible_pages
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
from .sigcon import (
    cronograma,
    plano_aplicacao,
    prorrogacao,
    sigcon,
    termo_aditivo,
    unidades_executoras,
)
from .stubs import alertas, emendas, execucao, monitoramento, relatorio, uniao

__all__ = [
    # painel
    "indicadores",
    "graficos",
    # consultas sigcon — telas
    "sigcon",
    "plano_aplicacao",
    "cronograma",
    "prorrogacao",
    "termo_aditivo",
    "unidades_executoras",
    # consultas sigcon — exports
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
    # grp
    "grp_instrumentos",
    "grp_cronograma",
    "grp_recursos_contrapartida",
    "grp_recursos_concedente",
    "grp_plano_aplicacao",
    "grp_plano_aplicacao_detalhes",
    "grp_esfera",
    # stubs
    "uniao",
    "execucao",
    "monitoramento",
    "relatorio",
    "alertas",
    "emendas",
    # helpers (privados, reexportados para quem já os importava de views)
    "_visible_pages",
    "_ler_filtros_sigcon",
    "_stub",
]
