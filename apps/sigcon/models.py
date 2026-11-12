"""
Models das tabelas do SIGCON-MG e de apoio (bases legadas).

Uma classe por tabela do Modelo de Extração SIGCON v1.0 (docs/modelo_extracao_sigcon.pdf).
Os nomes dos campos são IGUAIS às colunas da silver (bloco "renomear" do YAML em
core/transform/schemas/), o que permite um loader genérico, sem de-para escrito à mão.

São tabelas planas, ligadas por siafi_uo, cd_plano_trabalho etc. — não há nenhuma ForeignKey.
O grão é declarado em cada classe mas NÃO é imposto por constraint: a carga nunca descarta
linhas com dado, e duplicidades de grão são só alertadas na silver.
"""

from django.core.serializers.json import DjangoJSONEncoder

from django.db import models


# ---------------------------------------------------------------------------
# 01. sigcon_convenio (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por convênio (siafi_uo). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconConvenio(models.Model):
    """
    Núcleo do convênio no SIGCON: situação, vigência e valores. Tabela de referência do siafi_uo.
    dt_vigencia_termino_inicial é o término original; dt_vigencia_termino, o atual (com aditivos).
    4 linhas sem SIAFI ficam com siafi_uo nulo.

    Fonte: data/silver/sigcon_convenio.parquet
    """

    # --- Identificação ---
    nr_convenio = models.CharField(
        max_length=100, null=True, blank=True
    )  # Convênio Código (número legível, ex.: 'CV 98/2020')
    nr_siafi = models.CharField(
        max_length=20, db_index=True, null=True, blank=True
    )  # Convênio Número Sequencial SIAFI
    cd_uo = models.CharField(
        max_length=10, db_index=True, null=True, blank=True
    )  # Unidade Orçamentária Código
    siafi_uo = models.CharField(
        max_length=30, null=True, blank=True, db_index=True
    )  # (derivada: nr_siafi || cd_uo); o grão é garantido por T-C01, não por constraint
    ds_situacao_convenio = models.TextField(null=True, blank=True)  # Situação

    # --- Vigência ---
    dt_vigencia_inicio = models.DateField(null=True, blank=True)  # Data Início Vigência
    dt_vigencia_termino_inicial = models.DateField(
        null=True, blank=True
    )  # Data Término Vigência (término original)
    dt_vigencia_termino = models.DateField(
        null=True, blank=True
    )  # Data Real Convênio (término atual, com aditivos)

    # --- Valores ---
    vl_convenio_concedente_inicial = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Inicial Concedente Contratado
    vl_convenio_concedente_aditado = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Total Aditado Concedente Contratado
    vl_convenio_concedente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Concedente
    vl_convenio_proponente_inicial = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Inicial Proponente Contratado
    vl_convenio_proponente_aditado = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Total Aditado Proponente Contratado
    vl_convenio_proponente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Proponente
    vl_convenio_total = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Total Convênio

    class Meta:
        db_table = "sigcon_convenio"
        verbose_name = "Convênio SIGCON"
        verbose_name_plural = "Convênios SIGCON"
        indexes = [
            models.Index(fields=["nr_siafi"], name="idx_nr_siafi"),
            models.Index(fields=["cd_uo"], name="idx_cd_uo"),
            models.Index(fields=["nr_convenio"], name="idx_nr_convenio"),
            models.Index(fields=["ds_situacao_convenio"], name="idx_ds_situacao_convenio"),
        ]

    def __str__(self):
        return self.siafi_uo or f"Convênio {self.nr_convenio}"


