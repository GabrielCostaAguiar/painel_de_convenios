"""
Models das tabelas do GRP.

Vieram do app das Consultas SIGCON (label "convenios"), onde nasceram. O que
mudou foi o app; **as tabelas continuam as mesmas**, e por isso cada Meta traz
`db_table` com o nome antigo (`convenios_dadosgrp`, ...). A troca de app foi
feita com SeparateDatabaseAndState nas migracoes: o Django atualiza o estado,
o banco nao e tocado.

Sao tabelas planas, ligadas entre si por nr_grp na consulta — nao ha nenhuma
ForeignKey, nem entre elas nem para os models do SIGCON.
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
    concedente_cnpj = models.CharField(
        "CNPJ do Concedente", max_length=50, null=True, blank=True,
    )
    convenente_cnpj = models.CharField(
        "CNPJ do Convenente", max_length=50, null=True, blank=True,
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
        # A tabela ja existia sob o label "convenios"; o model mudou de app,
        # ela nao. Sem db_table explicito o Django procuraria grp_dadosgrp.
        db_table = "convenios_dadosgrp"
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
        # A tabela ja existia sob o label "convenios"; o model mudou de app,
        # ela nao. Sem db_table explicito o Django procuraria grp_recursoscontrapartidagrp.
        db_table = "convenios_recursoscontrapartidagrp"
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
        # A tabela ja existia sob o label "convenios"; o model mudou de app,
        # ela nao. Sem db_table explicito o Django procuraria grp_recursosconcedentegrp.
        db_table = "convenios_recursosconcedentegrp"
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
        # A tabela ja existia sob o label "convenios"; o model mudou de app,
        # ela nao. Sem db_table explicito o Django procuraria grp_planoaplicacaogrp.
        db_table = "convenios_planoaplicacaogrp"
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
        "Descrição do Item a executar", max_length=5000, null=True, blank=True,
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
        # A tabela ja existia sob o label "convenios"; o model mudou de app,
        # ela nao. Sem db_table explicito o Django procuraria grp_planoaplicacaogrpdetalhes.
        db_table = "convenios_planoaplicacaogrpdetalhes"
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
        # A tabela ja existia sob o label "convenios"; o model mudou de app,
        # ela nao. Sem db_table explicito o Django procuraria grp_esferagrp.
        db_table = "convenios_esferagrp"
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
        # A tabela ja existia sob o label "convenios"; o model mudou de app,
        # ela nao. Sem db_table explicito o Django procuraria grp_cronogramadesembolsogrp.
        db_table = "convenios_cronogramadesembolsogrp"
        verbose_name = "GRP — Cronograma de Desembolso"
        verbose_name_plural = "GRP — Cronogramas de Desembolso"
        indexes = [
            models.Index(fields=["nr_grp"], name="grp_cronograma_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nr_grp or '—'} — {self.parcela_desembolso or '—'}"

class TabelaUoGrp(models.Model):
    """
    Fonte: data/silver/dcgce_tabela_uo.xlsx
    Carga: full refresh via loader dedicado.
    Ligação: uo_cod → DadosGrp.uo_cod
    """

    # --- identificação ---
    uo_cod = models.CharField(
        "Código UO", max_length=5, null=True, blank=True,
    )
    uo_nome = models.CharField(
        "Nome da UO", max_length=255, null=True, blank=True,
    )

        # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        db_table = "convenios_tabelauogrp"
        verbose_name = "GRP — Tabela de Unidades Orçamentárias"
        verbose_name_plural = "GRP — Tabelas de Unidades Orçamentárias"
        indexes = [
            models.Index(fields=["uo_cod"], name="grp_tabela_uo_codigo_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.uo_cod or '—'} — {self.uo_nome or '—'}"

# ---------------------------------------------------------------------------
# GRP — Instrumento (consulta 01 do Modelo de Extração GRP v1.1)
# Grão: 1 linha por proposta/instrumento. Carga: full refresh a partir da silver.
# Os nomes dos campos são IGUAIS às colunas do parquet (bloco "renomear" do YAML),
# o que permite um loader genérico, sem de-para escrito à mão.
# ---------------------------------------------------------------------------
class GrpInstrumento(models.Model):
    """Proposta ou instrumento do GRP. Instrumentos têm nr_grp; propostas têm cd_proposta."""

    # --- Identificação ---
    tp_proposta_instrumento = models.TextField(null=True, blank=True)  # Tipo Proposta/Instrumento
    nr_proposta_instrumento = models.CharField(max_length=100, null=True, blank=True)  # Número Proposta/Instrumento
    nr_cnpj_proponente = models.CharField(max_length=14, null=True, blank=True)  # Proponente/ConvenenteGRP - CNPJ-CAPJ
    nm_proponente = models.TextField(null=True, blank=True)  # Proponente/ConvenenteGRP - Nome
    nm_projeto = models.TextField(null=True, blank=True)  # Nome Projeto
    nr_grp = models.CharField(max_length=20, unique=True, null=True, blank=True)  # Número InstrumentoGRP
    nr_instrumento = models.CharField(max_length=100, null=True, blank=True)  # Número Instrumento
    nr_instrumento_transferegov = models.CharField(max_length=100, null=True, blank=True)  # Número Instrumento+Brasil
    cd_proposta_origem = models.CharField(max_length=100, null=True, blank=True)  # Código PropostaOrigem
    cd_tipo_instrumento_juridico = models.CharField(max_length=100, null=True, blank=True)  # Tipo InstrumentoJurídico - Código
    ds_tipo_instrumento_juridico = models.TextField(null=True, blank=True)  # Tipo InstrumentoJurídico - Descrição
    ds_situacao_instrumento = models.TextField(null=True, blank=True)  # Situação Instrumento
    cd_proposta = models.CharField(max_length=30, unique=True, null=True, blank=True)  # Código Proposta
    tp_proposta = models.TextField(null=True, blank=True)  # Tipo Proposta
    nr_proposta_transferegov = models.CharField(max_length=100, null=True, blank=True)  # Número Proposta+Brasil
    ds_situacao_proposta = models.TextField(null=True, blank=True)  # Situação Proposta
    tx_objeto_projeto = models.TextField(null=True, blank=True)  # Objeto Projeto

    # --- Números SEI ---
    nr_sei_1 = models.CharField(max_length=100, null=True, blank=True)  # Número SEI 1
    nr_sei_2 = models.CharField(max_length=100, null=True, blank=True)  # Número SEI 2
    nr_sei_3 = models.CharField(max_length=100, null=True, blank=True)  # Número SEI 3
    nr_sei_4 = models.CharField(max_length=100, null=True, blank=True)  # Número SEI 4
    nr_sei_5 = models.CharField(max_length=100, null=True, blank=True)  # Número SEI 5

    # --- Categorias e flags do projeto ---
    ds_categoria_projeto_1 = models.TextField(null=True, blank=True)  # CategoriaProjeto 1
    ds_categoria_projeto_2 = models.TextField(null=True, blank=True)  # CategoriaProjeto 2
    ds_categoria_projeto_3 = models.TextField(null=True, blank=True)  # CategoriaProjeto 3
    fl_interveniente_executor = models.BooleanField(null=True, blank=True)  # IntervenienteExecutor S/N
    fl_emenda_parlamentar = models.BooleanField(null=True, blank=True)  # EmendaParlamentar S/N
    fl_instrumento_financiador = models.BooleanField(null=True, blank=True)  # Instrumento Financiador S/N
    tx_capacidade_tecnica_gerencial = models.TextField(null=True, blank=True)  # Capacidade TécnicaGerencial
    tx_relacao_projeto_acao = models.TextField(null=True, blank=True)  # Relação Projeto AçãoOrçamentária
    fl_convenio_restrito = models.BooleanField(null=True, blank=True)  # Convênio Restrito S/N
    tx_justificativa_restricao = models.TextField(null=True, blank=True)  # Justificativa Restrição

    # --- Valores da proposta ---
    vl_proposta_concedente = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Proposta - Concedente
    vl_proposta_contrapartida_fin = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Proposta - Contrapartida Financeira
    vl_proposta_contrapartida_nao_fin = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Proposta - Contrapartida nãoFinanceira
    vl_proposta_concedente_executado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Proposta - Concedente Executado
    vl_proposta_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Proposta - Total

    # --- Valores do instrumento (inicial = pactuado; demais = com aditivos) ---
    vl_instrumento_concedente_inicial = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Concedente Inicial
    vl_instrumento_contrapartida_fin_inicial = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Contrapartida Financeira Inicial
    vl_instrumento_contrapartida_nao_fin_inicial = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Contrapartida nãoFinanceira Inicial
    vl_instrumento_concedente_executado_inicial = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Concedente Executado Inicial
    vl_instrumento_total_inicial = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Total Inicial
    vl_instrumento_concedente = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Concedente
    vl_instrumento_contrapartida_fin = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Contrapartida Financeira
    vl_instrumento_contrapartida_nao_fin = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Contrapartida nãoFinanceira
    vl_instrumento_concedente_executado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Concedente Executado
    vl_instrumento_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento - Total
    vl_rendimento_autorizado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Rendimento Autorizado

    # --- Convenente, datas e dados operacionais ---
    nr_cnpj_convenente = models.CharField(max_length=14, null=True, blank=True)  # ConvenenteInstrumento - CNPJ-CAPJ
    nm_convenente = models.TextField(null=True, blank=True)  # ConvenenteInstrumento - Nome
    tx_justificativa_instrumento = models.TextField(null=True, blank=True)  # Justificativa Instrumento
    dt_assinatura = models.DateField(null=True, blank=True)  # Data Assinatura Instrumento
    dt_publicacao = models.DateField(null=True, blank=True)  # Data Publicação Instrumento
    dt_vigencia_inicio = models.DateField(null=True, blank=True)  # Data Vigência Instrumento - Inicio
    dt_vigencia_termino = models.DateField(null=True, blank=True)  # Data Vigência Instrumento - Término
    dt_vigencia_termino_inicial = models.DateField(null=True, blank=True)  # Data VigênciaInicial Instrumento - Término
    fl_contrato_repasse = models.BooleanField(null=True, blank=True)  # Contrato Repasse S/N
    nr_contrato_repasse = models.CharField(max_length=100, null=True, blank=True)  # Contrato Repasse
    nr_cnpj_mandataria = models.CharField(max_length=14, null=True, blank=True)  # Mandatária - CNPJ
    nm_mandataria = models.TextField(null=True, blank=True)  # Mandatária - Nome
    tp_transferencia = models.TextField(null=True, blank=True)  # Tipo Transferência
    fl_obtv = models.BooleanField(null=True, blank=True)  # OBTV S/N
    fl_contrapartida_depositada = models.BooleanField(null=True, blank=True)  # Contrapartida Depositada S/N
    fl_cartao_convenio = models.BooleanField(null=True, blank=True)  # CartãoConvênio S/N
    fl_validacao_vigencia_execucao = models.BooleanField(null=True, blank=True)  # Validação Vigência Execução S/N
    fl_validacao_item_despesa = models.BooleanField(null=True, blank=True)  # Validação ItemDespesa S/N
    fl_financiamento_despesa_pessoal = models.BooleanField(null=True, blank=True)  # Financiamento DespesaPessoal S/N
    fl_autorizacao_uso_rendimento = models.BooleanField(null=True, blank=True)  # Autorização Uso Rendimento S/N

    class Meta:
        db_table = "grp_instrumento"
        verbose_name = "Instrumento GRP"
        verbose_name_plural = "Instrumentos GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or f"Proposta {self.cd_proposta}"

class GrpConcedente(models.Model):
    """
    Fonte: data/silver/dcgce_concedente.parquet
    Carga: full refresh via loader dedicado.
    Ligação: nr_cnpj_concedente → GrpInstrumento.nr_cnpj_concedente
    """

    # --- identificação ---
    nr_grp = models.CharField(
        max_length=20, db_index=True, unique=False, null=True, blank=True
    ) # Número InstrumentoGRP
    cd_proposta = models.CharField(
        max_length=30, unique=False, null=True, blank=True
    )  # Código Proposta
    nr_cnpj_concedente = models.CharField(
        "CNPJ do Concedente", max_length=14, null=True, blank=True,
    ) # Concedente - CNPJ-CAPJ
    nm_concedente = models.CharField(
        "Nome do Concedente", max_length=255, null=True, blank=True,
    ) # Concedente - Nome
    ds_esfera_atuacao = models.CharField(
        "Esfera de Atuação", max_length=255, null=True, blank=True,
    ) #  Concedente - EsferaAtuação

    class Meta:
        db_table = "grp_concedente"
        verbose_name = "Concedente GRP"
        verbose_name_plural = "Concedentes GRP"
        ordering = ["nr_grp"]

    def __str__(self) -> str:
        return f"{self.nr_cnpj_concedente or '—'} — {self.nm_concedente or '—'}"
    # ---------------------------------------------------------------------------
# GRP — Instrumento (consulta 02 do Modelo de Extração GRP v1.2)
# Grão: 1 linha por instrumento. Prioridade: Should
# ---------------------------------------------------------------------------
class GrpPrestacaoContas(models.Model):
    """Fase própria do ciclo de vida, vazia para instrumentos vigentes. Alimenta um painel específico de prestação de contas. P"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    fl_pc_obrigatoria = models.BooleanField(null=True, blank=True)  # PrestaçãoContas Obrigatória S/N
    tx_pc_justificativa_nao_obrigatoriedade = models.TextField(null=True, blank=True)  # PrestaçãoContas Justificativa NãoObrigatoriedade
    qt_pc_prazo = models.IntegerField(null=True, blank=True)  # Prazo PrestaçãoContas
    dt_pc_limite = models.DateField(null=True, blank=True)  # Data Limite PrestaçãoContas
    dt_pc_limite_inicial = models.DateField(null=True, blank=True)  # Data Limite PrestaçãoContas Inicial
    tp_pc_final = models.TextField(null=True, blank=True)  # Tipo PrestaçãoContas Final
    dt_pc_envio = models.DateField(null=True, blank=True)  # Data Envio PrestaçãoContas
    fl_conclusao_objeto = models.BooleanField(null=True, blank=True)  # Conclusão Objeto S/N
    tx_pc_justificativa_conclusao = models.TextField(null=True, blank=True)  # PrestaçãoContas Justificativa Conclusão
    fl_pc_finalizada = models.BooleanField(null=True, blank=True)  # PrestaçãoContas Finalizada S/N
    fl_pendencia_contabilizacao = models.BooleanField(null=True, blank=True)  # Pendência Contabilização S/N
    dt_pc_finalizacao = models.DateField(null=True, blank=True)  # Data Finalização PrestaçãoContas
    tx_pc_justificativa_aprovacao = models.TextField(null=True, blank=True)  # PrestaçãoContas Justificativa Aprovação
    ds_pc_situacao_aprovacao = models.TextField(null=True, blank=True)  # PrestaçãoContas Situação Aprovação

    class Meta:
        db_table = "grp_prestacao_contas"
        verbose_name = "Prestacao Contas GRP"
        verbose_name_plural = "Prestacao Contas GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Instrumento (consulta 03 do Modelo de Extração GRP v1.2)
