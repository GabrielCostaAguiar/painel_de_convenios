"""
Rotas das Consultas SIGCON.

Incluidas na RAIZ em config/urls.py, e nao sob um prefixo /sigcon/: os
caminhos sao os mesmos de sempre (a lista de convenios e a home do painel).
O que mudou foi so o namespace dos nomes — `sigcon:plano_aplicacao` no lugar
de `dashboard:plano_aplicacao`.
"""

from django.urls import path

from . import views

app_name = "sigcon"

urlpatterns = [
    # Aba mestre — tambem a pagina inicial do painel
    path("",                                views.sigcon,                          name="sigcon"),
    path("export.csv",                      views.sigcon_export_csv,               name="sigcon_export_csv"),
    path("export.xlsx",                     views.sigcon_export_xlsx,              name="sigcon_export_xlsx"),

    path("plano_aplicacao/",                views.plano_aplicacao,                 name="plano_aplicacao"),
    path("plano_aplicacao/export.csv",      views.plano_aplicacao_export_csv,      name="plano_aplicacao_export_csv"),
    path("plano_aplicacao/export.xlsx",     views.plano_aplicacao_export_xlsx,     name="plano_aplicacao_export_xlsx"),

    path("cronograma/",                     views.cronograma,                      name="cronograma"),
    path("cronograma/export.csv",           views.cronograma_export_csv,           name="cronograma_export_csv"),
    path("cronograma/export.xlsx",          views.cronograma_export_xlsx,          name="cronograma_export_xlsx"),

    path("prorrogacao/",                    views.prorrogacao,                     name="prorrogacao"),
    path("prorrogacao/export.csv",          views.prorrogacao_export_csv,          name="prorrogacao_export_csv"),
    path("prorrogacao/export.xlsx",         views.prorrogacao_export_xlsx,         name="prorrogacao_export_xlsx"),

    path("termo_aditivo/",                  views.termo_aditivo,                   name="termo_aditivo"),
    path("termo_aditivo/export.csv",        views.termo_aditivo_export_csv,        name="termo_aditivo_export_csv"),
    path("termo_aditivo/export.xlsx",       views.termo_aditivo_export_xlsx,       name="termo_aditivo_export_xlsx"),

    path("unidades_executoras/",            views.unidades_executoras,             name="unidades_executoras"),
    path("unidades_executoras/export.csv",  views.unidades_executoras_export_csv,  name="unidades_executoras_export_csv"),
    path("unidades_executoras/export.xlsx", views.unidades_executoras_export_xlsx, name="unidades_executoras_export_xlsx"),
]