# ---------------------------------------------------------------------------
# 02. sigcon_convenio_geral (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por convênio (cd_convenio_sequencial). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconConvenioGeral(models.Model):
    """
    Complementa o convênio com assinatura, publicação, controles da SCCG e os vínculos com o plano
    de trabalho original e a declaração de contrapartida. Não traz UO: chega ao siafi_uo pela ponte
    sigcon_chave_convenio. cd_plano_trabalho tem colisões legítimas (planos compartilhados).

    Fonte: data/silver/sigcon_convenio_geral.parquet
    """

    # --- Chaves ---
    nr_convenio = models.CharField(
        max_length=100, null=True, blank=True
    )  # Convênio Código
    cd_convenio_sequencial = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Convênio Código Sequencial
    cd_declaracao_contrapartida = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Convênio Código Declaração
    cd_plano_trabalho = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Convênio Código Plano Trabalho
    nr_siafi = models.CharField(
        max_length=20, db_index=True, null=True, blank=True
    )  # Convênio Número Sequencial SIAFI

    # --- Dados do convênio ---
    dt_publicacao = models.DateField(
        null=True, blank=True
    )  # Convênio Data de Publicação
    nr_ano_convenio = models.IntegerField(null=True, blank=True)  # Convênio Ano
    fl_permite_alteracao = models.BooleanField(
        null=True, blank=True
    )  # Convênio Alteração
    dt_assinatura = models.DateField(
        null=True, blank=True
    )  # Convênio Data Assinatura Convênio
    dh_cadastramento = models.DateTimeField(
        null=True, blank=True
    )  # Convênio Data de Cadastramento

    # --- Controle SCCG ---
    cd_matricula_tecnico_sccg = models.CharField(
        max_length=30, null=True, blank=True, db_index=True
    )  # Convênio Matrícula Técnico SCCG (LGPD)
    dh_alteracao_sccg = models.DateTimeField(
        null=True, blank=True
    )  # Convênio Data Alteração SCCG
    tx_justificativa_alteracao = models.TextField(
        null=True, blank=True
    )  # Convênio Justificativa da Alteração
    dt_controle_sccg = models.DateField(
        null=True, blank=True
    )  # Convênio Data Controle SCCG Convênio
    cd_matricula_gestor = models.CharField(
        max_length=30, null=True, blank=True, db_index=True
    )  # Convênio Matrícula Gestor (LGPD)

    class Meta:
        db_table = "sigcon_convenio_geral"
        verbose_name = "Convênio Geral SIGCON"
        verbose_name_plural = "Convênios Gerais SIGCON"
        indexes = [
            models.Index(fields=["nr_ano_convenio"], name="idx_nr_ano_convenio"),
        ]

    def __str__(self):
        return self.cd_convenio_sequencial or "—"


# ---------------------------------------------------------------------------
# 03. sigcon_plano_trabalho (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por plano de trabalho (cd_plano_trabalho). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconPlanoTrabalho(models.Model):
    """
    Plano de trabalho do convênio original e de cada termo aditivo. Elo entre o convênio e os
    detalhes 1:N (cronograma, plano de aplicação, emendas). tp_instrumento_siafi mistura códigos e
    textos ('11', 'Convênio de Entrada', 'Portaria'): fica como veio.

    Fonte: data/silver/sigcon_plano_trabalho.parquet
    """

    # --- Identificação ---
    cd_plano_trabalho = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Plano Trabalho Código
    nm_plano_trabalho = models.TextField(null=True, blank=True)  # Plano Trabalho Título
    tx_objeto = models.TextField(null=True, blank=True)  # Plano Trabalho Objeto
    tx_justificativa = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Justificativa
    cd_execucao_exercicio = models.CharField(
        max_length=30, null=True, blank=True
    )  # Plano Trabalho Código Execução no Exercício
    nr_ano_plano_trabalho = models.IntegerField(
        null=True, blank=True
    )  # Plano Trabalho Ano

    # --- Classificação ---
    ds_status_plano_trabalho = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Status
    ds_caracteristica_contrapartida = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Característica
    tp_plano_trabalho = models.TextField(null=True, blank=True)  # Plano Trabalho Tipo
    tp_instrumento_siafi = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Tipo SIAFI
    ds_origem_cadastro = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Migrado ou Novo
    ds_alteracao_termo_aditivo = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Altera Termo Aditivo

    # --- Cadastro e envio ---
    dh_cadastro = models.DateTimeField(
        null=True, blank=True
    )  # Plano Trabalho Data Cadastro
    dh_envio_sccg = models.DateTimeField(
        null=True, blank=True
    )  # Plano Trabalho Data Envio SCCG

    # --- Cancelamento SCCG ---
    cd_matricula_cancelamento_sccg = models.CharField(
        max_length=30, null=True, blank=True
    )  # Plano Trabalho Matrícula SCCG Cancelamento (LGPD)
    dh_cancelamento_sccg = models.DateTimeField(
        null=True, blank=True
    )  # Plano Trabalho Data Cancelamento SCCG
    tx_justificativa_cancelamento = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Justificativa SCCG Cancelamento
    ds_cancelamento_sccg = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Cancelamento SCCG

    # --- Concedente e proponente ---
    nr_cnpj_concedente = models.CharField(
        max_length=14, db_index=True, null=True, blank=True
    )  # Plano Trabalho CNPJ Concedente
    nm_concedente = models.TextField(
        null=True, blank=True
    )  # Plano Trabalho Razão Social Concedente
    nr_cnpj_proponente = models.CharField(
        max_length=14, null=True, blank=True
    )  # Plano Trabalho CNPJ Proponente

    class Meta:
        db_table = "sigcon_plano_trabalho"
        verbose_name = "Plano de Trabalho SIGCON"
        verbose_name_plural = "Planos de Trabalho SIGCON"
        indexes = [
            models.Index(fields=["ds_alteracao_termo_aditivo"], name="idx_ds_alteracao_termo_aditivo"),
            models.Index(fields=["nm_concedente"], name="idx_nm_concedente"),
        ]
    def __str__(self):
        return self.cd_plano_trabalho or "—"


