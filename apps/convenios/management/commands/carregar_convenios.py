"""
Management command: carregar_convenios

Full refresh consolidado: lê dcgce_convenio + dcgce_geral + dcgce_plano_trabalho
+ dcgce_esfera, faz os joins internos (SIAFI+UO, plano de trabalho, esfera)
e recarrega a tabela Convenio no banco.

Pré-requisito: Silver de todas as fontes deve estar gerado.
  python manage.py rodar_silver dcgce_convenio
  python manage.py rodar_silver dcgce_geral
  python manage.py rodar_silver dcgce_plano_trabalho
  python manage.py rodar_silver dcgce_esfera
  python manage.py rodar_silver dcgce_codigo_convenio

Uso:
    python manage.py carregar_convenios
    python manage.py carregar_convenios --silver data/silver/dcgce_convenio.parquet
"""

from pathlib import Path

import logging

from django.core.management.base import BaseCommand, CommandError

from core.cache import invalidar_cache_indicadores

from apps.convenios.loader import carregar_convenios

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Full refresh consolidado: carrega Convenio unindo dcgce_convenio + dcgce_geral "
        "+ dcgce_plano_trabalho + dcgce_esfera."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--silver",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help=(
                "Caminho customizado para o Parquet Silver do convenio. "
                "Omitir = DATA_DIR/silver/dcgce_convenio.parquet"
            ),
        )

    def handle(self, *args, **options):
        silver_path = options["silver"]
        self.stdout.write("Carregando convênios no banco (full refresh)...")

        try:
            resultado = carregar_convenios(silver_path)
        except FileNotFoundError as exc:
            # Erro esperado: a fonte ainda nao foi ingerida/transformada. O
            # proprio loader ja diz qual arquivo falta e o que rodar antes,
            # entao basta repassar — sem traceback, porque nao ha bug aqui.
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            # Erro inesperado (dado corrompido, bug, queda de conexao): o
            # traceback completo vai para o log e a causa original fica
            # encadeada com `from exc`, para o diagnostico nao se perder atras
            # da mensagem generica. Antes, o `except (FileNotFoundError,
            # Exception)` engolia os dois casos do mesmo jeito.
            logger.exception("Falha inesperada ao carregar %s", "convênios")
            raise CommandError(f"Falha ao carregar {"convênios"}: {exc}") from exc

        # A carga alterou o banco: invalida os indicadores agora, para o painel
        # nao servir numeros velhos ate o TTL do cache expirar. Feito aqui (e
        # nao so no rodar_pipeline) porque este comando tambem roda sozinho.
        invalidar_cache_indicadores()

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído! Apagados: {resultado['apagados']} | "
                f"Inseridos: {resultado['inseridos']}"
            )
        )
