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
    from apps.sigcon.models import SigconConvenio
    from django.db.models.functions import ExtractYear

    return list(
        SigconConvenio.objects
        .exclude(dt_vigencia_inicio=None)
        .annotate(ano=ExtractYear("dt_vigencia_inicio"))
        .values_list("ano", flat=True)
        .distinct()
        .order_by("-ano")
    )


ORDENACAO_PLANO_APLICACAO = (
    "cd_plano_trabalho",
    "nr_ano_exercicio",
    "cd_funcional_programatica",
    "pk",
)

ORDENACAO_CRONOGRAMA = (
    "cd_plano_trabalho",
    "nr_ano_desembolso",
    "nr_mes_desembolso",
    "pk",
)

ORDENACAO_PRORROGACAO = (
    "cd_convenio_sequencial",
    "cd_prorrogacao_oficio",
    "pk",
)

ORDENACAO_TERMO_ADITIVO = (
    "cd_termo_aditivo",
    "nr_termo_aditivo",
    "pk",
)

ORDENACAO_UNIDADES_EXECUTORAS = (
    "nr_convenio",
    "nr_siafi",
    "cd_uo",
    "cd_unidade_executora",
    "pk",
)


# ---------------------------------------------------------------------------
# Ligações entre as tabelas SIGCON (todas planas, sem ForeignKey)
# ---------------------------------------------------------------------------
# SigconConvenio.siafi_uo é a chave de ligação com as pontes sigcon_chave_*:
#   SigconChaveConvenio       siafi_uo -> cd_convenio_sequencial
#   SigconChavePlanoTrabalho  siafi_uo -> cd_plano_trabalho (plano original)
#   SigconChaveTermoAditivo   siafi_uo -> cd_termo_aditivo + cd_plano_trabalho

def _planos_dos_siafi_uo(siafi_uos) -> set:
    """cd_plano_trabalho do plano original e dos planos dos aditivos dos siafi_uo dados."""
    from apps.sigcon.models import SigconChavePlanoTrabalho, SigconChaveTermoAditivo

    siafi_uos = [s for s in siafi_uos if s]
    if not siafi_uos:
        return set()
    planos = set(
        SigconChavePlanoTrabalho.objects.filter(siafi_uo__in=siafi_uos)
        .values_list("cd_plano_trabalho", flat=True)
    )
    planos |= set(
        SigconChaveTermoAditivo.objects.filter(siafi_uo__in=siafi_uos)
        .values_list("cd_plano_trabalho", flat=True)
    )
    planos.discard(None)
    planos.discard("")
    return planos


def _plano_original(siafi_uo: str | None) -> str:
    """cd_plano_trabalho do plano original do convênio, ou '' se não houver."""
    from apps.sigcon.models import SigconChavePlanoTrabalho

    if not siafi_uo:
        return ""
    return (
        SigconChavePlanoTrabalho.objects.filter(siafi_uo=siafi_uo)
        .exclude(cd_plano_trabalho=None)
        .values_list("cd_plano_trabalho", flat=True)
        .first()
    ) or ""


# ---------------------------------------------------------------------------
# Consultas SIGCON — serviços das 6 abas
# ---------------------------------------------------------------------------

