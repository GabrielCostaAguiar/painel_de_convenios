from django.apps import AppConfig


class ExecucaoConfig(AppConfig):
    """Aba Execucao Estadual: execucao orcamentaria dos convenios no SIAFI-MG."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.execucao"
    label = "execucao"
    verbose_name = "Execução Estadual"