# ---------------------------------------------------------------------------
# 04. sigcon_termo_aditivo (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por termo aditivo (cd_termo_aditivo). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconTermoAditivo(models.Model):
    """
    Aditivos de vigência e valor. Não traz convênio nem plano de trabalho: chega a eles pela ponte
    sigcon_chave_termo_aditivo. A quantidade de aditivos é calculada em SQL.

    Fonte: data/silver/sigcon_termo_aditivo.parquet
    """

    # --- Identificação ---
    cd_termo_aditivo = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Termo Aditivo Código Sequencial
    nr_termo_aditivo = models.CharField(
        max_length=100, null=True, blank=True
    )  # Termo Aditivo Número Termo Aditivo
    nr_ano_termo_aditivo = models.IntegerField(
        null=True, blank=True
    )  # Termo Aditivo Ano
    tp_termo_aditivo = models.TextField(null=True, blank=True)  # Tipo Termo Aditivo
    tx_justificativa = models.TextField(
        null=True, blank=True
    )  # Termo Aditivo Justificativa

    # --- Datas ---
    dt_assinatura = models.DateField(
        null=True, blank=True
    )  # Termo Aditivo Data Assinatura
    dt_vigencia_inicio = models.DateField(
        null=True, blank=True
    )  # Termo Aditivo Data Início Vigência
    dt_vigencia_termino = models.DateField(
        null=True, blank=True
    )  # Termo Aditivo Data Término Vigência
    dh_registro = models.DateTimeField(null=True, blank=True)  # Data Termo Aditivo

    # --- Valores ---
    vl_aditivo_concedente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Aditado Concedente Contratado
    vl_aditivo_proponente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Aditado Proponente Contratado

    class Meta:
        db_table = "sigcon_termo_aditivo"
        verbose_name = "Termo Aditivo SIGCON"
        verbose_name_plural = "Termos Aditivos SIGCON"

    def __str__(self):
        return self.cd_termo_aditivo or "—"


