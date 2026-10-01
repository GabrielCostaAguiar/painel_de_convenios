"""
Consultas das telas do GRP.

Os 3 filtros (nr_grp, nr_instrumento, uo_cod) valem para todas as sub-abas —
ver _grp_filtrar_por_nr_grp.
"""

def get_grp_dados_qs(filtros: dict):
    """
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    `filtros` é um dict com as chaves: nr_grp
    (string; "" significa "sem filtro").
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    """
    from .models import DadosGrp

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
    from .models import DadosGrp

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
    from .models import CronogramaDesembolsoGrp

    qs = _grp_filtrar_por_nr_grp(CronogramaDesembolsoGrp.objects.all(), filtros)
    return qs.order_by("nr_grp", "ano_desembolso", "mes_desembolso", "parcela_desembolso")

def get_grp_recursos_contrapartida_qs(filtros: dict):
    """QuerySet[RecursosContrapartidaGrp] filtrado pelos filtros do GRP."""
    from .models import RecursosContrapartidaGrp

    qs = _grp_filtrar_por_nr_grp(RecursosContrapartidaGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")

def get_grp_recursos_concedente_qs(filtros: dict):
    """QuerySet[RecursosConcedenteGrp] filtrado pelos filtros do GRP."""
    from .models import RecursosConcedenteGrp

    qs = _grp_filtrar_por_nr_grp(RecursosConcedenteGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")

def get_grp_plano_aplicacao_qs(filtros: dict):
    """QuerySet[PlanoAplicacaoGrp] filtrado pelos filtros do GRP."""
    from .models import PlanoAplicacaoGrp

    qs = _grp_filtrar_por_nr_grp(PlanoAplicacaoGrp.objects.all(), filtros)
    return qs.order_by("nr_grp")

def get_grp_plano_aplicacao_detalhes_qs(filtros: dict):
    """QuerySet[PlanoAplicacaoGrpDetalhes] filtrado pelos filtros do GRP."""
    from .models import PlanoAplicacaoGrpDetalhes

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
    from .models import EsferaGrp

    return EsferaGrp.objects.all().order_by("concedente_cnpj")

def get_grp_uo_qs(filtros: dict):
    """
    QuerySet[UoGrp] — sem filtro.

    UoGrp não tem nr_grp: ela é uma tabela de domínio ligada por uo_cod
    (→ Convenio.uo_cod) e não há caminho para nr_grp dentro das tabelas do
    GRP. A sub-aba sempre mostra tudo; a view sinaliza no template que o
    filtro não se aplica aqui.
    """
    from .models import TabelaUoGrp

    return TabelaUoGrp.objects.all().order_by("uo_cod")