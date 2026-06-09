"""
Management command: rodar_transformacao

Lê o arquivo Bronze mais recente de uma fonte, aplica as regras
da camada Silver e salva o resultado em data/silver/.

Uso:
    python manage.py rodar_transformacao convenios
"""

from django.core.management.base import BaseCommand, CommandError

from core.transform import convenios as transform_convenios

# Mapa: nome_fonte → módulo de transformação
# Quando adicionar uma nova fonte, registre aqui.
_TRANSFORMADORES = {
    "convenios": transform_convenios,
}


class Command(BaseCommand):
    help = "Transforma o Bronze mais recente de uma fonte e grava em Silver."

    def add_arguments(self, parser):
        parser.add_argument(
            "fonte",
            help=f"Fonte a transformar. Disponíveis: {', '.join(_TRANSFORMADORES)}",
        )

    def handle(self, *args, **options):
        nome = options["fonte"]

        modulo = _TRANSFORMADORES.get(nome)
        if modulo is None:
            raise CommandError(
                f"Fonte '{nome}' sem transformador registrado. "
                f"Disponíveis: {', '.join(_TRANSFORMADORES)}"
            )

        self.stdout.write(f"Transformando Bronze -> Silver: '{nome}'...")
        try:
            destino = modulo.transformar_bronze(nome)
        except (FileNotFoundError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(f"Concluído! Silver salvo em:\n  {destino}")
        )
