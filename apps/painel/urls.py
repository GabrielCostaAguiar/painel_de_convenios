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

    # GRP — 7 sub-abas de teste. Migram para apps.grp na proxima etapa.
    path("grp/dados/",                    views.grp_instrumentos,             name="grp_dados"),
    path("grp/cronograma/",               views.grp_cronograma,               name="grp_cronograma"),
    path("grp/recursos_contrapartida/",   views.grp_recursos_contrapartida,   name="grp_recursos_contrapartida"),
    path("grp/recursos_concedente/",      views.grp_recursos_concedente,      name="grp_recursos_concedente"),
    path("grp/plano_aplicacao/",          views.grp_plano_aplicacao,          name="grp_plano_aplicacao"),
    path("grp/plano_aplicacao_detalhes/", views.grp_plano_aplicacao_detalhes, name="grp_plano_aplicacao_detalhes"),
    path("grp/esfera/",                   views.grp_esfera,                   name="grp_esfera"),
]
