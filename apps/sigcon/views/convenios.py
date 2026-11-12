"""
Aba mestre das Consultas SIGCON: lista de convenios.

Mesmo desenho das views do GRP: `COLUNAS` (rótulo) e `CAMPOS` (atributo do
objeto) andam em paralelo — para trocar o que uma coluna mostra, mude o campo;
para trocar o título, mude a coluna. Tela e export usam as mesmas listas.
"""

from apps.sigcon.models import SigconConvenio, SigconPlanoTrabalho, SigconTermoAditivo
from apps.sigcon.services import (
    enrich_convenios_page,
    get_anos_disponiveis,
    get_sigcon_qs,
)
from core.gold.contrapartida import CATEGORIAS as CATEGORIAS_CONTRAPARTIDA

from ._filtros import ler_filtros_sigcon, sigcon_render

COLUNAS = [
    "Unidade Orçamentária",
    "Código SIGCON",
    "Código União",
    "Código Plano de Trabalho",
    "Código SIAFI",
    "SEI",
    "Instrumento",
    "Título",
    "Proponente",
    "Concedente",
    "Esfera Concedente",
    "Objeto",
    "Situação",
    "Tipo de Contrapartida",
    "Data de Assinatura",
    "Data de Publicação",
    "Início vigência",
    "Término vigência",
    "Valor proponente",
    "Valor concedente",
    "Valor total do Convênio",
    "Fim da vigência Inicial",
]

# Atributo de cada coluna, na mesma ordem. Os que não são campo de
# SigconConvenio são carimbados por `preparar` a partir de enrich_convenios_page.
CAMPOS = [
    "cd_uo",
    "nr_convenio",
    "cd_siconv",                      # fora do modelo SIGCON v1.0 (sempre "—")
    "cd_plano_trabalho",
    "nr_siafi",
    "nr_sei",                         # fora do modelo SIGCON v1.0 (sempre "—")
    "tp_instrumento",
    "nm_plano_trabalho",
    "nm_uo",             # troque aqui se passar a existir o NOME do proponente
    "nm_concedente",
    "ds_esfera",
    "tx_objeto",
    "ds_situacao_convenio",
    "ds_tipo_contrapartida",
    "dt_assinatura",
    "dt_publicacao",
    "dt_vigencia_inicio",
    "dt_vigencia_termino",
    "vl_convenio_proponente",
    "vl_convenio_concedente",
    "vl_convenio_total",
    "dt_vigencia_termino_inicial",
]

LARGURAS = [
    90, 150, 110, 120, 110, 90, 160, 280, 150, 240, 110,
    380, 150, 150, 110, 110, 110, 110, 150, 150, 160, 120,
]

# chave de enrich_convenios_page → atributo carimbado no convênio
_ENRIQUECIMENTO = {
    "codigo_siconv": "cd_siconv",
    "no_sei": "nr_sei",
    "plano_trabalho": "cd_plano_trabalho",
    "instrumento": "tp_instrumento",
    "titulo": "nm_plano_trabalho",
    "proponente": "nm_uo",
    "concedente": "nm_concedente",
    "esfera": "ds_esfera",
    "objeto": "tx_objeto",
    "tipo_contrapartida": "ds_tipo_contrapartida",
    "dt_assinatura": "dt_assinatura",
    "dt_publicacao": "dt_publicacao",
}


def preparar(convenios):
    """Carimba nos convênios os dados do plano, do geral e da contrapartida."""
    enriquecimento = enrich_convenios_page(convenios)
    for conv in convenios:
        extra = enriquecimento.get(conv.pk, {})
        for chave, atributo in _ENRIQUECIMENTO.items():
            setattr(conv, atributo, extra.get(chave))


def consulta(request):
    """QuerySet filtrado da aba — compartilhado por tela e export."""
    return get_sigcon_qs(ler_filtros_sigcon(request.GET)).order_by("nr_convenio", "pk")


def _listas():
    """Opções dos campos de filtro."""
    return {
        "anos": get_anos_disponiveis(),
        "situacoes": (
            SigconConvenio.objects.exclude(ds_situacao_convenio=None).exclude(ds_situacao_convenio="")
            .values_list("ds_situacao_convenio", flat=True).distinct().order_by("ds_situacao_convenio")
        ),
        "siafis": SigconConvenio.objects.values_list("nr_siafi", flat=True).distinct().order_by("nr_siafi"),
        "sigcons": SigconConvenio.objects.values_list("nr_convenio", flat=True).distinct().order_by("nr_convenio"),
        "instrumentos": (
            SigconPlanoTrabalho.objects.exclude(tp_instrumento_siafi=None)
            .values_list("tp_instrumento_siafi", flat=True).distinct().order_by("tp_instrumento_siafi")
        ),
        "termos_aditivo": (
            SigconTermoAditivo.objects.exclude(tp_termo_aditivo=None)
            .values_list("tp_termo_aditivo", flat=True).distinct().order_by("tp_termo_aditivo")
        ),
        "tipos_contrapartida": CATEGORIAS_CONTRAPARTIDA,
    }


def sigcon(request):
    filtros = ler_filtros_sigcon(request.GET)
    return sigcon_render(
        request,
        consulta(request),
        colunas=COLUNAS,
        campos=CAMPOS,
        titulo="Convênios",
        secao_sub="sigcon",
        larguras=LARGURAS,
        preparar=preparar,
        filtros_template="sigcon/_filtros_convenios.html",
        ano_sel=filtros["ano"],
        situacao_sel=filtros["situacao"],
        instrumento_sel=filtros["instrumento"],
        termo_aditivo_sel=filtros["termo_aditivo"],
        concedente_sel=filtros["concedente"],
        proponente_sel=filtros["proponente"],
        tipo_contrapartida_sel=filtros["tipo_contrapartida"],
        **_listas(),
    )
