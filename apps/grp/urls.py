"""
Rotas da aba GRP (em teste).

Incluidas na raiz em config/urls.py; o prefixo /grp/ ja vem escrito em cada
path, para os caminhos continuarem identicos aos de antes desta divisao.
"""

from django.urls import path

from . import views

app_name = "grp"

urlpatterns = [
    path("grp/", views.grp_instrumentos, name="grp_dados"),
    path("grp/dados/", views.grp_instrumentos, name="grp_instrumentos"),
    path("grp/cronograma/", views.grp_cronograma, name="grp_cronograma"),
    path("grp/plano_aplicacao/", views.grp_plano_aplicacao, name="grp_plano_aplicacao"),
    path("grp/emenda/", views.grp_emenda, name="grp_emenda"),
    path("grp/regioes_atendidas/", views.grp_regioes_atendidas, name="grp_regioes_atendidas"),
    path("grp/prestacao_contas/", views.grp_prestacao_contas, name="grp_prestacao_contas"),
]   
    