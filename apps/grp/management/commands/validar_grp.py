# apps/grp/management/commands/validar_grp.py
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.grp.models import ResultadoValidacao
from apps.grp.validacao.catalogo import TESTES


class Command(BaseCommand):
    help = "Roda o catálogo de testes de qualidade do GRP e registra o resultado."

    def handle(self, *args, **options):
        execucao = uuid.uuid4()
        falhas_bloqueantes = []

        for teste in TESTES:
            if "funcao" in teste:
                qt, amostra = teste["funcao"]()

            else:
                qt, amostra = self._rodar(teste["sql"])
            status = "PASSOU" if qt == 0 else "FALHOU"
            # 1. grave um ResultadoValidacao com os dados do teste
            ResultadoValidacao.objects.create(
                execucao=execucao,
                id_teste=teste["id"],
                severidade=teste["severidade"],
                tabela=teste["tabela"],
                descricao=teste["descricao"],
                status=status,
                amostra=amostra,
                qt_falhas=qt,
            )
            mensagem = (
                f"{teste['id']} {teste['severidade']} {status} "
                f"[{teste['tabela']}]: ({qt} linhas), {teste['descricao']}"
)
            if status == "FALHOU":
                self.stdout.write(self.style.ERROR(mensagem))
            else:
                self.stdout.write(self.style.SUCCESS(mensagem))

            # 2. se falhou e a severidade é ERRO, guarde o id em falhas_bloqueantes
            if status == "FALHOU" and teste["severidade"] == "ERRO":
                falhas_bloqueantes.append(teste["id"])

        if falhas_bloqueantes:
            raise CommandError(f"Falhas bloqueantes: {', '.join(falhas_bloqueantes)}")

    def _rodar(self, sql):
        """Devolve (quantidade de linhas que violam a regra, até 5 linhas de amostra)."""
        with connection.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM ({sql}) AS t")
            qt = cur.fetchone()[0]

            cur.execute(f"SELECT * FROM ({sql}) AS t LIMIT 5")
            linhas = cur.fetchall()

            colunas = cur.description

            cabecalho = [coluna[0] for coluna in colunas] 

            amostra = [dict(zip(cabecalho, linha)) for linha in linhas]

        return qt, amostra
