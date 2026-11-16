"""
Auxiliares de escrita no banco compartilhados pelos loaders.

Mora em core/ porque mais de um app carrega dados do mesmo jeito (sigcon e
grp), e a regra do projeto e que os apps de aba nao importem uns dos outros.
"""

import logging

from django.db import transaction

logger = logging.getLogger(__name__)

# Evita estourar o limite de parametros por query do SQLite.
BATCH_SIZE_PADRAO = 500


def bulk_refresh(model, objetos: list, batch_size: int = BATCH_SIZE_PADRAO) -> dict:
    """
    Substitui todo o conteudo da tabela de forma atomica.

    O delete e o bulk_create formam uma unica transacao: se qualquer passo
    falhar (valor invalido, erro de encoding, queda de conexao), o banco faz
    rollback e a tabela mantem os dados anteriores — em vez de ficar vazia,
    que era o resultado possivel quando os dois passos rodavam soltos.

    Efeito colateral desejado no PostgreSQL: pelo MVCC, quem estiver lendo o
    painel durante a carga continua enxergando os dados antigos ate o commit,
    em vez de pegar a tabela no intervalo entre o delete e o insert.

    Retorna {'apagados': int, 'inseridos': int}.
    """
    with transaction.atomic():
        apagados, _ = model.objects.all().delete()
        model.objects.bulk_create(objetos, batch_size=batch_size)
    logger.info("%s: %d apagados, %d inseridos", model.__name__, apagados, len(objetos))
    return {"apagados": apagados, "inseridos": len(objetos)}
