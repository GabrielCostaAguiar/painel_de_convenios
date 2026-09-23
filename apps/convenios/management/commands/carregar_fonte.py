"""
Management command: carregar_fonte

Full refresh de qualquer fonte auxiliar de convênios no banco.
Para o model principal Convenio, use: python manage.py carregar_convenios

Uso:
    python manage.py carregar_fonte <fonte>
    python manage.py carregar_fonte <fonte> --silver <caminho/para/arquivo.parquet>

Exemplos:
    python manage.py carregar_fonte dcgce_geral
    python manage.py carregar_fonte dcgce_termo.aditivo
    python manage.py carregar_fonte dcgce_plano.trabalho --silver data/silver/dcgce_plano.trabalho.parquet
"""

from pathlib import Path

import logging

from django.core.management.base import BaseCommand, CommandError

from core.cache import invalidar_cache_indicadores

from apps.convenios import loader as loaders

_LOADERS = {
    "dcgce_geral":                    loaders.carregar_convenio_geral,
    "dcgce_plano.trabalho":           loaders.carregar_plano_trabalho,
    "dcgce_Cronograma_desembolso":    loaders.carregar_cronograma_desembolso,
    "dcgce_plano_aplicacao":          loaders.carregar_plano_aplicacao,
    "dcgce_termo.aditivo":            loaders.carregar_termo_aditivo,
    "dcgce_declaracao_contrapartida": loaders.carregar_declaracao_contrapartida,
    "dcgce_prorrogacao_oficio":       loaders.carregar_prorrogacao_oficio,
    "dcgce_sigcon_nt_emenda":         loaders.carregar_nt_emenda,
    "dcgce_esfera":                   loaders.carregar_esfera,
    "dcgce_Codigo_convenio":          loaders.carregar_codigo_convenio,
    "dcgce_Codigo_plano_de_trabalho": loaders.carregar_codigo_plano_trabalho,
    "dcgce_Codigo_ta":                loaders.carregar_codigo_termo_aditivo,
    "dcgce_Codigo_dec_contrap":       loaders.carregar_codigo_declaracao_contrapartida,
}

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Full refresh de uma fonte auxiliar de convênios no banco de dados."

    def add_arguments(self, parser):
        parser.add_argument(
            "fonte",
            help=(
                "Nome da fonte a carregar. "
                f"Disponíveis: {', '.join(_LOADERS)}"
            ),
        )
        parser.add_argument(
            "--silver",
            type=Path,
            default=None,
            metavar="CAMINHO",
            help=(
                "Caminho customizado para o Parquet Silver. "
                "Omitir = DATA_DIR/silver/<fonte>.parquet"
            ),
        )

    def handle(self, *args, **options):
        fonte = options["fonte"]
        silver_path = options["silver"]

        loader_fn = _LOADERS.get(fonte)
        if loader_fn is None:
            disponiveis = ", ".join(_LOADERS)
            raise CommandError(
                f"Fonte '{fonte}' não registrada.\n"
                f"Disponíveis: {disponiveis}\n"
                "Para o model Convenio, use: python manage.py carregar_convenios"
            )

        self.stdout.write(f"Carregando '{fonte}' no banco (full refresh)...")

        try:
            resultado = loader_fn(silver_path=silver_path)
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
            logger.exception("Falha inesperada ao carregar %s", fonte)
            raise CommandError(f"Falha ao carregar {fonte}: {exc}") from exc

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
