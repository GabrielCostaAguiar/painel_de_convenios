"""
Camada de serviços do dashboard.

Responsabilidade: fazer a ponte entre o banco (ORM / Gold) e as views.
As views NÃO acessam o banco diretamente — elas chamam funções deste módulo.

Por que a lógica de query fica aqui e não na view?
  - Testabilidade: tests importam a função de serviço e criam dados de amostra sem passar
    pelo ciclo request/response do Django. A view vira apenas um roteador thin.
  - Reaproveitamento: outra view, um comando de gestão ou uma exportação CSV pode chamar
    get_plano_aplicacao_qs() sem duplicar a lógica de join.
  - Separação de conceitos: a view decide o que renderizar; o serviço decide como buscar.

Sobre o cache:
  Os dados mudam apenas quando `carregar_convenios` é executado.
  Ao concluir, ele pode chamar invalidar_cache() para forçar recálculo.
  Em produção, configure Redis em settings.py:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                          "LOCATION": "redis://127.0.0.1:6379/1"}}
"""

import logging

from django.conf import settings
from django.core.cache import cache

from core.gold import convenios as gold

logger = logging.getLogger(__name__)

_CACHE_TTL = getattr(settings, "GOLD_CACHE_SECONDS", 3600)
_CACHE_KEY = "gold:indicadores:convenios"


def get_indicadores(ano: int | None = None, usar_cache: bool = True) -> dict:
    """
    Retorna indicadores Gold prontos para as views.

    Parâmetros
    ----------
    ano         : filtra pelo ano de início de vigência; None = todos os anos
    usar_cache  : False força recálculo (útil após carga ou para debug)
    """
    cache_key = _CACHE_KEY if ano is None else f"{_CACHE_KEY}:ano:{ano}"

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


def get_anos_disponiveis() -> list[int]:
    """Lista de anos com convênios registrados, em ordem decrescente."""
    from apps.convenios.models import Convenio
    from django.db.models.functions import ExtractYear

    return list(
        Convenio.objects
        .exclude(data_inicio_vigencia=None)
        .annotate(ano=ExtractYear("data_inicio_vigencia"))
        .values_list("ano", flat=True)
        .distinct()
        .order_by("-ano")
    )


def invalidar_cache() -> None:
    """Limpa o cache principal. Chamar após cada carga de dados."""
    cache.delete(_CACHE_KEY)
    logger.info("Cache invalidado: %s", _CACHE_KEY)


# ---------------------------------------------------------------------------
# Consultas SIGCON — serviços das 6 abas
# ---------------------------------------------------------------------------

def enrich_convenios_page(page_items: list) -> dict:
    """
    Enriquece uma página de objetos Convenio com campos de ConvenioIntegrado.

    Retorna dict[pk_convenio → {'codigo_siconv', 'proponente', 'fim_vigencia_inicial'}].
    A join key é (convenio_numero_sequencial_siafi, unidade_orcamentaria_codigo).
    """
    from apps.convenios.models import ConvenioIntegrado

    if not page_items:
        return {}

    siafis = [c.convenio_numero_sequencial_siafi for c in page_items if c.convenio_numero_sequencial_siafi]
    if not siafis:
        return {}

    rows = ConvenioIntegrado.objects.filter(
        convenio_numero_sequencial_siafi__in=siafis,
    ).values(
        "convenio_numero_sequencial_siafi",
        "unidade_orcamentaria_codigo",
        "codigo_siconv",
        "g_proponente_pad",
        "g_fim_vigencia_inicial",
    )

    integ_map = {
        (r["convenio_numero_sequencial_siafi"], r["unidade_orcamentaria_codigo"]): r
        for r in rows
    }

    result = {}
    for conv in page_items:
        key = (conv.convenio_numero_sequencial_siafi, conv.unidade_orcamentaria_codigo)
        extra = integ_map.get(key, {})
        result[conv.pk] = {
            "codigo_siconv": extra.get("codigo_siconv") or "—",
            "proponente": extra.get("g_proponente_pad") or "—",
            "fim_vigencia_inicial": extra.get("g_fim_vigencia_inicial"),
        }
    return result


def get_plano_aplicacao_qs(cod_sigcon: str | None = None):
    """
    Retorna (QuerySet[PlanoAplicacao], context_dict) para a aba Plano de Aplicação.

    Chave de ligação: Convenio.plano_trabalho_codigo → PlanoAplicacao.codigo_plano_trabalho
    context_dict fornece convenio_codigo, siafi e uo ao template (campos não presentes
    diretamente em PlanoAplicacao).
    """
    from apps.convenios.models import Convenio, PlanoAplicacao

    context = {"convenio_codigo": cod_sigcon or ""}

    if cod_sigcon:
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        if not conv:
            return PlanoAplicacao.objects.none(), context
        context["siafi"] = conv.convenio_numero_sequencial_siafi or "—"
        context["uo"] = conv.unidade_orcamentaria_codigo or "—"
        context["plano_trabalho_codigo"] = conv.plano_trabalho_codigo or "—"
        if conv.plano_trabalho_codigo:
            qs = PlanoAplicacao.objects.filter(codigo_plano_trabalho=conv.plano_trabalho_codigo)
        else:
            qs = PlanoAplicacao.objects.none()
    else:
        context.update({"siafi": "", "uo": "", "plano_trabalho_codigo": ""})
        qs = PlanoAplicacao.objects.all()

    return qs, context