def enrich_convenios_page(page_items: list) -> dict:
    """
    Enriquece uma lista de SigconConvenio com dados das tabelas ligadas pelo
    siafi_uo: plano de trabalho original, convênio geral, concedente e tipo de
    contrapartida (Gold).

    Retorna dict[pk_convenio → {
        'codigo_siconv', 'no_sei', 'proponente', 'fim_vigencia_inicial',
        'tipo_contrapartida', 'plano_trabalho', 'instrumento', 'titulo',
        'concedente', 'esfera', 'objeto', 'dt_assinatura', 'dt_publicacao'
    }].

    O modelo SIGCON não traz SICONV nem Controle SEI (fontes de ondas futuras):
    'codigo_siconv' e 'no_sei' saem como "—". 'proponente' é o CNPJ do proponente
    do plano de trabalho original.
    """
    from apps.sigcon.models import (
        SigconChaveConvenio,
        SigconChavePlanoTrabalho,
        SigconConcedente,
        SigconConvenioGeral,
        SigconPlanoTrabalho,
    )
    from core.gold.contrapartida import tipo_por_siafi_uo

    if not page_items:
        return {}

    siafi_uos = [c.siafi_uo for c in page_items if c.siafi_uo]

    plano_por_siafi_uo = {}
    for siafi_uo, plano in (
        SigconChavePlanoTrabalho.objects.filter(siafi_uo__in=siafi_uos)
        .exclude(cd_plano_trabalho=None)
        .order_by("-pk")
        .values_list("siafi_uo", "cd_plano_trabalho")
    ):
        plano_por_siafi_uo[siafi_uo] = plano

    planos = {}
    for pt in (
        SigconPlanoTrabalho.objects.filter(cd_plano_trabalho__in=set(plano_por_siafi_uo.values()))
        .order_by("-pk")
        .values("cd_plano_trabalho", "nm_plano_trabalho", "tx_objeto", "nm_concedente",
                "nr_cnpj_concedente", "nr_cnpj_proponente", "tp_instrumento_siafi")
    ):
        planos[pt["cd_plano_trabalho"]] = pt

    esfera_por_cnpj = dict(
        SigconConcedente.objects
        .filter(nr_cnpj_concedente__in={p["nr_cnpj_concedente"] for p in planos.values() if p["nr_cnpj_concedente"]})
        .values_list("nr_cnpj_concedente", "ds_esfera")
    )

    seq_por_siafi_uo = {}
    for siafi_uo, seq in (
        SigconChaveConvenio.objects.filter(siafi_uo__in=siafi_uos)
        .exclude(cd_convenio_sequencial=None)
        .order_by("-pk")
        .values_list("siafi_uo", "cd_convenio_sequencial")
    ):
        seq_por_siafi_uo[siafi_uo] = seq
    geral_por_seq = {}
    for g in (
        SigconConvenioGeral.objects.filter(cd_convenio_sequencial__in=set(seq_por_siafi_uo.values()))
        .order_by("-pk")
        .values("cd_convenio_sequencial", "dt_assinatura", "dt_publicacao")
    ):
        geral_por_seq[g["cd_convenio_sequencial"]] = g

    contra_map = tipo_por_siafi_uo(siafi_uos) if siafi_uos else {}

    result = {}
    for conv in page_items:
        plano_cd = plano_por_siafi_uo.get(conv.siafi_uo)
        pt = planos.get(plano_cd, {})
        geral = geral_por_seq.get(seq_por_siafi_uo.get(conv.siafi_uo), {})
        result[conv.pk] = {
            "codigo_siconv":        "—",
            "no_sei":               "—",
            "proponente":           pt.get("nr_cnpj_proponente") or "—",
            "fim_vigencia_inicial": conv.dt_vigencia_termino_inicial,
            "tipo_contrapartida":   contra_map.get(conv.siafi_uo) or "—",
            "plano_trabalho":       plano_cd or "",
            "instrumento":          pt.get("tp_instrumento_siafi") or "",
            "titulo":               pt.get("nm_plano_trabalho") or "",
            "concedente":           pt.get("nm_concedente") or "",
            "esfera":               esfera_por_cnpj.get(pt.get("nr_cnpj_concedente")) or "",
            "objeto":               pt.get("tx_objeto") or "",
            "dt_assinatura":        geral.get("dt_assinatura"),
            "dt_publicacao":        geral.get("dt_publicacao"),
        }
    return result


def anexar_convenio_por_plano(items) -> None:
    """
    Carimba nr_convenio_ext e nr_siafi_ext em cada linha que tem cd_plano_trabalho
    (cronograma, plano de aplicação). O novo model é plano: o convênio chega pelo
    plano → siafi_uo (plano original ou de aditivo) → SigconConvenio.
    """
    from apps.sigcon.models import SigconChavePlanoTrabalho, SigconChaveTermoAditivo, SigconConvenio

    items = list(items)
    planos = {i.cd_plano_trabalho for i in items if i.cd_plano_trabalho}
    siafi_uo_por_plano: dict = {}
    for modelo in (SigconChavePlanoTrabalho, SigconChaveTermoAditivo):
        for plano, siafi_uo in (
            modelo.objects.filter(cd_plano_trabalho__in=planos)
            .exclude(siafi_uo=None)
            .order_by("pk")
            .values_list("cd_plano_trabalho", "siafi_uo")
        ):
            siafi_uo_por_plano.setdefault(plano, siafi_uo)
    conv_por_siafi_uo = {
        siafi_uo: (nr_convenio, nr_siafi)
        for siafi_uo, nr_convenio, nr_siafi in SigconConvenio.objects.filter(
            siafi_uo__in=set(siafi_uo_por_plano.values()),
        ).values_list("siafi_uo", "nr_convenio", "nr_siafi")
    }
    for item in items:
        nr_convenio, nr_siafi = conv_por_siafi_uo.get(siafi_uo_por_plano.get(item.cd_plano_trabalho), (None, None))
        item.nr_convenio_ext = nr_convenio
        item.nr_siafi_ext = nr_siafi


