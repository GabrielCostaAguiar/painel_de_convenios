"""
Views de export CSV/XLSX das abas de Consultas SIGCON.

Cada export repete os filtros da tela correspondente em sigcon.py, para que
o arquivo baixado tenha exatamente as linhas que o usuário está vendo.

Atenção: core.export.xlsx não pode importar pandas/numpy (erro de OpenBLAS com
múltiplos workers em produção) — não introduza esse import neste caminho.
"""

import csv

from django.http import HttpResponse

from apps.dashboard.services import (
    enrich_convenios_page,
    get_cronograma_qs,
    get_plano_aplicacao_qs,
    get_prorrogacao_qs,
    get_sigcon_qs,
    get_termos_aditivos_qs,
    get_unidades_executoras_qs,
)
from core.export.xlsx import exportar_xlsx

from ._helpers import _ler_filtros_sigcon


def sigcon_export_csv(request):
    """Exporta para CSV os Convenio que respeitam os mesmos filtros da tela."""
    filtros = _ler_filtros_sigcon(request.GET)
    qs = get_sigcon_qs(filtros).order_by("convenio_codigo")

    items = list(qs)
    enrichment = enrich_convenios_page(items)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="convenios.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Unidade Orçamentária", "Código SIGCON", "Código União", "Código Plano de Trabalho",
        "Código SIAFI", "SEI", "Instrumento", "Título", "Proponente", "Concedente",
        "Esfera Concedente", "Objeto", "Situação", "Tipo de Contrapartida",
        "Data de Assinatura", "Data de Publicação", "Início vigência", "Término vigência",
        "Valor proponente", "Valor concedente", "Valor total do Convênio",
        "Fim da vigência Inicial",
    ])
    for conv in items:
        extra = enrichment.get(conv.pk, {})
        writer.writerow([
            conv.unidade_orcamentaria_codigo or "",
            conv.convenio_codigo,
            extra.get("codigo_siconv", "—"),
            conv.plano_trabalho_codigo or "",
            conv.convenio_numero_sequencial_siafi or "",
            extra.get("no_sei", "—"),
            conv.instrumento or "",
            conv.titulo or "",
            extra.get("proponente", "—"),
            conv.concedente or "",
            conv.esfera or "",
            conv.objeto or "",
            conv.situacao or "",
            extra.get("tipo_contrapartida", "—"),
            conv.data_assinatura.isoformat() if conv.data_assinatura else "",
            conv.data_publicacao.isoformat() if conv.data_publicacao else "",
            conv.data_inicio_vigencia.isoformat() if conv.data_inicio_vigencia else "",
            conv.data_termino_vigencia.isoformat() if conv.data_termino_vigencia else "",
            conv.valor_proponente if conv.valor_proponente is not None else "",
            conv.valor_concedente if conv.valor_concedente is not None else "",
            conv.valor_total_convenio if conv.valor_total_convenio is not None else "",
            extra.get("fim_vigencia_inicial") or "",
        ])

    return response

_COLUNAS_SIGCON_XLSX = [
    "Unidade Orçamentária", "Código SIGCON", "Código União", "Código Plano de Trabalho",
    "Código SIAFI", "SEI", "Instrumento", "Título", "Proponente", "Concedente",
    "Esfera Concedente", "Objeto", "Situação", "Tipo de Contrapartida",
    "Data de Assinatura", "Data de Publicação", "Início vigência", "Término vigência",
    "Valor proponente", "Valor concedente", "Valor total do Convênio",
    "Fim da vigência Inicial",
]

