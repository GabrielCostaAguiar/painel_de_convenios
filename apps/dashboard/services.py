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
  Os dados mudam apenas quando um comando de carga é executado. Todos eles
  invalidam o cache ao terminar, chamando core.cache.invalidar_cache_indicadores()
  — não é preciso lembrar de invalidar à mão. As chaves e a estratégia de
  invalidação (número de versão) estão documentadas em core/cache.py.
  Em produção, configure Redis em settings.py:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                          "LOCATION": "redis://127.0.0.1:6379/1"}}
"""

import logging

from django.conf import settings
from django.core.cache import cache

from apps.convenios.models import DadosGrp
from core.cache import (
    CHAVE_INDICADORES,
    chave_indicadores,
    invalidar_cache_indicadores,
)
from core.gold import convenios as gold

logger = logging.getLogger(__name__)

_CACHE_TTL = getattr(settings, "GOLD_CACHE_SECONDS", 3600)
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
    """
    Limpa o cache de indicadores — a chave base e todas as variantes por ano.

    Mantido como fachada do módulo de serviços (outros pontos do projeto podem
    chamá-lo); a implementação vive em core/cache.py, que é de onde os loaders
    e o pipeline invalidam sem precisar importar a camada de apresentação.
    """
    invalidar_cache_indicadores()


# ---------------------------------------------------------------------------
# Consultas SIGCON — serviços das 6 abas
# ---------------------------------------------------------------------------

def enrich_convenios_page(page_items: list) -> dict:
    """
    Enriquece uma página de objetos Convenio com campos de ConvenioIntegrado,
    ControleSEI e tipo de contrapartida (Gold).

    Retorna dict[pk_convenio → {
        'codigo_siconv', 'proponente', 'fim_vigencia_inicial',
        'no_sei', 'tipo_contrapartida'
    }].

    Chaves de join:
      ConvenioIntegrado:  (siafi, uo)  — chave composta
      ControleSEI:        siafi puro   — NÃO siafi_uo
      tipo_contrapartida: siafi_uo     — siafi + uo concatenados (sem separador)
    """
    from apps.convenios.models import ControleSEI, ConvenioIntegrado
    from core.gold.contrapartida import tipo_por_siafi_uo

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

    sei_rows = ControleSEI.objects.filter(
        no_siafi_sigcon__in=siafis,
    ).values("no_siafi_sigcon", "no_sei")
    sei_map = {r["no_siafi_sigcon"]: r["no_sei"] for r in sei_rows}

    siafi_uos = [
        (c.convenio_numero_sequencial_siafi or "") + (c.unidade_orcamentaria_codigo or "")
        for c in page_items
        if c.convenio_numero_sequencial_siafi
    ]
    contra_map = tipo_por_siafi_uo(siafi_uos)

    result = {}
    for conv in page_items:
        key = (conv.convenio_numero_sequencial_siafi, conv.unidade_orcamentaria_codigo)
        extra = integ_map.get(key, {})
        siafi_uo = (conv.convenio_numero_sequencial_siafi or "") + (conv.unidade_orcamentaria_codigo or "")
        result[conv.pk] = {
            "codigo_siconv":      extra.get("codigo_siconv") or "—",
            "proponente":         extra.get("g_proponente_pad") or "—",
            "fim_vigencia_inicial": extra.get("g_fim_vigencia_inicial"),
            "no_sei":             sei_map.get(conv.convenio_numero_sequencial_siafi) or "—",
            "tipo_contrapartida": contra_map.get(siafi_uo) or "—",
        }
    return result


def get_plano_aplicacao_qs(cod_sigcon: str | None = None, cod_siafi: str | None = None):
    """
    Retorna (QuerySet[PlanoAplicacao], context_dict) para a aba Plano de Aplicação.

    Chave de ligação: Convenio.plano_trabalho_codigo → PlanoAplicacao.codigo_plano_trabalho
    context_dict fornece siafi e uo ao template (campos não presentes diretamente em
    PlanoAplicacao). O Código SIGCON de cada linha vem do próprio model
    (PlanoAplicacao.convenio_codigo, carimbado no loader) — não pertence a este context,
    que é por página, não por linha (SIAFI é 1:N convênio).

    cod_sigcon tem prioridade; cod_siafi (filtro global) é usado quando cod_sigcon
    não foi informado — resolve plano_trabalho_codigo via Convenio, pois
    PlanoAplicacao não tem SIAFI diretamente.
    """
    from apps.convenios.models import Convenio, PlanoAplicacao

    context = {}

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
    elif cod_siafi:
        context.update({"siafi": cod_siafi, "uo": "", "plano_trabalho_codigo": ""})
        planos = set(
            Convenio.objects.filter(convenio_numero_sequencial_siafi=cod_siafi)
            .exclude(plano_trabalho_codigo=None).exclude(plano_trabalho_codigo="")
            .values_list("plano_trabalho_codigo", flat=True)
        )
        qs = PlanoAplicacao.objects.filter(codigo_plano_trabalho__in=planos) if planos else PlanoAplicacao.objects.none()
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

    O Código SIGCON de cada linha vem do próprio model
    (CronogramaDesembolso.convenio_codigo, carimbado no loader) — não pertence a
    este context, que é por página, não por linha (SIAFI é 1:N convênio).
    """
    from apps.convenios.models import Convenio, CronogramaDesembolso

    context = {}
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


