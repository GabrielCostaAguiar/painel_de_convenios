from django.contrib import admin

from .models import SigconConvenio


@admin.register(SigconConvenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = [
        "nr_convenio",
        "ds_situacao_convenio",
        "dt_vigencia_inicio",
        "dt_vigencia_termino",
        "vl_convenio_total",
    ]
    list_filter = ["ds_situacao_convenio"]
    search_fields = ["nr_convenio", "nr_siafi", "siafi_uo"]
    ordering = ["-dt_vigencia_inicio"]
    date_hierarchy = "dt_vigencia_inicio"

    fieldsets = (
        ("Identificação", {
            "fields": (
                "nr_convenio",
                "nr_siafi",
                "cd_uo",
                "siafi_uo",
            ),
        }),
        ("Situação e Datas", {
            "fields": (
                "ds_situacao_convenio",
                "dt_vigencia_inicio",
                "dt_vigencia_termino_inicial",
                "dt_vigencia_termino",
            ),
        }),
        ("Financeiro — Concedente", {
            "fields": (
                "vl_convenio_concedente_inicial",
                "vl_convenio_concedente_aditado",
                "vl_convenio_concedente",
            ),
        }),
        ("Financeiro — Proponente", {
            "fields": (
                "vl_convenio_proponente_inicial",
                "vl_convenio_proponente_aditado",
                "vl_convenio_proponente",
            ),
        }),
        ("Financeiro — Total", {
            "fields": ("vl_convenio_total",),
        }),
    )


# @admin.register(ConvenioIntegrado)
# class ConvenioIntegradoAdmin(admin.ModelAdmin):
#     list_display = [
#         "siafi_uo",
#         "siafi_uo_atual",
#         "g_situacao_convenio_categorizado",
#         "g_vigencia",
#         "g_valor_global",
#         "g_ano_convenio",
#         "g_proponente_pad",
#     ]
#     list_filter = [
#         "g_vigencia",
#         "g_situacao_convenio_categorizado",
#         "g_esfera",
#         "g_instrumento",
#     ]
#     search_fields = [
#         "siafi_uo",
#         "siafi_uo_atual",
#         "codigo_siconv",
#         "g_proponente",
#         "g_concedente",
#         "convenio_numero_sequencial_siafi",
#     ]
#     ordering = ["-g_fim_vigencia"]
#     readonly_fields = ["atualizado_em"]
#     date_hierarchy = "g_fim_vigencia"

#     fieldsets = (
#         ("Chaves", {
#             "fields": (
#                 "siafi_uo",
#                 "siafi_uo_atual",
#                 "convenio_numero_sequencial_siafi",
#                 "unidade_orcamentaria_codigo",
#                 "siafiatual",
#                 "uo_atual",
#                 "codigo_siconv",
#             ),
#         }),
#         ("De-Paras / Chaves Meta", {
#             "fields": (
#                 "instrumento_chaves",
#                 "situacao",
#                 "situacao_std",
#                 "uo_nome_std",
#                 "uo_sigla_std",
#                 "uo_descricao_std",
#             ),
#             "classes": ("collapse",),
#         }),
#         ("G_ — Campos Integrados", {
#             "fields": (
#                 "g_situacao_convenio",
#                 "g_situacao_convenio_categorizado",
#                 "g_vigencia",
#                 "g_instrumento",
#                 "g_esfera",
#                 "g_dia_assinatura",
#                 "g_ano_assinatura",
#                 "g_inicio_vigencia",
#                 "g_ano_inicio_vigencia",
#                 "g_fim_vigencia",
#                 "g_fim_vigencia_inicial",
#                 "g_ano_convenio",
#                 "g_objeto_convenio",
#                 "g_proponente",
#                 "g_proponente_pad",
#                 "g_proponente_pad_siglas",
#                 "g_concedente",
#                 "g_concedente_pad",
#                 "g_uo",
#                 "g_uo_descricao",
#                 "g_valor_concedente",
#                 "g_valor_proponente",
#                 "g_valor_global",
#                 "g_periodo_nao_aditado",
#                 "g_valor_nao_aditado",
#                 "limpeza_g",
#             ),
#         }),
#         ("A_ — Campos Projetados (SIAFI Atual)", {
#             "fields": (
#                 "a_situacao_convenio",
#                 "a_situacao_convenio_categorizado",
#                 "a_vigencia",
#                 "a_instrumento",
#                 "a_esfera",
#                 "a_dia_assinatura",
#                 "a_ano_assinatura",
#                 "a_inicio_vigencia",
#                 "a_ano_inicio_vigencia",
#                 "a_fim_vigencia",
#                 "a_fim_vigencia_inicial",
#                 "a_ano_convenio",
#                 "a_objeto_convenio",
#                 "a_proponente",
#                 "a_proponente_pad",
#                 "a_proponente_pad_siglas",
#                 "a_concedente",
#                 "a_concedente_pad",
#                 "a_valor_concedente",
#                 "a_valor_proponente",
#                 "a_valor_global",
#                 "a_periodo_nao_aditado",
#                 "a_valor_nao_aditado",
#             ),
#             "classes": ("collapse",),
#         }),
#         ("Controle", {
#             "fields": ("atualizado_em",),
#             "classes": ("collapse",),
#         }),
#     )
