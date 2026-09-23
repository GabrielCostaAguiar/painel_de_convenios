"""
Tabelas de mapeamento de códigos (chaves naturais entre entidades).

Não têm valor próprio para o usuário: existem para ligar as entidades do
SIGCON-MG entre si nos joins dos loaders (código sequencial ↔ SIAFI ↔ UO).
"""

from django.db import models


# ---------------------------------------------------------------------------
# Tabelas de mapeamento de códigos (chaves naturais entre entidades)
# ---------------------------------------------------------------------------

class CodigoConvenio(models.Model):
    """
    Fonte: data/silver/dcgce_Codigo_convenio.parquet
    Carga: full refresh via loader dedicado.
    Mapeia convenio_codigo → convenio_codigo_sequencial, SIAFI e UO.
    """

    convenio_codigo = models.CharField(
        "Código do Convênio", max_length=50, db_index=True, null=True, blank=True,
    )
    convenio_codigo_sequencial = models.CharField(
        "Código Sequencial", max_length=50, null=True, blank=True,
    )
    convenio_numero_sequencial_siafi = models.CharField(
        "Nº Sequencial SIAFI", max_length=50, null=True, blank=True,
    )
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. Unidade Orçamentária", max_length=50, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Mapeamento de Códigos do Convênio"
        verbose_name_plural = "Mapeamentos de Códigos de Convênios"
        indexes = [
            models.Index(fields=["convenio_codigo"], name="cod_convenio_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.convenio_codigo or '—'}"

class CodigoPlanoTrabalho(models.Model):
    """
    Fonte: data/silver/dcgce_Codigo_plano_de_trabalho.parquet
    Carga: full refresh via loader dedicado.
    Mapeia conveno_codigo_plano_trabalho → SIAFI e UO.
    """

    conveno_codigo_plano_trabalho = models.CharField(
        "Código do Plano de Trabalho", max_length=50, db_index=True, null=True, blank=True,
    )
    convenio_numero_sequencial_siafi = models.CharField(
        "Nº Sequencial SIAFI", max_length=50, null=True, blank=True,
    )
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. Unidade Orçamentária", max_length=50, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Mapeamento de Códigos do Plano de Trabalho"
        verbose_name_plural = "Mapeamentos de Códigos de Planos de Trabalho"
        indexes = [
            models.Index(
                fields=["conveno_codigo_plano_trabalho"],
                name="cod_plano_trabalho_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.conveno_codigo_plano_trabalho or '—'}"

class CodigoTermoAditivo(models.Model):
    """
    Fonte: data/silver/dcgce_Codigo_ta.parquet
    Carga: full refresh via loader dedicado.
    Mapeia termo_aditivo_codigo_sequencial → convênio SIAFI e plano de trabalho.
    """

    convenio_numero_sequencial_siafi = models.CharField(
        "Nº Sequencial SIAFI", max_length=50, db_index=True, null=True, blank=True,
    )
    termo_aditivo_codigo_sequencial = models.CharField(
        "Código Sequencial do Termo Aditivo", max_length=50, db_index=True, null=True, blank=True,
    )
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. Unidade Orçamentária", max_length=50, null=True, blank=True,
    )
    plano_trabalho_codigo = models.CharField(
        "Código do Plano de Trabalho", max_length=50, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Mapeamento de Códigos do Termo Aditivo"
        verbose_name_plural = "Mapeamentos de Códigos de Termos Aditivos"
        indexes = [
            models.Index(
                fields=["termo_aditivo_codigo_sequencial"],
                name="cod_ta_sequencial_idx",
            ),
            models.Index(
                fields=["convenio_numero_sequencial_siafi"],
                name="cod_ta_siafi_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.termo_aditivo_codigo_sequencial or '—'}"

class CodigoDeclaracaoContrapartida(models.Model):
    """
    Fonte: data/silver/dcgce_Codigo_dec_contrap.parquet
    Carga: full refresh via loader dedicado.
    Mapeia declaracao_contrapartida_codigo → convênio SIAFI e UO.
    """

    declaracao_contrapartida_codigo = models.CharField(
        "Código da Declaração", max_length=50, db_index=True, null=True, blank=True,
    )
    convenio_numero_sequencial_siafi = models.CharField(
        "Nº Sequencial SIAFI", max_length=50, db_index=True, null=True, blank=True,
    )
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. Unidade Orçamentária", max_length=50, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Mapeamento de Códigos da Declaração de Contrapartida"
        verbose_name_plural = "Mapeamentos de Códigos de Declarações de Contrapartida"
        indexes = [
            models.Index(
                fields=["declaracao_contrapartida_codigo"],
                name="cod_decl_contrap_idx",
            ),
            models.Index(
                fields=["convenio_numero_sequencial_siafi"],
                name="cod_decl_siafi_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.declaracao_contrapartida_codigo or '—'}"
