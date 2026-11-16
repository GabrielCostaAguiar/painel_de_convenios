"""
Management command: validar_grp

Roda o catálogo de testes de qualidade do GRP (apps/grp/validacao/catalogo.py) e
grava cada resultado em ResultadoValidacao. A mecânica comum (UUID de execução,
severidade, amostra, saída != 0 em falha ERRO) está em core.validacao.executor.

Uso:
    python manage.py validar_grp
"""

from apps.grp.models import ResultadoValidacao
from apps.grp.validacao.catalogo import TESTES
from core.validacao.executor import ComandoValidacao


class Command(ComandoValidacao):
    help = "Roda o catálogo de testes de qualidade do GRP e registra o resultado."

    def obter_testes(self):
        return TESTES

    def modelo_resultado(self):
        return ResultadoValidacao
