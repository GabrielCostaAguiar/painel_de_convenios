"""
Management command: carregar_unidades_executoras

Full refresh consolidado: lê dcgce_convenio + dcgce_geral + dcgce_plano_trabalho
+ dcgce_esfera, faz os joins internos (SIAFI+UO, plano de trabalho, esfera)
e recarrega a tabela Convenio no banco.

Pré-requisito: Silver de todas as fontes deve estar gerado.
  python manage.py rodar_silver dcgce_convenio
  python manage.py rodar_silver dcgce_geral
  python manage.py rodar_silver dcgce_plano_trabalho
  python manage.py rodar_silver dcgce_esfera
  python manage.py rodar_silver dcgce_codigo_convenio

Uso:
    python manage.py carregar_unidades_executoras
    python manage.py carregar_unidades_executoras --silver data/silver/dcgce_unidade_executora.parquet
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.convenios.loader import carregar_unidades_executoras


class Command(BaseCommand):
    help = (
        "Full refresh consolidado: carrega UnidadesExecutoras unindo dcgce_unidade_executora + dcgce_geral "
        "+ dcgce_plano_trabalho + dcgce_esfera."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--silver",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help=(
                "Caminho customizado para o Parquet Silver da unidade executora. "
                "Omitir = DATA_DIR/silver/dcgce_unidade_executora.parquet"
            ),
        )

    def handle(self, *args, **options):
        silver_path = options["silver"]
        self.stdout.write("Carregando unidades executoras no banco (full refresh)...")

        try:
            resultado = carregar_unidades_executoras(silver_path)
        except (FileNotFoundError, Exception) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído! Apagados: {resultado['apagados']} | "
                f"Inseridos: {resultado['inseridos']}"
            )
        )