def get_prorrogacao_qs(cod_sigcon: str | None = None, cod_siafi: str | None = None):
    """
    Retorna (QuerySet[ProrrogacaoOficio], context_dict).

    Chave de ligação DIRETA: ProrrogacaoOficio.prorrogacao_oficio_codigo_convenio = convenio_codigo
    Não há plano_trabalho_codigo nem SIAFI em ProrrogacaoOficio; exibe-os via Convenio.

    cod_sigcon tem prioridade; cod_siafi (filtro global) resolve os convenio_codigo
    correspondentes via Convenio quando cod_sigcon não foi informado.
    """
    from apps.convenios.models import Convenio, ProrrogacaoOficio

    context = {"convenio_codigo": cod_sigcon or ""}
    qs = ProrrogacaoOficio.objects.all()

    if cod_sigcon:
        qs = qs.filter(prorrogacao_oficio_codigo_convenio=cod_sigcon)
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        context["plano_trabalho_codigo"] = (conv.plano_trabalho_codigo or "—") if conv else "—"
    elif cod_siafi:
        codigos = set(
            Convenio.objects.filter(convenio_numero_sequencial_siafi=cod_siafi)
            .values_list("convenio_codigo", flat=True)
        )
        qs = qs.filter(prorrogacao_oficio_codigo_convenio__in=codigos) if codigos else qs.none()
        context["plano_trabalho_codigo"] = ""
    else:
        context["plano_trabalho_codigo"] = ""

    return qs, context


