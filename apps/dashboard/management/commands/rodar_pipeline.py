"""
Management command: rodar_pipeline

Maestro raw->bronze: dispara a extração (transferegov, gmail) e, na
sequência, a ingestão Bronze das fontes que a ponte sabe mapear
(core/ingestion/ponte_extracao.py). Comando magro — só orquestra; toda a
lógica de download vive em core/extract/, toda a lógica de ingestão vive em
core/ingestion/.

Ordem: extrair -> bronze. O Bronze processa o arquivo MAIS RECENTE
disponível em data/raw/ por fonte, independente de a extração de hoje ter
rodado com sucesso (mesma semântica já usada por rodar_silver/_bronze_mais_recente
para bronze->silver). Se não existir nenhum arquivo, de nenhuma data, a
fonte é logada e pulada — não aborta as demais.

Falha de um duto de extração, ou de uma fonte na ingestão Bronze, é
registrada e a execução segue para os próximos.

Uso:
    python manage.py rodar_pipeline
"""

from django.core.management.base import BaseCommand

from core.extract import gmail, transferegov
from core.ingestion.ponte_extracao import ingerir_gmail_mapeados, ingerir_transferegov


class Command(BaseCommand):
    help = "Maestro: extração (transferegov + gmail) seguida da ingestão Bronze das fontes mapeadas."

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
                # impedir a execução do outro, nem a etapa de Bronze a seguir.
                self.stderr.write(self.style.ERROR(f"[{nome}] falhou: {exc}"))
                resultados[nome] = []
                continue

            resultados[nome] = arquivos
            for arquivo in arquivos:
                self.stdout.write(f"  [{nome}] {arquivo}")

        total = sum(len(arquivos) for arquivos in resultados.values())
        resumo = ", ".join(f"{nome}={len(arquivos)}" for nome, arquivos in resultados.items())
        self.stdout.write(
            self.style.SUCCESS(f"Extração concluída: {total} arquivo(s) novo(s) ({resumo}).")
        )

        self.stdout.write("Ingerindo Bronze a partir do raw mais recente...")
        bronze_gerados = []

        try:
            bronze_gerados += ingerir_gmail_mapeados()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"[bronze/gmail] falhou: {exc}"))

        try:
            destino = ingerir_transferegov()
            if destino is not None:
                bronze_gerados.append(destino)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"[bronze/transferegov] falhou: {exc}"))

        for destino in bronze_gerados:
            self.stdout.write(f"  [bronze] {destino}")

        self.stdout.write(
            self.style.SUCCESS(f"Bronze concluído: {len(bronze_gerados)} arquivo(s) gerado(s).")
        )