# Grão: 1 linha por instrumento. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpPlanejamentoObras(models.Model):
    """Só se aplica a instrumentos de obras. Separar evita 13 colunas quase sempre vazias no núcleo. Também é 1:1 e pode ser in"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    fl_projeto_basico_elaborado = models.BooleanField(null=True, blank=True)  # ProjetoBásico Elaborado S/N
    fl_projeto_basico_em_elaboracao = models.BooleanField(null=True, blank=True)  # ProjetoBásico emElaboração S/N
    fl_projeto_complementar = models.BooleanField(null=True, blank=True)  # ProjetoComplementar S/N
    fl_projeto_complementar_em_elaboracao = models.BooleanField(null=True, blank=True)  # ProjetoComplementar emElaboração S/N
    fl_licenciamento_ambiental = models.BooleanField(null=True, blank=True)  # LicenciamentoAmbiental S/N
    fl_licenciamento_ambiental_em_obtencao = models.BooleanField(null=True, blank=True)  # LicenciamentoAmbiental emObtenção S/N
    fl_titularidade_imovel = models.BooleanField(null=True, blank=True)  # TitularidadeImóvel S/N
    fl_titularidade_imovel_em_regularizacao = models.BooleanField(null=True, blank=True)  # TitularidadeImóvel emRegularização S/N
    fl_desapropriacao = models.BooleanField(null=True, blank=True)  # Desapropriação S/N
    ds_desapropriacao_origem_recurso = models.TextField(null=True, blank=True)  # Desapropriação Origem Recurso
    fl_desapropriacao_providencias = models.BooleanField(null=True, blank=True)  # Desapropriação Providências S/N
    tx_desapropriacao_providencias = models.TextField(null=True, blank=True)  # Desapropriação Providências
    ds_competencia_execucao_obra = models.TextField(null=True, blank=True)  # Competência Execução Obra

    class Meta:
        db_table = "grp_planejamento_obras"
        verbose_name = "Planejamento Obras GRP"
        verbose_name_plural = "Planejamento Obras GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Instrumento (consulta 04 do Modelo de Extração GRP v1.2)
# Grão: 1 linha por instrumento. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpPropostaMarcoLogico(models.Model):
    """Textos longos do marco lógico: pesados, raramente filtrados e sujeitos a corte no Excel. Deve permanecer separada também"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    tx_interesses_reciprocos = models.TextField(null=True, blank=True)  # Interesses Recíprocos Projeto
    tx_relacao_projeto_objetivo = models.TextField(null=True, blank=True)  # Relação Projeto Objetivo
    tx_publico_alvo = models.TextField(null=True, blank=True)  # Público Alvo Projeto
    tx_problema = models.TextField(null=True, blank=True)  # Problema Projeto
    tx_resultado_esperado = models.TextField(null=True, blank=True)  # ResultadoEsperado Projeto
    tx_objetivo_geral = models.TextField(null=True, blank=True)  # ObjetivoGeral Projeto
    tx_indicadores_objetivo_geral = models.TextField(null=True, blank=True)  # Indicadores ObjetivoGeral
    tx_metas_prazo_objetivo_geral = models.TextField(null=True, blank=True)  # MetasPrazo ObjetivoGeral
    tx_criterios_aceitacao_objetivo_geral = models.TextField(null=True, blank=True)  # Critérios Aceitação ObjetivoGeral
    tx_verificacao_indicadores_objetivo_geral = models.TextField(null=True, blank=True)  # Verificação Indicadores ObjetivoGeral
    tx_pressupostos_objetivo_geral = models.TextField(null=True, blank=True)  # Pressupostos ObjetivoGeral
    tx_proposito = models.TextField(null=True, blank=True)  # Propósito Projeto
    tx_indicadores_proposito = models.TextField(null=True, blank=True)  # Indicadores Propósito
    tx_metas_prazo_proposito = models.TextField(null=True, blank=True)  # MetasPrazo Propósito
    tx_criterios_aceitacao_proposito = models.TextField(null=True, blank=True)  # Critérios Aceitação Propósito
    tx_verificacao_indicadores_proposito = models.TextField(null=True, blank=True)  # Verificação Indicadores Propósito
    tx_pressupostos_proposito = models.TextField(null=True, blank=True)  # Pressupostos Propósito

    class Meta:
        db_table = "grp_proposta_marco_logico"
        verbose_name = "Proposta Marco Logico GRP"
        verbose_name_plural = "Proposta Marco Logico GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Partes e abrangência (consulta 06 do Modelo de Extração GRP v1.2)
