"""
Helpers de view compartilhados entre os apps do painel.

Mora em core/ porque e usado por mais de um app: deixar em qualquer app
obrigaria os outros a importar dele, e a regra de dependencia do projeto e que
os apps de aba (sigcon, grp, uniao, execucao) nao importam uns dos outros nem
do dashboard.

Pode importar Django. **Nao pode importar apps.\*** — core/ nao conhece os apps.
"""

from .exportacao import exportar_objetos, exportar_xlsx, resposta_csv
from .filtros import Filtro, aplicar_filtros, como_lista, ler_filtros, querystring_de
from .formatacao import fmt_data, fmt_valor, formatar_celula
from .paginacao import paginas_visiveis
from .stubs import view_em_construcao
from .totais import calcular_totais, cards_totais, filtros_ativos

__all__ = [
    "Filtro",
    "aplicar_filtros",
    "como_lista",
    "ler_filtros",
    "querystring_de",
    "calcular_totais",
    "cards_totais",
    "filtros_ativos",
    "exportar_objetos",
    "exportar_xlsx",
    "fmt_data",
    "fmt_valor",
    "formatar_celula",
    "paginas_visiveis",
    "resposta_csv",
    "view_em_construcao",
]
