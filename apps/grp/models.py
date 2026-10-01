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