"""
Management command: carregar_relacionamento

Full refresh do model ConvenioIntegrado (tabela Gold integrada G_/A_).

Fluxo:
  - Sem --gold: SEMPRE reconstrói a tabela a partir dos Silver files e regrava
    data/gold/convenios_integrado.parquet. Nunca reaproveita um Gold antigo,
    que poderia ter sido montado com Silver desatualizada.
  - Com --gold <arquivo>: carrega esse Parquet como está, sem reconstruir.
  - --construir é aceito por compatibilidade e equivale ao comportamento padrão.

Pré-requisitos dos Silver files:
  python manage.py rodar_silver sigcon_chave_siconv
  python manage.py rodar_silver depara_siafi
  python manage.py rodar_silver sigcon_convenio
  python manage.py rodar_silver sigcon_chave_convenio
  python manage.py rodar_silver sigcon_convenio_geral
  python manage.py rodar_silver sigcon_plano_trabalho
  python manage.py rodar_silver sigcon_concedente
  python manage.py rodar_silver siconv_convenio          # opcional

Uso:
  python manage.py carregar_relacionamento
  python manage.py carregar_relacionamento --gold caminho/arquivo.parquet
"""

from pathlib import Path

import logging

from django.core.management.base import BaseCommand, CommandError

from core.cache import invalidar_cache_indicadores
from django.conf import settings

from apps.sigcon.loader import carregar_tabela_integrada

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Full refresh do ConvenioIntegrado (tabela Gold G_/A_): "
        "reconstrói dos Silver files, ou carrega o Parquet dado em --gold."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--gold",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help="Carrega este Parquet Gold sem reconstruir. Omitir = reconstrói dos Silver files.",
        )
        parser.add_argument(
            "--construir",
            action="store_true",
            default=False,
            help="Compatibilidade: reconstruir já é o comportamento padrão (sem --gold).",
        )

    def handle(self, *args, **options):
        gold_path = options["gold"]

        if gold_path is None:
            # Sem --gold: reconstrói sempre. O Gold antigo é removido para o
            # loader não o reaproveitar.
            antigo = Path(settings.DATA_DIR) / "gold" / "convenios_integrado.parquet"
            if antigo.exists():
                antigo.unlink()
                self.stdout.write(f"Gold removido para rebuild: {antigo}")

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
