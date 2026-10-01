from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    # Cada aba do menu e um app com as suas proprias rotas.
    #
    # Todas entram na raiz, e nao sob um prefixo por app: os caminhos do painel
    # ja existiam antes desta divisao (/plano_aplicacao/, /grp/dados/, ...) e
    # nao podem mudar. O que separa um app do outro e o namespace do nome da
    # rota (sigcon:, painel:, ...), nao o prefixo do caminho.
    #
    # O sigcon vem primeiro porque responde tambem pela raiz ("").
    path("", include("apps.sigcon.urls")),
    path("", include("apps.grp.urls")),
    path("", include("apps.uniao.urls")),
    path("", include("apps.execucao.urls")),
    path("", include("apps.painel.urls")),
]