def anexar_convenio_por_sequencial(items) -> None:
    """Carimba nr_convenio_ext em cada linha com cd_convenio_sequencial (prorrogação)."""
    from apps.sigcon.models import SigconChaveConvenio

    items = list(items)
    nr_por_seq = dict(
        SigconChaveConvenio.objects
        .filter(cd_convenio_sequencial__in={i.cd_convenio_sequencial for i in items if i.cd_convenio_sequencial})
        .order_by("-pk")
        .values_list("cd_convenio_sequencial", "nr_convenio")
    )
    for item in items:
        item.nr_convenio_ext = nr_por_seq.get(item.cd_convenio_sequencial)

def get_plano_aplicacao_qs(nr_convenio: str | None = None, nr_siafi: str | None = None):
    """
    Retorna (QuerySet[SigconPlanoAplicacao], context_dict) para a aba Plano de Aplicação.

    Chave de ligação: cd_plano_trabalho, resolvido a partir do convênio pelas
    pontes sigcon_chave_plano_trabalho / sigcon_chave_termo_aditivo.
    context_dict fornece siafi e uo ao template.

    nr_convenio tem prioridade; nr_siafi (filtro global) é usado quando nr_convenio
    não foi informado.
    """
    from apps.sigcon.models import SigconConvenio, SigconPlanoAplicacao

    context = {}

    if nr_convenio:
        conv = SigconConvenio.objects.filter(nr_convenio=nr_convenio).first()
        if not conv:
            # Mesmo vazio, sai ordenado: o contrato da funcao e sempre
            # devolver queryset ordenado, e a view pagina o resultado.
            return SigconPlanoAplicacao.objects.none().order_by(*ORDENACAO_PLANO_APLICACAO), context
        context["siafi"] = conv.nr_siafi or "—"
        context["uo"] = conv.cd_uo or "—"
        context["cd_plano_trabalho"] = _plano_original(conv.siafi_uo) or "—"
        planos = _planos_dos_siafi_uo([conv.siafi_uo])
        qs = SigconPlanoAplicacao.objects.filter(cd_plano_trabalho__in=planos)
    elif nr_siafi:
        context.update({"siafi": nr_siafi, "uo": "", "cd_plano_trabalho": ""})
        siafi_uos = SigconConvenio.objects.filter(nr_siafi=nr_siafi).values_list("siafi_uo", flat=True)
        planos = _planos_dos_siafi_uo(siafi_uos)
        qs = SigconPlanoAplicacao.objects.filter(cd_plano_trabalho__in=planos)
    else:
        context.update({"siafi": "", "uo": "", "cd_plano_trabalho": ""})
        qs = SigconPlanoAplicacao.objects.all()

    return qs.order_by(*ORDENACAO_PLANO_APLICACAO), context

def get_cronograma_qs(
    nr_convenio: str | None = None,
    nr_siafi: str | None = None,
    plano: str | None = None,
):
    """
    Retorna (QuerySet[SigconCronogramaDesembolso], context_dict).

    Modo detalhe (nr_convenio): planos do convênio (original + aditivos).
    Modo standalone: filtra por nr_siafi e/ou plano.
    """
    from apps.sigcon.models import SigconConvenio, SigconCronogramaDesembolso

    context = {}
    # Linhas marcadas pelo motor Silver (bloco desalinhado do relatório do BO,
    # sem plano de trabalho) estão no banco, mas não entram nas telas, nos
    # exports nem nas somas.
    qs = SigconCronogramaDesembolso.objects.filter(ds_alerta_linha__isnull=True)

    if nr_convenio:
        conv = SigconConvenio.objects.filter(nr_convenio=nr_convenio).first()
        if not conv:
            # Mesmo vazio, sai ordenado (ver nota em get_plano_aplicacao_qs).
            return SigconCronogramaDesembolso.objects.none().order_by(*ORDENACAO_CRONOGRAMA), context
        context["siafi"] = conv.nr_siafi or "—"
        context["cd_plano_trabalho"] = _plano_original(conv.siafi_uo) or "—"
        qs = qs.filter(cd_plano_trabalho__in=_planos_dos_siafi_uo([conv.siafi_uo]))
    else:
        context["siafi"] = nr_siafi or ""
        context["cd_plano_trabalho"] = plano or ""
        if nr_siafi:
            siafi_uos = SigconConvenio.objects.filter(nr_siafi__icontains=nr_siafi).values_list("siafi_uo", flat=True)
            qs = qs.filter(cd_plano_trabalho__in=_planos_dos_siafi_uo(siafi_uos))
        if plano:
            qs = qs.filter(cd_plano_trabalho__icontains=plano)

    return qs.order_by(*ORDENACAO_CRONOGRAMA), context

