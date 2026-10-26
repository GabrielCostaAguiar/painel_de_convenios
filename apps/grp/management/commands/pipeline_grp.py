from django.core.management import call_command
from django.core.management.base import BaseCommand

ETAPAS = [
    "carregar_grp",
    "validar_grp",
    # "aplicar_gold" — entra na fase 2.0, depois do validar_grp.
    # A gold só é atualizada se a validação passar.
]


class Command(BaseCommand):
    help = "Orquestra carga e validação do GRP com portão de qualidade."

    def handle(self, *args, **options):
        for etapa in ETAPAS:
            self.stdout.write(f">>> {etapa}")
            call_command(etapa)
            self.stdout.write(self.style.SUCCESS(f"    {etapa} OK"))
