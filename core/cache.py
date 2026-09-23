"""
Chaves e invalidação do cache de indicadores Gold.

Por que este módulo fica em core/ e não em apps/dashboard/:
  quem invalida o cache são os loaders e o orquestrador do pipeline — código de
  núcleo. Se a função de invalidação morasse em apps/dashboard/services.py,
  core/ passaria a importar da camada de apresentação, invertendo a direção das
  dependências. Aqui, core/ define o contrato e apps/dashboard/ o consome.

Estratégia de invalidação: número de versão
-------------------------------------------
Os indicadores são cacheados em várias chaves — uma para o agregado geral e uma
por ano consultado (`...:ano:2024`, `...:ano:2023`, ...). Apagar só a chave base
deixa todas as variantes por ano servindo dado velho por até um TTL inteiro.

Apagar "todas as variantes" exigiria varrer o cache por padrão de chave, e o
LocMemCache (usado em dev e nos testes) não oferece isso — só o Redis, via
`delete_pattern`, que é extensão de biblioteca e não da API do Django.

Por isso as chaves carregam um número de versão que fica guardado no próprio
cache: `gold:indicadores:convenios:v3:ano:2024`. Invalidar é incrementar a
versão — uma única operação, que funciona igual nos dois backends. As entradas
da versão anterior deixam de ser consultadas e expiram sozinhas pelo TTL.

Alternativa descartada: apagar explicitamente as chaves dos anos retornados por
`get_anos_disponiveis()`. Ela falha justamente quando mais importa — se uma
carga remove um ano do conjunto de dados, a chave daquele ano não aparece mais
na lista e nunca seria apagada — e forçaria core/ a consultar o ORM do painel.
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Prefixo das chaves de indicadores. Mantido igual ao histórico do projeto.
CHAVE_INDICADORES = "gold:indicadores:convenios"

# Sufixo por ano, aplicado sobre a chave já versionada.
FORMATO_SUFIXO_ANO = ":ano:{ano}"

# Onde o número de versão corrente é guardado.
CHAVE_VERSAO = "gold:indicadores:versao"

# Versão assumida quando o cache está vazio (primeiro acesso, cache recém-criado
# ou Redis reiniciado). Nesse caso não há entrada antiga para servir dado velho.
VERSAO_INICIAL = 1


def versao_indicadores() -> int:
    """Número de versão corrente das chaves de indicadores."""
    return cache.get(CHAVE_VERSAO, VERSAO_INICIAL)


def chave_indicadores(ano: int | None = None) -> str:
    """
    Chave de cache dos indicadores, já versionada.

    ano=None  → agregado de todos os anos
    ano=<N>   → recorte daquele ano
    """
    chave = f"{CHAVE_INDICADORES}:v{versao_indicadores()}"
    if ano is None:
        return chave
    return chave + FORMATO_SUFIXO_ANO.format(ano=ano)


def invalidar_cache_indicadores() -> int:
    """
    Invalida a chave base e todas as variantes por ano de uma só vez,
    incrementando o número de versão embutido nas chaves.

    Retorna a nova versão. Idempotente no sentido que importa: chamar duas vezes
    seguidas não deixa nenhuma entrada antiga acessível.
    """
    try:
        nova_versao = cache.incr(CHAVE_VERSAO)
    except ValueError:
        # cache.incr levanta ValueError quando a chave ainda não existe
        # (LocMemCache e RedisCache se comportam igual aqui).
        nova_versao = VERSAO_INICIAL + 1
        # timeout=None = nunca expira: se a versão sumisse antes das entradas
        # que ela invalida, o contador voltaria a apontar para dado velho.
        cache.set(CHAVE_VERSAO, nova_versao, None)

    logger.info(
        "Cache de indicadores invalidado: %s agora na versão %d",
        CHAVE_INDICADORES, nova_versao,
    )
    return nova_versao