# Grão: instrumento x emenda. Prioridade: Must
# ---------------------------------------------------------------------------
class GrpEmenda(models.Model):
    """Elo central da DCGCE com as emendas parlamentares. Permite painéis por parlamentar, ano e situação da emenda."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    nr_ano_emenda = models.CharField(max_length=100, null=True, blank=True)  # Emenda - Ano
    nr_emenda = models.CharField(max_length=100, null=True, blank=True)  # Emenda - Número
    nm_parlamentar = models.TextField(null=True, blank=True)  # Emenda - Parlamentar
    tp_transferencia_emenda = models.TextField(null=True, blank=True)  # Emenda - Tipo Transferência
    ds_situacao_emenda = models.TextField(null=True, blank=True)  # Emenda - Situação

    class Meta:
        db_table = "grp_emenda"
        verbose_name = "Emenda GRP"
        verbose_name_plural = "Emenda GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Partes e abrangência (consulta 07 do Modelo de Extração GRP v1.2)
# Grão: instrumento x interveniente. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpInterveniente(models.Model):
    """Identifica quem executa em nome do convenente, quando há interveniente (ver fl_interveniente_executor na 01)."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    nm_interveniente = models.TextField(null=True, blank=True)  # Interveniente - Nome
    sg_interveniente = models.CharField(max_length=100, null=True, blank=True)  # Interveniente - Sigla
    cd_interveniente = models.CharField(max_length=100, null=True, blank=True)  # Interveniente - Código
    nr_cnpj_interveniente = models.CharField(max_length=14, null=True, blank=True)  # Interveniente - CNPJ-CAPJ

    class Meta:
        db_table = "grp_interveniente"
        verbose_name = "Interveniente GRP"
        verbose_name_plural = "Interveniente GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Partes e abrangência (consulta 08 do Modelo de Extração GRP v1.2)
