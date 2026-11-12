"""
Consultas das telas do GRP.

Os 3 filtros (nr_grp, nr_instrumento, cd_uo) valem para todas as sub-abas —
ver _grp_filtrar_por_nr_grp.
"""

import logging
import operator
from functools import reduce

from django.db.models import Q

from apps.grp import models


logger = logging.getLogger(__name__)

_LIMITE_TERMOS = 200


def _filtrar_nr_grp_multiplo(qs, valor: str, campo: str = "nr_grp"):
    """Filtra por um ou vários nr_grp separados por espaço (OR de icontains).

    Aceita espaços, tabs e quebras de linha como separador (cobre valores
    colados de uma coluna do Excel).  Cada termo é buscado com icontains,
    combinados com OR.  Valor vazio ou só com espaços retorna o queryset
    sem alteração.
    """
    if not valor or not valor.strip():
        return qs

    termos = list(dict.fromkeys(valor.split()))

    if len(termos) > _LIMITE_TERMOS:
        logger.warning(
            "nr_grp: %d termos recebidos, usando apenas os %d primeiros",
            len(termos),
            _LIMITE_TERMOS,
        )
        termos = termos[:_LIMITE_TERMOS]

    filtro = reduce(operator.or_, (Q(**{f"{campo}__icontains": t}) for t in termos))
    return qs.filter(filtro)


def get_grp_dados_qs(filtros: dict):
    """
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    `filtros` é um dict com as chaves: nr_grp
    (string; "" significa "sem filtro").
    Retorna QuerySet[NúmeroGRP] filtrado para a aba GRP (tela teste).
    """
    from .models import GrpGoldInstrumento

    qs = GrpGoldInstrumento.objects.all()

    qs = _filtrar_nr_grp_multiplo(qs, filtros.get("nr_grp", ""))
    if filtros.get("nr_instrumento"):
        qs = qs.filter(nr_instrumento__icontains=filtros["nr_instrumento"])
    if filtros.get("cd_uo"):
        qs = qs.filter(cd_uo=filtros["cd_uo"])

    return qs.order_by("nr_grp")


# ---------------------------------------------------------------------------
# GRP — sub-abas ligadas por nr_grp
#
# As 6 sub-abas abaixo reaproveitam os mesmos 3 filtros da aba Dados
# (nr_grp, nr_instrumento, cd_uo), com as MESMAS chaves de querystring.
# Só `nr_grp` existe em todas as tabelas; `nr_instrumento` e `cd_uo` são
# resolvidos em GrpGoldInstrumento e aplicados como conjunto de nr_grp, para
# que o recorte visto em cada sub-aba seja exatamente o da aba Dados.
# ---------------------------------------------------------------------------


def _grp_filtrar_por_nr_grp(qs, filtros: dict):
    """Aplica os filtros do GRP a qualquer QuerySet que tenha o campo nr_grp.

    nr_instrumento e cd_uo só existem no instrumento: são resolvidos em
    GrpGoldInstrumento (mesma base da aba Dados) e aplicados como
    'nr_grp IN (subquery)'.
    """
    from .models import GrpGoldInstrumento

    qs = _filtrar_nr_grp_multiplo(qs, filtros.get("nr_grp", ""))

    dados = None
    if filtros.get("nr_instrumento"):
        dados = GrpGoldInstrumento.objects.filter(
            nr_instrumento__icontains=filtros["nr_instrumento"]
        )
    if filtros.get("cd_uo"):
        dados = (
            dados if dados is not None else GrpGoldInstrumento.objects.all()
        ).filter(cd_uo=filtros["cd_uo"])
    if dados is not None:
        qs = qs.filter(nr_grp__in=dados.values("nr_grp"))

    return qs


def get_grp_cronograma_qs(filtros: dict):
    """QuerySet[GrpCronogramaDesembolso] filtrado pelos filtros do GRP."""
    from .models import GrpCronogramaDesembolso

    qs = _grp_filtrar_por_nr_grp(GrpCronogramaDesembolso.objects.all(), filtros)
    return qs.order_by(
        "nr_grp", "nr_parcela", "nr_mes_desembolso", "nr_ano_desembolso", "ds_origem_recurso_parcela", "vl_desembolso"
    )

def get_grp_cronograma_fisico_qs(filtros: dict):
    """QuerySet[CronogramaFisicoGrp] filtrado pelos filtros do GRP."""
    from .models import GrpCronogramaFisico

    qs = _grp_filtrar_por_nr_grp(GrpCronogramaFisico.objects.all(), filtros)
    return qs.order_by(
        "nr_grp", "cd_proposta", "tp_meta_etapa", "tx_meta_especificacao", "dt_meta_inicio", "dt_meta_termino",
        "qt_meta_duracao", "vl_meta", "tx_etapa_especificacao", "dt_etapa_inicio", "dt_etapa_termino", "qt_etapa_duracao",
        "vl_etapa"
    )

def get_grp_emenda_qs(filtros: dict):
    """
    QuerySet[EmendaGrp] — sem filtro.

    GrpEmenda para instrumentos que são financiados por emendas parlamentares. 
    """
    from .models import GrpEmenda
    qs = _grp_filtrar_por_nr_grp(GrpEmenda.objects.all(), filtros)
    return qs.order_by("nr_grp", "cd_proposta", "nr_emenda", "nr_ano_emenda")

