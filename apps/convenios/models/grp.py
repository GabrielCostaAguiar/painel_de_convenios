"""
Models das tabelas do GRP.

Trabalho em andamento: alimentam as sub-abas GRP (em teste) do painel.
"""

from django.db import models


class DadosGrp(models.Model):
    """
    Fonte: data/silver/dcgce_dados_grp.parquet
    Carga: full refresh via loader dedicado.
    Ligação: convenio_codigo → Convenio.convenio_codigo
    """

    # --- identificação ---
    nr_grp = models.CharField(
        "Número GRP", max_length=50, null=True, blank=True,
    )
    nr_instrumento = models.CharField(
        "Número Instrumento", max_length=50, null=True, blank=True,
    )
    uo_cod = models.CharField(
        "Código UO", max_length=50, null=True, blank=True,
    )
    situacao = models.CharField(
        "Situação", max_length=50, null=True, blank=True,
    )
    dt_vigencia_inicial = models.DateField(
        "Data Vigência Inicial", null=True, blank=True,
    )
    dt_vigencia_termino = models.DateField(
        "Data Vigência Término", null=True, blank=True,
    )
    dt_vigenciainicial_termino = models.DateField(
        "Data Vigência Inicial Término", null=True, blank=True,
    )
    vl_instrumento_concedente_inicial = models.DecimalField(
        "Valor Instrumento Concedente Inicial", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    vl_instrumento_concedente = models.DecimalField(
        "Valor Instrumento Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    vl_instrumento_contrapartida_fin_inicial = models.DecimalField(
        "Valor Instrumento Contrapartida Financeira Inicial", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    vl_instrumento_contrapartida_fin = models.DecimalField(
        "Valor Instrumento Contrapartida Financeira", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    vl_instrumento_total = models.DecimalField(
        "Valor Instrumento Total", max_digits=18, decimal_places=2, null=True, blank=True,
    )

        # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "GRP — Dados Gerais"
        verbose_name_plural = "GRP — Dados Gerais"
        indexes = [
            models.Index(fields=["nr_grp"], name="grp_geral_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nr_grp or '—'}"

class RecursosContrapartidaGrp(models.Model):
    """
    Fonte: data/silver/dcgce_recursos_contrapartida_grp.parquet
    Carga: full refresh via loader dedicado.
    Ligação: nr_grp → DadosGrp.nr_grp
    """

    # --- identificação ---
    uo_cod = models.CharField(
            "Código UO", max_length=50, null=True, blank=True,
        )
    fonte = models.CharField(
        "Fonte Recurso", max_length=50, null=True, blank=True,
    )
    nr_grp = models.CharField(
        "Número GRP", max_length=50, null=True, blank=True,
    )
    ipu = models.CharField(
        "IPU", max_length=50, null=True, blank=True,
    )
    vl_contrapartida_financeira = models.DecimalField(
        "Valor Contrapartida financeira", max_digits=18, decimal_places=2, null=True, blank=True,
    )

        # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "GRP — Recursos de Contrapartida"
        verbose_name_plural = "GRP — Recursos de Contrapartida"
        indexes = [
            models.Index(fields=["nr_grp"], name="grp_recurso_contr_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nr_grp or '—'} — {self.ipu or '—'}"

class RecursosConcedenteGrp(models.Model):
    """
    Fonte: data/silver/dcgce_recursos_concedente_grp.parquet
    Carga: full refresh via loader dedicado.
    Ligação: nr_grp → DadosGrp.nr_grp
    """

    # --- identificação ---
    uo_cod = models.CharField(
            "Código UO", max_length=50, null=True, blank=True,
        )
    nr_grp = models.CharField(
    "Número GRP", max_length=50, null=True, blank=True,
    )
    fonte = models.CharField(
        "Fonte Recurso", max_length=50, null=True, blank=True,
    )

    ipu = models.CharField(
        "IPU", max_length=50, null=True, blank=True,
    )
    vl_concedente = models.DecimalField(
        "Valor Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )

        # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "GRP — Recursos do Concedente"
        verbose_name_plural = "GRP — Recursos do Concedente"
        indexes = [
            models.Index(fields=["nr_grp"], name="grp_recurso_conc_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nr_grp or '—'} — {self.ipu or '—'}"

class PlanoAplicacaoGrp(models.Model):
    """
    Fonte: data/silver/dcgce_plano_aplicacao_grp.parquet
    Carga: full refresh via loader dedicado.
    Ligação: nr_grp → DadosGrp.nr_grp
    """

    # --- identificação ---
    nr_grp = models.CharField(
        "Número GRP", max_length=50, null=True, blank=True,
    )
    nome_projeto = models.CharField(
        "Nome do Projeto", max_length=255, null=True, blank=True,
    )
    objeto_projeto = models.CharField(
        "Objeto do Projeto", max_length=500, null=True, blank=True,
    )
    situacao_instrumento = models.CharField(
        "Situação do Instrumento", max_length=50, null=True, blank=True,
    )
    tipo_instrumento = models.CharField(
        "Tipo do Instrumento", max_length=50, null=True, blank=True,
    )
    responsavel_nome = models.CharField(
        "Nome do Responsável", max_length=50, null=True, blank=True,
    )
    responsavel_atribuicao = models.CharField(
        "Atribuição do Responsável", max_length=50, null=True, blank=True,
    )
    cnpj_convenente = models.CharField(
        "CNPJ do Convenente", max_length=50, null=True, blank=True,
    )

    #--- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "GRP — Plano de Aplicação"
        verbose_name_plural = "GRP — Planos de Aplicação"
        indexes = [
            models.Index(fields=["nr_grp"], name="grp_plano_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nr_grp or '—'} — {self.nome_projeto or '—'}"

class PlanoAplicacaoGrpDetalhes(models.Model):
    """
    Fonte: data/silver/dcgce_plano_aplicacao_detalhes.parquet
    Carga: full refresh via loader dedicado.
    Ligação: nr_grp → PlanoAplicacaoGrp.nr_grp
    """

    # --- identificação ---
    nr_catmas = models.CharField(
        "Número CATMAS", max_length=50, null=True, blank=True,
    )
    nr_grp = models.CharField(
            "Número GRP", max_length=50, null=True, blank=True,
    )
    tipo_despesa = models.CharField(
        "Tipo de Despesa", max_length=50, null=True, blank=True,
    )
    categoria_despesa = models.CharField(
        "Categoria de Despesa", max_length=50, null=True, blank=True,
    )
    grupo_despesa = models.CharField(
        "Grupo de Despesa", max_length=50, null=True, blank=True,
    )
    modalidade = models.CharField(
        "Modalidade", max_length=50, null=True, blank=True,
    )
    elemento_despesa = models.CharField(
        "Elemento de Despesa", max_length=50, null=True, blank=True,
    )
    beneficiario_cnpj = models.CharField(
        "CNPJ do Beneficiário", max_length=50, null=True, blank=True,
    )
    descricao_item = models.CharField(
        "Descrição do Item a executar", max_length=250, null=True, blank=True,
    )
    origem_recurso = models.CharField(
        "Origem do Recurso", max_length=50, null=True, blank=True,
    )
    qt_item_executar = models.DecimalField(
        "Quantidade do Item a executar", max_digits=18, decimal_places=2, null=True, blank=True
    )
    vl_uni_item_a_executar = models.DecimalField(
        "Valor Unitário do Item a executar", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    vl_total_item_a_executar = models.DecimalField(
        "Valor Total do Item a executar", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    situacao_item_a_executar = models.CharField(
        "Situação do Item a executar", max_length=50, null=True, blank=True,
    )

        # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "GRP — Detalhes do Plano de Aplicação"
        verbose_name_plural = "GRP — Detalhes dos Planos de Aplicação"
        indexes = [
            models.Index(fields=["nr_grp"], name="grp_plano_detalhe_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nr_grp or '—'} — {self.descricao_item or '—'}"

class EsferaGrp(models.Model):
    """
    Fonte: data/silver/dcgce_esfera.parquet
    Carga: full refresh via loader dedicado.
    Ligação: concedente_cnpj → Convenio.concedente_cnpj
    """

    # --- identificação ---
    concedente_nome = models.CharField(
        "Nome do Concedente", max_length=255, null=True, blank=True,
    )
    concedente_cnpj = models.CharField(
        "CNPJ do Concedente", max_length=50, db_index=True, null=True, blank=True,
    )
    concedente_esfera = models.CharField(
        "Esfera", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Esfera do Concedente"
        verbose_name_plural = "Esferas dos Concedentes"
        indexes = [
            models.Index(fields=["concedente_cnpj"], name="esfera_concedente_cnpj_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.concedente_cnpj or '—'} — {self.concedente_esfera or '—'}"

class CronogramaDesembolsoGrp(models.Model):
    """
    Fonte: data/silver/dcgce_cronograma_desembolso_grp.parquet
    Carga: full refresh via loader dedicado.
    Ligação: nr_grp → DadosGrp.nr_grp
    """

    # --- identificação ---
    nr_grp = models.CharField(
        "Número GRP", max_length=50, null=True, blank=True,
    )
    parcela_desembolso = models.CharField(
        "Parcela do Desembolso", max_length=50, null=True, blank=True,
    )
    mes_desembolso = models.CharField(
        "Mês do Desembolso", max_length=50, null=True, blank=True,
    )
    ano_desembolso = models.CharField(
        "Ano do Desembolso", max_length=50, null=True, blank=True,
    )
    origem_recurso_parcela = models.CharField(
        "Origem do Recurso da Parcela", max_length=50, null=True, blank=True,
    )
    vl_desembolso = models.DecimalField(
        "Valor do Desembolso", max_digits=18, decimal_places=2, null=True, blank=True,
    )

        # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "GRP — Cronograma de Desembolso"
        verbose_name_plural = "GRP — Cronogramas de Desembolso"
        indexes = [
            models.Index(fields=["nr_grp"], name="grp_cronograma_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nr_grp or '—'} — {self.parcela_desembolso or '—'}"