# Grão: instrumento x unidade administrativa. Prioridade: Should
# ---------------------------------------------------------------------------
class GrpUnidadeExecutora(models.Model):
    """Responde à pergunta 'quais as unidades executoras?'. Os códigos de órgão devem apontar para a dimensão única de UO/órgão"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    cd_orgao_unidade_adm = models.CharField(max_length=100, null=True, blank=True)  # Órgão UnidadeAdm - Código
    sg_orgao_unidade_adm = models.CharField(max_length=100, null=True, blank=True)  # Órgão UnidadeAdm - Sigla
    nm_orgao_unidade_adm = models.TextField(null=True, blank=True)  # Órgão UnidadeAdm - Nome
    cd_unidade_adm = models.CharField(max_length=100, null=True, blank=True)  # UnidadeAdm - Código
    nm_unidade_adm = models.TextField(null=True, blank=True)  # UnidadeAdm - Nome

    class Meta:
        db_table = "grp_unidade_executora"
        verbose_name = "Unidade Executora GRP"
        verbose_name_plural = "Unidade Executora GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Partes e abrangência (consulta 09 do Modelo de Extração GRP v1.2)
# Grão: instrumento x município. Prioridade: Should
# ---------------------------------------------------------------------------
class GrpMunicipioAtendido(models.Model):
    """Base para mapas e recortes territoriais. O código do município permite cruzar com IBGE."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    nm_municipio = models.TextField(null=True, blank=True)  # MunicípioAtendido - Nome
    cd_municipio = models.CharField(max_length=100, null=True, blank=True)  # MunicípioAtendido - Código
    sg_uf = models.CharField(max_length=100, null=True, blank=True)  # UnidadeFederação

    class Meta:
        db_table = "grp_municipio_atendido"
        verbose_name = "Municipio Atendido GRP"
        verbose_name_plural = "Municipio Atendido GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Partes e abrangência (consulta 10 do Modelo de Extração GRP v1.2)
