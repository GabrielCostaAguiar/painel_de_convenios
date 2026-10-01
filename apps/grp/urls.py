"""
Rotas da aba GRP (em teste).

Incluidas na raiz em config/urls.py; o prefixo /grp/ ja vem escrito em cada
path, para os caminhos continuarem identicos aos de antes desta divisao.
"""

from django.urls import path

from . import views 

app_name = "grp"

urlpatterns = [
    path("grp/",                          views.grp_instrumentos,             name="grp_dados"),
    path("grp/dados/",                    views.grp_instrumentos,             name="grp_instrumentos"),
    path("grp/cronograma/",               views.grp_cronograma,               name="grp_cronograma"),
    path("grp/recursos_contrapartida/",   views.grp_recursos_contrapartida,   name="grp_recursos_contrapartida"),
    path("grp/recursos_concedente/",      views.grp_recursos_concedente,      name="grp_recursos_concedente"),
    path("grp/plano_aplicacao/",          views.grp_plano_aplicacao,          name="grp_plano_aplicacao"),
    path("grp/plano_aplicacao_detalhes/", views.grp_plano_aplicacao_detalhes, name="grp_plano_aplicacao_detalhes"),
    path("grp/esfera/",                   views.grp_esfera,                   name="grp_esfera"),
]
