"""
Filtros e montagem das telas SIGCON — mesmo desenho das views do GRP.

Cada sub-aba declara só `colunas` (rótulo), `campos` (atributo do objeto, na
mesma ordem) e `larguras`; `sigcon_render` monta a tabela, e `sigcon_exportar`
gera CSV/XLSX com os MESMOS campos. Para trocar o que uma coluna mostra, mude o
nome em `campos`; para trocar o título, mude em `colunas`.

O formato da célula sai do prefixo do campo (igual ao GRP): vl_ → valor,
dt_ → data, fl_ → Sim/Não.
"""

import csv
import logging

from django.core.paginator import Paginator
from django.shortcuts import render
from django.urls import reverse

from apps.sigcon.services import SPEC_FILTROS, get_opcoes_filtros
from core.web import (
    calcular_totais,
    cards_totais,
    exportar_xlsx,
    filtros_ativos,
    formatar_celula,
    ler_filtros,
    paginas_visiveis,
    resposta_csv,
)

logger = logging.getLogger(__name__)


def ler_filtros_sigcon(get_params):
    """
    Filtros da tela, lidos da querystring.

    Usado pela tela e pelo export correspondente — e por isso que ele vive num
    modulo proprio, e nao dentro da view: os dois precisam ler exatamente os
    mesmos parametros, senao o arquivo baixado nao bate com o que esta em tela.
    """
    return ler_filtros(get_params, SPEC_FILTROS)


# ---------------------------------------------------------------------------
# Tela
# ---------------------------------------------------------------------------

def sigcon_render(
    request,
    qs,
    colunas,
    campos,
    titulo,
    secao_sub,
    larguras=None,
    **kwargs,
):
    """
    Pagina `qs` e renderiza sigcon/sigcon_generico.html, com os mesmos filtros
    em todas as sub-abas.

    secao_sub — também é o prefixo das rotas de export: sigcon:<secao_sub>_export_xlsx.
    """
    if len(campos) != len(colunas):
        raise ValueError(f"'{secao_sub}': {len(campos)} campos para {len(colunas)} colunas")
    if larguras is not None and len(larguras) != len(colunas):
        logger.warning(
            "larguras (%d) != colunas (%d) na sub-aba '%s'", len(larguras), len(colunas), secao_sub,
        )
        larguras = None

    # totais sobre TODO o queryset filtrado, antes do Paginator
    totais = calcular_totais(qs, campos)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    objetos = list(page_obj.object_list)
    linhas = [[formatar_celula(c, getattr(obj, c, None)) for c in campos] for obj in objetos]

    params = request.GET.copy()
    params.pop("page", None)
    filtros = ler_filtros_sigcon(request.GET)
    contexto = {
        "titulo": titulo,
        "colunas": colunas,
        "linhas": linhas,
        "larguras": larguras,
        "largura_total": sum(larguras) if larguras else None,
        "colunas_numericas": [i for i, c in enumerate(campos) if c.startswith("vl_")],
        "totais": totais,
        "totais_cards": cards_totais(totais, colunas, campos),
        "filtros_ativos": filtros_ativos(request.GET),
        "page_obj": page_obj,
        "total": paginator.count,
        "querystring": params.urlencode(),
        "visible_pages": paginas_visiveis(page_obj),
        "f": filtros,
        "url_limpar": request.path,
        **get_opcoes_filtros(),
        "url_export_xlsx": reverse(f"sigcon:{secao_sub}_export_xlsx"),
        "url_export_csv": reverse(f"sigcon:{secao_sub}_export_csv"),
        "secao_ativa": "sigcon",
        "secao_sub": secao_sub,
    }
    contexto.update(kwargs)
    return render(request, "sigcon/sigcon_generico.html", contexto)


# ---------------------------------------------------------------------------
# Export (mesmos campos da tela, valores crus)
# ---------------------------------------------------------------------------

def sigcon_exportar(objetos, colunas, campos, nome, formato):
    """
    Gera o arquivo da sub-aba. CSV: data em ISO e valor puro; XLSX: tipos nativos
    (data e número), para o Excel poder ordenar e somar.
    """
    objetos = list(objetos)

    if formato == "xlsx":
        linhas = [[getattr(o, c, None) for c in campos] for o in objetos]
        return exportar_xlsx(linhas, colunas, nome)

    response = resposta_csv(nome)
    writer = csv.writer(response, delimiter=";")
    writer.writerow(colunas)
    for obj in objetos:
        writer.writerow([
            "" if v is None else (v.isoformat() if hasattr(v, "isoformat") else v)
            for v in (getattr(obj, c, None) for c in campos)
        ])
    return response