def get_termos_aditivos_qs(cod_sigcon: str | None = None, cod_siafi: str | None = None):
    """
    Retorna (QuerySet[TermoAditivo], context_dict).

    Chave de ligação: Convenio.(siafi, uo)
        → CodigoTermoAditivo.(siafi, uo) → termo_aditivo_codigo_sequencial
        → TermoAditivo.termo_aditivo_codigo_sequencial
    CodigoTermoAditivo também fornece plano_trabalho_codigo por termo.
    context_dict inclui 'ta_pt_map': {ta_codigo_seq → plano_trabalho_codigo}.

    cod_sigcon tem prioridade (resolve siafi+uo via Convenio); cod_siafi (filtro
    global) consulta a ponte CodigoTermoAditivo direto pelo SIAFI, sem exigir UO.
    """
    from apps.convenios.models import Convenio, CodigoTermoAditivo, TermoAditivo

    context = {"convenio_codigo": cod_sigcon or "", "ta_pt_map": {}}

    if cod_sigcon:
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        if not conv:
            return TermoAditivo.objects.none(), context

        context["plano_trabalho_codigo"] = conv.plano_trabalho_codigo or "—"
        ta_rows = list(
            CodigoTermoAditivo.objects.filter(
                convenio_numero_sequencial_siafi=conv.convenio_numero_sequencial_siafi,
                unidade_orcamentaria_codigo=conv.unidade_orcamentaria_codigo,
            ).values("termo_aditivo_codigo_sequencial", "plano_trabalho_codigo")
        )
        ta_codes = [r["termo_aditivo_codigo_sequencial"] for r in ta_rows if r["termo_aditivo_codigo_sequencial"]]
        context["ta_pt_map"] = {
            r["termo_aditivo_codigo_sequencial"]: r["plano_trabalho_codigo"] or "—"
            for r in ta_rows
            if r["termo_aditivo_codigo_sequencial"]
        }
        qs = TermoAditivo.objects.filter(termo_aditivo_codigo_sequencial__in=ta_codes)
    elif cod_siafi:
        context["plano_trabalho_codigo"] = ""
        ta_rows = list(
            CodigoTermoAditivo.objects.filter(
                convenio_numero_sequencial_siafi=cod_siafi,
            ).values("termo_aditivo_codigo_sequencial", "plano_trabalho_codigo")
        )
        ta_codes = [r["termo_aditivo_codigo_sequencial"] for r in ta_rows if r["termo_aditivo_codigo_sequencial"]]
        context["ta_pt_map"] = {
            r["termo_aditivo_codigo_sequencial"]: r["plano_trabalho_codigo"] or "—"
            for r in ta_rows
            if r["termo_aditivo_codigo_sequencial"]
        }
        qs = TermoAditivo.objects.filter(termo_aditivo_codigo_sequencial__in=ta_codes) if ta_codes else TermoAditivo.objects.none()
    else:
        context["plano_trabalho_codigo"] = ""
        qs = TermoAditivo.objects.all()

    return qs, context


def get_unidades_executoras_qs(cod_sigcon: str | None = None, cod_siafi: str | None = None):
    """
    Retorna (QuerySet[UnidadesExecutoras], context_dict).

    Chave de ligação DIRETA: UnidadesExecutoras.convenio_codigo = convenio_codigo.
    cod_siafi (filtro global) usa convenio_numero_sequencial_siafi, presente
    diretamente no model — sem precisar passar por Convenio.
    """
    from apps.convenios.models import UnidadesExecutoras

    context = {"convenio_codigo": cod_sigcon or ""}
    qs = UnidadesExecutoras.objects.all()

    if cod_sigcon:
        qs = qs.filter(convenio_codigo=cod_sigcon)
    elif cod_siafi:
        qs = qs.filter(convenio_numero_sequencial_siafi=cod_siafi)

    return qs, context


def _filtrar_por_siafi_uo_pares(qs, pares):
    """Restringe qs aos Convenio cujo (siafi, uo) está no conjunto de pares dado."""
    from django.db.models import Q

    if not pares:
        return qs.none()
    condicao = Q()
    for siafi, uo in pares:
        condicao |= Q(convenio_numero_sequencial_siafi=siafi, unidade_orcamentaria_codigo=uo)
    return qs.filter(condicao)


