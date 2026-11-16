"""
Base dos comandos `validar_<app>`: roda o catálogo de testes do app e grava cada
resultado no `ResultadoValidacao` do app, todos com o mesmo UUID de execução.

Falha de teste ERRO faz o comando sair com código != 0 (o agendador percebe);
falha de ALERTA só é registrada. Testes com `limite` gravam ALERTA até o limite
e ERRO acima dele (core.validacao.limites).

A subclasse implementa `obter_testes()` e `modelo_resultado()` (métodos, não
atributos: o catálogo e o model são resolvidos a cada execução).
"""

import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from core.validacao.limites import severidade_efetiva

TAMANHO_AMOSTRA = 5


class ComandoValidacao(BaseCommand):
    def obter_testes(self):
        raise NotImplementedError

    def modelo_resultado(self):
        raise NotImplementedError

    def handle(self, *args, **options):
        execucao = uuid.uuid4()
        resultado_model = self.modelo_resultado()
        falhas_bloqueantes = []

        for teste in self.obter_testes():
            if "funcao" in teste:
                qt, amostra = teste["funcao"]()
            else:
                qt, amostra = self._rodar(teste["sql"])
            status = "PASSOU" if qt == 0 else "FALHOU"
            # Teste com `limite` (exceção conhecida): ALERTA até o limite, ERRO acima.
            severidade = severidade_efetiva(teste, qt)

            resultado_model.objects.create(
                execucao=execucao,
                id_teste=teste["id"],
                severidade=severidade,
                tabela=teste["tabela"],
                descricao=teste["descricao"],
                status=status,
                amostra=amostra,
                qt_falhas=qt,
            )

            mensagem = (
                f"{teste['id']} {severidade} {status} "
                f"[{teste['tabela']}]: ({qt} linhas), {teste['descricao']}"
            )
            if status == "FALHOU":
                self.stdout.write(self.style.ERROR(mensagem))
            else:
                self.stdout.write(self.style.SUCCESS(mensagem))

            if status == "FALHOU" and severidade == "ERRO":
                falhas_bloqueantes.append(teste["id"])

        if falhas_bloqueantes:
            raise CommandError(f"Falhas bloqueantes: {', '.join(falhas_bloqueantes)}")

    def _rodar(self, sql):
        """Devolve (quantidade de linhas que violam a regra, até 5 linhas de amostra)."""
        with connection.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM ({sql}) AS t")
            qt = cur.fetchone()[0]

            cur.execute(f"SELECT * FROM ({sql}) AS t LIMIT {TAMANHO_AMOSTRA}")
            linhas = cur.fetchall()
            cabecalho = [coluna[0] for coluna in cur.description]

        return qt, [dict(zip(cabecalho, linha)) for linha in linhas]
