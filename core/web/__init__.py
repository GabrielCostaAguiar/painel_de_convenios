"""
Helpers de view compartilhados entre os apps do painel.

Mora em core/ porque e usado por mais de um app: deixar em qualquer app
obrigaria os outros a importar dele, e a regra de dependencia do projeto e que
os apps de aba (sigcon, grp, uniao, execucao) nao importam uns dos outros nem
do painel.

Pode importar Django. **Nao pode importar apps.\*** — core/ nao conhece os apps.
"""

from .exports import resposta_csv
from .paginacao import paginas_visiveis
from .stubs import view_em_construcao

__all__ = [
    "paginas_visiveis",
    "resposta_csv",
    "view_em_construcao",
]
