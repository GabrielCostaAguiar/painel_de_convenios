"""
Management command: carregar_sigcon

Full refresh das tabelas do SIGCON a partir dos Parquets Silver.

Carga avulsa: não é chamado pelo `rodar_pipeline` (cujo CARGAS_ORM ainda aponta
para os comandos de carga antigos, removidos).
Cada carga bem-sucedida grava a contagem de linhas em SigconHistoricoCarga, que
o teste de volumetria histórica de `validar_sigcon` compara com a carga anterior.

Pré-requisito por fonte:
    python manage.py rodar_ingestao <fonte>
    python manage.py rodar_silver <fonte>

Uso:
    python manage.py carregar_sigcon
    python manage.py carregar_sigcon --fonte sigcon_convenio
    python manage.py carregar_sigcon --fonte sigcon_convenio --fonte sigcon_concedente
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.sigcon import loader as loaders
from apps.sigcon.models import SigconHistoricoCarga
from core.cache import invalidar_cache_indicadores

logger = logging.getLogger(__name__)

# Nome da fonte (chave de core.ingestion.sources.FONTES, sempre com underscore)
# → função de carga. A ordem do dict é a ordem de carga.
#
# Sobre a ordem: os models do SIGCON não têm nenhuma ForeignKey entre si ainda — 
# tabelas serão ligadas por siafi_uo na view gold, não por integridade
# referencial. Então a ordem não afeta a consistência do banco. Mantemos
# sigcon_convenio primeiro por ser a tabela "mãe" do conjunto (é dela que as
# telas tiram a lista de instrumentos), de modo que uma carga interrompida
# deixe o painel num estado mais útil.
_LOADERS_SIGCON = {
    "sigcon_convenio": loaders.carregar_sigcon_convenio,
    "sigcon_convenio_geral": loaders.carregar_sigcon_convenio_geral,
    "sigcon_plano_trabalho": loaders.carregar_sigcon_plano_trabalho,
    "sigcon_termo_aditivo": loaders.carregar_sigcon_termo_aditivo,
    "sigcon_prorrogacao_oficio": loaders.carregar_sigcon_prorrogacao_oficio,
    "sigcon_declaracao_contrapartida": loaders.carregar_sigcon_declaracao_contrapartida,
    "sigcon_cronograma_desembolso": loaders.carregar_sigcon_cronograma_desembolso,
    "sigcon_plano_aplicacao": loaders.carregar_sigcon_plano_aplicacao,
    "sigcon_unidade_executora": loaders.carregar_sigcon_unidade_executora,
    "sigcon_nt_emenda": loaders.carregar_sigcon_nt_emenda,
    "sigcon_chave_convenio": loaders.carregar_sigcon_chave_convenio,
    "sigcon_chave_termo_aditivo": loaders.carregar_sigcon_chave_termo_aditivo,
    "sigcon_chave_plano_trabalho": loaders.carregar_sigcon_chave_plano_trabalho,
    "sigcon_chave_declaracao": loaders.carregar_sigcon_chave_declaracao,
    "sigcon_concedente": loaders.carregar_sigcon_concedente,
    "sigcon_tabela_uo": loaders.carregar_sigcon_tabela_uo,
}

FONTES_SIGCON = tuple(_LOADERS_SIGCON)


class Command(BaseCommand):
    help = (
        "Full refresh das tabelas do SIGCON a partir dos Parquets Silver. "
        "Sem argumentos, carrega todas; use --fonte para escolher."
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
                f"Disponíveis: {', '.join(FONTES_SIGCON)}. "
                "Omitir = carrega todas."
            ),
        )

    def handle(self, *args, **options):
        fontes = self._resolver_fontes(options["fontes"])

        self.stdout.write(
            f"Carregando {len(fontes)} tabela(s) do SIGCON (full refresh)..."
        )

        resultados, falhas = {}, {}

        for fonte in fontes:
            # Falha de uma fonte não aborta as demais — mesma semântica do
            # rodar_pipeline. O resumo no final diz o que entrou e o que não.
            try:
                resultados[fonte] = _LOADERS_SIGCON[fonte]()
                SigconHistoricoCarga.objects.create(
                    tabela=fonte, qt_linhas=resultados[fonte]["inseridos"]
                )
            except FileNotFoundError as exc:
                # Erro esperado: o Silver dessa fonte ainda não foi gerado.
                logger.warning("sigcon: %r sem Silver: %s", fonte, exc)
                falhas[fonte] = str(exc)
            except Exception as exc:
                # Erro inesperado: traceback completo no log, para o
                # diagnóstico não se perder no resumo.
                logger.exception("sigcon: falha inesperada ao carregar %r", fonte)
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
                f"{len(falhas)} de {len(fontes)} fonte(s) do SIGCON falharam: "
                f"{', '.join(falhas)}"
            )

    # -- auxiliares ---------------------------------------------------------

    def _resolver_fontes(self, pedidas):
        if not pedidas:
            return list(FONTES_SIGCON)  # cópia, não referência direta

        desconhecidas = [f for f in pedidas if f not in _LOADERS_SIGCON]
        if desconhecidas:
            raise CommandError(
                f"Fonte(s) não registrada(s) no SIGCON: {', '.join(desconhecidas)}\n"
                f"Disponíveis: {', '.join(FONTES_SIGCON)}"
            )

        # Respeita a ordem canônica de _LOADERS_SIGCON e remove repetições.
        return [f for f in FONTES_SIGCON if f in set(pedidas)]

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
