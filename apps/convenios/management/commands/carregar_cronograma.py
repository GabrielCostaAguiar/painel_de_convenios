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

from django.core.management.base import BaseCommand, CommandError

from apps.convenios.loader import carregar_cronograma_desembolso


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
        except (FileNotFoundError, Exception) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído! Apagados: {resultado['apagados']} | "
                f"Inseridos: {resultado['inseridos']}"
            )
        )
