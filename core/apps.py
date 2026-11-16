from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Núcleo: comandos de pipeline e utilitários compartilhados. Sem models."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    label = "core"
    verbose_name = "Núcleo (pipeline e utilitários compartilhados)"
