"""
Model da camada Gold: ConvenioIntegrado.

Tabela integrada SIGCON ↔ SICONV ↔ SIAFI com os campos coalescidos G_/A_,
construída por core/gold/relacionamento.py e carregada por
carregar_relacionamento.
"""

from django.db import models


# dcgce_chave e dcgce_unidades.executoras: schemas com erro de geração (header não
# detectado corretamente). Modelar após reinspecionar o arquivo raw.


# ---------------------------------------------------------------------------
# ConvenioIntegrado — tabela Gold: SIGCON ↔ SICONV ↔ SIAFI com campos G_/A_
# ---------------------------------------------------------------------------

class ConvenioIntegrado(models.Model):
    """
    Tabela Gold integrada — equivalente Python do 'miolo' do QlikView.

    Chave natural: siafi_uo (única por convenio, montada como str(siafi)+str(uo)).
    Fonte: data/gold/convenios_integrado.parquet
    Carga: full refresh via 'python manage.py carregar_relacionamento'.

    G_ = coalesce(SICONV, SIGCON) — melhor informação disponível.
    A_ = G_ projetado sobre siafi_uo_atual — estado atual da UO que carrega o convênio.
    """

    # --- chaves / bridge ---
    siafi_uo = models.CharField(
        "SIAFI_UO", max_length=30, unique=True, db_index=True,
    )
    siafi_uo_atual = models.CharField(
        "SIAFI_UO Atual", max_length=30, null=True, blank=True, db_index=True,
    )
    convenio_numero_sequencial_siafi = models.CharField(
        "Nr. SIAFI", max_length=20, null=True, blank=True,
    )
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. UO", max_length=15, null=True, blank=True,
    )
    siafiatual = models.CharField("SIAFI Atual", max_length=20, null=True, blank=True)
    uo_atual = models.CharField("UO Atual", max_length=15, null=True, blank=True)
    codigo_siconv = models.CharField("Cód. SICONV", max_length=30, null=True, blank=True)

    # --- de-paras aplicados às chaves ---
    instrumento_chaves = models.CharField("Instrumento (chaves)", max_length=100, null=True, blank=True)
    situacao = models.CharField("Situação (chaves)", max_length=100, null=True, blank=True)
    situacao_std = models.CharField("Situação Padronizada", max_length=100, null=True, blank=True)
    uo_nome_std = models.CharField("Nome UO", max_length=255, null=True, blank=True)
    uo_sigla_std = models.CharField("Sigla UO", max_length=50, null=True, blank=True)
    uo_descricao_std = models.CharField("Descrição UO", max_length=255, null=True, blank=True)

    # --- G_ datas ---
    g_dia_assinatura = models.DateField("G_ Data Assinatura", null=True, blank=True)
    g_inicio_vigencia = models.DateField("G_ Início Vigência", null=True, blank=True)
    g_fim_vigencia = models.DateField("G_ Fim Vigência", null=True, blank=True)
    g_fim_vigencia_inicial = models.DateField("G_ Fim Vigência Inicial", null=True, blank=True)

    # --- G_ anos (inteiros) ---
    g_ano_assinatura = models.SmallIntegerField("G_ Ano Assinatura", null=True, blank=True)
    g_ano_inicio_vigencia = models.SmallIntegerField("G_ Ano Início Vigência", null=True, blank=True)
    g_ano_convenio = models.SmallIntegerField("G_ Ano Convênio", null=True, blank=True)

    # --- G_ texto ---
    g_situacao_convenio = models.CharField("G_ Situação", max_length=100, null=True, blank=True)
    g_objeto_convenio = models.TextField("G_ Objeto", null=True, blank=True)
    g_proponente = models.CharField("G_ Proponente", max_length=255, null=True, blank=True)
    g_concedente = models.CharField("G_ Concedente", max_length=255, null=True, blank=True)
    g_instrumento = models.CharField("G_ Instrumento", max_length=100, null=True, blank=True)
    g_esfera = models.CharField("G_ Esfera", max_length=100, null=True, blank=True)
    g_uo = models.CharField("G_ UO", max_length=20, null=True, blank=True)
    g_vigencia = models.CharField("G_ Vigência", max_length=20, null=True, blank=True)
    g_situacao_convenio_categorizado = models.CharField(
        "G_ Situação Categorizada", max_length=100, null=True, blank=True,
    )
    g_concedente_pad = models.CharField("G_ Concedente Pad.", max_length=255, null=True, blank=True)
    g_proponente_pad = models.CharField("G_ Proponente Pad.", max_length=255, null=True, blank=True)
    g_proponente_pad_siglas = models.CharField(
        "G_ Proponente Siglas", max_length=50, null=True, blank=True,
    )
    g_uo_descricao = models.CharField("G_ Descrição UO", max_length=255, null=True, blank=True)

    # --- G_ valores ---
    g_valor_concedente = models.DecimalField(
        "G_ Valor Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    g_valor_proponente = models.DecimalField(
        "G_ Valor Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    g_valor_global = models.DecimalField(
        "G_ Valor Global", max_digits=18, decimal_places=2, null=True, blank=True,
    )

    # --- G_ flags (0/1) ---
    g_periodo_nao_aditado = models.SmallIntegerField("G_ Período Não Aditado", null=True, blank=True)
    g_valor_nao_aditado = models.SmallIntegerField("G_ Valor Não Aditado", null=True, blank=True)
    limpeza_g = models.SmallIntegerField("Limpeza G_", null=True, blank=True)

    # --- A_ datas ---
    a_dia_assinatura = models.DateField("A_ Data Assinatura", null=True, blank=True)
    a_inicio_vigencia = models.DateField("A_ Início Vigência", null=True, blank=True)
    a_fim_vigencia = models.DateField("A_ Fim Vigência", null=True, blank=True)
    a_fim_vigencia_inicial = models.DateField("A_ Fim Vigência Inicial", null=True, blank=True)

    # --- A_ anos ---
    a_ano_assinatura = models.SmallIntegerField("A_ Ano Assinatura", null=True, blank=True)
    a_ano_inicio_vigencia = models.SmallIntegerField("A_ Ano Início Vigência", null=True, blank=True)
    a_ano_convenio = models.SmallIntegerField("A_ Ano Convênio", null=True, blank=True)

    # --- A_ texto ---
    a_situacao_convenio = models.CharField("A_ Situação", max_length=100, null=True, blank=True)
    a_objeto_convenio = models.TextField("A_ Objeto", null=True, blank=True)
    a_proponente = models.CharField("A_ Proponente", max_length=255, null=True, blank=True)
    a_concedente = models.CharField("A_ Concedente", max_length=255, null=True, blank=True)
    a_instrumento = models.CharField("A_ Instrumento", max_length=100, null=True, blank=True)
    a_esfera = models.CharField("A_ Esfera", max_length=100, null=True, blank=True)
    a_vigencia = models.CharField("A_ Vigência", max_length=20, null=True, blank=True)
    a_situacao_convenio_categorizado = models.CharField(
        "A_ Situação Categorizada", max_length=100, null=True, blank=True,
    )
    a_concedente_pad = models.CharField("A_ Concedente Pad.", max_length=255, null=True, blank=True)
    a_proponente_pad = models.CharField("A_ Proponente Pad.", max_length=255, null=True, blank=True)
    a_proponente_pad_siglas = models.CharField(
        "A_ Proponente Siglas", max_length=50, null=True, blank=True,
    )

    # --- A_ valores ---
    a_valor_concedente = models.DecimalField(
        "A_ Valor Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    a_valor_proponente = models.DecimalField(
        "A_ Valor Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    a_valor_global = models.DecimalField(
        "A_ Valor Global", max_digits=18, decimal_places=2, null=True, blank=True,
    )

    # --- A_ flags ---
    a_periodo_nao_aditado = models.SmallIntegerField("A_ Período Não Aditado", null=True, blank=True)
    a_valor_nao_aditado = models.SmallIntegerField("A_ Valor Não Aditado", null=True, blank=True)

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ["-g_fim_vigencia"]
        verbose_name = "Convênio Integrado"
        verbose_name_plural = "Convênios Integrados"
        indexes = [
            models.Index(fields=["siafi_uo_atual"], name="conv_int_siafi_atual_idx"),
            models.Index(fields=["g_situacao_convenio_categorizado"], name="conv_int_sit_cat_idx"),
            models.Index(fields=["g_vigencia"], name="conv_int_vigencia_idx"),
            models.Index(fields=["g_fim_vigencia"], name="conv_int_fim_vig_idx"),
            models.Index(fields=["g_ano_convenio"], name="conv_int_ano_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.siafi_uo} → {self.siafi_uo_atual or '—'} ({self.g_situacao_convenio or '—'})"
