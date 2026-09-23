"""
Rotas da aba Execução Estadual.

Incluidas na raiz em config/urls.py: o caminho /execucao/ ja existia antes
desta divisao em apps e nao pode mudar.
"""

from django.urls import path

from . import views

app_name = "execucao"

urlpatterns = [
    path("execucao/", views.execucao, name="execucao"),
]