def sigcon_export_xlsx(request):
    """Exporta para XLSX os Convenio que respeitam os mesmos filtros e ordem da tela."""
    filtros = _ler_filtros_sigcon(request.GET)
    items = list(get_sigcon_qs(filtros))
    enrichment = enrich_convenios_page(items)

    linhas = [
        [
            conv.unidade_orcamentaria_codigo or "",
            conv.convenio_codigo,
            enrichment.get(conv.pk, {}).get("codigo_siconv", "—"),
            conv.plano_trabalho_codigo or "",
            conv.convenio_numero_sequencial_siafi or "",
            enrichment.get(conv.pk, {}).get("no_sei", "—"),
            conv.instrumento or "",
            conv.titulo or "",
            enrichment.get(conv.pk, {}).get("proponente", "—"),
            conv.concedente or "",
            conv.esfera or "",
            conv.objeto or "",
            conv.situacao or "",
            enrichment.get(conv.pk, {}).get("tipo_contrapartida", "—"),
            conv.data_assinatura,
            conv.data_publicacao,
            conv.data_inicio_vigencia,
            conv.data_termino_vigencia,
            conv.valor_proponente,
            conv.valor_concedente,
            conv.valor_total_convenio,
            enrichment.get(conv.pk, {}).get("fim_vigencia_inicial"),
        ]
        for conv in items
    ]
    return exportar_xlsx(linhas, _COLUNAS_SIGCON_XLSX, "convenios")

def plano_aplicacao_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Plano de Aplicação."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_plano_aplicacao_qs(cod_sigcon or None, cod_siafi or None)

    siafi_sel = ctx.get("siafi", "")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="plano_aplicacao.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Ano Exercício",
        "Dotação Orçamentária", "UO", "Identificador Orçamento", "Função", "Ação",
        "Categ. Econôm. Despesa", "Grupo", "Modalidade Aplicação", "Fonte", "Fonte nova",
        "Procedência", "Elemento Despesa", "Valor Concedente R$", "Valor Proponente R$",
    ])
    for pa in qs:
        writer.writerow([
            siafi_sel,
            pa.convenio_codigo or "",
            pa.codigo_plano_trabalho or "",
            pa.ano_exercicio_programa_trabalho or "",
            pa.funcional_programatica_formatado or "",
            pa.codigo_unidade_orcamentaria or "",
            pa.identificador_orcamento_codigo or "",
            pa.funcao_codigo or "",
            pa.identificador_projeto_atividade_codigo or "",
            pa.categoria_economica_despesa_codigo or "",
            pa.grupo_despesa_codigo or "",
            pa.modalidade_aplicacao_codigo or "",
            pa.fonte_recurso_codigo or "",
            "— sem fonte —",
            pa.procedencia_codigo or "",
            pa.elemento_despesa_codigo or "",
            pa.valor_concedente if pa.valor_concedente is not None else "",
            pa.valor_proponente if pa.valor_proponente is not None else "",
        ])

    return response

def plano_aplicacao_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Plano de Aplicação."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_plano_aplicacao_qs(cod_sigcon or None, cod_siafi or None)

    siafi_sel = ctx.get("siafi", "")
    colunas = [
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Ano Exercício",
        "Dotação Orçamentária", "UO", "Identificador Orçamento", "Função", "Ação",
        "Categ. Econôm. Despesa", "Grupo", "Modalidade Aplicação", "Fonte", "Fonte nova",
        "Procedência", "Elemento Despesa", "Valor Concedente R$", "Valor Proponente R$",
    ]
    linhas = [
        [
            siafi_sel,
            pa.convenio_codigo or "",
            pa.codigo_plano_trabalho or "",
            pa.ano_exercicio_programa_trabalho or "",
            pa.funcional_programatica_formatado or "",
            pa.codigo_unidade_orcamentaria or "",
            pa.identificador_orcamento_codigo or "",
            pa.funcao_codigo or "",
            pa.identificador_projeto_atividade_codigo or "",
            pa.categoria_economica_despesa_codigo or "",
            pa.grupo_despesa_codigo or "",
            pa.modalidade_aplicacao_codigo or "",
            pa.fonte_recurso_codigo or "",
            "— sem fonte —",
            pa.procedencia_codigo or "",
            pa.elemento_despesa_codigo or "",
            pa.valor_concedente,
            pa.valor_proponente,
        ]
        for pa in qs
    ]
    return exportar_xlsx(linhas, colunas, "plano_aplicacao")

