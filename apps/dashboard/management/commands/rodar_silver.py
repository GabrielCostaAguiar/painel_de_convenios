"""
Management command: rodar_silver

Transforma o Bronze mais recente de uma fonte, valida o resultado e grava
em data/silver/<fonte>.parquet (Parquet preserva datetime, float e StringDtype).

Pré-requisito: o schema YAML da fonte deve existir em core/transform/schemas/.
  python manage.py gerar_schemas <fonte>   ← gera o schema se ainda não existir

Uso:
    python manage.py rodar_silver <fonte>
    python manage.py rodar_silver <fonte> --bronze <caminho/para/arquivo.csv>

Exemplos:
    python manage.py rodar_silver dcgce_convenios
    python manage.py rodar_silver dcgce_geral
    python manage.py rodar_silver dcgce_convenios --bronze data/bronze/dcgce_convenios/dcgce_convenios_20260609_164337.csv
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.ingestion.sources import FONTES
from core.transform.silver import gravar_silver, transformar_fonte


class Command(BaseCommand):
    help = "Transforma o Bronze de qualquer fonte registrada e grava o Silver em Parquet (data/silver/)."

    def add_arguments(self, parser):
        parser.add_argument(
            "fonte",
            help=f"Fonte a transformar. Disponíveis: {', '.join(FONTES)}",
        )
        parser.add_argument(
            "--bronze",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help=(
                "Caminho customizado para o CSV Bronze de entrada. "
                "Quando omitido, usa o arquivo mais recente em DATA_DIR/bronze/<fonte>/."
            ),
        )

    def handle(self, *args, **options):
        nome = options["fonte"]
        bronze_path = options["bronze"]

        if nome not in FONTES:
            disponiveis = ", ".join(FONTES)
            raise CommandError(
                f"Fonte '{nome}' não registrada em FONTES. Disponíveis: {disponiveis}"
            )

        self.stdout.write(f"Iniciando Silver: '{nome}'...")

        try:
            df = transformar_fonte(nome, bronze_path)
            destino = gravar_silver(nome, df)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(f"Concluído! Silver salvo em:\n  {destino}")
        )