# ---------------------------------------------------------------------------
# 05. sigcon_prorrogacao_oficio (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por prorrogação (cd_prorrogacao_oficio). Prioridade: Should. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconProrrogacaoOficio(models.Model):
    """
    Prorrogações de ofício. cd_convenio_sequencial é o código sequencial do convênio, não o número
    legível: liga-se a sigcon_chave_convenio.

    Fonte: data/silver/sigcon_prorrogacao_oficio.parquet
    """

    # --- Chaves ---
    cd_prorrogacao_oficio = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # PRORROGAÇÃO OFÍCIO Código
    cd_convenio_sequencial = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # PRORROGAÇÃO OFÍCIO Código Convênio

    # --- Datas ---
    dt_vigencia_inicio = models.DateField(
        null=True, blank=True
    )  # PRORROGAÇÃO OFÍCIO Data Início Vigência
    dt_vigencia_termino = models.DateField(
        null=True, blank=True
    )  # PRORROGAÇÃO OFÍCIO Data Término Vigência
    dt_envio = models.DateField(null=True, blank=True)  # PRORROGAÇÃO OFÍCIO Data Envio
    dt_parecer = models.DateField(
        null=True, blank=True
    )  # PRORROGAÇÃO OFÍCIO Data Parecer
    dt_publicacao = models.DateField(
        null=True, blank=True
    )  # PRORROGAÇÃO OFÍCIO Data Publicação

    class Meta:
        db_table = "sigcon_prorrogacao_oficio"
        verbose_name = "Prorrogação de Ofício SIGCON"
        verbose_name_plural = "Prorrogações de Ofício SIGCON"

    def __str__(self):
        return self.cd_prorrogacao_oficio or "—"


# ---------------------------------------------------------------------------
# 06. sigcon_declaracao_contrapartida (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por declaração (cd_declaracao_contrapartida). Prioridade: Should. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconDeclaracaoContrapartida(models.Model):
    """
    Declarações de contrapartida e seus pareceres. Só parte delas está ligada a um convênio.
    dt_emissao e dt_parecer_aprovacao derivam das datas completas (dh_*) e são redundantes.

    Fonte: data/silver/sigcon_declaracao_contrapartida.parquet
    """

    # --- Identificação ---
    cd_declaracao_contrapartida = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Declaração Contrapartida Código
    dh_emissao = models.DateTimeField(
        null=True, blank=True
    )  # Declaração Contrapartida Data Completa Emissão
    dt_emissao = models.DateField(
        null=True, blank=True
    )  # Declaração Contrapartida Data Emissão (redundante)
    nr_ano_declaracao = models.IntegerField(
        null=True, blank=True
    )  # Declaração Contrapartida Ano
    ds_status_declaracao = models.TextField(
        null=True, blank=True
    )  # Declaração Contrapartida Status
    cd_nota_tecnica = models.CharField(
        max_length=30, null=True, blank=True, db_index=True
    )  # Declaração Contrapartida Código Nota Técnica
    tx_observacao = models.TextField(
        null=True, blank=True
    )  # Declaração Contrapartida Observação
    ds_momento = models.TextField(
        null=True, blank=True
    )  # Declaração Contrapartida Momento

    # --- Aprovação ---
    ds_parecer_aprovacao = models.TextField(
        null=True, blank=True
    )  # Declaração Contrapartida Código Parecer Aprovação
    dh_parecer_aprovacao = models.DateTimeField(
        null=True, blank=True
    )  # Declaração Contrapartida Data Completa Parecer Aprovação
    dt_parecer_aprovacao = models.DateField(
        null=True, blank=True
    )  # Declaração Contrapartida Data Parecer Aprovação (redundante)
    tx_observacao_aprovacao = models.TextField(
        null=True, blank=True
    )  # Declaração Contrapartida Observação Aprovação
    cd_matricula_aprovacao = models.CharField(
        max_length=30, null=True, blank=True, db_index=True
    )  # Declaração Contrapartida Matrícula Aprovação (LGPD)

    class Meta:
        db_table = "sigcon_declaracao_contrapartida"
        verbose_name = "Declaração de Contrapartida SIGCON"
        verbose_name_plural = "Declarações de Contrapartida SIGCON"

    def __str__(self):
        return self.cd_declaracao_contrapartida or "—"