def get_cronograma_qs(
    cod_sigcon: str | None = None,
    cod_siafi: str | None = None,
    plano: str | None = None,
):
    """
    Retorna (QuerySet[CronogramaDesembolso], context_dict).

    Modo detalhe (cod_sigcon): filtra por siafi+uo derivados de Convenio.
    Modo standalone: filtra por cod_siafi e/ou plano (comportamento existente).
    """
    from apps.convenios.models import Convenio, CronogramaDesembolso

    context = {"convenio_codigo": cod_sigcon or ""}
    qs = CronogramaDesembolso.objects.all()

    if cod_sigcon:
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        if not conv:
            return CronogramaDesembolso.objects.none(), context
        context["siafi"] = conv.convenio_numero_sequencial_siafi or "—"
        context["plano_trabalho_codigo"] = conv.plano_trabalho_codigo or "—"
        # CronogramaDesembolso carrega siafi+uo via loader (ver loader.py)
        if conv.convenio_numero_sequencial_siafi:
            qs = qs.filter(
                convenio_numero_sequencial_siafi=conv.convenio_numero_sequencial_siafi,
                unidade_orcamentaria_codigo=conv.unidade_orcamentaria_codigo,
            )
        elif conv.plano_trabalho_codigo:
            qs = qs.filter(plano_trabalho_codigo=conv.plano_trabalho_codigo)
        else:
            qs = CronogramaDesembolso.objects.none()
    else:
        context["siafi"] = cod_siafi or ""
        context["plano_trabalho_codigo"] = plano or ""
        if cod_siafi:
            qs = qs.filter(convenio_numero_sequencial_siafi__icontains=cod_siafi)
        if plano:
            qs = qs.filter(plano_trabalho_codigo__icontains=plano)

    return qs, context


def get_prorrogacao_qs(cod_sigcon: str | None = None):
    """
    Retorna (QuerySet[ProrrogacaoOficio], context_dict).

    Chave de ligação DIRETA: ProrrogacaoOficio.prorrogacao_oficio_codigo_convenio = convenio_codigo
    Não há plano_trabalho_codigo em ProrrogacaoOficio; exibe-o via Convenio quando em modo detalhe.
    """
    from apps.convenios.models import Convenio, ProrrogacaoOficio

    context = {"convenio_codigo": cod_sigcon or ""}
    qs = ProrrogacaoOficio.objects.all()

    if cod_sigcon:
        qs = qs.filter(prorrogacao_oficio_codigo_convenio=cod_sigcon)
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        context["plano_trabalho_codigo"] = (conv.plano_trabalho_codigo or "—") if conv else "—"
    else:
        context["plano_trabalho_codigo"] = ""

    return qs, context


def get_termos_aditivos_qs(cod_sigcon: str | None = None):
    """
    Retorna (QuerySet[TermoAditivo], context_dict).

    Chave de ligação: Convenio.(siafi, uo)
        → CodigoTermoAditivo.(siafi, uo) → termo_aditivo_codigo_sequencial
        → TermoAditivo.termo_aditivo_codigo_sequencial
    CodigoTermoAditivo também fornece plano_trabalho_codigo por termo.
    context_dict inclui 'ta_pt_map': {ta_codigo_seq → plano_trabalho_codigo}.
    """
    from apps.convenios.models import Convenio, CodigoTermoAditivo, TermoAditivo

    context = {"convenio_codigo": cod_sigcon or "", "ta_pt_map": {}}

    if cod_sigcon:
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        if not conv:
            return TermoAditivo.objects.none(), context

        context["plano_trabalho_codigo"] = conv.plano_trabalho_codigo or "—"
        siafi = conv.convenio_numero_sequencial_siafi
        uo = conv.unidade_orcamentaria_codigo

        ta_rows = list(
            CodigoTermoAditivo.objects.filter(
                convenio_numero_sequencial_siafi=siafi,
                unidade_orcamentaria_codigo=uo,
            ).values("termo_aditivo_codigo_sequencial", "plano_trabalho_codigo")
        )
        ta_codes = [r["termo_aditivo_codigo_sequencial"] for r in ta_rows if r["termo_aditivo_codigo_sequencial"]]
        context["ta_pt_map"] = {
            r["termo_aditivo_codigo_sequencial"]: r["plano_trabalho_codigo"] or "—"
            for r in ta_rows
            if r["termo_aditivo_codigo_sequencial"]
        }
        qs = TermoAditivo.objects.filter(termo_aditivo_codigo_sequencial__in=ta_codes)
    else:
        context["plano_trabalho_codigo"] = ""
        qs = TermoAditivo.objects.all()

    return qs, context
