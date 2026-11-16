"""
Management command: carregar_grp

Full refresh das tabelas do GRP a partir dos Parquets Silver.

O GRP ainda está **em teste**: por isso ele entra na CLI mas fica FORA do
`rodar_pipeline` por padrão. Uma falha ou ausência de arquivo GRP não pode
afetar a atualização diária do painel SIGCON. Para incluí-lo no pipeline,
defina PIPELINE_INCLUIR_GRP=True (ver config/settings/base.py).

Pré-requisito por fonte:
    python manage.py rodar_ingestao <fonte>
    python manage.py rodar_silver <fonte>

Uso:
    python manage.py carregar_grp
    python manage.py carregar_grp --fonte grp_instrumento
    python manage.py carregar_grp --fonte grp_instrumento --fonte grp_concedente
"""

from apps.grp.loader import _LOADERS_GRP
from core.carga.comando import ComandoCarga


class Command(ComandoCarga):
    help = (
        "Full refresh das tabelas do GRP a partir dos Parquets Silver. "
        "Sem argumentos, carrega todas; use --fonte para escolher."
    )
    rotulo = "GRP"
    loaders = _LOADERS_GRP