def cronograma_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Cronograma de Desembolso."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    plano      = request.GET.get("plano", "")

    qs, _ = get_cronograma_qs(
        cod_sigcon=cod_sigcon or None,
        cod_siafi=cod_siafi or None,
        plano=plano or None,
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="cronograma_desembolso.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Mês", "Ano",
        "Valor Concedente R$", "Valor Proponente R$",
    ])
    for item in qs:
        writer.writerow([
            item.convenio_numero_sequencial_siafi or "",
            item.convenio_codigo or "",
            item.plano_trabalho_codigo or "",
            item.mes_cronograma_desembolso or "",
            item.ano_cronograma_desembolso or "",
            item.valor_concedente_cronograma_desembolso if item.valor_concedente_cronograma_desembolso is not None else "",
            item.valor_proponente_cronograma_desembolso if item.valor_proponente_cronograma_desembolso is not None else "",
        ])

    return response

def cronograma_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Cronograma de Desembolso."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    plano      = request.GET.get("plano", "")

    qs, _ = get_cronograma_qs(
        cod_sigcon=cod_sigcon or None,
        cod_siafi=cod_siafi or None,
        plano=plano or None,
    )

    colunas = [
        "Código SIAFI", "Código SIGCON", "Código Plano de Trabalho", "Mês", "Ano",
        "Valor Concedente R$", "Valor Proponente R$",
    ]
    linhas = [
        [
            item.convenio_numero_sequencial_siafi or "",
            item.convenio_codigo or "",
            item.plano_trabalho_codigo or "",
            item.mes_cronograma_desembolso or "",
            item.ano_cronograma_desembolso or "",
            item.valor_concedente_cronograma_desembolso,
            item.valor_proponente_cronograma_desembolso,
        ]
        for item in qs
    ]
    return exportar_xlsx(linhas, colunas, "cronograma_desembolso")

def prorrogacao_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Prorrogação de Ofício."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_prorrogacao_qs(cod_sigcon or None, cod_siafi or None)

    plano_sel = ctx.get("plano_trabalho_codigo", "")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="prorrogacao_oficio.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIGCON", "Código Plano de Trabalho", "Código Prorrogação de Ofício",
        "Data de Publicação", "Data Vigência Prorrogada",
    ])
    for po in qs:
        writer.writerow([
            po.prorrogacao_oficio_codigo_convenio or "",
            plano_sel,
            po.prorrogacao_oficio_codigo or "",
            po.prorrogacao_oficio_data_publicacao.isoformat() if po.prorrogacao_oficio_data_publicacao else "",
            po.prorrogacao_oficio_data_termino_vigencia.isoformat() if po.prorrogacao_oficio_data_termino_vigencia else "",
        ])

    return response

def prorrogacao_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Prorrogação de Ofício."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_prorrogacao_qs(cod_sigcon or None, cod_siafi or None)

    plano_sel = ctx.get("plano_trabalho_codigo", "")
    colunas = [
        "Código SIGCON", "Código Plano de Trabalho", "Código Prorrogação de Ofício",
        "Data de Publicação", "Data Vigência Prorrogada",
    ]
    linhas = [
        [
            po.prorrogacao_oficio_codigo_convenio or "",
            plano_sel,
            po.prorrogacao_oficio_codigo or "",
            po.prorrogacao_oficio_data_publicacao,
            po.prorrogacao_oficio_data_termino_vigencia,
        ]
        for po in qs
    ]
    return exportar_xlsx(linhas, colunas, "prorrogacao_oficio")

