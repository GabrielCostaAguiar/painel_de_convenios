"""
Base dos comandos `carregar_<app>`: full refresh de várias fontes a partir dos
Parquets Silver, com --fonte repetível, resumo, invalidação do cache e o padrão
de exceções do projeto.

A subclasse declara `rotulo`, `loaders` (nome da fonte → função de carga, na
ordem de carga) e, se precisar, sobrescreve `apos_carga`.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from core.cache import invalidar_cache_indicadores

logger = logging.getLogger(__name__)


class ComandoCarga(BaseCommand):
    rotulo = ""   # "GRP", "SIGCON"
    loaders: dict = {}

    @property
    def fontes_disponiveis(self):
        return tuple(self.loaders)

    def add_arguments(self, parser):
        parser.add_argument(
            "--fonte",
            action="append",
            dest="fontes",
            default=None,
            metavar="NOME",
            help=(
                "Fonte a carregar; pode repetir. "
                f"Disponíveis: {', '.join(self.fontes_disponiveis)}. "
                "Omitir = carrega todas."
            ),
        )

    def apos_carga(self, fonte, resultado):
        """Gancho chamado após cada carga bem-sucedida (dentro do try)."""

    def handle(self, *args, **options):
        fontes = self._resolver_fontes(options["fontes"])
        rotulo = self.rotulo

        self.stdout.write(
            f"Carregando {len(fontes)} tabela(s) do {rotulo} (full refresh)..."
        )

        resultados, falhas = {}, {}

        for fonte in fontes:
            # Falha de uma fonte não aborta as demais — mesma semântica do
            # rodar_pipeline. O resumo no final diz o que entrou e o que não.
            try:
                resultados[fonte] = self.loaders[fonte]()
                self.apos_carga(fonte, resultados[fonte])
            except FileNotFoundError as exc:
                # Erro esperado: o Silver dessa fonte ainda não foi gerado.
                logger.warning("%s: %r sem Silver: %s", rotulo.lower(), fonte, exc)
                falhas[fonte] = str(exc)
            except Exception as exc:
                # Erro inesperado: traceback completo no log.
                logger.exception(
                    "%s: falha inesperada ao carregar %r", rotulo.lower(), fonte
                )
                falhas[fonte] = str(exc)

        self._imprimir_resumo(resultados, falhas)

        if resultados:
            # Pelo menos uma tabela mudou: o painel não pode seguir servindo
            # indicadores calculados antes da carga.
            invalidar_cache_indicadores()

        if falhas:
            # CommandError faz o comando sair com código != 0 (agendador/deploy).
            raise CommandError(
                f"{len(falhas)} de {len(fontes)} fonte(s) do {rotulo} falharam: "
                f"{', '.join(falhas)}"
            )

    # -- auxiliares ---------------------------------------------------------

    def _resolver_fontes(self, pedidas):
        canonicas = self.fontes_disponiveis
        if not pedidas:
            return list(canonicas)

        desconhecidas = [f for f in pedidas if f not in self.loaders]
        if desconhecidas:
            raise CommandError(
                f"Fonte(s) não registrada(s) no {self.rotulo}: "
                f"{', '.join(desconhecidas)}\n"
                f"Disponíveis: {', '.join(canonicas)}"
            )

        # Respeita a ordem canônica e remove repetições.
        return [f for f in canonicas if f in set(pedidas)]

    def _imprimir_resumo(self, resultados, falhas):
        for fonte, resultado in resultados.items():
            self.stdout.write(
                f"  {fonte}: Apagados: {resultado['apagados']} | "
                f"Inseridos: {resultado['inseridos']}"
            )
        for fonte, erro in falhas.items():
            primeira_linha = erro.splitlines()[0] if erro else erro
            self.stdout.write(self.style.ERROR(f"  {fonte}: FALHOU — {primeira_linha}"))

        total_inserido = sum(r["inseridos"] for r in resultados.values())
        resumo = (
            f"Concluído! {len(resultados)} tabela(s) carregada(s), "
            f"{total_inserido} linha(s) inseridas."
        )
        estilo = self.style.WARNING if falhas else self.style.SUCCESS
        self.stdout.write(estilo(resumo))
