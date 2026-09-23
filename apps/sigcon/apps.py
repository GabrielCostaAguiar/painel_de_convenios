from django.apps import AppConfig


class SigconConfig(AppConfig):
    """
    App das Consultas SIGCON.

    O pacote Python chama-se `apps.sigcon`, mas o **label continua "convenios"**
    de proposito. O Django deriva do label o nome das tabelas
    (`convenios_convenio`, ...), o app_label gravado em django_content_type e a
    pasta de migracoes que o historico ja aplicou. Trocar o label renomearia 24
    tabelas e invalidaria as 11 migracoes existentes — o pacote e so o endereco
    do codigo, o label e o identificador no banco.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sigcon"
    label = "convenios"
    verbose_name = "Consultas SIGCON"
