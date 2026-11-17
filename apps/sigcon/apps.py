from django.apps import AppConfig


class SigconConfig(AppConfig):
    """
    App das Consultas SIGCON.

    Pacote, label e prefixo das tabelas (`sigcon_*`) coincidem. O label antigo
    era "convenios"; a troca exigiu atualizar django_migrations e
    django_content_type (ver docs/sql/renomear_label_sigcon.sql). Nenhuma
    tabela de dados foi renomeada.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sigcon"
    label = "sigcon"
    verbose_name = "Consultas SIGCON"