# Grão: instrumento x região x município da região. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpRegiaoAtendida(models.Model):
    """Recorte por região. Atenção: o grão inclui o município da região, então nunca juntar com a 09 sem agregar antes."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    nm_regiao = models.TextField(null=True, blank=True)  # RegiãoAtendida - Nome
    cd_regiao = models.CharField(max_length=100, null=True, blank=True)  # RegiãoAtendida - Código
    ds_situacao_regiao = models.TextField(null=True, blank=True)  # RegiãoAtendida - Situação
    nm_municipio_regiao = models.TextField(null=True, blank=True)  # MunicípioRegião - Nome
    cd_municipio_regiao = models.CharField(max_length=100, null=True, blank=True)  # MunicípioRegião - Código
    sg_uf_municipio_regiao = models.CharField(max_length=100, null=True, blank=True)  # MunicípioRegião - UF

    class Meta:
        db_table = "grp_regiao_atendida"
        verbose_name = "Regiao Atendida GRP"
        verbose_name_plural = "Regiao Atendida GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Financeiro / Plano de Aplicação (consulta 11 do Modelo de Extração GRP v1.2)
# Grão: instrumento x UO de arrecadação x fonte x IPU x situação. Prioridade: Must
# ---------------------------------------------------------------------------
class GrpRecursoConcedente(models.Model):
    """Origem do recurso federal no orçamento estadual, por UO arrecadadora, com o órgão gestor. Substitui a atual recursos_con"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    cd_uo_arrecadacao = models.CharField(max_length=100, null=True, blank=True)  # UnidOrçamentária Arrecadação - Código
    nm_uo_arrecadacao = models.TextField(null=True, blank=True)  # UnidOrçamentária Arrecadação - Nome
    sg_uo_arrecadacao = models.CharField(max_length=100, null=True, blank=True)  # UnidOrçamentária Arrecadação - Sigla
    ds_situacao_recurso_concedente = models.TextField(null=True, blank=True)  # Situação Recurso Concedente
    vl_recurso_concedente = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Recurso Concedente
    cd_orgao_gestor_arrecadacao = models.CharField(max_length=100, null=True, blank=True)  # ÓrgãoGestor Arrecadação - Código
    nm_orgao_gestor_arrecadacao = models.TextField(null=True, blank=True)  # ÓrgãoGestor Arrecadação - Nome
    sg_orgao_gestor_arrecadacao = models.CharField(max_length=100, null=True, blank=True)  # ÓrgãoGestor Arrecadação - Sigla
    cd_fonte_recurso = models.CharField(max_length=100, null=True, blank=True)  # FonteRecurso - Código
    cd_ipu = models.CharField(max_length=100, null=True, blank=True)  # IPU - Código

    class Meta:
        db_table = "grp_recurso_concedente"
        verbose_name = "Recurso Concedente GRP"
        verbose_name_plural = "Recurso Concedente GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Financeiro / Plano de Aplicação (consulta 12 do Modelo de Extração GRP v1.2)
