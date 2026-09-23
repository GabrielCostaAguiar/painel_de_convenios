"""
Management command: carregar_relacionamento

Full refresh do model ConvenioIntegrado (tabela Gold integrada G_/A_).

Fluxo:
  - Se data/gold/convenios_integrado.parquet existir: lê direto.
  - Senão (ou com --construir): constrói a partir dos Silver files e grava o Gold.

Pré-requisitos dos Silver files:
  python manage.py rodar_silver chaves_convenio
  python manage.py rodar_silver siafi2
  python manage.py rodar_silver dcgce_convenio
  python manage.py rodar_silver dcgce_codigo_convenio
  python manage.py rodar_silver dcgce_geral
  python manage.py rodar_silver dcgce_plano_trabalho
  python manage.py rodar_silver dcgce_esfera

Uso:
  python manage.py carregar_relacionamento
  python manage.py carregar_relacionamento --construir       # força rebuild do Gold
  python manage.py carregar_relacionamento --gold caminho/arquivo.parquet
"""

from pathlib import Path

import logging

from django.core.management.base import BaseCommand, CommandError

from core.cache import invalidar_cache_indicadores
from django.conf import settings

from apps.convenios.loader import carregar_tabela_integrada

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Full refresh do ConvenioIntegrado (tabela Gold G_/A_): "
        "lê data/gold/convenios_integrado.parquet ou reconstrói dos Silver files."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--gold",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help="Caminho explícito para o Parquet Gold. Omitir = data/gold/convenios_integrado.parquet",
        )
        parser.add_argument(
            "--construir",
            action="store_true",
            default=False,
            help="Força a reconstrução da tabela a partir dos Silver files (ignora Gold existente).",
        )

    def handle(self, *args, **options):
        gold_path = options["gold"]
        forcar_rebuild = options["construir"]

        if forcar_rebuild:
            # Apaga o Gold existente para forçar rebuild
            padrao = Path(settings.DATA_DIR) / "gold" / "convenios_integrado.parquet"
            destino = gold_path or padrao
            if destino.exists():
                destino.unlink()
                self.stdout.write(f"Gold removido para rebuild: {destino}")

        self.stdout.write("Carregando ConvenioIntegrado no banco (full refresh)...")

        try:
            resultado = carregar_tabela_integrada(gold_path)
        except FileNotFoundError as exc:
            # Erro esperado: a fonte ainda nao foi ingerida/transformada. O
            # proprio loader ja diz qual arquivo falta e o que rodar antes,
            # entao basta repassar — sem traceback, porque nao ha bug aqui.
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            # Erro inesperado (dado corrompido, bug, queda de conexao): o
            # traceback completo vai para o log e a causa original fica
            # encadeada com `from exc`, para o diagnostico nao se perder atras
            # da mensagem generica. Antes, o `except (FileNotFoundError,
            # Exception)` engolia os dois casos do mesmo jeito.
            logger.exception("Falha inesperada ao carregar %s", "ConvenioIntegrado")
            raise CommandError(f"Falha ao carregar {"ConvenioIntegrado"}: {exc}") from exc

        # A carga alterou o banco: invalida os indicadores agora, para o painel
        # nao servir numeros velhos ate o TTL do cache expirar. Feito aqui (e
        # nao so no rodar_pipeline) porque este comando tambem roda sozinho.
        invalidar_cache_indicadores()

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído! Apagados: {resultado['apagados']} | "
                f"Inseridos: {resultado['inseridos']}"
            )
        )
