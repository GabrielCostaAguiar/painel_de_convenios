"""
Consultas das telas SIGCON.

As views nao acessam o ORM direto — elas chamam estas funcoes. A logica de
query fica aqui, e nao na view, porque assim um teste monta os dados e chama a
funcao sem passar pelo ciclo request/response, e porque o mesmo queryset serve
a tela e aos exports CSV/XLSX.

Ordenacao: toda tela paginada precisa de order_by deterministico, terminando
em "pk" — ver a nota nas constantes ORDENACAO_* abaixo.
"""


# ---------------------------------------------------------------------------
# Ordenacao das telas paginadas
# ---------------------------------------------------------------------------
# Paginar um queryset sem order_by pede ao banco "as linhas 51 a 100" sem dizer
# em que ordem — o banco pode devolver ordens diferentes a cada consulta, e o
# usuario acaba vendo um registro em duas paginas e nunca vendo outro. O Django
# avisa disso com UnorderedObjectListWarning.
#
# Cada ORDENACAO_* abaixo segue as colunas da tela, da esquerda para a direita,
# e TERMINA SEMPRE em "pk": as chaves de negocio do SIGCON-MG admitem empate
# (varias linhas do mesmo convenio, do mesmo exercicio), e so uma coluna unica
# torna a ordem totalmente deterministica.
#
# A ordenacao fica aqui, e nao na view nem em Meta.ordering do model:
# Meta.ordering valeria para TODAS as consultas daquele model, inclusive as
# agregacoes do Gold, que nao paginam e nao deveriam pagar por isso.
#
# Tela, export CSV e export XLSX compartilham estas funcoes, entao os arquivos
# baixados saem na mesma ordem da tela — que e o desejado.

def get_anos_disponiveis() -> list[int]:
    """Lista de anos com convênios registrados, em ordem decrescente."""
    from apps.sigcon.models import Convenio
    from django.db.models.functions import ExtractYear

    return list(
        Convenio.objects
        .exclude(data_inicio_vigencia=None)
        .annotate(ano=ExtractYear("data_inicio_vigencia"))
        .values_list("ano", flat=True)
        .distinct()
        .order_by("-ano")
    )


ORDENACAO_PLANO_APLICACAO = (
    "convenio_numero_sequencial_siafi",
    "convenio_codigo",
    "ano_exercicio_programa_trabalho",
    "funcional_programatica_formatado",
    "pk",
)

ORDENACAO_CRONOGRAMA = (
    "convenio_numero_sequencial_siafi",
    "convenio_codigo",
    "ano_cronograma_desembolso",
    "mes_cronograma_desembolso",
    "pk",
)

ORDENACAO_PRORROGACAO = (
    "prorrogacao_oficio_codigo_convenio",
    "prorrogacao_oficio_codigo",
    "pk",
)

ORDENACAO_TERMO_ADITIVO = (
    "termo_aditivo_codigo_sequencial",
    "termo_aditivo_numero_termo_aditivo",
    "pk",
)

ORDENACAO_UNIDADES_EXECUTORAS = (
    "convenio_codigo",
    "convenio_numero_sequencial_siafi",
    "unidade_orcamentaria_codigo",
    "unidade_executora",
    "pk",
)


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
    from apps.sigcon.models import ControleSEI, ConvenioIntegrado
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
    from apps.sigcon.models import Convenio, PlanoAplicacao

    context = {}

    if cod_sigcon:
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        if not conv:
            # Mesmo vazio, sai ordenado: o contrato da funcao e sempre
            # devolver queryset ordenado, e a view pagina o resultado.
            return PlanoAplicacao.objects.none().order_by(*ORDENACAO_PLANO_APLICACAO), context
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

    return qs.order_by(*ORDENACAO_PLANO_APLICACAO), context

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
    from apps.sigcon.models import Convenio, CronogramaDesembolso

    context = {}
    qs = CronogramaDesembolso.objects.all()

    if cod_sigcon:
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        if not conv:
            # Mesmo vazio, sai ordenado (ver nota em get_plano_aplicacao_qs).
            return CronogramaDesembolso.objects.none().order_by(*ORDENACAO_CRONOGRAMA), context
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

    return qs.order_by(*ORDENACAO_CRONOGRAMA), context

def get_prorrogacao_qs(cod_sigcon: str | None = None, cod_siafi: str | None = None):
    """
    Retorna (QuerySet[ProrrogacaoOficio], context_dict).

    Chave de ligação DIRETA: ProrrogacaoOficio.prorrogacao_oficio_codigo_convenio = convenio_codigo
    Não há plano_trabalho_codigo nem SIAFI em ProrrogacaoOficio; exibe-os via Convenio.

    cod_sigcon tem prioridade; cod_siafi (filtro global) resolve os convenio_codigo
    correspondentes via Convenio quando cod_sigcon não foi informado.
    """
    from apps.sigcon.models import Convenio, ProrrogacaoOficio

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

    return qs.order_by(*ORDENACAO_PRORROGACAO), context

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
    from apps.sigcon.models import Convenio, CodigoTermoAditivo, TermoAditivo

    context = {"convenio_codigo": cod_sigcon or "", "ta_pt_map": {}}

    if cod_sigcon:
        conv = Convenio.objects.filter(convenio_codigo=cod_sigcon).first()
        if not conv:
            # Mesmo vazio, sai ordenado (ver nota em get_plano_aplicacao_qs).
            return TermoAditivo.objects.none().order_by(*ORDENACAO_TERMO_ADITIVO), context

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

    return qs.order_by(*ORDENACAO_TERMO_ADITIVO), context

def get_unidades_executoras_qs(cod_sigcon: str | None = None, cod_siafi: str | None = None):
    """
    Retorna (QuerySet[UnidadesExecutoras], context_dict).

    Chave de ligação DIRETA: UnidadesExecutoras.convenio_codigo = convenio_codigo.
    cod_siafi (filtro global) usa convenio_numero_sequencial_siafi, presente
    diretamente no model — sem precisar passar por Convenio.
    """
    from apps.sigcon.models import UnidadesExecutoras

    context = {"convenio_codigo": cod_sigcon or ""}
    qs = UnidadesExecutoras.objects.all()

    if cod_sigcon:
        qs = qs.filter(convenio_codigo=cod_sigcon)
    elif cod_siafi:
        qs = qs.filter(convenio_numero_sequencial_siafi=cod_siafi)

    return qs.order_by(*ORDENACAO_UNIDADES_EXECUTORAS), context

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
    from apps.sigcon.models import Convenio, TermoAditivo, CodigoTermoAditivo, ConvenioIntegrado
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
