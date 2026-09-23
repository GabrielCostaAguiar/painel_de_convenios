"""
Management command: carregar_grp

Full refresh das 7 tabelas do GRP a partir dos Parquets Silver.

Os models, migrações, schemas, services e telas do GRP já existiam, mas os
loaders `carregar_*_grp()` não eram chamados por nenhum comando — só dava para
popular as telas abrindo um shell Python. Este comando fecha essa lacuna.

O GRP ainda está **em teste**: por isso ele entra na CLI mas fica FORA do
`rodar_pipeline` por padrão. Uma falha ou ausência de arquivo GRP não pode
afetar a atualização diária do painel SIGCON. Para incluí-lo no pipeline,
defina PIPELINE_INCLUIR_GRP=True (ver config/settings/base.py).

Pré-requisito por fonte:
    python manage.py rodar_ingestao <fonte>
    python manage.py rodar_silver <fonte>

Uso:
    python manage.py carregar_grp
    python manage.py carregar_grp --fonte dcgce_esfera_grp
    python manage.py carregar_grp --fonte dcgce_dados_grp --fonte dcgce_esfera_grp
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.convenios import loader as loaders
from core.cache import invalidar_cache_indicadores

logger = logging.getLogger(__name__)

# Nome da fonte (chave de core.ingestion.sources.FONTES, sempre com underscore)
# → função de carga. A ordem do dict é a ordem de carga.
#
# Sobre a ordem: os models do GRP não têm nenhuma ForeignKey entre si — são
# tabelas planas ligadas por nr_grp na consulta, não por integridade
# referencial. Então a ordem não afeta a consistência do banco. Mantemos
# dcgce_dados_grp primeiro por ser a tabela "mãe" do conjunto (é dela que as
# telas tiram a lista de instrumentos), de modo que uma carga interrompida
# deixe o painel num estado mais útil.
_LOADERS_GRP = {
    "dcgce_dados_grp": loaders.carregar_dados_grp,
    "dcgce_cronograma_desembolso_grp": loaders.carregar_cronograma_desembolso_grp,
    "dcgce_recursos_contrapartida_grp": loaders.carregar_recurso_contrapartida_grp,
    "dcgce_recursos_concedente_grp": loaders.carregar_recurso_concedente_grp,
    "dcgce_plano_aplicacao_grp": loaders.carregar_plano_aplicacao_grp,
    "dcgce_plano_aplicacao_grp_detalhes": loaders.carregar_plano_aplicacao_grp_detalhes,
    "dcgce_esfera_grp": loaders.carregar_esfera_grp,
}

FONTES_GRP = tuple(_LOADERS_GRP)


class Command(BaseCommand):
    help = (
        "Full refresh das tabelas do GRP a partir dos Parquets Silver. "
        "Sem argumentos, carrega as 7; use --fonte para escolher."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fonte",
            action="append",
            dest="fontes",
            default=None,
            metavar="NOME",
            help=(
                "Fonte a carregar; pode repetir. "
                f"Disponíveis: {', '.join(FONTES_GRP)}. "
                "Omitir = carrega todas."
            ),
        )

    def handle(self, *args, **options):
        fontes = self._resolver_fontes(options["fontes"])

        self.stdout.write(
            f"Carregando {len(fontes)} tabela(s) do GRP (full refresh)..."
        )

        resultados, falhas = {}, {}

        for fonte in fontes:
            # Falha de uma fonte não aborta as demais — mesma semântica do
            # rodar_pipeline. O resumo no final diz o que entrou e o que não.
            try:
                resultados[fonte] = _LOADERS_GRP[fonte]()
            except FileNotFoundError as exc:
                # Erro esperado: o Silver dessa fonte ainda não foi gerado.
                logger.warning("grp: %r sem Silver: %s", fonte, exc)
                falhas[fonte] = str(exc)
            except Exception as exc:
                # Erro inesperado: traceback completo no log, para o
                # diagnóstico não se perder no resumo.
                logger.exception("grp: falha inesperada ao carregar %r", fonte)
                falhas[fonte] = str(exc)

        self._imprimir_resumo(resultados, falhas)

        if resultados:
            # Pelo menos uma tabela mudou: o painel não pode seguir servindo
            # indicadores calculados antes da carga.
            invalidar_cache_indicadores()

        if falhas:
            # CommandError faz o comando sair com código != 0, que é o que
            # agendador e script de deploy usam para detectar problema.
            raise CommandError(
                f"{len(falhas)} de {len(fontes)} fonte(s) do GRP falharam: "
                f"{', '.join(falhas)}"
            )

    # -- auxiliares ---------------------------------------------------------

    def _resolver_fontes(self, pedidas):
        if not pedidas:
            return list(FONTES_GRP)

        desconhecidas = [f for f in pedidas if f not in _LOADERS_GRP]
        if desconhecidas:
            raise CommandError(
                f"Fonte(s) não registrada(s) no GRP: {', '.join(desconhecidas)}\n"
                f"Disponíveis: {', '.join(FONTES_GRP)}"
            )

        # Respeita a ordem canônica de _LOADERS_GRP e remove repetições.
        return [f for f in FONTES_GRP if f in set(pedidas)]

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
