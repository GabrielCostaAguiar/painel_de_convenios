from django.apps import AppConfig


class UniaoConfig(AppConfig):
    """Aba Consultas Uniao: convenios do painel vistos pelo lado da Uniao
    (Transferegov/SICONV)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.uniao"
    label = "uniao"
    verbose_name = "Consultas União"