# Grão: instrumento x UO financiadora x fonte x IPU x situação. Prioridade: Must
# ---------------------------------------------------------------------------
class GrpRecursoContrapartida(models.Model):
    """Contrapartida financeira do estado por UO financiadora. Substitui a atual recursos_contrapartida_grp."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    cd_uo_financiadora = models.CharField(max_length=100, null=True, blank=True)  # UnidOrçamentária Financiadora - Código
    nm_uo_financiadora = models.TextField(null=True, blank=True)  # UnidOrçamentária Financiadora - Nome
    sg_uo_financiadora = models.CharField(max_length=100, null=True, blank=True)  # UnidOrçamentária Financiadora - Sigla
    ds_situacao_contrapartida = models.TextField(null=True, blank=True)  # Situação Contrapartida Financeira
    vl_contrapartida_financeira = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Contrapartida Financeira
    cd_orgao_gestor_financiadora = models.CharField(max_length=100, null=True, blank=True)  # ÓrgãoGestor Financiadora - Código
    nm_orgao_gestor_financiadora = models.TextField(null=True, blank=True)  # ÓrgãoGestor Financiadora - Nome
    sg_orgao_gestor_financiadora = models.CharField(max_length=100, null=True, blank=True)  # ÓrgãoGestor Financiadora - Sigla
    cd_fonte_recurso_contrapartida = models.CharField(max_length=100, null=True, blank=True)  # FonteRecurso - Código
    cd_ipu_contrapartida = models.CharField(max_length=100, null=True, blank=True)  # IPU - Código

    class Meta:
        db_table = "grp_recurso_contrapartida"
        verbose_name = "Recurso Contrapartida GRP"
        verbose_name_plural = "Recurso Contrapartida GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Financeiro / Plano de Aplicação (consulta 13 do Modelo de Extração GRP v1.2)
# Grão: instrumento x dotação x situação. Prioridade: Should
# ---------------------------------------------------------------------------
class GrpDotacaoContrapartida(models.Model):
    """Dotação orçamentária que suporta a contrapartida. Complementa a 12."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    cd_dotacao_contrapartida = models.CharField(max_length=100, null=True, blank=True)  # Dotação Contrapartida
    ds_situacao_dotacao = models.TextField(null=True, blank=True)  # Situação Dotação Contrapartida
    vl_dotacao_contrapartida = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Dotação Contrapartida

    class Meta:
        db_table = "grp_dotacao_contrapartida"
        verbose_name = "Dotacao Contrapartida GRP"
        verbose_name_plural = "Dotacao Contrapartida GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Financeiro / Plano de Aplicação (consulta 14 do Modelo de Extração GRP v1.2)
