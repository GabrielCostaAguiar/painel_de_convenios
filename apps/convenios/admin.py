from django.contrib import admin

from .models import Convenio, ConvenioIntegrado


@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = [
        "convenio_codigo",
        "situacao",
        "data_inicio_vigencia",
        "data_termino_vigencia",
        "valor_total_convenio",
    ]
    list_filter = ["situacao"]
    search_fields = ["convenio_codigo", "convenio_numero_sequencial_siafi"]
    ordering = ["-data_inicio_vigencia"]
    readonly_fields = ["atualizado_em"]
    date_hierarchy = "data_inicio_vigencia"

    fieldsets = (
        ("Identificação", {
            "fields": (
                "convenio_codigo",
                "convenio_numero_sequencial_siafi",
                "unidade_orcamentaria_codigo",
            ),
        }),
        ("Situação e Datas", {
            "fields": (
                "situacao",
                "data_inicio_vigencia",
                "data_termino_vigencia",
                "data_real_convenio",
            ),
        }),
        ("Financeiro — Concedente", {
            "fields": (
                "valor_inicial_concedente_contratado",
                "valor_total_aditado_concedente_contratado",
                "valor_concedente",
            ),
        }),
        ("Financeiro — Proponente", {
            "fields": (
                "valor_inicial_proponente_contratado",
                "valor_total_aditado_proponente_contratado",
                "valor_proponente",
            ),
        }),
        ("Financeiro — Total", {
            "fields": ("valor_total_convenio",),
        }),
        ("Controle", {
            "fields": ("atualizado_em",),
            "classes": ("collapse",),
        }),
    )


@admin.register(ConvenioIntegrado)
class ConvenioIntegradoAdmin(admin.ModelAdmin):
    list_display = [
        "siafi_uo",
        "siafi_uo_atual",
        "g_situacao_convenio_categorizado",
        "g_vigencia",
        "g_valor_global",
        "g_ano_convenio",
        "g_proponente_pad",
    ]
    list_filter = [
        "g_vigencia",
        "g_situacao_convenio_categorizado",
        "g_esfera",
        "g_instrumento",
    ]
    search_fields = [
        "siafi_uo",
        "siafi_uo_atual",
        "codigo_siconv",
        "g_proponente",
        "g_concedente",
        "convenio_numero_sequencial_siafi",
    ]
    ordering = ["-g_fim_vigencia"]
    readonly_fields = ["atualizado_em"]
    date_hierarchy = "g_fim_vigencia"

    fieldsets = (
        ("Chaves", {
            "fields": (
                "siafi_uo",
                "siafi_uo_atual",
                "convenio_numero_sequencial_siafi",
                "unidade_orcamentaria_codigo",
                "siafiatual",
                "uo_atual",
                "codigo_siconv",
            ),
        }),
        ("De-Paras / Chaves Meta", {
            "fields": (
                "instrumento_chaves",
                "situacao",
                "situacao_std",
                "uo_nome_std",
                "uo_sigla_std",
                "uo_descricao_std",
            ),
            "classes": ("collapse",),
        }),
        ("G_ — Campos Integrados", {
            "fields": (
                "g_situacao_convenio",
                "g_situacao_convenio_categorizado",
                "g_vigencia",
                "g_instrumento",
                "g_esfera",
                "g_dia_assinatura",
                "g_ano_assinatura",
                "g_inicio_vigencia",
                "g_ano_inicio_vigencia",
                "g_fim_vigencia",
                "g_fim_vigencia_inicial",
                "g_ano_convenio",
                "g_objeto_convenio",
                "g_proponente",
                "g_proponente_pad",
                "g_proponente_pad_siglas",
                "g_concedente",
                "g_concedente_pad",
                "g_uo",
                "g_uo_descricao",
                "g_valor_concedente",
                "g_valor_proponente",
                "g_valor_global",
                "g_periodo_nao_aditado",
                "g_valor_nao_aditado",
                "limpeza_g",
            ),
        }),
        ("A_ — Campos Projetados (SIAFI Atual)", {
            "fields": (
                "a_situacao_convenio",
                "a_situacao_convenio_categorizado",
                "a_vigencia",
                "a_instrumento",
                "a_esfera",
                "a_dia_assinatura",
                "a_ano_assinatura",
                "a_inicio_vigencia",
                "a_ano_inicio_vigencia",
                "a_fim_vigencia",
                "a_fim_vigencia_inicial",
                "a_ano_convenio",
                "a_objeto_convenio",
                "a_proponente",
                "a_proponente_pad",
                "a_proponente_pad_siglas",
                "a_concedente",
                "a_concedente_pad",
                "a_valor_concedente",
                "a_valor_proponente",
                "a_valor_global",
                "a_periodo_nao_aditado",
                "a_valor_nao_aditado",
            ),
            "classes": ("collapse",),
        }),
        ("Controle", {
            "fields": ("atualizado_em",),
            "classes": ("collapse",),
        }),
    )
