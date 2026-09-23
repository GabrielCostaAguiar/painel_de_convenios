from django.apps import AppConfig


class PainelConfig(AppConfig):
    """
    Casca do painel: sidebar, indicadores, graficos e filtros globais.

    Diferente do app das Consultas SIGCON, aqui o label pode mudar junto com o
    pacote: o app nao tem models, nenhuma tabela `dashboard_*` e nenhuma linha
    em django_migrations com app='dashboard'.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.painel"
    label = "painel"
    verbose_name = "Painel"