# ---------------------------------------------------------------------------
# 07. sigcon_cronograma_desembolso (Modelo de Extração SIGCON v1.0)
# Grão: plano de trabalho x ano x mês. Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconCronogramaDesembolso(models.Model):
    """
    Fluxo financeiro previsto. Parte das linhas do arquivo é um bloco desalinhado do relatório do BO
    (sem plano de trabalho): ficam na tabela marcadas em ds_alerta_linha, com o texto original em
    tx_linha_bruta, e as consultas filtram ds_alerta_linha__isnull=True.

    Fonte: data/silver/sigcon_cronograma_desembolso.parquet
    """

    # --- Grão ---
    cd_plano_trabalho = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Plano Trabalho Código
    nr_ano_desembolso = models.IntegerField(
        null=True, blank=True
    )  # Ano Cronograma Desembolso
    nr_mes_desembolso = models.IntegerField(
        null=True, blank=True
    )  # Mês Cronograma Desembolso

    # --- Valores ---
    vl_desembolso_concedente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Concedente Cronograma Desembolso
    vl_desembolso_proponente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Proponente Cronograma Desembolso

    # --- Marcação de linha ---
    ds_alerta_linha = models.TextField(
        null=True, blank=True
    )  # motivo da marcação (marcar_linhas_se_nulo); nulo = linha válida
    tx_linha_bruta = models.TextField(
        null=True, blank=True
    )  # texto original da linha marcada

    class Meta:
        db_table = "sigcon_cronograma_desembolso"
        verbose_name = "Cronograma de Desembolso SIGCON"
        verbose_name_plural = "Cronogramas de Desembolso SIGCON"

    def __str__(self):
        return f"{self.cd_plano_trabalho or '—'} {self.nr_ano_desembolso}/{self.nr_mes_desembolso}"


# ---------------------------------------------------------------------------
# 08. sigcon_plano_aplicacao (Modelo de Extração SIGCON v1.0)
# Grão: plano de trabalho x classificação orçamentária x ano. Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconPlanoAplicacao(models.Model):
    """
    Classificação orçamentária (funcional-programática e natureza de despesa) de cada plano.
    cd_funcional_programatica não é a concatenação dos códigos, por isso é mantida.

    Fonte: data/silver/sigcon_plano_aplicacao.parquet
    """

    # --- Plano e unidade ---
    cd_plano_trabalho = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Código Plano Trabalho
    cd_uo = models.CharField(
        max_length=10, null=True, blank=True
    )  # Código Unidade Orçamentária
    nr_ano_exercicio = models.IntegerField(
        null=True, blank=True
    )  # Ano Exercício Programa Trabalho

    # --- Classificação funcional-programática ---
    cd_funcao = models.CharField(max_length=10, null=True, blank=True)  # Função Código
    cd_subfuncao = models.CharField(
        max_length=10, null=True, blank=True
    )  # Subfunção Código
    cd_programa = models.CharField(
        max_length=10, null=True, blank=True
    )  # Programa Código
    cd_identificador_projeto_atividade = models.CharField(
        max_length=10, null=True, blank=True
    )  # Identificador Projeto_Atividade Código
    cd_projeto_atividade = models.CharField(
        max_length=10, null=True, blank=True
    )  # Projeto_Atividade Código
    cd_subprojeto_subatividade = models.CharField(
        max_length=10, null=True, blank=True
    )  # Subprojeto_Subatividade Código
    cd_funcional_programatica = models.CharField(
        max_length=60, null=True, blank=True
    )  # Funcional Programática Formatado

    # --- Natureza da despesa e fonte ---
    cd_categoria_economica = models.CharField(
        max_length=10, null=True, blank=True
    )  # Categoria Econômica Despesa Código
    cd_grupo_despesa = models.CharField(
        max_length=10, null=True, blank=True
    )  # Grupo Despesa Código
    cd_modalidade_aplicacao = models.CharField(
        max_length=10, null=True, blank=True
    )  # Modalidade Aplicação Código
    cd_elemento_despesa = models.CharField(
        max_length=10, null=True, blank=True
    )  # Elemento Despesa Código
    cd_identificador_orcamento = models.CharField(
        max_length=10, null=True, blank=True
    )  # Identificador Orçamento Código
    cd_fonte_recurso = models.CharField(
        max_length=10, null=True, blank=True
    )  # Fonte Recurso Código
    cd_procedencia = models.CharField(
        max_length=10, null=True, blank=True
    )  # Procedência Código

    # --- Valores ---
    vl_aplicacao_concedente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Concedente
    vl_aplicacao_proponente = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Valor Proponente

    class Meta:
        db_table = "sigcon_plano_aplicacao"
        verbose_name = "Plano de Aplicação SIGCON"
        verbose_name_plural = "Planos de Aplicação SIGCON"

    def __str__(self):
        return (
            f"{self.cd_plano_trabalho or '—'} / {self.cd_funcional_programatica or '—'}"
        )


