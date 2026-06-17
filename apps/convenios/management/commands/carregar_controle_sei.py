"""
Management command: carregar_controle_sei

Full refresh do model ControleSEI a partir do Silver controle_sei.parquet.

Pré-requisito:
  python manage.py rodar_silver controle_sei

Uso:
    python manage.py carregar_controle_sei
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.convenios.loader import carregar_controle_sei


class Command(BaseCommand):
    help = "Full refresh do ControleSEI a partir de data/silver/controle_sei.parquet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--silver",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help="Caminho customizado para o Parquet Silver. Omitir = DATA_DIR/silver/controle_sei.parquet",
        )

    def handle(self, *args, **options):
        self.stdout.write("Carregando Controle SEI no banco (full refresh)...")

        try:
            resultado = carregar_controle_sei(options["silver"])
        except (FileNotFoundError, Exception) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído! Apagados: {resultado['apagados']} | "
                f"Inseridos: {resultado['inseridos']}"
            )
        )