# Grão: instrumento x ação x UO de execução x situação. Prioridade: Must
# ---------------------------------------------------------------------------
class GrpAcaoOrcamentaria(models.Model):
    """Vínculo com o orçamento estadual. É a ponte natural com SIAFI/SIGCON (ação + UO)."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    cd_acao = models.CharField(max_length=100, null=True, blank=True)  # Código Ação
    cd_uo_execucao = models.CharField(max_length=100, null=True, blank=True)  # UnidOrçamentária Execução - Código
    nm_uo_execucao = models.TextField(null=True, blank=True)  # UnidOrçamentária Execução - Nome
    sg_uo_execucao = models.CharField(max_length=100, null=True, blank=True)  # UnidOrçamentária Execução - Sigla
    ds_situacao_acao = models.TextField(null=True, blank=True)  # Situação Ação Orçamentária
    vl_execucao_orcamentaria = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Execução Orçamentária
    cd_orgao_gestor_execucao = models.CharField(max_length=100, null=True, blank=True)  # ÓrgãoGestor Execução - Código
    nm_orgao_gestor_execucao = models.TextField(null=True, blank=True)  # ÓrgãoGestor Execução - Nome
    sg_orgao_gestor_execucao = models.CharField(max_length=100, null=True, blank=True)  # ÓrgãoGestor Execução - Sigla

    class Meta:
        db_table = "grp_acao_orcamentaria"
        verbose_name = "Acao Orcamentaria GRP"
        verbose_name_plural = "Acao Orcamentaria GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Financeiro / Plano de Aplicação (consulta 15 do Modelo de Extração GRP v1.2)
# Grão: instrumento x instrumento financiado. Prioridade: Should
# ---------------------------------------------------------------------------
class GrpInstrumentoFinanciado(models.Model):
    """Responde à pergunta 'quais são os outros instrumentos financiados?'. Relaciona instrumentos entre si."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    nr_instrumento_financiado = models.CharField(max_length=100, null=True, blank=True)  # Número Instrumento Financiado
    tp_instrumento_financiado = models.TextField(null=True, blank=True)  # Tipo Instrumento Financiado
    vl_instrumento_financiado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Instrumento Financiado

    class Meta:
        db_table = "grp_instrumento_financiado"
        verbose_name = "Instrumento Financiado GRP"
        verbose_name_plural = "Instrumento Financiado GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Financeiro / Plano de Aplicação (consulta 16 do Modelo de Extração GRP v1.2)
# Grão: instrumento x item a executar. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpItemExecutar(models.Model):
    """Detalhe da despesa prevista. Maior volume do modelo: exportar em CSV. A fonte não tem ID de item, por isso todos os atri"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    cd_catmas = models.CharField(max_length=100, null=True, blank=True)  # Número CATMAS
    tp_despesa = models.TextField(null=True, blank=True)  # Tipo Despesa aExecutar
    nr_cnpj_beneficiario = models.CharField(max_length=14, null=True, blank=True)  # Beneficiário - CNPJ-CAPJ
    ds_item = models.TextField(null=True, blank=True)  # Descrição Item aExecutar
    ds_origem_recurso = models.TextField(null=True, blank=True)  # Origem Recurso
    ds_situacao_item = models.TextField(null=True, blank=True)  # Situação Item aExecutar
    qt_item = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Quantidade Item aExecutar
    vl_unitario_item = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Unitário Item aExecutar
    vl_total_item = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Total Item aExecutar
    cd_categoria_economica = models.CharField(max_length=100, null=True, blank=True)  # CategoriaEconômica - Código
    cd_grupo_despesa = models.CharField(max_length=100, null=True, blank=True)  # GrupoDespesa - Código
    cd_modalidade_aplicacao = models.CharField(max_length=100, null=True, blank=True)  # Modalidade - Código
    cd_elemento_despesa = models.CharField(max_length=100, null=True, blank=True)  # ElementoDespesa - Código
    cd_elemento_item = models.CharField(max_length=100, null=True, blank=True)  # ElementoItem - Código

    class Meta:
        db_table = "grp_item_executar"
        verbose_name = "Item Executar GRP"
        verbose_name_plural = "Item Executar GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Execução e cronogramas (consulta 17 do Modelo de Extração GRP v1.2)
# Grão: instrumento x parcela x origem do recurso. Prioridade: Must
# ---------------------------------------------------------------------------
class GrpCronogramaDesembolso(models.Model):
    """Fluxo financeiro previsto. 'Mês Descritivo' e 'Mês Abreviado' foram excluídos porque derivam de 'Desembolso - Mês' e ser"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    nr_parcela = models.CharField(max_length=100, null=True, blank=True)  # Parcela Desembolso
    ds_origem_recurso_parcela = models.TextField(null=True, blank=True)  # Origem Recurso Parcela
    nr_ano_desembolso = models.CharField(max_length=100, null=True, blank=True)  # Desembolso - Ano
    nr_mes_desembolso = models.CharField(max_length=100, null=True, blank=True)  # Desembolso - Mês
    vl_desembolso = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor Desembolso

    class Meta:
        db_table = "grp_cronograma_desembolso"
        verbose_name = "Cronograma Desembolso GRP"
        verbose_name_plural = "Cronograma Desembolso GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Execução e cronogramas (consulta 18 do Modelo de Extração GRP v1.2)
