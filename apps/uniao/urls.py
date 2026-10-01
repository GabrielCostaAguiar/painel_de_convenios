"""
Rotas da aba Consultas União.

Incluidas na raiz em config/urls.py: o caminho /uniao/ ja existia antes
desta divisao em apps e nao pode mudar.
"""

from django.urls import path

from . import views

app_name = "uniao"

urlpatterns = [
    path("uniao/", views.consultas_uniao, name="uniao"),
]
