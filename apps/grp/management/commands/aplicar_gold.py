from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection, transaction

PASTA_GOLD = Path(__file__).resolve().parents[2] / "sql" / "gold"


class Command(BaseCommand):
    help = "Recria o schema gold a partir dos arquivos .sql, em ordem de nome."

    def handle(self, *args, **options):
        arquivos = sorted(PASTA_GOLD.glob("*.sql"))   # todos os .sql da pasta, ordenados
        with transaction.atomic():
            with connection.cursor() as cur:
                for arq in arquivos:
                    cur.execute(arq.read_text(encoding="utf-8"))   # ler o arquivo e executar
                    self.stdout.write(f"aplicado: {arq.name}")