def termo_aditivo_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Termo Aditivo."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_termos_aditivos_qs(cod_sigcon or None, cod_siafi or None)
    ta_pt_map = ctx.get("ta_pt_map", {})

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="termo_aditivo.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Código SIGCON", "Código Plano de Trabalho", "Nº Termo Aditivo", "Tipo",
        "Data Assinatura", "Data Término Vigência", "Justificativa",
        "Valor Aditado Concedente R$", "Valor Aditado Proponente R$",
    ])
    for ta in qs:
        writer.writerow([
            cod_sigcon,
            ta_pt_map.get(ta.termo_aditivo_codigo_sequencial, "—"),
            ta.termo_aditivo_numero_termo_aditivo or "",
            ta.termo_aditivo_tipo or ta.tipo_termo_aditivo or "",
            ta.termo_aditivo_data_assinatura.isoformat() if ta.termo_aditivo_data_assinatura else "",
            ta.termo_aditivo_data_termino_vigencia.isoformat() if ta.termo_aditivo_data_termino_vigencia else "",
            ta.termo_aditivo_justificativa or "",
            ta.valor_aditado_concedente_contratado if ta.valor_aditado_concedente_contratado is not None else "",
            ta.valor_aditado_proponente_contratado if ta.valor_aditado_proponente_contratado is not None else "",
        ])

    return response

def termo_aditivo_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Termo Aditivo."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, ctx = get_termos_aditivos_qs(cod_sigcon or None, cod_siafi or None)
    ta_pt_map = ctx.get("ta_pt_map", {})

    colunas = [
        "Código SIGCON", "Código Plano de Trabalho", "Nº Termo Aditivo", "Tipo",
        "Data Assinatura", "Data Término Vigência", "Justificativa",
        "Valor Aditado Concedente R$", "Valor Aditado Proponente R$",
    ]
    linhas = [
        [
            cod_sigcon,
            ta_pt_map.get(ta.termo_aditivo_codigo_sequencial, "—"),
            ta.termo_aditivo_numero_termo_aditivo or "",
            ta.termo_aditivo_tipo or ta.tipo_termo_aditivo or "",
            ta.termo_aditivo_data_assinatura,
            ta.termo_aditivo_data_termino_vigencia,
            ta.termo_aditivo_justificativa or "",
            ta.valor_aditado_concedente_contratado,
            ta.valor_aditado_proponente_contratado,
        ]
        for ta in qs
    ]
    return exportar_xlsx(linhas, colunas, "termo_aditivo")

def unidades_executoras_export_csv(request):
    """Exporta para CSV os mesmos registros e colunas exibidos na aba Unidades Executoras."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, _ = get_unidades_executoras_qs(cod_sigcon or None, cod_siafi or None)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="unidades_executoras.csv"'
    response.write("﻿")  # BOM — Excel abre UTF-8 corretamente

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Código SIGCON", "Código SIAFI", "Cód. UO", "Unidade Executora"])
    for ue in qs:
        writer.writerow([
            ue.convenio_codigo or "",
            ue.convenio_numero_sequencial_siafi or "",
            ue.unidade_orcamentaria_codigo or "",
            ue.unidade_executora or "",
        ])

    return response

def unidades_executoras_export_xlsx(request):
    """Exporta para XLSX os mesmos registros e colunas exibidos na aba Unidades Executoras."""
    cod_sigcon = request.GET.get("cod_sigcon", "")
    cod_siafi  = request.GET.get("cod_siafi", "")
    qs, _ = get_unidades_executoras_qs(cod_sigcon or None, cod_siafi or None)

    colunas = ["Código SIGCON", "Código SIAFI", "Cód. UO", "Unidade Executora"]
    linhas = [
        [
            ue.convenio_codigo or "",
            ue.convenio_numero_sequencial_siafi or "",
            ue.unidade_orcamentaria_codigo or "",
            ue.unidade_executora or "",
        ]
        for ue in qs
    ]
    return exportar_xlsx(linhas, colunas, "unidades_executoras")
