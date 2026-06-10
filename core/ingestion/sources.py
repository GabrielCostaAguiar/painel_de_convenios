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
    # -----------------------------------------------------------------------

    # ---- Tabelas a manter (alimentam o painel Consultas SIGCON) ----

    "dcgce_convenio": FonteDados(
        nome="dcgce_convenio",
        arquivo="sigcon/dcgce_convenio.xlsx",
        formato="excel",
        descricao="Convênios do SIGCON-MG — chave SIAFI+UO, valores e datas de vigência",
        opcoes_leitura={"header": 1},
    ),
    "dcgce_geral": FonteDados(
        nome="dcgce_geral",
        arquivo="sigcon/dcgce_Geral.xlsx",
        formato="excel",
        descricao=(
            "Dados gerais do SIGCON-MG — traz data de publicação, assinatura e "
            "código do plano de trabalho. Fundido em Convenio no ETL."
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_plano_trabalho": FonteDados(
        nome="dcgce_plano_trabalho",
        arquivo="sigcon/dcgce_plano.trabalho.xlsx",
        formato="excel",
        descricao=(
            "Planos de trabalho — PK: plano_trabalho_codigo. Traz título, objeto, "
            "razão social e CNPJ do concedente, CNPJ do proponente."
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_cronograma_desembolso": FonteDados(
        nome="dcgce_cronograma_desembolso",
        arquivo="sigcon/dcgce_Cronograma_desembolso.xlsx",
        formato="excel",
        descricao=(
            "Cronograma de desembolsos — liga-se ao convênio via plano_trabalho_codigo. "
            "SIAFI+UO são carimbados no ETL via Geral+CodigoConvenio."
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_plano_aplicacao": FonteDados(
        nome="dcgce_plano_aplicacao",
        arquivo="sigcon/dcgce_plano_aplicacao.xlsx",
        formato="excel",
        descricao="Planos de aplicação — liga-se ao convênio via codigo_plano_trabalho",
        opcoes_leitura={"header": 1},
    ),
    "dcgce_termo_aditivo": FonteDados(
        nome="dcgce_termo_aditivo",
        arquivo="sigcon/dcgce_termo.aditivo.xlsx",
        formato="excel",
        descricao=(
            "Termos aditivos — PK: termo_aditivo_codigo_sequencial. "
            "SIAFI+UO carimbados via ponte dcgce_codigo_ta."
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_prorrogacao_oficio": FonteDados(
        nome="dcgce_prorrogacao_oficio",
        arquivo="sigcon/dcgce_prorrogacao_oficio.xlsx",
        formato="excel",
        descricao=(
            "Prorrogações de ofício — prorrogacao_oficio_codigo_convenio equivale a "
            "convenio_codigo_sequencial (não é SIAFI)."
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_declaracao_contrapartida": FonteDados(
        nome="dcgce_declaracao_contrapartida",
        arquivo="sigcon/dcgce_declaracao_contrapartida.xlsx",
        formato="excel",
        descricao=(
            "Declarações de contrapartida — PK: declaracao_contrapartida_codigo. "
            "SIAFI+UO carimbados via ponte dcgce_codigo_dec_contrap."
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_unidades_executoras": FonteDados(
        nome="dcgce_unidades_executoras",
        arquivo="sigcon/dcgce_unidades.executoras.xlsx",
        formato="excel",
        descricao="Unidades executoras — chave composta SIAFI+UO direta",
        opcoes_leitura={"header": 0},
    ),
    "dcgce_sigcon_nt_emenda": FonteDados(
        nome="dcgce_sigcon_nt_emenda",
        arquivo="sigcon/dcgce_sigcon_nt_emenda.xlsx",
        formato="excel",
        descricao="Notas técnicas de emendas parlamentares — liga via plano_trabalho_codigo+UO",
        opcoes_leitura={"header": 1},
    ),
    "dcgce_esfera": FonteDados(
        nome="dcgce_esfera",
        arquivo="sigcon/dcgce_esfera.xlsx",
        formato="excel",
        descricao="Dimensão de esferas — chave: concedente_cnpj → concedente_esfera",
        opcoes_leitura={"header": 1},
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

    "dcgce_codigo_ta": FonteDados(
        nome="dcgce_codigo_ta",
        arquivo="sigcon/dcgce_Codigo_ta.xlsx",
        formato="excel",
        descricao=(
            "Ponte ETL: mapeia termo_aditivo_codigo_sequencial → SIAFI+UO+plano_trabalho_codigo"
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_codigo_dec_contrap": FonteDados(
        nome="dcgce_codigo_dec_contrap",
        arquivo="sigcon/dcgce_Codigo_dec_contrap.xlsx",
        formato="excel",
        descricao=(
            "Ponte ETL: mapeia declaracao_contrapartida_codigo → SIAFI+UO"
        ),
        opcoes_leitura={"header": 1},
    ),
    "dcgce_codigo_convenio": FonteDados(
        nome="dcgce_codigo_convenio",
        arquivo="sigcon/dcgce_Codigo_convenio.xlsx",
        formato="excel",
        descricao=(
            "Ponte ETL: mapeia convenio_codigo_sequencial → SIAFI+UO. "
            "Usada para enriquecer dcgce_geral (que não tem UO) e o cronograma."
        ),
        opcoes_leitura={"header": 1},
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

}
