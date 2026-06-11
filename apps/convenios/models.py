from django.db import models


class Convenio(models.Model):
    """
    Convênio consolidado: dcgce_convenio + dcgce_geral + dcgce_plano_trabalho + dcgce_esfera.
    Chave natural: (convenio_numero_sequencial_siafi, unidade_orcamentaria_codigo).
    Carga: full refresh via 'python manage.py carregar_convenios'.
    """

    # --- identificação — chave composta SIAFI+UO ---
    convenio_codigo = models.CharField(
        "Código SIGCON", max_length=50, db_index=True,
    )
    convenio_numero_sequencial_siafi = models.CharField(
        "Código SIAFI", max_length=50, null=True, blank=True,
    )
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. UO", max_length=20, null=True, blank=True,
    )

    # --- de dcgce_geral ---
    plano_trabalho_codigo = models.CharField(
        "Código Plano de Trabalho", max_length=50, null=True, blank=True, db_index=True,
    )
    data_publicacao = models.DateField("Data de Publicação", null=True, blank=True)
    data_assinatura = models.DateField("Data de Assinatura", null=True, blank=True)
    convenio_ano = models.CharField("Ano", max_length=10, null=True, blank=True)

    # --- de dcgce_plano_trabalho ---
    instrumento = models.CharField("Instrumento", max_length=100, null=True, blank=True)
    titulo = models.TextField("Título", null=True, blank=True)
    objeto = models.TextField("Objeto", null=True, blank=True)
    concedente = models.CharField("Concedente", max_length=255, null=True, blank=True)
    cnpj_concedente = models.CharField("CNPJ Concedente", max_length=20, null=True, blank=True)
    cnpj_proponente = models.CharField("CNPJ Proponente", max_length=20, null=True, blank=True)

    # --- de dcgce_esfera ---
    esfera = models.CharField("Esfera", max_length=50, null=True, blank=True)

    # --- de dcgce_convenio: status ---
    situacao = models.CharField("Situação", max_length=100, null=True, blank=True)

    # --- de dcgce_convenio: datas de vigência ---
    data_inicio_vigencia = models.DateField("Início de Vigência", null=True, blank=True)
    data_termino_vigencia = models.DateField("Término de Vigência", null=True, blank=True)
    data_real_convenio = models.DateField("Data Real do Convênio", null=True, blank=True)

    # --- de dcgce_convenio: financeiro ---
    valor_inicial_concedente_contratado = models.DecimalField(
        "Valor Inicial Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_total_aditado_concedente_contratado = models.DecimalField(
        "Valor Total Aditado Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_concedente = models.DecimalField(
        "Valor Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_inicial_proponente_contratado = models.DecimalField(
        "Valor Inicial Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_total_aditado_proponente_contratado = models.DecimalField(
        "Valor Total Aditado Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_proponente = models.DecimalField(
        "Valor Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_total_convenio = models.DecimalField(
        "Valor Total do Convênio", max_digits=18, decimal_places=2, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ["-data_inicio_vigencia"]
        verbose_name = "Convênio"
        verbose_name_plural = "Convênios"
        indexes = [
            models.Index(fields=["situacao"], name="convenios_situacao_idx"),
            models.Index(fields=["data_inicio_vigencia"], name="convenios_data_inicio_idx"),
            models.Index(
                fields=["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"],
                name="convenios_chave_composta_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.convenio_codigo} — {self.situacao or '—'}"


# ---------------------------------------------------------------------------
# ConvenioGeral — dados gerais do SIGCON-MG (dcgce_geral)
# ---------------------------------------------------------------------------

class ConvenioGeral(models.Model):
    """
    Fonte: data/silver/dcgce_geral.parquet
    Carga: full refresh via loader dedicado.
    Ligação: convenio_codigo → Convenio.convenio_codigo
    """

    # --- identificação ---
    convenio_codigo = models.CharField(
        "Código do Convênio", max_length=50, db_index=True, null=True, blank=True,
    )
    convenio_codigo_sequencial = models.CharField(
        "Código Sequencial", max_length=50, null=True, blank=True,
    )
    conveno_codigo_plano_trabalho = models.CharField(
        "Código Plano de Trabalho", max_length=50, null=True, blank=True,
    )
    convenio_numero_sequencial_siafi = models.CharField(
        "Nº Sequencial SIAFI", max_length=50, null=True, blank=True,
    )
    convenio_codigo_declaracao = models.CharField(
        "Código Declaração", max_length=50, null=True, blank=True,
    )

    # --- datas ---
    convenio_data_de_publicacao = models.DateField(
        "Data de Publicação", null=True, blank=True,
    )
    convenio_data_alteracao_sccg = models.DateField(
        "Data de Alteração SCCG", null=True, blank=True,
    )
    convenio_data_controle_sccg_convenio = models.DateField(
        "Data Controle SCCG", null=True, blank=True,
    )
    convenio_data_assinatura_convenio = models.DateField(
        "Data de Assinatura", null=True, blank=True,
    )
    convenio_data_de_cadastramento = models.DateField(
        "Data de Cadastramento", null=True, blank=True,
    )

    # --- texto ---
    convenio_ano = models.CharField("Ano", max_length=255, null=True, blank=True)
    convenio_alteracao = models.CharField("Alteração", max_length=255, null=True, blank=True)
    convenio_matricula_tecnico_sccg = models.CharField(
        "Matrícula Técnico SCCG", max_length=255, null=True, blank=True,
    )
    convenio_justificativa_da_alteracao = models.TextField(
        "Justificativa da Alteração", null=True, blank=True,
    )
    convenio_matricula_gestor = models.CharField(
        "Matrícula Gestor", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Convênio — Dados Gerais"
        verbose_name_plural = "Convênios — Dados Gerais"
        indexes = [
            models.Index(fields=["convenio_codigo"], name="conv_geral_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.convenio_codigo or '—'}"


# ---------------------------------------------------------------------------
# PlanoTrabalho — planos de trabalho (dcgce_plano.trabalho)
# ---------------------------------------------------------------------------

class PlanoTrabalho(models.Model):
    """
    Fonte: data/silver/dcgce_plano.trabalho.parquet
    Carga: full refresh via loader dedicado.
    PK natural: plano_trabalho_codigo — referenciado por CronogramaDesembolso,
    PlanoAplicacao e NtEmenda.
    """

    # --- identificação ---
    plano_trabalho_codigo = models.CharField(
        "Código do Plano de Trabalho", max_length=50, db_index=True, null=True, blank=True,
    )
    plano_trabalho_codigo_execucao_no_exercicio = models.CharField(
        "Código Execução no Exercício", max_length=50, null=True, blank=True,
    )
    plano_trabalho_tipo_siafi = models.CharField(
        "Tipo SIAFI", max_length=50, null=True, blank=True,
    )
    plano_trabalho_cnpj_concedente = models.CharField(
        "CNPJ Concedente", max_length=50, null=True, blank=True,
    )
    plano_trabalho_cnpj_proponente = models.CharField(
        "CNPJ Proponente", max_length=50, null=True, blank=True,
    )

    # --- datas ---
    plano_trabalho_data_cancelamento_sccg = models.DateField(
        "Data Cancelamento SCCG", null=True, blank=True,
    )
    plano_trabalho_data_cadastro = models.DateField(
        "Data de Cadastro", null=True, blank=True,
    )
    plano_trabalho_data_envio_sccg = models.DateField(
        "Data de Envio SCCG", null=True, blank=True,
    )

    # --- texto (longos) ---
    plano_trabalho_titulo = models.TextField("Título", null=True, blank=True)
    plano_trabalho_objeto = models.TextField("Objeto", null=True, blank=True)
    plano_trabalho_justificativa = models.TextField("Justificativa", null=True, blank=True)

    # --- texto (curtos) ---
    plano_trabalho_status = models.CharField("Status", max_length=255, null=True, blank=True)
    plano_trabalho_caracteristica = models.CharField(
        "Característica", max_length=255, null=True, blank=True,
    )
    plano_trabalho_tipo = models.CharField("Tipo", max_length=255, null=True, blank=True)
    plano_trabalho_migrado_ou_novo = models.CharField(
        "Migrado ou Novo", max_length=255, null=True, blank=True,
    )
    plano_trabalho_matricula_sccg_cancelamento = models.CharField(
        "Matrícula SCCG Cancelamento", max_length=255, null=True, blank=True,
    )
    plano_trabalho_justificativa_sccg_cancelamento = models.CharField(
        "Justificativa SCCG Cancelamento", max_length=255, null=True, blank=True,
    )
    plano_trabalho_cancelamento_sccg = models.CharField(
        "Cancelamento SCCG", max_length=255, null=True, blank=True,
    )
    plano_trabalho_ano = models.CharField("Ano", max_length=255, null=True, blank=True)
    plano_trabalho_altera_termo_aditivo = models.CharField(
        "Altera Termo Aditivo", max_length=255, null=True, blank=True,
    )
    plano_trabalho_razao_social_concedente = models.CharField(
        "Razão Social Concedente", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Plano de Trabalho"
        verbose_name_plural = "Planos de Trabalho"
        indexes = [
            models.Index(fields=["plano_trabalho_codigo"], name="plano_trabalho_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.plano_trabalho_codigo or '—'} — {self.plano_trabalho_titulo or '—'}"


# ---------------------------------------------------------------------------
# CronogramaDesembolso — cronograma de desembolsos (dcgce_Cronograma_desembolso)
# ---------------------------------------------------------------------------

class CronogramaDesembolso(models.Model):
    """
    Cronograma enriquecido: dcgce_cronograma_desembolso + SIAFI+UO do convênio.
    Rota: plano_trabalho_codigo → dcgce_geral → dcgce_codigo_convenio → SIAFI+UO.
    Carga: full refresh via 'python manage.py carregar_cronograma'.
    """

    # --- identificação ---
    plano_trabalho_codigo = models.CharField(
        "Código do Plano de Trabalho", max_length=50, db_index=True, null=True, blank=True,
    )
    # carimbados no ETL via Geral+CodigoConvenio
    convenio_numero_sequencial_siafi = models.CharField(
        "Código SIAFI", max_length=50, null=True, blank=True,
    )
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. UO", max_length=20, null=True, blank=True,
    )

    # --- financeiro ---
    valor_concedente_cronograma_desembolso = models.DecimalField(
        "Valor Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_proponente_cronograma_desembolso = models.DecimalField(
        "Valor Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )

    # --- tempo ---
    mes_cronograma_desembolso = models.CharField(
        "Mês", max_length=10, null=True, blank=True,
    )
    ano_cronograma_desembolso = models.CharField(
        "Ano", max_length=10, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Cronograma de Desembolso"
        verbose_name_plural = "Cronogramas de Desembolso"
        indexes = [
            models.Index(fields=["plano_trabalho_codigo"], name="cronograma_plano_codigo_idx"),
            models.Index(
                fields=["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"],
                name="cronograma_chave_composta_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.plano_trabalho_codigo or '—'} — "
            f"{self.mes_cronograma_desembolso or '—'}/{self.ano_cronograma_desembolso or '—'}"
        )


# ---------------------------------------------------------------------------
# PlanoAplicacao — planos de aplicação (dcgce_plano_aplicacao)
# ---------------------------------------------------------------------------

class PlanoAplicacao(models.Model):
    """
    Fonte: data/silver/dcgce_plano_aplicacao.parquet
    Carga: full refresh via loader dedicado.
    Ligação: codigo_plano_trabalho → PlanoTrabalho.plano_trabalho_codigo
    """

    # --- identificação ---
    codigo_plano_trabalho = models.CharField(
        "Código do Plano de Trabalho", max_length=50, db_index=True, null=True, blank=True,
    )
    codigo_unidade_orcamentaria = models.CharField(
        "Cód. Unidade Orçamentária", max_length=50, null=True, blank=True,
    )
    funcao_codigo = models.CharField("Cód. Função", max_length=50, null=True, blank=True)
    subfuncao_codigo = models.CharField("Cód. Subfunção", max_length=50, null=True, blank=True)
    programa_codigo = models.CharField("Cód. Programa", max_length=50, null=True, blank=True)
    identificador_projeto_atividade_codigo = models.CharField(
        "Cód. Identificador Projeto/Atividade", max_length=50, null=True, blank=True,
    )
    projeto_atividade_codigo = models.CharField(
        "Cód. Projeto/Atividade", max_length=50, null=True, blank=True,
    )
    subprojeto_subatividade_codigo = models.CharField(
        "Cód. Subprojeto/Subatividade", max_length=50, null=True, blank=True,
    )
    categoria_economica_despesa_codigo = models.CharField(
        "Cód. Categoria Econômica", max_length=50, null=True, blank=True,
    )
    grupo_despesa_codigo = models.CharField(
        "Cód. Grupo de Despesa", max_length=50, null=True, blank=True,
    )
    modalidade_aplicacao_codigo = models.CharField(
        "Cód. Modalidade de Aplicação", max_length=50, null=True, blank=True,
    )
    elemento_despesa_codigo = models.CharField(
        "Cód. Elemento de Despesa", max_length=50, null=True, blank=True,
    )
    identificador_orcamento_codigo = models.CharField(
        "Cód. Identificador Orçamento", max_length=50, null=True, blank=True,
    )
    fonte_recurso_codigo = models.CharField(
        "Cód. Fonte de Recurso", max_length=50, null=True, blank=True,
    )
    procedencia_codigo = models.CharField(
        "Cód. Procedência", max_length=50, null=True, blank=True,
    )
    funcional_programatica_formatado = models.CharField(
        "Funcional Programática", max_length=50, null=True, blank=True,
    )

    # --- financeiro ---
    valor_concedente = models.DecimalField(
        "Valor Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_proponente = models.DecimalField(
        "Valor Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )

    # --- texto ---
    ano_exercicio_programa_trabalho = models.CharField(
        "Ano Exercício", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Plano de Aplicação"
        verbose_name_plural = "Planos de Aplicação"
        indexes = [
            models.Index(fields=["codigo_plano_trabalho"], name="plano_aplicacao_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_plano_trabalho or '—'}"


# ---------------------------------------------------------------------------
# TermoAditivo — termos aditivos (dcgce_termo.aditivo)
# ---------------------------------------------------------------------------

class TermoAditivo(models.Model):
    """
    Fonte: data/silver/dcgce_termo.aditivo.parquet
    Carga: full refresh via loader dedicado.
    PK natural: termo_aditivo_codigo_sequencial — ligação com Convenio feita via
    CodigoTermoAditivo.
    """

    # --- identificação ---
    termo_aditivo_codigo_sequencial = models.CharField(
        "Código Sequencial", max_length=50, db_index=True, null=True, blank=True,
    )
    termo_aditivo_numero_termo_aditivo = models.CharField(
        "Número do Termo Aditivo", max_length=50, null=True, blank=True,
    )

    # --- datas ---
    termo_aditivo_data_assinatura = models.DateField(
        "Data de Assinatura", null=True, blank=True,
    )
    termo_aditivo_data_inicio_vigencia = models.DateField(
        "Data Início de Vigência", null=True, blank=True,
    )
    termo_aditivo_data_termino_vigencia = models.DateField(
        "Data Término de Vigência", null=True, blank=True,
    )
    data_termo_aditivo = models.DateField("Data do Termo Aditivo", null=True, blank=True)

    # --- financeiro ---
    valor_aditado_concedente_contratado = models.DecimalField(
        "Valor Aditado Concedente", max_digits=18, decimal_places=2, null=True, blank=True,
    )
    valor_aditado_proponente_contratado = models.DecimalField(
        "Valor Aditado Proponente", max_digits=18, decimal_places=2, null=True, blank=True,
    )

    # --- texto (longo) ---
    termo_aditivo_justificativa = models.TextField("Justificativa", null=True, blank=True)

    # --- texto (curtos) ---
    termo_aditivo_ano = models.CharField("Ano", max_length=255, null=True, blank=True)
    termo_aditivo_alteracao = models.CharField("Alteração", max_length=255, null=True, blank=True)
    termo_aditivo_tipo = models.CharField("Tipo", max_length=255, null=True, blank=True)
    tipo_termo_aditivo = models.CharField("Tipo (alt.)", max_length=255, null=True, blank=True)
    quantidade_termo_aditivo = models.CharField(
        "Quantidade", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Termo Aditivo"
        verbose_name_plural = "Termos Aditivos"
        indexes = [
            models.Index(fields=["termo_aditivo_codigo_sequencial"], name="termo_aditivo_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.termo_aditivo_codigo_sequencial or '—'}"


# ---------------------------------------------------------------------------
# DeclaracaoContrapartida — declarações de contrapartida (dcgce_declaracao_contrapartida)
# ---------------------------------------------------------------------------

class DeclaracaoContrapartida(models.Model):
    """
    Fonte: data/silver/dcgce_declaracao_contrapartida.parquet
    Carga: full refresh via loader dedicado.
    PK natural: declaracao_contrapartida_codigo
    """

    # --- identificação ---
    declaracao_contrapartida_codigo = models.CharField(
        "Código da Declaração", max_length=50, db_index=True, null=True, blank=True,
    )
    declaracao_contrapartida_codigo_nota_tecnica = models.CharField(
        "Código Nota Técnica", max_length=50, null=True, blank=True,
    )
    declaracao_contrapartida_codigo_parecer_aprovacao = models.CharField(
        "Código Parecer de Aprovação", max_length=50, null=True, blank=True,
    )

    # --- datas ---
    declaracao_contrapartida_data_completa_emissao = models.DateField(
        "Data Completa de Emissão", null=True, blank=True,
    )
    declaracao_contrapartida_data_emissao = models.DateField(
        "Data de Emissão", null=True, blank=True,
    )
    declaracao_contrapartida_data_completa_parecer_aprovacao = models.DateField(
        "Data Completa Parecer Aprovação", null=True, blank=True,
    )
    declaracao_contrapartida_data_parecer_aprovacao = models.DateField(
        "Data Parecer Aprovação", null=True, blank=True,
    )

    # --- texto (longos) ---
    declaracao_contrapartida_observacao = models.TextField(
        "Observação", null=True, blank=True,
    )
    declaracao_contrapartida_observacao_aprovacao = models.TextField(
        "Observação de Aprovação", null=True, blank=True,
    )

    # --- texto (curtos) ---
    declaracao_contrapartida_ano = models.CharField("Ano", max_length=255, null=True, blank=True)
    declaracao_contrapartida_status = models.CharField(
        "Status", max_length=255, null=True, blank=True,
    )
    declaracao_contrapartida_matricula_aprovacao = models.CharField(
        "Matrícula Aprovação", max_length=255, null=True, blank=True,
    )
    declaracao_contrapartida_momento = models.CharField(
        "Momento", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Declaração de Contrapartida"
        verbose_name_plural = "Declarações de Contrapartida"
        indexes = [
            models.Index(
                fields=["declaracao_contrapartida_codigo"],
                name="decl_contrap_codigo_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.declaracao_contrapartida_codigo or '—'}"


# ---------------------------------------------------------------------------
# ProrrogacaoOficio — prorrogações de ofício (dcgce_prorrogacao_oficio)
# ---------------------------------------------------------------------------

class ProrrogacaoOficio(models.Model):
    """
    Fonte: data/silver/dcgce_prorrogacao_oficio.parquet
    Carga: full refresh via loader dedicado.
    Ligação: prorrogacao_oficio_codigo_convenio → Convenio.convenio_codigo
    """

    # --- identificação ---
    prorrogacao_oficio_codigo = models.CharField(
        "Código da Prorrogação", max_length=50, null=True, blank=True,
    )
    prorrogacao_oficio_codigo_convenio = models.CharField(
        "Código do Convênio", max_length=50, db_index=True, null=True, blank=True,
    )

    # --- datas ---
    prorrogacao_oficio_data_inicio_vigencia = models.DateField(
        "Data Início de Vigência", null=True, blank=True,
    )
    prorrogacao_oficio_data_termino_vigencia = models.DateField(
        "Data Término de Vigência", null=True, blank=True,
    )
    prorrogacao_oficio_data_envio = models.DateField(
        "Data de Envio", null=True, blank=True,
    )
    prorrogacao_oficio_data_parecer = models.DateField(
        "Data do Parecer", null=True, blank=True,
    )
    prorrogacao_oficio_data_publicacao = models.DateField(
        "Data de Publicação", null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Prorrogação de Ofício"
        verbose_name_plural = "Prorrogações de Ofício"
        indexes = [
            models.Index(
                fields=["prorrogacao_oficio_codigo_convenio"],
                name="prorrogacao_conv_codigo_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.prorrogacao_oficio_codigo or '—'} — Conv. {self.prorrogacao_oficio_codigo_convenio or '—'}"


# ---------------------------------------------------------------------------
# NtEmenda — notas técnicas de emendas parlamentares (dcgce_sigcon_nt_emenda)
# ---------------------------------------------------------------------------

class NtEmenda(models.Model):
    """
    Fonte: data/silver/dcgce_sigcon_nt_emenda.parquet
    Carga: full refresh via loader dedicado.
    Ligação: plano_trabalho_codigo → PlanoTrabalho.plano_trabalho_codigo
    """

    # --- identificação ---
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. Unidade Orçamentária", max_length=50, null=True, blank=True,
    )
    plano_trabalho_codigo = models.CharField(
        "Código do Plano de Trabalho", max_length=50, db_index=True, null=True, blank=True,
    )

    # --- texto ---
    nt_emenda_no = models.CharField("Nº NT Emenda", max_length=255, null=True, blank=True)
    nt_emenda_nome = models.CharField("Nome NT Emenda", max_length=255, null=True, blank=True)
    nota_tecnica_emenda_parlamentar_federal_situacao = models.CharField(
        "Situação", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "NT Emenda Parlamentar"
        verbose_name_plural = "NTs Emendas Parlamentares"
        indexes = [
            models.Index(fields=["plano_trabalho_codigo"], name="nt_emenda_plano_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nt_emenda_no or '—'} — {self.nt_emenda_nome or '—'}"


# ---------------------------------------------------------------------------
# Esfera — lookup: CNPJ do concedente → esfera (dcgce_esfera)
# ---------------------------------------------------------------------------

class Esfera(models.Model):
    """
    Fonte: data/silver/dcgce_esfera.parquet
    Carga: full refresh via loader dedicado.
    Tabela de dimensão: concedente_cnpj é chave única.
    """

    concedente_cnpj = models.CharField(
        "CNPJ do Concedente", max_length=50, db_index=True, unique=True, null=True, blank=True,
    )
    concedente_esfera = models.CharField(
        "Esfera", max_length=255, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Esfera do Concedente"
        verbose_name_plural = "Esferas dos Concedentes"

    def __str__(self) -> str:
        return f"{self.concedente_cnpj or '—'} — {self.concedente_esfera or '—'}"


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

# ---------------------------------------------------------------------------
# ControleSEI — planilha interna de controle do nº SEI por convênio
# ---------------------------------------------------------------------------

class ControleSEI(models.Model):
    """
    Fonte: data/silver/controle_sei.parquet
    Carga: full refresh via carregar_controle_sei().

    Chave de ligação principal:
      no_siafi_sigcon → Convenio.convenio_numero_sequencial_siafi  (SIAFI puro, não siafi_uo)
    Chave secundária (SICONV):
      no_proposta_siconv → ConvenioIntegrado.codigo_siconv

    Atenção: o Parquet Silver usa nomes no_siafi_(sigcon) e no_proposta_(siconv)
    com parênteses — o loader mapeia para estes campos sem parênteses.
    """

    no_sei = models.CharField(
        "Nº SEI", max_length=100, db_index=True, null=True, blank=True,
    )
    no_siafi_sigcon = models.CharField(
        "Nº SIAFI (SIGCON)", max_length=50, db_index=True, null=True, blank=True,
    )
    no_proposta_siconv = models.CharField(
        "Nº Proposta (SICONV)", max_length=50, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Controle SEI"
        verbose_name_plural = "Controles SEI"
        indexes = [
            models.Index(fields=["no_siafi_sigcon"], name="sei_siafi_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.no_sei or '—'} → SIAFI {self.no_siafi_sigcon or '—'}"


# ---------------------------------------------------------------------------
# UnidadesExecutoras — dados das unidades executoras do SIGCON-MG (dcgce_unidades.executoras)
# ---------------------------------------------------------------------------

class UnidadesExecutoras(models.Model):
    """
    Fonte: data/silver/dcgce_unidades_executoras.parquet
    Carga: full refresh via loader dedicado.
    Ligação: convenio_codigo → Convenio.convenio_codigo
    """

    # --- identificação ---
    unidade_orcamentaria_codigo = models.CharField(
        "Cód. UO", max_length=50, db_index=True, null=True, blank=True,
    )
    convenio_numero_sequencial_siafi = models.CharField(
        "Código SIAFI", max_length=50, null=True, blank=True,
    )
    unidade_executora = models.CharField(
        "Unidade Executora", max_length=50, null=True, blank=True,
    )
    convenio_codigo = models.CharField(
        "Código SIGCON", max_length=50, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Convênio — Unidade Executora"
        verbose_name_plural = "Convênios — Unidades Executoras"
        indexes = [
            models.Index(fields=["convenio_numero_sequencial_siafi", "unidade_orcamentaria_codigo"],
                name="unid_exec_chave_composta_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.convenio_codigo or '—'}"
