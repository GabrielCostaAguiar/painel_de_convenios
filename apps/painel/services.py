"""
Camada de serviços do painel.

Indicadores, gráficos e filtros globais. As consultas das telas SIGCON
moram em apps/sigcon/services.py; as do GRP, em apps/grp/services.py.

Responsabilidade: fazer a ponte entre o banco (ORM / Gold) e as views.
As views NÃO acessam o banco diretamente — elas chamam funções deste módulo.

Por que a lógica de query fica aqui e não na view?
  - Testabilidade: tests importam a função de serviço e criam dados de amostra sem passar
    pelo ciclo request/response do Django. A view vira apenas um roteador thin.
  - Reaproveitamento: outra view, um comando de gestão ou uma exportação CSV pode chamar
    get_plano_aplicacao_qs() sem duplicar a lógica de join.
  - Separação de conceitos: a view decide o que renderizar; o serviço decide como buscar.

Sobre o cache:
  Os dados mudam apenas quando um comando de carga é executado. Todos eles
  invalidam o cache ao terminar, chamando core.cache.invalidar_cache_indicadores()
  — não é preciso lembrar de invalidar à mão. As chaves e a estratégia de
  invalidação (número de versão) estão documentadas em core/cache.py.
  O backend é escolhido por ambiente: LocMemCache em dev.py; em prod.py,
  Redis quando REDIS_URL está definida, senão DatabaseCache. Produção precisa
  de um backend compartilhado — com LocMemCache cada worker teria a sua cópia
  e a invalidação feita pelo comando de carga não chegaria a nenhum deles.
  O TTL vem de settings.GOLD_CACHE_SECONDS (base.py, default 3600 s).
"""

import logging

from django.conf import settings
from django.core.cache import cache

from core.cache import (
    CHAVE_INDICADORES,
    chave_indicadores,
    invalidar_cache_indicadores,
)
from core.gold import convenios as gold

logger = logging.getLogger(__name__)

_CACHE_TTL = settings.GOLD_CACHE_SECONDS
_CACHE_KEY = CHAVE_INDICADORES


logger = logging.getLogger(__name__)

_CACHE_TTL = settings.GOLD_CACHE_SECONDS

_CACHE_KEY = CHAVE_INDICADORES

logger = logging.getLogger(__name__)

_CACHE_TTL = settings.GOLD_CACHE_SECONDS

_CACHE_KEY = CHAVE_INDICADORES

logger = logging.getLogger(__name__)

_CACHE_TTL = settings.GOLD_CACHE_SECONDS

_CACHE_KEY = CHAVE_INDICADORES

def get_indicadores(ano: int | None = None, usar_cache: bool = True) -> dict:
    """
    Retorna indicadores Gold prontos para as views.

    Parâmetros
    ----------
    ano         : filtra pelo ano de início de vigência; None = todos os anos
    usar_cache  : False força recálculo (útil após carga ou para debug)
    """
    cache_key = chave_indicadores(ano)

    if usar_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    resumo = gold.kpis(ano)

    if resumo["total_convenios"] == 0:
        return {"vazio": True}

    resultado = {
        "vazio": False,
        "resumo": resumo,
        "por_situacao": gold.por_situacao(ano),
        "por_ano": gold.por_ano(),          # série histórica completa (ignora filtro de ano)
        "recentes": gold.recentes(ano=ano),
    }

    if usar_cache:
        cache.set(cache_key, resultado, _CACHE_TTL)

    return resultado

# get_anos_disponiveis consulta Convenio, um model do SIGCON, e e usado tanto
# pelos graficos quanto pela tela de convenios. Mora em apps.sigcon.services e
# e reexportado aqui para quem ja o importava do painel. A direcao
# painel -> sigcon e permitida; a inversa nao.
from apps.sigcon.services import get_anos_disponiveis  # noqa: E402,F401

def invalidar_cache() -> None:
    """
    Limpa o cache de indicadores — a chave base e todas as variantes por ano.

    Mantido como fachada do módulo de serviços (outros pontos do projeto podem
    chamá-lo); a implementação vive em core/cache.py, que é de onde os loaders
    e o pipeline invalidam sem precisar importar a camada de apresentação.
    """
    invalidar_cache_indicadores()
