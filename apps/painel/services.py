"""
Camada de serviços do painel.

Indicadores, gráficos e filtros globais. As consultas das telas SIGCON
moram em apps/sigcon/services.py; as do GRP, em apps.painel por ora.

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

from apps.sigcon.models import DadosGrp
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

def get_grp_dados_qs(filtros: dict):
    """
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    `filtros` é um dict com as chaves: nr_grp
    (string; "" significa "sem filtro").
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    """
    from apps.sigcon.models import DadosGrp, TermoAditivo, CodigoTermoAditivo, ConvenioIntegrado
    from core.gold.contrapartida import tipo_por_siafi_uo

    qs = DadosGrp.objects.all()

    if filtros.get("nr_grp"):
        qs = qs.filter(nr_grp__icontains=filtros["nr_grp"])
    if filtros.get("nr_instrumento"):
        qs = qs.filter(nr_instrumento__icontains=filtros["nr_instrumento"])
    if filtros.get("uo_cod"):
        qs = qs.filter(uo_cod=filtros["uo_cod"])

    return qs.order_by("nr_grp")


# ---------------------------------------------------------------------------
# GRP — sub-abas ligadas por nr_grp
#
# As 6 sub-abas abaixo reaproveitam os mesmos 3 filtros da aba Dados
# (nr_grp, nr_instrumento, uo_cod), com as MESMAS chaves de querystring.
# Só `nr_grp` existe em todas as tabelas; `nr_instrumento` e `uo_cod` são
# resolvidos em DadosGrp e aplicados como conjunto de nr_grp, para que o
# recorte visto em cada sub-aba seja exatamente o da aba Dados.
# ---------------------------------------------------------------------------

def _grp_filtrar_por_nr_grp(qs, filtros: dict):
    """Aplica os filtros do GRP a qualquer QuerySet que tenha o campo nr_grp."""
    from apps.sigcon.models import DadosGrp

    if filtros.get("nr_grp"):
        qs = qs.filter(nr_grp__icontains=filtros["nr_grp"])

    # Filtros que só existem em DadosGrp: vira um "nr_grp IN (subquery)".
    dados = None
    if filtros.get("nr_instrumento"):
        dados = DadosGrp.objects.filter(
            nr_instrumento__icontains=filtros["nr_instrumento"]
        )
    if filtros.get("uo_cod"):
        dados = (dados if dados is not None else DadosGrp.objects.all()).filter(
            uo_cod=filtros["uo_cod"]
        )
    if dados is not None:
        qs = qs.filter(nr_grp__in=dados.values("nr_grp"))

    return qs

def get_grp_cronograma_qs(filtros: dict):
    """QuerySet[CronogramaDesembolsoGrp] filtrado pelos filtros do GRP."""
    from apps.sigcon.models import CronogramaDesembolsoGrp

    qs = _grp_filtrar_por_nr_grp(CronogramaDesembolsoGrp.objects.all(), filtros)
    return qs.order_by("nr_grp", "ano_desembolso", "mes_desembolso", "parcela_desembolso")

def get_grp_recursos_contrapartida_qs(filtros: dict):
    """QuerySet[RecursosContrapartidaGrp] filtrado pelos filtros do GRP."""
    from apps.sigcon.models import RecursosContrapartidaGrp

    qs = _grp_filtrar_por_nr_grp(RecursosContrapartidaGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")

def get_grp_recursos_concedente_qs(filtros: dict):
    """QuerySet[RecursosConcedenteGrp] filtrado pelos filtros do GRP."""
    from apps.sigcon.models import RecursosConcedenteGrp

    qs = _grp_filtrar_por_nr_grp(RecursosConcedenteGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")

def get_grp_plano_aplicacao_qs(filtros: dict):
    """QuerySet[PlanoAplicacaoGrp] filtrado pelos filtros do GRP."""
    from apps.sigcon.models import PlanoAplicacaoGrp

    qs = _grp_filtrar_por_nr_grp(PlanoAplicacaoGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")

def get_grp_plano_aplicacao_detalhes_qs(filtros: dict):
    """QuerySet[PlanoAplicacaoGrpDetalhes] filtrado pelos filtros do GRP."""
    from apps.sigcon.models import PlanoAplicacaoGrpDetalhes

    qs = _grp_filtrar_por_nr_grp(PlanoAplicacaoGrpDetalhes.objects.all(), filtros)
    return qs.order_by("nr_grp", "nr_catmas")

def get_grp_esfera_qs(filtros: dict):
    """
    QuerySet[EsferaGrp] — sem filtro.

    EsferaGrp não tem nr_grp: ela é uma tabela de domínio ligada por
    concedente_cnpj (→ Convenio.concedente_cnpj) e não há caminho para
    nr_grp dentro das tabelas do GRP. A sub-aba sempre mostra tudo; a view
    sinaliza no template que o filtro não se aplica aqui.
    """
    from apps.sigcon.models import EsferaGrp

    return EsferaGrp.objects.all().order_by("concedente_cnpj")