# ---------------------------------------------------------------------------
# 09. sigcon_unidade_executora (Modelo de Extração SIGCON v1.0)
# Grão: convênio (siafi_uo) x unidade executora. Prioridade: Should. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconUnidadeExecutora(models.Model):
    """
    Unidades executoras de cada convênio (1:N). nr_convenio repete o número legível de
    sigcon_convenio e é redundante.

    Fonte: data/silver/sigcon_unidade_executora.parquet
    """

    # --- Chaves ---
    siafi_uo = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # (derivada: nr_siafi || cd_uo)
    nr_siafi = models.CharField(
        max_length=20, null=True, blank=True
    )  # Convênio Número Sequencial SIAFI
    cd_uo = models.CharField(
        max_length=10, null=True, blank=True
    )  # Unidade Orçamentária Código
    nr_convenio = models.CharField(
        max_length=100, null=True, blank=True
    )  # Convênio Código (redundante)
    cd_unidade_executora = models.CharField(
        max_length=30, null=True, blank=True
    )  # Unidade Executora

    class Meta:
        db_table = "sigcon_unidade_executora"
        verbose_name = "Unidade Executora SIGCON"
        verbose_name_plural = "Unidades Executoras SIGCON"
        indexes = [
            models.Index(fields=["cd_unidade_executora"], name="idx_cd_unidade_executora"),
        ]

    def __str__(self):
        return f"{self.siafi_uo or '—'} / {self.cd_unidade_executora or '—'}"


# ---------------------------------------------------------------------------
# 10. sigcon_nt_emenda (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por plano de trabalho (cd_plano_trabalho). Prioridade: Should. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconNtEmenda(models.Model):
    """
    Nota técnica de emenda parlamentar por plano de trabalho. O sentinela 99999999 (UO 9999) vira
    nulo. nm_parlamentar é padronizado por de-para em onda futura.

    Fonte: data/silver/sigcon_nt_emenda.parquet
    """

    # --- Dados da emenda ---
    cd_uo = models.CharField(
        max_length=10, null=True, blank=True
    )  # Unidade Orçamentária Código
    cd_plano_trabalho = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Plano Trabalho Código
    nr_emenda = models.CharField(max_length=30, null=True, blank=True)  # NT emenda nº
    nm_parlamentar = models.TextField(null=True, blank=True)  # NT emenda Nome
    fl_emenda_parlamentar_federal = models.BooleanField(
        null=True, blank=True
    )  # Nota Técnica Emenda Parlamentar Federal Situação

    class Meta:
        db_table = "sigcon_nt_emenda"
        verbose_name = "Nota Técnica de Emenda SIGCON"
        verbose_name_plural = "Notas Técnicas de Emenda SIGCON"

    def __str__(self):
        return self.cd_plano_trabalho or "—"


# ---------------------------------------------------------------------------
# 11. sigcon_chave_convenio (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por convênio (cd_convenio_sequencial). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconChaveConvenio(models.Model):
    """
    Ponte central: traduz o código sequencial (usado por geral e prorrogação) em siafi_uo.

    Fonte: data/silver/sigcon_chave_convenio.parquet
    """

    # --- Chaves ---
    nr_convenio = models.CharField(
        max_length=100, null=True, blank=True
    )  # Convênio Código
    cd_convenio_sequencial = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Convênio Código Sequencial
    nr_siafi = models.CharField(
        max_length=20, null=True, blank=True
    )  # Convênio Número Sequencial SIAFI
    cd_uo = models.CharField(
        max_length=10, null=True, blank=True
    )  # Unidade Orçamentária Código
    siafi_uo = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # (derivada: nr_siafi || cd_uo)

    class Meta:
        db_table = "sigcon_chave_convenio"
        verbose_name = "Chave de Convênio SIGCON"
        verbose_name_plural = "Chaves de Convênio SIGCON"

    def __str__(self):
        return self.cd_convenio_sequencial or "—"