def get_municipios_atendidos_qs(filtros: dict):
    """
    QuerySet[MunicipiosAtendidosGrp] — sem filtro.

    MunicipiosAtendidosGrp para instrumentos que são financiados por emendas parlamentares. 
    """
    from .models import GrpMunicipioAtendido
    qs = _grp_filtrar_por_nr_grp(GrpMunicipioAtendido.objects.all(), filtros)
    return qs.order_by("nr_grp", "cd_proposta", "nm_municipio", "cd_municipio", "sg_uf")

def get_regioes_atendidas_qs(filtros: dict):
    """
    QuerySet[RegioesAtendidasGrp] — sem filtro.

    RegioesAtendidasGrp para instrumentos que são financiados por emendas parlamentares. 
    """
    from .models import GrpRegiaoAtendida
    qs = _grp_filtrar_por_nr_grp(GrpRegiaoAtendida.objects.all(), filtros)
    return qs.order_by("nr_grp", "cd_proposta", "nm_regiao", "cd_regiao", "ds_situacao_regiao", "nm_municipio_regiao",
                       "cd_municipio_regiao", "sg_uf_municipio_regiao")

def get_grp_prestacao_contas_qs(filtros: dict):
    """
    QuerySet[PrestacaoContasGrp] — sem filtro.

    PrestacaoContasGrp para instrumentos que são financiados por emendas parlamentares. 
    """
    from .models import GrpPrestacaoContas
    qs = _grp_filtrar_por_nr_grp(GrpPrestacaoContas.objects.all(), filtros)
    return qs.order_by("nr_grp", "cd_proposta", "fl_pc_obrigatoria", 
                        "tx_pc_justificativa_nao_obrigatoriedade", 
                        "qt_pc_prazo",
                        "dt_pc_limite",
                        "dt_pc_limite_inicial",
                        "tp_pc_final",
                        "dt_pc_envio",
                        "fl_conclusao_objeto",
                        "tx_pc_justificativa_conclusao",
                        "fl_pc_finalizada",
                        "fl_pendencia_contabilizacao", 
                        "dt_pc_finalizacao", 
                        "tx_pc_justificativa_aprovacao", 
                        "ds_pc_situacao_aprovacao")

def get_grp_instrumento_financiado_qs(filtros: dict):
    """
    QuerySet[InstrumentoFinanciadoGrp] — sem filtro.

    InstrumentoFinanciadoGrp para instrumentos que são financiados por emendas parlamentares. 
    """
    from .models import GrpInstrumentoFinanciado
    qs = _grp_filtrar_por_nr_grp(GrpInstrumentoFinanciado.objects.all(), filtros)
    return qs.order_by("nr_grp",
                "cd_proposta",
                "nr_instrumento_financiado",
                "tp_instrumento_financiado",
                "vl_instrumento_financiado")

def get_grp_unidades_administrativas_qs(filtros: dict):
    """
    QuerySet[UnidadeAdministrativaGrp] — sem filtro.

    UnidadeAdministrativaGrp para instrumentos que são financiados por emendas parlamentares. 
    """
    from .models import GrpUnidadeExecutora
    qs = _grp_filtrar_por_nr_grp(GrpUnidadeExecutora.objects.all(), filtros)
    return qs.order_by("nr_grp",
                "cd_proposta",
                "sg_orgao_unidade_adm",
                "cd_unidade_adm",
                "nm_unidade_adm")

# ---------------------------------------------------------------------------
# GRP — Plano de Aplicação (camada gold)
# Ordenação por "id" (gerado por ROW_NUMBER sobre o grão na view): é única,
# então a paginação não repete nem pula linhas.
# ---------------------------------------------------------------------------


def get_grp_gold_plano_itens_qs(filtros: dict):
    """QuerySet[GrpGoldPlanoAplicacao] — itens a executar."""
    from .models import GrpGoldPlanoAplicacao

    return _grp_filtrar_por_nr_grp(
        GrpGoldPlanoAplicacao.objects.all(), filtros
    ).order_by("id")


def get_grp_gold_recurso_concedente_qs(filtros: dict):
    """QuerySet[GrpGoldRecursoConcedente] — recursos do concedente."""
    from .models import GrpGoldRecursoConcedente

    return _grp_filtrar_por_nr_grp(
        GrpGoldRecursoConcedente.objects.all(), filtros
    ).order_by("id")


def get_grp_gold_recurso_contrapartida_qs(filtros: dict):
    """QuerySet[GrpGoldRecursoContrapartida] — contrapartida financeira."""
    from .models import GrpGoldRecursoContrapartida

    return _grp_filtrar_por_nr_grp(
        GrpGoldRecursoContrapartida.objects.all(), filtros
    ).order_by("id")


def get_grp_gold_acao_orcamentaria_qs(filtros: dict):
    """QuerySet[GrpGoldAcaoOrcamentaria] — ações orçamentárias de execução."""
    from .models import GrpGoldAcaoOrcamentaria

    return _grp_filtrar_por_nr_grp(
        GrpGoldAcaoOrcamentaria.objects.all(), filtros
    ).order_by("id")
