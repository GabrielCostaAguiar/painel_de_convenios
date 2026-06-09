from django.db import models


class Convenio(models.Model):
    """
    Representa um convênio após a passagem pela camada Silver.
    Campos refletem o dado limpo e tipado — não o CSV bruto do Bronze.

    nr_convenio é a chave natural do domínio (ex: "123456/2024").
    Usamos unique=True aqui para garantir idempotência na carga.
    """

    # --- identificação ---
    nr_convenio = models.CharField(
        "Nº Convênio", max_length=30, unique=True,
        help_text="Identificador único do convênio (ex: 123456/2024)",
    )
    nr_processo = models.CharField("Nº Processo", max_length=50, blank=True)
    objeto = models.TextField("Objeto")

    # --- partes ---
    concedente = models.CharField("Concedente", max_length=255)
    convenente = models.CharField("Convenente", max_length=255)

    # --- status ---
    situacao = models.CharField("Situação", max_length=100)

    # --- financeiro ---
    valor_global = models.DecimalField(
        "Valor Global (R$)", max_digits=16, decimal_places=2,
        null=True, blank=True,
    )

    # --- datas ---
    data_inicio = models.DateField("Data de Início", null=True, blank=True)
    data_termino = models.DateField("Data de Término", null=True, blank=True)

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ["-data_inicio"]
        verbose_name = "Convênio"
        verbose_name_plural = "Convênios"
        indexes = [
            models.Index(fields=["situacao"]),
            models.Index(fields=["concedente"]),
            models.Index(fields=["data_inicio"]),
        ]

    def __str__(self) -> str:
        return f"{self.nr_convenio} — {self.convenente}"
