"""
Management command: rodar_ingestao

Uso:
    python manage.py rodar_ingestao <fonte>
    python manage.py rodar_ingestao <fonte> --arquivo <caminho/para/arquivo.csv>

Exemplos:
    python manage.py rodar_ingestao convenios
    python manage.py rodar_ingestao convenios --arquivo tests/fixtures/convenios_exemplo.csv
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.ingestion.bronze import ingerir
from core.ingestion.sources import FONTES


class Command(BaseCommand):
    help = "Ingere um CSV de fonte bruta e o salva na camada Bronze (data/bronze/)."

    def add_arguments(self, parser):
        parser.add_argument(
            "fonte",
            help=f"Identificador da fonte a ingerir. Disponíveis: {', '.join(FONTES)}",
        )
        parser.add_argument(
            "--arquivo",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help=(
                "Caminho customizado para o arquivo CSV de entrada. "
                "Quando omitido, usa DATA_DIR/raw/<arquivo configurado em sources.py>."
            ),
        )

    def handle(self, *args, **options):
        nome = options["fonte"]
        arquivo = options["arquivo"]

        self.stdout.write(f"Iniciando ingestão: '{nome}'...")

        try:
            destino = ingerir(nome, arquivo=arquivo)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(f"Concluído! Bronze salvo em:\n  {destino}")
        )
