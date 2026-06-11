from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # Página inicial — Consultas SIGCON: aba mestre
    path("",                        views.sigcon,               name="sigcon"),

    # Painel
    path("indicadores/",            views.indicadores,          name="indicadores"),
    path("graficos/",               views.graficos,             name="graficos"),

    # Sub-tabs de Consultas SIGCON
    path("plano_aplicacao/",        views.plano_aplicacao,      name="plano_aplicacao"),
    path("cronograma/",             views.cronograma,           name="cronograma"),
    path("prorrogacao/",            views.prorrogacao,          name="prorrogacao"),
    path("termo_aditivo/",          views.termo_aditivo,        name="termo_aditivo"),
    path("unidades_executoras/",    views.unidades_executoras,  name="unidades_executoras"),

    # Consultas
    path("uniao/",                  views.uniao,                name="uniao"),
    path("execucao/",               views.execucao,             name="execucao"),

    # Acompanhamento
    path("monitoramento/",          views.monitoramento,        name="monitoramento"),
    path("relatorio/",              views.relatorio,            name="relatorio"),
    path("alertas/",                views.alertas,              name="alertas"),
    path("emendas/",                views.emendas,              name="emendas"),
]
