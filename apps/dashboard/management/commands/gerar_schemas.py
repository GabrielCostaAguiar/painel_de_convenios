"""
Management command: gerar_schemas

Amostra cada fonte registrada (Bronze ou raw), classifica as colunas
automaticamente e salva um schema YAML editável em core/transform/schemas/.

Uso:
    python manage.py gerar_schemas                    # todas as fontes
    python manage.py gerar_schemas dcgce_convenios    # uma fonte específica
    python manage.py gerar_schemas --sobrescrever     # força regeneração de YAMLs existentes
"""

from django.core.management.base import BaseCommand, CommandError

from core.transform.gerar_schemas import gerar_todos, gerar_um


class Command(BaseCommand):
    help = "Gera schemas YAML de classificação de colunas para as fontes registradas."

    def add_arguments(self, parser):
        parser.add_argument(
            "fonte",
            nargs="?",
            default=None,
            help="Nome da fonte (omita para processar todas as fontes registradas)",
        )
        parser.add_argument(
            "--sobrescrever",
            action="store_true",
            default=False,
            help="Regenera o YAML mesmo que já exista (padrão: pula existentes)",
        )

    def handle(self, *args, **options):
        nome = options.get("fonte")
        sobrescrever = options["sobrescrever"]

        if nome:
            resultados = [gerar_um(nome, sobrescrever=sobrescrever)]
            if resultados[0].get("status") == "erro":
                raise CommandError(resultados[0].get("msg", "Erro desconhecido"))
        else:
            self.stdout.write("Gerando schemas para todas as fontes registradas...")
            resultados = gerar_todos(sobrescrever=sobrescrever)

        self._imprimir_relatorio(resultados)

    # -----------------------------------------------------------------------
    # Relatório tabular
    # -----------------------------------------------------------------------

    def _imprimir_relatorio(self, resultados: list[dict]) -> None:
        cabecalho = "{:<38} {:>6} {:>5} {:>6} {:>4} {:>6} {:>9}".format(
            "Fonte", "Total", "Data", "Valor", "ID", "Texto", "Duvidosas"
        )
        self.stdout.write("")
        self.stdout.write(cabecalho)
        self.stdout.write("-" * 80)

        for r in resultados:
            status = r.get("status", "?")

            if status == "sem_dados":
                linha = "{:<38} {}".format(r["fonte"], "(sem dados — arquivo não encontrado)")
                self.stdout.write(self.style.WARNING("  " + linha))
                continue

            if status == "erro":
                linha = "{:<38} {}".format(r["fonte"], "(ERRO: " + r.get("msg", "") + ")")
                self.stdout.write(self.style.ERROR("  " + linha))
                continue

            pt = r.get("por_tipo", {})
            n_duv = len(r.get("duvidosas", []))

            linha = "{:<38} {:>6} {:>5} {:>6} {:>4} {:>6} {:>9}".format(
                r["fonte"],
                r.get("total", 0),
                pt.get("data", 0),
                pt.get("valor", 0),
                pt.get("identificador", 0),
                pt.get("texto", 0),
                n_duv,
            )
            if n_duv > 0:
                self.stdout.write(self.style.WARNING("  " + linha))
            else:
                self.stdout.write("  " + linha)

        self.stdout.write("")

        # Detalha colunas duvidosas para facilitar a revisão dos YAMLs
        tem_duvidosas = any(r.get("duvidosas") for r in resultados)
        if tem_duvidosas:
            self.stdout.write(
                self.style.WARNING("Colunas classificadas como 'texto' por segurança (revisar YAML):")
            )
            for r in resultados:
                duv = r.get("duvidosas", [])
                if duv:
                    self.stdout.write(f"  {r['fonte']}:")
                    for col in duv:
                        self.stdout.write(f"    - {col}")
            self.stdout.write("")

        ok = sum(1 for r in resultados if r.get("status") == "ok")
        skip = sum(1 for r in resultados if r.get("status") == "sem_dados")
        self.stdout.write(
            self.style.SUCCESS(f"Concluído: {ok} schema(s) gerado(s), {skip} fonte(s) ignorada(s) por falta de dados.")
        )
