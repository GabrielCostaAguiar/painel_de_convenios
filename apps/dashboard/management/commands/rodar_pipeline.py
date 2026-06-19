"""
Management command: rodar_pipeline

Roda o pipeline completo: extracao+bronze -> silver -> gold/carga ORM.
Comando magro - toda a logica de orquestracao vive em
core/pipeline.py::atualizar_painel().

Uso:
    python manage.py rodar_pipeline
"""

from django.core.management.base import BaseCommand

from core.pipeline import atualizar_painel


class Command(BaseCommand):
    help = "Roda o pipeline completo: extracao+bronze -> silver -> gold/carga ORM."

    def handle(self, *args, **options):
        resultado = atualizar_painel()

        for etapa in resultado["etapas"]:
            rotulo = self.style.SUCCESS("OK") if etapa["sucesso"] else self.style.ERROR("FALHOU")
            self.stdout.write(f"[{etapa['nome']}] {rotulo} - {etapa['contagens']}")
            for erro in etapa["erros"]:
                self.stderr.write(self.style.WARNING(f"  {erro}"))

        if resultado["sucesso"]:
            self.stdout.write(self.style.SUCCESS("Pipeline concluido com sucesso."))
        else:
            self.stderr.write(self.style.ERROR("Pipeline interrompido - ver erros acima."))
