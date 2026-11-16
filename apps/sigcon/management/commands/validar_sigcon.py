"""
Management command: validar_sigcon

Roda o catálogo de testes de qualidade do SIGCON (apps/sigcon/validacao/catalogo.py,
Modelo de Extração SIGCON v1.0, checklist V1–V14) e grava cada resultado em
ResultadoValidacao (tabela dq_resultado_validacao_sigcon), todos com o mesmo
UUID de execução. A mecânica comum está em core.validacao.executor.

Falha de teste ERRO faz o comando sair com código != 0 (o agendador percebe);
falha de ALERTA só é registrada. Testes com `limite` (exceções conhecidas,
apps/sigcon/validacao/limites.py) gravam ALERTA até o limite e ERRO acima dele.

Uso:
    python manage.py validar_sigcon
"""

from apps.sigcon.models import ResultadoValidacao
from apps.sigcon.validacao.catalogo import TESTES
from core.validacao.executor import ComandoValidacao


class Command(ComandoValidacao):
    help = "Roda o catálogo de testes de qualidade do SIGCON e registra o resultado."

    def obter_testes(self):
        return TESTES

    def modelo_resultado(self):
        return ResultadoValidacao
