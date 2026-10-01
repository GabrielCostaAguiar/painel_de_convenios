from django.apps import AppConfig


class GrpConfig(AppConfig):
    """Aba GRP (em teste): instrumentos e planos de aplicacao vindos do GRP."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.grp"
    label = "grp"
    verbose_name = "GRP (dev)"