def get_prorrogacao_qs(nr_convenio: str | None = None, nr_siafi: str | None = None):
    """
    Retorna (QuerySet[SigconProrrogacaoOficio], context_dict).

    Chave de ligação: SigconProrrogacaoOficio.cd_convenio_sequencial, que se
    traduz em convênio pela ponte SigconChaveConvenio (siafi_uo).

    nr_convenio tem prioridade; nr_siafi (filtro global) resolve os códigos
    sequenciais via SigconChaveConvenio quando nr_convenio não foi informado.
    """
    from apps.sigcon.models import SigconChaveConvenio, SigconConvenio, SigconProrrogacaoOficio

    context = {"convenio_codigo": nr_convenio or ""}
    qs = SigconProrrogacaoOficio.objects.all()

    if nr_convenio:
        codigos = set(
            SigconChaveConvenio.objects.filter(nr_convenio=nr_convenio)
            .values_list("cd_convenio_sequencial", flat=True)
        )
        qs = qs.filter(cd_convenio_sequencial__in=codigos) if codigos else qs.none()
        conv = SigconConvenio.objects.filter(nr_convenio=nr_convenio).first()
        context["cd_plano_trabalho"] = (_plano_original(conv.siafi_uo) or "—") if conv else "—"
    elif nr_siafi:
        codigos = set(
            SigconChaveConvenio.objects.filter(nr_siafi=nr_siafi)
            .values_list("cd_convenio_sequencial", flat=True)
        )
        qs = qs.filter(cd_convenio_sequencial__in=codigos) if codigos else qs.none()
        context["cd_plano_trabalho"] = ""
    else:
        context["cd_plano_trabalho"] = ""

    return qs.order_by(*ORDENACAO_PRORROGACAO), context

def get_termos_aditivos_qs(nr_convenio: str | None = None, nr_siafi: str | None = None):
    """
    Retorna (QuerySet[SigconTermoAditivo], context_dict).

    Chave de ligação: SigconConvenio.siafi_uo
        → SigconChaveTermoAditivo.siafi_uo → cd_termo_aditivo
        → SigconTermoAditivo.cd_termo_aditivo
    SigconChaveTermoAditivo também fornece cd_plano_trabalho por termo.
    context_dict inclui 'ta_pt_map': {cd_termo_aditivo → cd_plano_trabalho}.

    nr_convenio tem prioridade (resolve siafi_uo via SigconConvenio); nr_siafi
    (filtro global) consulta a ponte direto pelo SIAFI, sem exigir UO.
    """
    from apps.sigcon.models import SigconChaveTermoAditivo, SigconConvenio, SigconTermoAditivo

    context = {"convenio_codigo": nr_convenio or "", "ta_pt_map": {}}

    if nr_convenio:
        conv = SigconConvenio.objects.filter(nr_convenio=nr_convenio).first()
        if not conv:
            # Mesmo vazio, sai ordenado (ver nota em get_plano_aplicacao_qs).
            return SigconTermoAditivo.objects.none().order_by(*ORDENACAO_TERMO_ADITIVO), context

        context["cd_plano_trabalho"] = _plano_original(conv.siafi_uo) or "—"
        ta_rows = list(
            SigconChaveTermoAditivo.objects.filter(siafi_uo=conv.siafi_uo)
            .values("cd_termo_aditivo", "cd_plano_trabalho")
        ) if conv.siafi_uo else []
    elif nr_siafi:
        context["cd_plano_trabalho"] = ""
        ta_rows = list(
            SigconChaveTermoAditivo.objects.filter(nr_siafi=nr_siafi)
            .values("cd_termo_aditivo", "cd_plano_trabalho")
        )
    else:
        context["cd_plano_trabalho"] = ""
        return SigconTermoAditivo.objects.all().order_by(*ORDENACAO_TERMO_ADITIVO), context

    ta_codes = [r["cd_termo_aditivo"] for r in ta_rows if r["cd_termo_aditivo"]]
    context["ta_pt_map"] = {
        r["cd_termo_aditivo"]: r["cd_plano_trabalho"] or "—"
        for r in ta_rows
        if r["cd_termo_aditivo"]
    }
    qs = SigconTermoAditivo.objects.filter(cd_termo_aditivo__in=ta_codes)

    return qs.order_by(*ORDENACAO_TERMO_ADITIVO), context