# ---------------------------------------------------------------------------
# 12. sigcon_chave_termo_aditivo (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por termo aditivo (cd_termo_aditivo). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconChaveTermoAditivo(models.Model):
    """
    Liga cada aditivo ao convênio e ao seu próprio plano de trabalho. Fonte dos planos de trabalho
    dos aditivos: os planos de um convênio são o original (geral) mais os dos aditivos (esta tabela).

    Fonte: data/silver/sigcon_chave_termo_aditivo.parquet
    """

    # --- Chaves ---
    nr_siafi = models.CharField(
        max_length=20, null=True, blank=True
    )  # Convênio Número Sequencial SIAFI
    cd_termo_aditivo = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Termo Aditivo Código Sequencial
    cd_uo = models.CharField(
        max_length=10, null=True, blank=True
    )  # Unidade Orçamentária Código
    siafi_uo = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # (derivada: nr_siafi || cd_uo)
    cd_plano_trabalho = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Plano Trabalho Código

    class Meta:
        db_table = "sigcon_chave_termo_aditivo"
        verbose_name = "Chave de Termo Aditivo SIGCON"
        verbose_name_plural = "Chaves de Termo Aditivo SIGCON"

    def __str__(self):
        return self.cd_termo_aditivo or "—"


# ---------------------------------------------------------------------------
# 13. sigcon_chave_plano_trabalho (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por convênio (siafi_uo). Prioridade: Could. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconChavePlanoTrabalho(models.Model):
    """
    Liga o convênio ao plano de trabalho original. Provavelmente redundante com geral + chave_convenio.

    Fonte: data/silver/sigcon_chave_plano_trabalho.parquet
    """

    # --- Chaves ---
    cd_plano_trabalho = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Convênio Código Plano Trabalho
    nr_siafi = models.CharField(
        max_length=20, null=True, blank=True
    )  # Convênio Número Sequencial SIAFI
    cd_uo = models.CharField(
        max_length=10, null=True, blank=True
    )  # Unidade Orçamentária Código
    siafi_uo = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # (derivada: nr_siafi || cd_uo)

    class Meta:
        db_table = "sigcon_chave_plano_trabalho"
        verbose_name = "Chave de Plano de Trabalho SIGCON"
        verbose_name_plural = "Chaves de Plano de Trabalho SIGCON"

    def __str__(self):
        return self.siafi_uo or "—"


# ---------------------------------------------------------------------------
# 14. sigcon_chave_declaracao (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por convênio (siafi_uo). Prioridade: Could. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconChaveDeclaracao(models.Model):
    """
    Liga o convênio à sua declaração de contrapartida (sentinela 99999999 = sem declaração).
    Provavelmente redundante com sigcon_convenio_geral.cd_declaracao_contrapartida.

    Fonte: data/silver/sigcon_chave_declaracao.parquet
    """

    # --- Chaves ---
    cd_declaracao_contrapartida = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # Declaração Contrapartida Código
    nr_siafi = models.CharField(
        max_length=20, null=True, blank=True
    )  # Convênio Número Sequencial SIAFI
    cd_uo = models.CharField(
        max_length=10, null=True, blank=True
    )  # Unidade Orçamentária Código
    siafi_uo = models.CharField(
        max_length=30, db_index=True, null=True, blank=True
    )  # (derivada: nr_siafi || cd_uo)

    class Meta:
        db_table = "sigcon_chave_declaracao"
        verbose_name = "Chave de Declaração SIGCON"
        verbose_name_plural = "Chaves de Declaração SIGCON"

    def __str__(self):
        return self.siafi_uo or "—"


