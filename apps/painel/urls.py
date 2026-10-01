"""
Rotas da casca do painel: indicadores, graficos e telas de Acompanhamento.

As rotas de cada aba ficam no app da aba (apps.sigcon.urls, apps.grp.urls, ...)
e sao incluidas em config/urls.py.
"""

from django.urls import path

from . import views

app_name = "painel"

urlpatterns = [
    # Painel
    path("indicadores/",   views.indicadores,   name="indicadores"),
    path("graficos/",      views.graficos,      name="graficos"),

    # Acompanhamento
    path("monitoramento/", views.monitoramento, name="monitoramento"),
    path("relatorio/",     views.relatorio,     name="relatorio"),
    path("alertas/",       views.alertas,       name="alertas"),
    path("emendas/",       views.emendas,       name="emendas"),

]
