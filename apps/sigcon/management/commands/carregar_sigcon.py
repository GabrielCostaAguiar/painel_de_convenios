"""
Management command: carregar_sigcon

Full refresh das tabelas do SIGCON a partir dos Parquets Silver.

Carga avulsa: não é chamado pelo `rodar_pipeline` (cujo CARGAS_ORM ainda aponta
para os comandos de carga antigos, removidos).
Cada carga bem-sucedida grava a contagem de linhas em SigconHistoricoCarga, que
o teste de volumetria histórica de `validar_sigcon` compara com a carga anterior.

Pré-requisito por fonte:
    python manage.py rodar_ingestao <fonte>
    python manage.py rodar_silver <fonte>

Uso:
    python manage.py carregar_sigcon
    python manage.py carregar_sigcon --fonte sigcon_convenio
    python manage.py carregar_sigcon --fonte sigcon_convenio --fonte sigcon_concedente
"""

from apps.sigcon.loader import _LOADERS_SIGCON
from apps.sigcon.models import SigconHistoricoCarga
from core.carga.comando import ComandoCarga


class Command(ComandoCarga):
    help = (
        "Full refresh das tabelas do SIGCON a partir dos Parquets Silver. "
        "Sem argumentos, carrega todas; use --fonte para escolher."
    )
    rotulo = "SIGCON"
    loaders = _LOADERS_SIGCON

    def apos_carga(self, fonte, resultado):
        SigconHistoricoCarga.objects.create(
            tabela=fonte, qt_linhas=resultado["inseridos"]
        )