# Grão: instrumento x meta x etapa. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpCronogramaFisico(models.Model):
    """Execução física planejada. Atenção: os dados da meta se repetem em cada etapa dela; nunca somar vl_meta diretamente nest"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    tp_meta_etapa = models.TextField(null=True, blank=True)  # Tipo Meta/Etapa
    tx_meta_especificacao = models.TextField(null=True, blank=True)  # Meta - Especificação
    dt_meta_inicio = models.DateField(null=True, blank=True)  # Meta - Data Início
    dt_meta_termino = models.DateField(null=True, blank=True)  # Meta - Data Término
    qt_meta_duracao = models.IntegerField(null=True, blank=True)  # Meta - Duração
    vl_meta = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Meta - Valor
    tx_etapa_especificacao = models.TextField(null=True, blank=True)  # Etapa - Especificação
    dt_etapa_inicio = models.DateField(null=True, blank=True)  # Etapa - Data Início
    dt_etapa_termino = models.DateField(null=True, blank=True)  # Etapa - Data Término
    qt_etapa_duracao = models.IntegerField(null=True, blank=True)  # Etapa - Duração
    vl_etapa = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Etapa - Valor

    class Meta:
        db_table = "grp_cronograma_fisico"
        verbose_name = "Cronograma Fisico GRP"
        verbose_name_plural = "Cronograma Fisico GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Marco lógico e governança (consulta 19 do Modelo de Extração GRP v1.2)
# Grão: instrumento x entrega. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpEntregaProjeto(models.Model):
    """Produtos do projeto no marco lógico."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    tx_entrega = models.TextField(null=True, blank=True)  # Entrega Projeto
    tx_indicador_produto = models.TextField(null=True, blank=True)  # IndicadorProduto Entrega
    tx_meta_prazo_entrega = models.TextField(null=True, blank=True)  # MetaPrazo Entrega
    tx_criterio_aceitacao_entrega = models.TextField(null=True, blank=True)  # Critério Aceitação Entrega
    tx_meio_verificacao_entrega = models.TextField(null=True, blank=True)  # MeioVerificação Entrega
    tx_pressuposto_entrega = models.TextField(null=True, blank=True)  # Pressuposto Entrega

    class Meta:
        db_table = "grp_entrega_projeto"
        verbose_name = "Entrega Projeto GRP"
        verbose_name_plural = "Entrega Projeto GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Marco lógico e governança (consulta 20 do Modelo de Extração GRP v1.2)
# Grão: instrumento x atividade. Prioridade: Could
# ---------------------------------------------------------------------------
class GrpAtividadeProjeto(models.Model):
    """Pasta CAPS independente das entregas, portanto consulta separada."""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    tx_atividade = models.TextField(null=True, blank=True)  # Atividade Projeto

    class Meta:
        db_table = "grp_atividade_projeto"
        verbose_name = "Atividade Projeto GRP"
        verbose_name_plural = "Atividade Projeto GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Marco lógico e governança (consulta 21 do Modelo de Extração GRP v1.2)
# Grão: instrumento x responsável x tipo. Prioridade: Won't (por ora)
# ---------------------------------------------------------------------------
class GrpMatrizResponsabilidade(models.Model):
    """Quem responde por cada instrumento. Contém dados pessoais (LGPD): extrair apenas o necessário, nunca versionar o arquivo"""

    nr_grp = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # Número InstrumentoGRP
    cd_proposta = models.CharField(max_length=30, null=True, blank=True)  # Código Proposta
    tp_gestor_participante = models.TextField(null=True, blank=True)  # Tipo Gestor/Participante
    cd_unidade_adm_vinculacao = models.CharField(max_length=100, null=True, blank=True)  # UnidadeAdm Vinculação - Código
    nm_unidade_adm_vinculacao = models.TextField(null=True, blank=True)  # UnidadeAdm Vinculação - Nome
    sg_unidade_adm_vinculacao = models.CharField(max_length=100, null=True, blank=True)  # UnidadeAdm Vinculação - Sigla
    nr_cpf_responsavel = models.CharField(max_length=11, null=True, blank=True)  # Responsável - CPF-CAPF
    nm_responsavel = models.TextField(null=True, blank=True)  # Responsável - Nome
    ds_nivel_hierarquico = models.TextField(null=True, blank=True)  # Responsável - NívelHierárquico
    ds_atribuicao = models.TextField(null=True, blank=True)  # Responsável - Atribuição
    ds_email_responsavel = models.TextField(null=True, blank=True)  # Responsável - Email
    nr_telefone_responsavel = models.CharField(max_length=100, null=True, blank=True)  # Responsável - Telefone
    fl_responsavel_monitoramento = models.BooleanField(null=True, blank=True)  # Responsável Monitoramento S/N

    class Meta:
        db_table = "grp_matriz_responsabilidade"
        verbose_name = "Matriz Responsabilidade GRP"
        verbose_name_plural = "Matriz Responsabilidade GRP"
        ordering = ["nr_grp"]

    def __str__(self):
        return self.nr_grp or "—"


# ---------------------------------------------------------------------------
# GRP — Dimensões de apoio (consulta 22 do Modelo de Extração GRP v1.2)
# Grão: 1 linha por unidade orçamentária. Prioridade: Must
# ---------------------------------------------------------------------------
class GrpTabelaUo(models.Model):
    """Tabela que consta todas as UOs e seus respectivos nomes. É a dimensão única de UO para a qual apontam os códigos das con"""

    cd_uo = models.CharField(max_length=20, db_index=True, null=True, blank=True)  # UnidadeOrçam - Código
    nm_uo = models.TextField(null=True, blank=True)  # UnidadeOrçam - Nome

    class Meta:
        db_table = "grp_tabela_uo"
        verbose_name = "Tabela Uo GRP"
        verbose_name_plural = "Tabela Uo GRP"
        ordering = ["cd_uo"]

    def __str__(self):
        return f"{self.cd_uo} — {self.nm_uo or '—'}"