def get_unidades_executoras_qs(nr_convenio: str | None = None, nr_siafi: str | None = None):
    """
    Retorna (QuerySet[SigconUnidadeExecutora], context_dict).

    SigconUnidadeExecutora traz nr_convenio (redundante) e nr_siafi direto,
    sem precisar passar por SigconConvenio.
    """
    from apps.sigcon.models import SigconUnidadeExecutora

    context = {"convenio_codigo": nr_convenio or ""}
    qs = SigconUnidadeExecutora.objects.all()

    if nr_convenio:
        qs = qs.filter(nr_convenio=nr_convenio)
    elif nr_siafi:
        qs = qs.filter(nr_siafi=nr_siafi)

    return qs.order_by(*ORDENACAO_UNIDADES_EXECUTORAS), context

def get_sigcon_qs(filtros: dict):
    """
    Retorna QuerySet[SigconConvenio] filtrado para a aba Convênios (tela mestre).

    `filtros` é um dict com as chaves: ano, situacao, nr_convenio, nr_siafi,
    instrumento, termo_aditivo, concedente, proponente, tipo_contrapartida
    (todas strings; "" significa "sem filtro").

    instrumento, concedente e proponente vêm do plano de trabalho original;
    termo_aditivo vem da ponte SigconChaveTermoAditivo. Todos são resolvidos
    para um conjunto de siafi_uo.
    """
    from apps.sigcon.models import (
        SigconChavePlanoTrabalho,
        SigconChaveTermoAditivo,
        SigconConvenio,
        SigconPlanoTrabalho,
        SigconTermoAditivo,
    )
    from core.gold.contrapartida import tipo_por_siafi_uo

    qs = SigconConvenio.objects.all()

    if filtros.get("ano", "").isdigit():
        qs = qs.filter(dt_vigencia_inicio__year=int(filtros["ano"]))
    if filtros.get("situacao"):
        qs = qs.filter(ds_situacao_convenio=filtros["situacao"])
    # A tela envia cod_sigcon/cod_siafi (ver views/_filtros.py); nr_* também é aceito.
    nr_convenio = filtros.get("cod_sigcon") or filtros.get("nr_convenio")
    nr_siafi = filtros.get("cod_siafi") or filtros.get("nr_siafi")
    if nr_convenio:
        qs = qs.filter(nr_convenio=nr_convenio)
    if nr_siafi:
        qs = qs.filter(nr_siafi=nr_siafi)

    filtros_plano = {}
    if filtros.get("instrumento"):
        filtros_plano["tp_instrumento_siafi"] = filtros["instrumento"]
    if filtros.get("concedente"):
        filtros_plano["nm_concedente__icontains"] = filtros["concedente"]
    if filtros.get("proponente"):
        filtros_plano["nr_cnpj_proponente__icontains"] = filtros["proponente"]
    if filtros_plano:
        planos = SigconPlanoTrabalho.objects.filter(**filtros_plano).values_list("cd_plano_trabalho", flat=True)
        siafi_uos = SigconChavePlanoTrabalho.objects.filter(
            cd_plano_trabalho__in=planos,
        ).values_list("siafi_uo", flat=True)
        qs = qs.filter(siafi_uo__in=siafi_uos)

    if filtros.get("termo_aditivo"):
        ta_codes = SigconTermoAditivo.objects.filter(
            tp_termo_aditivo=filtros["termo_aditivo"],
        ).values_list("cd_termo_aditivo", flat=True)
        siafi_uos = SigconChaveTermoAditivo.objects.filter(
            cd_termo_aditivo__in=ta_codes,
        ).values_list("siafi_uo", flat=True)
        qs = qs.filter(siafi_uo__in=siafi_uos)

    if filtros.get("tipo_contrapartida"):
        contra_map = tipo_por_siafi_uo()
        ids_validos = [
            c.pk for c in qs.only("pk", "siafi_uo")
            if contra_map.get(c.siafi_uo or "") == filtros["tipo_contrapartida"]
        ]
        qs = qs.filter(pk__in=ids_validos)

    return qs
