from django.contrib import admin

from .models import Convenio


@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = [
        "nr_convenio",
        "convenente",
        "concedente",
        "situacao",
        "valor_global",
        "data_inicio",
        "data_termino",
    ]
    list_filter = ["situacao", "concedente"]
    search_fields = ["nr_convenio", "nr_processo", "objeto", "convenente", "concedente"]
    ordering = ["-data_inicio"]
    readonly_fields = ["atualizado_em"]
    date_hierarchy = "data_inicio"

    fieldsets = (
        ("Identificação", {
            "fields": ("nr_convenio", "nr_processo", "objeto"),
        }),
        ("Partes", {
            "fields": ("concedente", "convenente"),
        }),
        ("Situação e Datas", {
            "fields": ("situacao", "data_inicio", "data_termino"),
        }),
        ("Financeiro", {
            "fields": ("valor_global",),
        }),
        ("Controle", {
            "fields": ("atualizado_em",),
            "classes": ("collapse",),
        }),
    )
