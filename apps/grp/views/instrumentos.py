from django.core.paginator import Paginator
from django.shortcuts import render

from core.web import formatar_celula, paginas_visiveis
from ._filtros import (
    _grp_contexto_pagina,
    _grp_exportar,
    _grp_selecionados,
    _grp_listas,
    _ler_filtros_grp,
)

from apps.grp.services import get_grp_dados_qs

# ---------------------------------------------------------------------------
# GRP — aba teste: lista de instrumentos
# ---------------------------------------------------------------------------


def grp_instrumentos(request):
    filtros = _ler_filtros_grp(request.GET)
    qs = get_grp_dados_qs(filtros)

    # monta as linhas da tabela
    colunas = [
        "Origem do Instrumento",
        "UO",
        "Nº GRP",
        "Tipo do Instrumento",
        "Nº Instrumento",
        "Nº União",
        "Nome do Projeto",
        "Objeto",
        "Convenente",
        "Concedente",
        "Esfera",
        "Situação",
        "Status do Instrumento",
        "Data de assinatura",
        "Data de publicação",
        "Inicio de vigência",
        "Término de vigência",
        "Rendimento (R$)",
        "Valor concedente (R$)",
        "Valor contrapartida (R$)",
        "Valor contrapartida não financeira (R$)",
        "Valor Total (R$)",
        "Término de vigência inicial",
    ]
    campos = [
        "ds_origem_instrumento",
        "cd_uo",
        "nr_grp",
        "ds_tipo_instrumento_juridico",
        "nr_instrumento",
        "nr_instrumento_transferegov",
        "nm_projeto",
        "tx_objeto_projeto",
        "nm_convenente",
        "nm_concedente",
        "ds_esfera_atuacao",
        "ds_situacao_instrumento",
        "ds_status_instrumento",
        "dt_assinatura",
        "dt_publicacao",
        "dt_vigencia_inicio",
        "dt_vigencia_termino",
        "vl_rendimento_autorizado",
        "vl_instrumento_concedente",
        "vl_instrumento_contrapartida_fin",
        "vl_instrumento_contrapartida_nao_fin",
        "vl_instrumento_total",
        "dt_vigencia_termino_inicial",
    ]
    download = _grp_exportar(request, qs, colunas, campos, "grp_dados")
    if download is not None:
        return download

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    linhas = [
        [formatar_celula(c, getattr(obj, c)) for c in campos] for obj in page_obj
    ]

    larguras = [
        150,
        90,
        90,
        150,
        170,
        100,
        280,
        450,
        220,
        220,
        100,
        90,
        210,
        120,
        120,
        120,
        120,
        140,
        140,
        160,
        180,
        140,
        150,
    ]

    contexto = {
        "titulo": "Dados gerais",
        "page_obj": page_obj,
        "total": paginator.count,
        "colunas": colunas,
        "linhas": linhas,
        "larguras": larguras,
        "largura_total": sum(larguras),
        **_grp_selecionados(filtros),
        **_grp_contexto_pagina(request, qs, colunas, campos),
        "visible_pages": paginas_visiveis(page_obj),
        "secao_ativa": "grp",
        "secao_sub": "grp_dados",
    }
    contexto.update(_grp_listas())
    return render(request, "grp/grp_generico.html", contexto)
