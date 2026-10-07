"""
Registro declarativo de todas as fontes de dados do projeto.

Para adicionar uma nova fonte:
  1. Crie uma instância de FonteDados com nome, arquivo, formato e opcoes_leitura.
  2. Adicione-a ao dicionário FONTES com a chave sendo o identificador da fonte.
  3. Coloque o arquivo (CSV ou Excel) em data/raw/<arquivo> antes de rodar a ingestão.

Não importe Django aqui — este módulo é carregado antes do setup do Django
em alguns contextos (ex.: testes unitários puros).

Estrutura de data/raw/:
  sigcon/   — exportações Business Objects / PRODEMGE do SIGCON-MG
  execucao/ — exportações QlikView de despesas estaduais
  uniao/    — dados abertos Transferegov (baixar_siconv.py → siconv.zip)
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FonteDados:
    nome: str        # identificador único; usado como chave em FONTES e como nome de pasta em bronze/
    arquivo: str     # caminho relativo a data/raw/ (pode incluir subpasta, ex.: "sigcon/dcgce_convenio.xlsx")
    formato: str     # "csv" ou "excel"
    descricao: str   # texto livre para documentação
    opcoes_leitura: dict = field(default_factory=dict)  # kwargs extras repassados a pd.read_csv / pd.read_excel


# ---------------------------------------------------------------------------
# Registro central de fontes
# Cada entrada aqui habilita: leitura, ingestão Bronze e comando de gerência.
# ---------------------------------------------------------------------------
FONTES: dict[str, FonteDados] = {

    # -----------------------------------------------------------------------
    # SIGCON-MG — exportações Business Objects / PRODEMGE
    # Arquivos em: data/raw/sigcon/
    # Todos usam header=1 (linha 0 é vazia; cabeçalho real está na linha 1)
    # exceto dcgce_unidades_executoras que usa header=0.
    # engine=openpyxl é explícito (não apenas inferido da extensão .xlsx)
    # porque estas 15 fontes também podem chegar via core/extract/gmail.py +
    # core/ingestion/ponte_extracao.py, cujo anexo pousa sem extensão.
    # -----------------------------------------------------------------------

    # ---- Tabelas a manter (alimentam o painel Consultas SIGCON) ----

    "dcgce_convenio": FonteDados(
        nome="dcgce_convenio",
        arquivo="sigcon/dcgce_convenio.xlsx",
        formato="excel",
        descricao="Convênios do SIGCON-MG — chave SIAFI+UO, valores e datas de vigência",
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_geral": FonteDados(
        nome="dcgce_geral",
        arquivo="sigcon/dcgce_Geral.xlsx",
        formato="excel",
        descricao=(
            "Dados gerais do SIGCON-MG — traz data de publicação, assinatura e "
            "código do plano de trabalho. Fundido em Convenio no ETL."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_plano_trabalho": FonteDados(
        nome="dcgce_plano_trabalho",
        arquivo="sigcon/dcgce_plano.trabalho.xlsx",
        formato="excel",
        descricao=(
            "Planos de trabalho — PK: plano_trabalho_codigo. Traz título, objeto, "
            "razão social e CNPJ do concedente, CNPJ do proponente."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_cronograma_desembolso": FonteDados(
        nome="dcgce_cronograma_desembolso",
        arquivo="sigcon/dcgce_Cronograma_desembolso.xlsx",
        formato="excel",
        descricao=(
            "Cronograma de desembolsos — liga-se ao convênio via plano_trabalho_codigo. "
            "SIAFI+UO são carimbados no ETL via Geral+CodigoConvenio."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_plano_aplicacao": FonteDados(
        nome="dcgce_plano_aplicacao",
        arquivo="sigcon/dcgce_plano_aplicacao.xlsx",
        formato="excel",
        descricao="Planos de aplicação — liga-se ao convênio via codigo_plano_trabalho",
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_termo_aditivo": FonteDados(
        nome="dcgce_termo_aditivo",
        arquivo="sigcon/dcgce_termo.aditivo.xlsx",
        formato="excel",
        descricao=(
            "Termos aditivos — PK: termo_aditivo_codigo_sequencial. "
            "SIAFI+UO carimbados via ponte dcgce_codigo_ta."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_prorrogacao_oficio": FonteDados(
        nome="dcgce_prorrogacao_oficio",
        arquivo="sigcon/dcgce_prorrogacao_oficio.xlsx",
        formato="excel",
        descricao=(
            "Prorrogações de ofício — prorrogacao_oficio_codigo_convenio equivale a "
            "convenio_codigo_sequencial (não é SIAFI)."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_declaracao_contrapartida": FonteDados(
        nome="dcgce_declaracao_contrapartida",
        arquivo="sigcon/dcgce_declaracao_contrapartida.xlsx",
        formato="excel",
        descricao=(
            "Declarações de contrapartida — PK: declaracao_contrapartida_codigo. "
            "SIAFI+UO carimbados via ponte dcgce_codigo_dec_contrap."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_unidades_executoras": FonteDados(
        nome="dcgce_unidades_executoras",
        arquivo="sigcon/dcgce_unidades.executoras.xlsx",
        formato="excel",
        descricao="Unidades executoras — chave composta SIAFI+UO direta",
        opcoes_leitura={"header": 0, "engine": "openpyxl"},
    ),
    "dcgce_sigcon_nt_emenda": FonteDados(
        nome="dcgce_sigcon_nt_emenda",
        arquivo="sigcon/dcgce_sigcon_nt_emenda.xlsx",
        formato="excel",
        descricao="Notas técnicas de emendas parlamentares — liga via plano_trabalho_codigo+UO",
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_esfera": FonteDados(
        nome="dcgce_esfera",
        arquivo="sigcon/dcgce_esfera.xlsx",
        formato="excel",
        descricao="Dimensão de esferas — chave: concedente_cnpj → concedente_esfera",
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),

    # ---- Tabela de relacionamento SIGCON↔SICONV ----

    "chaves_convenio": FonteDados(
        nome="chaves_convenio",
        arquivo="sigcon/Chaves_convenio.csv",
        formato="csv",
        descricao=(
            "Ponte de relacionamento SIGCON↔SICONV. "
            "Colunas-chave: convenio_numero_sequencial_siafi + unidade_orcamentaria_codigo → SIAFI_UO; "
            "codigo_siconv → NR_CONVENIO (chave para SICONV); "
            "plano_trabalho_tipo_siafi → tipo do instrumento (11=Acordo, 15=Transf. Especial)."
        ),
        opcoes_leitura={"sep": ";", "encoding": "latin-1"},
    ),

    # ---- Pontes ETL (carimbo de chaves; usadas só no loader, não geram aba no painel) ----

    "dcgce_Codigo_plano_de_trabalho": FonteDados(
        nome="dcgce_Codigo_plano_de_trabalho",
        arquivo="sigcon/dcgce_Codigo_plano_de_trabalho.xlsx",
        formato="excel",
        descricao=(
            "Ponte ETL: mapeia conveno_codigo_plano_trabalho → SIAFI+UO. "
            "Usada para derivar tipo de contrapartida por SIAFI_UO."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_codigo_ta": FonteDados(
        nome="dcgce_codigo_ta",
        arquivo="sigcon/dcgce_Codigo_ta.xlsx",
        formato="excel",
        descricao=(
            "Ponte ETL: mapeia termo_aditivo_codigo_sequencial → SIAFI+UO+plano_trabalho_codigo"
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_codigo_dec_contrap": FonteDados(
        nome="dcgce_codigo_dec_contrap",
        arquivo="sigcon/dcgce_Codigo_dec_contrap.xlsx",
        formato="excel",
        descricao=(
            "Ponte ETL: mapeia declaracao_contrapartida_codigo → SIAFI+UO"
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),
    "dcgce_codigo_convenio": FonteDados(
        nome="dcgce_codigo_convenio",
        arquivo="sigcon/dcgce_Codigo_convenio.xlsx",
        formato="excel",
        descricao=(
            "Ponte ETL: mapeia convenio_codigo_sequencial → SIAFI+UO. "
            "Usada para enriquecer dcgce_geral (que não tem UO) e o cronograma."
        ),
        opcoes_leitura={"header": 1, "engine": "openpyxl"},
    ),

    # -----------------------------------------------------------------------
    # Execução estadual — exportações QlikView / Business Objects
    # Arquivos em: data/raw/execucao/
    #
    # ANTI-PADRÃO herdado do QlikView: cada ano é uma fonte separada.
    # TODO (R2+): substituir por uma fonte única qv_despesa com leitura de
    #   todos os arquivos da pasta execucao/ de uma só vez, sem replicar a
    #   entrada por ano. Manter entradas por enquanto para não quebrar cargas
    #   existentes.
    # -----------------------------------------------------------------------

    "qv_despesa_ano_2019": FonteDados(
        nome="qv_despesa_ano_2019",
        arquivo="execucao/qv_despesa_ano_2019.csv",
        formato="csv",
        descricao="Despesas do ano 2019 (exportação QlikView / Business Objects) — ver TODO acima",
        opcoes_leitura={"sep": ";", "encoding": "latin-1"},
    ),
    "qv_despesa_ano_2020": FonteDados(
        nome="qv_despesa_ano_2020",
        arquivo="execucao/qv_despesa_ano_2020.csv",
        formato="csv",
        descricao="Despesas do ano 2020 (exportação QlikView / Business Objects) — ver TODO acima",
        opcoes_leitura={"sep": ";", "encoding": "latin-1"},
    ),

    # -----------------------------------------------------------------------
    # Transferegov / SICONV — dados abertos do governo federal
    # Arquivos em: data/raw/uniao/   (baixar via baixar_siconv.py)
    # -----------------------------------------------------------------------

    "siconv_convenio": FonteDados(
        nome="siconv_convenio",
        arquivo="uniao/siconv_convenio.csv",
        formato="csv",
        descricao="Convênios Transferegov — dados abertos (SICONV/União)",
        opcoes_leitura={"sep": ";", "encoding": "latin-1"},
    ),

    # -----------------------------------------------------------------------
    # Controle interno DCGCE — arquivo avulso em data/raw/
    # -----------------------------------------------------------------------

    "controle_sei": FonteDados(
        nome="controle_sei",
        arquivo="Controle SEI.xlsx",
        formato="excel",
        descricao=(
            "Planilha de controle do nº SEI por convênio. "
            "Chave: Nº_SEI + Nº SIAFI_(SIGCON). "
            "usecols=range(27) exclui colunas duplicadas das posições 29-31 "
            "e os separadores Unnamed:27/28."
        ),
        opcoes_leitura={"header": 0, "sheet_name": "Página1", "usecols": list(range(27))},
    ),

    # -----------------------------------------------------------------------
    # De-paras e tabelas de dimensão — arquivos avulsos em data/raw/
    # Usados na etapa de relacionamento R2+ (não geram aba no painel diretamente)
    # -----------------------------------------------------------------------

    "siafi2": FonteDados(
        nome="siafi2",
        arquivo="SIAFI2.csv",
        formato="csv",
        descricao=(
            "De-para de números SIAFI: mapeia (SIAFI2, UO2) → SIAFIATUAL+UOATUAL. "
            "Usado para projetar convênios na UO atual. "
            "Colunas: SIAFI1;UO1;SIAFI2;UO2;SIAFIATUAL;UOATUAL. "
            "Chave de join com sigcon_chaves: SIAFI_UO = SIAFI2 & UO2 (sem separador)."
        ),
        opcoes_leitura={"sep": ";", "encoding": "latin-1"},
    ),
    "parlamentares": FonteDados(
        nome="parlamentares",
        arquivo="De para nomes parlamentares.xlsx",
        formato="excel",
        descricao=(
            "De-para de nomes de parlamentares (Mapa_Nomes_Parlamentares do QlikView). "
            "Normaliza variações de grafia para um nome canônico."
        ),
        opcoes_leitura={"header": 0},
    ),

    # -----------------------------------------------------------------------
    # Tabelas do GRP — arquivos avulsos em data/raw/grp/
    # -----------------------------------------------------------------------

#     "dcgce_dados_grp": FonteDados(
#         nome="dcgce_dados_grp",
#         arquivo="grp/dcgce_convenio.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de dados do GRP — usada para derivar convenios, cronogramas" \
#             "Chaves: nr_grp"
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
#     "dcgce_cronograma_desembolso_grp": FonteDados(
#         nome="dcgce_cronograma_desembolso_grp",
#         arquivo="grp/dcgce_cronograma_desembolso.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de cronograma de desembolso do GRP. Chave: nr_grp"
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
#     "dcgce_recursos_contrapartida_grp": FonteDados(
#         nome="dcgce_recursos_contrapartida_grp",
#         arquivo="grp/dcgce_recursos_contrapartida.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de recursos de contrapartida do GRP. Chave:nr_grp"
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
#     "dcgce_recursos_concedente_grp": FonteDados(
#         nome="dcgce_recursos_concedente_grp",
#         arquivo="grp/dcgce_recursos_concedente.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de recursos de concedente do GRP. Chave:nr_grp"
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
#     "dcgce_plano_aplicacao_grp": FonteDados(
#         nome="dcgce_plano_aplicacao_grp",
#         arquivo="grp/dcgce_plano_aplicacao.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de planos de aplicação do GRP. Chave: nr_grp."
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
#     "dcgce_plano_aplicacao_grp_detalhes": FonteDados(
#         nome="dcgce_plano_aplicacao_grp_detalhes",
#         arquivo="grp/dcgce_plano_aplicacao_desc.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de detalhes dos planos de aplicação do GRP. Chave: nr_grp."
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
#     "dcgce_esfera_grp": FonteDados(
#         nome="dcgce_esfera_grp",
#         arquivo="grp/dcgce_esfera.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de esferas do GRP. Chave: nr_grp."
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
#     "dcgce_tabela_uo_grp": FonteDados(
#         nome="dcgce_tabela_uo_grp",
#         arquivo="grp/dcgce_tabela_uo.xlsx",
#         formato="excel",
#         descricao=(
#             "Tabela de unidades orçamentárias do GRP. Chave: uo_cod."
#         ),
#         opcoes_leitura={"header": 0, "engine": "openpyxl"},
#     ),
# }

    "grp_instrumento": FonteDados(
            nome="grp_instrumento",
            arquivo="grp/grp_instrumento.csv",
            formato="csv",
            descricao=(
                "Núcleo usado por todas as telas: identificação, situação, vigência, convenente e valores."
                "Todas as variáveis são 1:1 com o instrumento, então reuni-las não duplica linhas."
            ),
            opcoes_leitura={"sep": ",", "encoding": "UTF-8"},  # sep ',' (com todos os campos entre aspas): os campos de texto livre têm vírgulas e quebravam a leitura; exportado com aspas, a ',' dentro do texto fica protegida e não vira coluna extra.
        ),
    "grp_prestacao_contas": FonteDados(
            nome="grp_prestacao_contas",
            arquivo="grp/grp_prestacao_contas.csv",
            formato="csv",
            descricao=(
                "Fase própria do ciclo de vida, vazia para instrumentos vigentes."
                "Alimenta um painel específico de prestação de contas."
                "Por ser 1:1, pode ser incorporada à consulta 01 sem risco, se preferir menos extrações."
           ),
           opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_planejamento_obras": FonteDados(
            nome="grp_planejamento_obras",
            arquivo="grp/grp_planejamento_obras.csv",
            formato="csv",
            descricao=(
                "Só se aplica a instrumentos de obras."
                "Separar evita 13 colunas quase sempre vazias no núcleo."
                "Também é 1:1 e pode ser incorporada à 01"
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_proposta_marco_logico": FonteDados(
            nome="grp_proposta_marco_logico",
            arquivo="grp/grp_proposta_marco_logico.csv",
            formato="csv",
            descricao=(
                "Textos longos do marco lógico: pesados, raramente filtrados e sujeitos a corte no Excel."
                "Deve permanecer separada também na silver (texto longo e pouco consultado é um motivo legítimo para uma tabela 1:1). Exportar em CSV."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_concedente": FonteDados(
            nome="grp_concedente",
            arquivo="grp/grp_concedente.csv",
            formato="csv",
            descricao=(
                "Origem da dimensão Concedente, cuja chave natural é o CNPJ"
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_emenda": FonteDados(
            nome="grp_emenda",
            arquivo="grp/grp_emenda.csv",
            formato="csv",
            descricao=(
                "Elo central da DCGCE com as emendas parlamentares. Permite painéis por parlamentar, ano e situação da emenda."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_interveniente": FonteDados(
            nome="grp_interveniente",
            arquivo="grp/grp_interveniente.csv",
            formato="csv",
            descricao=(
                "Identifica quem executa em nome do convenente, quando há interveniente (ver fl_interveniente_executor na 01)."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_unidade_executora": FonteDados(
            nome="grp_unidade_executora",
            arquivo="grp/grp_unidade_executora.csv",
            formato="csv",
            descricao=(
                "Responde à pergunta 'quais as unidades executoras?'. Os códigos de órgão devem apontar para a dimensão única de UO/órgão."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_municipio_atendido": FonteDados(
            nome="grp_municipio_atendido",
            arquivo="grp/grp_municipio_atendido.csv",
            formato="csv",
            descricao=(
                "Base para mapas e recortes territoriais. O código do município permite cruzar com IBGE."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_regiao_atendida": FonteDados(
            nome="grp_regiao_atendida",
            arquivo="grp/grp_regiao_atendida.csv",
            formato="csv",
            descricao=(
                "Recorte por região. Atenção: o grão inclui o município da região, então nunca juntar com a 09 sem agregar antes."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_recurso_concedente": FonteDados(
            nome="grp_recurso_concedente",
            arquivo="grp/grp_recurso_concedente.csv",
            formato="csv",
            descricao=(
                "Origem do recurso federal no orçamento estadual, por UO arrecadadora, com o órgão gestor."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_recurso_contrapartida": FonteDados(
            nome="grp_recurso_contrapartida",
            arquivo="grp/grp_recurso_contrapartida.csv",
            formato="csv",
            descricao=(
                "Contrapartida financeira do estado por UO financiadora."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_dotacao_contrapartida": FonteDados(
            nome="grp_dotacao_contrapartida",
            arquivo="grp/grp_dotacao_contrapartida.csv",
            formato="csv",
            descricao=(
                "Dotação orçamentária que suporta a contrapartida. Complementa a grp_recurso_contrapartida."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_acao_orcamentaria": FonteDados(
            nome="grp_acao_orcamentaria",
            arquivo="grp/grp_acao_orcamentaria.csv",
            formato="csv",
            descricao=(
                "Vínculo com o orçamento estadual. É a ponte natural com SIAFI/SIGCON (ação + UO)."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_instrumento_financiado": FonteDados(
            nome="grp_instrumento_financiado",
            arquivo="grp/grp_instrumento_financiado.csv",
            formato="csv",
            descricao=(
                "Responde à pergunta 'quais são os outros instrumentos financiados?'. Relaciona instrumentos entre si."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_item_executar": FonteDados(
            nome="grp_item_executar",
            arquivo="grp/grp_item_executar.csv",
            formato="csv",
            descricao=(
                "Detalhe da despesa prevista. Maior volume do modelo: exportar em CSV. A fonte não tem ID de item, por isso todos os atributos marcados G são obrigatórios."
            ),
            opcoes_leitura={"sep": ",", "encoding": "UTF-8"},  # sep ',' (com todos os campos entre aspas): os campos de texto livre têm vírgulas e quebravam a leitura; exportado com aspas, a ',' dentro do texto fica protegida e não vira coluna extra.
        ),
    "grp_cronograma_desembolso": FonteDados(
            nome="grp_cronograma_desembolso",
            arquivo="grp/grp_cronograma_desembolso.csv",
            formato="csv",
            descricao=(
                "Fluxo financeiro previsto. 'Mês Descritivo' e 'Mês Abreviado' foram excluídos porque derivam de 'Desembolso - Mês' e serão calculados em SQL."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_cronograma_fisico": FonteDados(
            nome="grp_cronograma_fisico",
            arquivo="grp/grp_cronograma_fisico.csv",
            formato="csv",
            descricao=(
                "Execução física planejada. Atenção: os dados da meta se repetem em cada etapa dela; nunca somar vl_meta diretamente nesta tabela."
            ),
            opcoes_leitura={"sep": ",", "encoding": "UTF-8"},  # sep ',' (com todos os campos entre aspas): os campos de texto livre têm vírgulas e quebravam a leitura; exportado com aspas, a ',' dentro do texto fica protegida e não vira coluna extra.
        ),
    "grp_entrega_projeto": FonteDados(
            nome="grp_entrega_projeto",
            arquivo="grp/grp_entrega_projeto.csv",
            formato="csv",
            descricao=(
                "Produtos do projeto no marco lógico."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_atividade_projeto": FonteDados(
            nome="grp_atividade_projeto",
            arquivo="grp/grp_atividade_projeto.csv",
            formato="csv",
            descricao=(
                "Atividades do projeto no marco lógico."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_matriz_responsabilidade": FonteDados(
            nome="grp_matriz_responsabilidade",
            arquivo="grp/grp_matriz_responsabilidade.csv",
            formato="csv",
            descricao=(
                " Quem responde por cada instrumento. Contém dados pessoais (LGPD): extrair apenas o necessário, nunca versionar o arquivo e restringir o acesso no painel."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        ),
    "grp_tabela_uo": FonteDados(
            nome="grp_tabela_uo",
            arquivo="grp/grp_tabela_uo.csv",
            formato="csv",
            descricao=(
                "Tabela que consta todas as UOs e seus respectivos nomes."
            ),
            opcoes_leitura={"sep": ";", "encoding": "UTF-8", "header": 0},  # sep ';': padrão do export do GRP (Excel pt-BR) — a ',' é o separador decimal dos valores (ex.: 133.829,20), então não pode separar colunas. header=0: a 1ª linha do arquivo traz os nomes das colunas (é o default do pandas, deixado explícito para documentar o layout).
        )
}