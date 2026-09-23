"""
Management command: carregar_cronograma

Full refresh: apaga todos os registros de CronogramaDesembolso e reinsere
a partir dos Parquets Silver, carimbando SIAFI+UO via joins internos.

Pipeline de join:
  dcgce_cronograma_desembolso.plano_trabalho_codigo
    → dcgce_geral.conveno_codigo_plano_trabalho  → convenio_codigo_sequencial
    → dcgce_codigo_convenio.convenio_codigo_sequencial → SIAFI + UO

Uso:
    python manage.py carregar_cronograma
    python manage.py carregar_cronograma --silver data/silver/dcgce_cronograma_desembolso.parquet
"""

from pathlib import Path

import logging

from django.core.management.base import BaseCommand, CommandError

from core.cache import invalidar_cache_indicadores

from apps.convenios.loader import carregar_cronograma_desembolso

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Full refresh: apaga e reinsere o cronograma de desembolsos com SIAFI+UO carimbados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--silver",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help=(
                "Caminho customizado para o Parquet Silver do cronograma. "
                "Omitir = DATA_DIR/silver/dcgce_cronograma_desembolso.parquet"
            ),
        )

    def handle(self, *args, **options):
        silver_path = options["silver"]
        self.stdout.write("Carregando cronograma de desembolsos (full refresh + join SIAFI)...")

        try:
            resultado = carregar_cronograma_desembolso(silver_path)
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
            logger.exception("Falha inesperada ao carregar %s", "cronograma de desembolsos")
            raise CommandError(f"Falha ao carregar {"cronograma de desembolsos"}: {exc}") from exc

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