# ---------------------------------------------------------------------------
# 15. sigcon_concedente (Modelo de Extração SIGCON v1.0)
# Grão: 1 linha por concedente (nr_cnpj_concedente). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconConcedente(models.Model):
    """
    Dimensão de concedente com a esfera. A chave natural é o CNPJ.

    Fonte: data/silver/sigcon_concedente.parquet
    """

    # --- Dados ---
    ds_esfera = models.TextField(null=True, blank=True)  # Concedente Esfera
    nr_cnpj_concedente = models.CharField(
        max_length=14, db_index=True, null=True, blank=True
    )  # Concedente CNPJ

    class Meta:
        db_table = "sigcon_concedente"
        verbose_name = "Concedente SIGCON"
        verbose_name_plural = "Concedentes SIGCON"

    def __str__(self):
        return self.nr_cnpj_concedente or "—"

# ---------------------------------------------------------------------------
# 16. sigcon_tabela_uo (Ainda não está no Modelo de Extração SIGCON v1.0)
# Grão: várias linhas por unidade orçamentária (cd_uo). Prioridade: Must. Carga: full refresh a partir da silver.
# ---------------------------------------------------------------------------
class SigconTabelaUo(models.Model):
    """
    Tabela de unidades orçamentárias (UO) com seus códigos, nomes e anos de exercício. A chave natural é o código da UO.

    Fonte: data/silver/sigcon_tabela_uo.parquet
    """

    # --- Dados ---
    cd_uo = models.CharField(
        max_length=10, db_index=True, null=False, blank=True
    )  # Unidade Orçamentária Código
    nm_uo = models.TextField(null=False, blank=True)  # Unidade Orçamentária Nome
    nr_ano_exercicio = models.IntegerField(null=False, blank=True)  # Unidade Orçamentária Ano de Exercício

    class Meta:
        db_table = "sigcon_tabela_uo"
        verbose_name = "Tabela de Unidade Orçamentária SIGCON"
        verbose_name_plural = "Tabelas de Unidade Orçamentária SIGCON"

    def __str__(self):
        return self.cd_uo or "—"

class SigconHistoricoCarga(models.Model):
    """
    Uma linha por tabela a cada carga bem-sucedida (`carregar_sigcon`), com a
    quantidade de linhas carregadas. O teste de volumetria histórica de
    `validar_sigcon` compara a carga mais recente com a anterior.

    Fica fora do prefixo `sigcon_` de propósito: não é uma tabela do modelo de
    extração, então não entra nos testes de grão, tipo e volumetria.
    """

    dt_carga = models.DateTimeField(auto_now_add=True, db_index=True)
    tabela = models.CharField(max_length=80, db_index=True)
    qt_linhas = models.IntegerField()

    class Meta:
        db_table = "dq_historico_carga_sigcon"
        ordering = ["-dt_carga", "-id"]


class ResultadoValidacao(models.Model):
    """
    Tabela para gerenciado pelo próprio Django do histórico de full refesh.
    o banco só guarda a fotografia de hoje. O resultado dos testes é o seu histórico de qualidade,
    e também é evidência para auditoria
    """

    execucao = models.UUIDField(db_index=True)
    dt_execucao = models.DateTimeField(auto_now_add=True)
    id_teste = models.CharField(max_length=20)
    tabela = models.CharField(max_length=80)
    descricao = models.TextField(null=True, blank=True)
    severidade = models.CharField(
        max_length=6, choices=[("ERRO", "Erro"), ("ALERTA", "Alerta")]
    )
    status = models.CharField(
        max_length=6, choices=[("PASSOU", "Passou"), ("FALHOU", "Falhou")]
    )  # "PASSOU" ou "FALHOU"
    qt_falhas = models.IntegerField(null=True, blank=True)
    amostra = models.JSONField(default=list, encoder=DjangoJSONEncoder)

    class Meta:
        db_table = "dq_resultado_validacao_sigcon"
        ordering = ["-dt_execucao", "id_teste"]