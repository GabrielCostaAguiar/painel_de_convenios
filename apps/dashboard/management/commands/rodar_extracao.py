"""
Management command: rodar_extracao

Orquestra os dutos de extração (transferegov, gmail): cada um pousa seus
arquivos em data/raw/<fonte>/ e retorna a lista de Paths baixados.
Falha de um duto não impede a execução do outro.

Não chama a camada de ingestion (Bronze) — só extrai.

Uso:
    python manage.py rodar_extracao
"""

from django.core.management.base import BaseCommand

from core.extract import gmail, transferegov


class Command(BaseCommand):
    help = "Orquestra a extração (transferegov + gmail) pousando arquivos em data/raw/."

    def handle(self, *args, **options):
        dutos = [
            ("transferegov", transferegov.extrair),
            ("gmail", gmail.extrair),
        ]

        resultados = {}
        for nome, extrair in dutos:
            self.stdout.write(f"Extraindo '{nome}'...")
            try:
                arquivos = extrair()
            except Exception as exc:
                # Captura ampla e intencional: um duto com falha não pode
                # impedir a execução do outro.
                self.stderr.write(self.style.ERROR(f"[{nome}] falhou: {exc}"))
                resultados[nome] = []
                continue

            resultados[nome] = arquivos
            for arquivo in arquivos:
                self.stdout.write(f"  [{nome}] {arquivo}")

        total = sum(len(arquivos) for arquivos in resultados.values())
        resumo = ", ".join(f"{nome}={len(arquivos)}" for nome, arquivos in resultados.items())
        self.stdout.write(
            self.style.SUCCESS(f"Concluído! {total} arquivo(s) novo(s) ({resumo}).")
        )