def get_sigcon_qs(filtros: dict):
    """
    Retorna QuerySet[Convenio] filtrado para a aba Convênios (tela mestre).

    `filtros` é um dict com as chaves: ano, situacao, cod_sigcon, cod_siafi,
    instrumento, termo_aditivo, concedente, proponente, tipo_contrapartida
    (todas strings; "" significa "sem filtro").

    termo_aditivo, proponente e tipo_contrapartida não são campos diretos do
    model Convenio — resolvidos via (siafi, uo) a partir das tabelas-ponte e
    da Gold, no mesmo padrão usado em enrich_convenios_page.
    """
    from apps.convenios.models import Convenio, TermoAditivo, CodigoTermoAditivo, ConvenioIntegrado
    from core.gold.contrapartida import tipo_por_siafi_uo

    qs = Convenio.objects.all()

    if filtros.get("ano", "").isdigit():
        qs = qs.filter(data_inicio_vigencia__year=int(filtros["ano"]))
    if filtros.get("situacao"):
        qs = qs.filter(situacao=filtros["situacao"])
    if filtros.get("cod_sigcon"):
        qs = qs.filter(convenio_codigo=filtros["cod_sigcon"])
    if filtros.get("cod_siafi"):
        qs = qs.filter(convenio_numero_sequencial_siafi=filtros["cod_siafi"])
    if filtros.get("instrumento"):
        qs = qs.filter(instrumento=filtros["instrumento"])
    if filtros.get("concedente"):
        qs = qs.filter(concedente__icontains=filtros["concedente"])

    if filtros.get("termo_aditivo"):
        ta_codes = TermoAditivo.objects.filter(
            tipo_termo_aditivo=filtros["termo_aditivo"],
        ).values_list("termo_aditivo_codigo_sequencial", flat=True)
        pares = set(
            CodigoTermoAditivo.objects.filter(
                termo_aditivo_codigo_sequencial__in=ta_codes,
            ).values_list("convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo")
        )
        qs = _filtrar_por_siafi_uo_pares(qs, pares)

    if filtros.get("proponente"):
        pares = set(
            ConvenioIntegrado.objects.filter(
                g_proponente_pad__icontains=filtros["proponente"],
            ).values_list("convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo")
        )
        qs = _filtrar_por_siafi_uo_pares(qs, pares)

    if filtros.get("tipo_contrapartida"):
        contra_map = tipo_por_siafi_uo()
        ids_validos = [
            c.pk for c in qs.only(
                "pk", "convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo",
            )
            if contra_map.get(
                (c.convenio_numero_sequencial_siafi or "") + (c.unidade_orcamentaria_codigo or "")
            ) == filtros["tipo_contrapartida"]
        ]
        qs = qs.filter(pk__in=ids_validos)

    return qs

def get_grp_dados_qs(filtros: dict):
    """
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    `filtros` é um dict com as chaves: nr_grp
    (string; "" significa "sem filtro").
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    """
    from apps.convenios.models import DadosGrp, TermoAditivo, CodigoTermoAditivo, ConvenioIntegrado
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
    from apps.convenios.models import DadosGrp

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
    from apps.convenios.models import CronogramaDesembolsoGrp

    qs = _grp_filtrar_por_nr_grp(CronogramaDesembolsoGrp.objects.all(), filtros)
    return qs.order_by("nr_grp", "ano_desembolso", "mes_desembolso", "parcela_desembolso")


def get_grp_recursos_contrapartida_qs(filtros: dict):
    """QuerySet[RecursosContrapartidaGrp] filtrado pelos filtros do GRP."""
    from apps.convenios.models import RecursosContrapartidaGrp

    qs = _grp_filtrar_por_nr_grp(RecursosContrapartidaGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")


def get_grp_recursos_concedente_qs(filtros: dict):
    """QuerySet[RecursosConcedenteGrp] filtrado pelos filtros do GRP."""
    from apps.convenios.models import RecursosConcedenteGrp

    qs = _grp_filtrar_por_nr_grp(RecursosConcedenteGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")


def get_grp_plano_aplicacao_qs(filtros: dict):
    """QuerySet[PlanoAplicacaoGrp] filtrado pelos filtros do GRP."""
    from apps.convenios.models import PlanoAplicacaoGrp

    qs = _grp_filtrar_por_nr_grp(PlanoAplicacaoGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")


def get_grp_plano_aplicacao_detalhes_qs(filtros: dict):
    """QuerySet[PlanoAplicacaoGrpDetalhes] filtrado pelos filtros do GRP."""
    from apps.convenios.models import PlanoAplicacaoGrpDetalhes

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
    from apps.convenios.models import EsferaGrp

    return EsferaGrp.objects.all().order_by("concedente_cnpj")
