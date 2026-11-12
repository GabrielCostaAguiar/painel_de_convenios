"""
Catálogo de testes de qualidade do SIGCON (Modelo de Extração SIGCON v1.0,
docs/modelo_extracao_sigcon.pdf — seção 12, checklist V1–V14).

Cada teste é um dict com `id`, `severidade` (ERRO bloqueia, ALERTA só registra),
`tabela`, `descricao` e `sql` (linhas que VIOLAM a regra) ou `funcao`
(devolve (qt, amostra)). `validar_sigcon` roda tudo e grava em
ResultadoValidacao (tabela dq_resultado_validacao_sigcon).

IDs: `T-<categoria><nn>`, numerados automaticamente por `_numerar` na ordem em
que o teste aparece em cada categoria. Não há número escrito à mão: inserir um
teste no meio renumera os seguintes — o histórico de resultados é por execução,
então o id só precisa ser único DENTRO de uma execução (garantido por teste).
As letras: A volumetria e arquivos, B tipos, C grão, D completude, E formato e
encoding, F órfãos, G reconciliação, H domínio, I datas. As tabelas de resultado
do SIGCON e do GRP são separadas, então os ids podem repetir entre os apps.

  ERRO   = o modelo declara a regra como verdadeira.
  ALERTA = exceção conhecida e documentada no modelo, ou regra ainda não
           confirmada contra a base real (por isso não bloqueia o pipeline).
  limite = teste com exceção conhecida medida (limites.py): ALERTA até o limite,
           ERRO acima dele.
"""

from functools import partial

from apps.sigcon.validacao.arquivos import (
    teste_arquivos_antigos,
    teste_arquivos_ausentes,
)
from apps.sigcon.validacao.generico import (
    sql_formato,
    sql_nao_nulo,
    sql_orfaos,
    sql_unicidade,
    sql_valores_aceitos,
)
from apps.sigcon.validacao.limites import LIMITES_CONHECIDOS as LIM
from apps.sigcon.validacao.texto import teste_mojibake
from apps.sigcon.validacao.volumetria import (
    teste_variacao_volumetria,
    teste_volumetria,
)

# ---------------------------------------------------------------------------
# Grãos (modelo de extração, seção 6 — "Grão: o que é uma linha").
# Têm de coincidir com `grao:` do YAML de cada fonte em core/transform/schemas/
# (tests/test_validacao_sigcon.py confere os dois).
# ---------------------------------------------------------------------------
GRAOS = {
    "sigcon_convenio": ["siafi_uo"],
    "sigcon_convenio_geral": ["cd_convenio_sequencial"],
    "sigcon_plano_trabalho": ["cd_plano_trabalho"],
    "sigcon_termo_aditivo": ["cd_termo_aditivo"],
    "sigcon_prorrogacao_oficio": ["cd_prorrogacao_oficio"],
    "sigcon_declaracao_contrapartida": ["cd_declaracao_contrapartida"],
    # plano de trabalho x ano x mês (só as linhas válidas: ver FILTRO_GRAO)
    "sigcon_cronograma_desembolso": [
        "cd_plano_trabalho",
        "nr_ano_desembolso",
        "nr_mes_desembolso",
    ],
    # plano x classificação orçamentária x ano; sem o ano há 3 duplicatas (P8/V14)
    "sigcon_plano_aplicacao": [
        "cd_plano_trabalho",
        "cd_uo",
        "cd_funcao",
        "cd_subfuncao",
        "cd_programa",
        "cd_identificador_projeto_atividade",
        "cd_projeto_atividade",
        "cd_subprojeto_subatividade",
        "cd_categoria_economica",
        "cd_grupo_despesa",
        "cd_modalidade_aplicacao",
        "cd_elemento_despesa",
        "cd_identificador_orcamento",
        "cd_fonte_recurso",
        "cd_procedencia",
        "nr_ano_exercicio",
    ],
    # convênio x unidade executora: em média 12 por convênio (1:N)
    "sigcon_unidade_executora": ["siafi_uo", "cd_unidade_executora"],
    "sigcon_nt_emenda": ["cd_plano_trabalho"],
    "sigcon_chave_convenio": ["cd_convenio_sequencial"],
    "sigcon_chave_termo_aditivo": ["cd_termo_aditivo"],
    "sigcon_chave_plano_trabalho": ["siafi_uo"],
    "sigcon_chave_declaracao": ["siafi_uo"],
    "sigcon_concedente": ["nr_cnpj_concedente"],
    # Fora do modelo v1.0 (tabela 16, ainda sem grão no YAML): uma linha por
    # UO por exercício, já que o nome da UO muda entre exercícios.
    "sigcon_tabela_uo": ["cd_uo", "nr_ano_exercicio"],
}

# Tabelas cujo grão ainda não está fechado: duplicata vira ALERTA, não ERRO.
GRAOS_EM_TRATAMENTO = {"sigcon_tabela_uo"}

# Linhas que a Silver marca em vez de excluir ficam de fora do grão e da
# completude. No cronograma, ~38% do arquivo do BO é um bloco desalinhado
# (sem plano, ano nem valor): ds_alerta_linha diz o motivo (premissa P6).
FILTRO_GRAO = {
    "sigcon_cronograma_desembolso": "ds_alerta_linha IS NULL",
    # Chaves nulas não são duplicata de si mesmas: a ausência é testada em T-D.
    "sigcon_convenio": "siafi_uo IS NOT NULL",
    "sigcon_nt_emenda": "cd_plano_trabalho IS NOT NULL",
    "sigcon_unidade_executora": "siafi_uo IS NOT NULL",
    "sigcon_chave_plano_trabalho": "siafi_uo IS NOT NULL",
    "sigcon_chave_declaracao": "siafi_uo IS NOT NULL",
}

# Variação máxima entre duas cargas consecutivas: acima de 5% é ALERTA, acima de
# 30% é ERRO. Na primeira carga (sem histórico) o teste passa.
VARIACAO_ALERTA = 0.05
VARIACAO_ERRO = 0.30

TABELAS_MUST = [
    "sigcon_convenio",
    "sigcon_convenio_geral",
    "sigcon_plano_trabalho",
    "sigcon_termo_aditivo",
    "sigcon_cronograma_desembolso",
    "sigcon_plano_aplicacao",
    "sigcon_chave_convenio",
    "sigcon_chave_termo_aditivo",
    "sigcon_concedente",
    "sigcon_tabela_uo",
]


def _numerar(categoria, testes):
    """Atribui `T-<categoria><nn>` em sequência a cada teste da lista."""
    for i, teste in enumerate(testes, start=1):
        teste["id"] = f"T-{categoria}{i:02d}"
    return testes


def _limitado(teste, chave):
    """Marca o teste como 'exceção conhecida com limite' (ver limites.py)."""
    limite = LIM[chave]
    teste["severidade"] = "ERRO"
    teste["limite"] = limite
    teste["chave_limite"] = chave
    teste["descricao"] += f" [exceção conhecida: até {limite} em ALERTA, acima disso ERRO]"
    return teste


def _uniao_vazias(tabelas):
    """SQL que lista as tabelas que não têm nenhuma linha."""
    return "\nUNION ALL\n".join(
        f"SELECT '{t}' AS tabela WHERE NOT EXISTS (SELECT 1 FROM {t})"
        for t in tabelas
    )


# --- T-A: volumetria e arquivos de entrada ------------------------------------

TESTES_A = _numerar(
    "A",
    [
        {
            "severidade": "ERRO",
            "tabela": "sigcon_*",
            "descricao": "Linhas do parquet iguais às da tabela no banco, nas tabelas sigcon_*",
            "funcao": teste_volumetria,
        },
        {
            "severidade": "ERRO",
            "tabela": f"{len(TABELAS_MUST)} tabelas Must",
            "descricao": "Tabelas Must não podem estar vazias",
            "sql": _uniao_vazias(TABELAS_MUST),
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_*",
            "descricao": (
                f"Linhas carregadas variaram mais de {VARIACAO_ALERTA:.0%} e até "
                f"{VARIACAO_ERRO:.0%} em relação à carga anterior (histórico de carregar_sigcon)"
            ),
            "funcao": partial(teste_variacao_volumetria, VARIACAO_ALERTA, VARIACAO_ERRO),
        },
        {
            "severidade": "ERRO",
            "tabela": "sigcon_*",
            "descricao": (
                f"Linhas carregadas variaram mais de {VARIACAO_ERRO:.0%} em relação à "
                "carga anterior (histórico de carregar_sigcon)"
            ),
            "funcao": partial(teste_variacao_volumetria, VARIACAO_ERRO),
        },
        {
            "severidade": "ERRO",
            "tabela": "data/raw/sigcon",
            "descricao": "Todo arquivo de entrada esperado existe em data/raw",
            "funcao": teste_arquivos_ausentes,
        },
        {
            "severidade": "ALERTA",
            "tabela": "data/raw/sigcon",
            "descricao": "Arquivos de entrada com mais dias que SIGCON_RAW_MAX_DIAS desde a última modificação",
            "funcao": teste_arquivos_antigos,
        },
    ],
)

# --- T-B: tipos pelo prefixo da coluna ---------------------------------------

TESTES_B = _numerar(
    "B",
    [
        {
            "severidade": "ERRO",
            "tabela": "sigcon_* (colunas por prefixo)",
            "descricao": (
                "O prefixo da coluna define o tipo: vl_ numérico, dt_/dh_ data, "
                "fl_ booleano, códigos e CNPJ texto"
            ),
            "sql": r"""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name LIKE 'sigcon\_%'
                  AND (
                      (column_name LIKE 'vl\_%' AND data_type <> 'numeric')
                      OR (column_name ~ '^d[th]_' AND data_type NOT IN
                          ('date', 'timestamp without time zone', 'timestamp with time zone'))
                      OR (column_name LIKE 'fl\_%' AND data_type <> 'boolean')
                      OR (column_name ~ '^(cd|nr_cnpj)_|^siafi_uo$'
                          AND data_type NOT IN ('character varying', 'text'))
                  )
            """,
        },
        {
            "severidade": "ERRO",
            "tabela": "sigcon_* (anos e meses)",
            "descricao": "nr_ano_* e nr_mes_* devem ser inteiros, não texto",
            "sql": r"""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name LIKE 'sigcon\_%'
                  AND column_name ~ '^nr_(ano|mes)_'
                  AND data_type NOT IN ('integer', 'bigint', 'smallint')
            """,
        },
    ],
)

# --- T-C: grão ---------------------------------------------------------------

# cd_plano_trabalho se repete em sigcon_convenio_geral porque convênios
# diferentes compartilham o mesmo plano (T6): colisão legítima, não duplicata.
# Lista medida em 2026-11-12 (18 códigos, 51 linhas; o PDF cita 38). Código fora
# desta lista é colisão nova e merece conferência.
PLANOS_COMPARTILHADOS_CONHECIDOS = [
    "1043", "1197", "1595", "1663", "1709", "3587", "3603", "3655", "444",
    "5707", "627", "7328", "7848", "7964", "8023", "8687", "9240", "9299",
]

TESTES_C = _numerar(
    "C",
    [
        {
            "severidade": "ALERTA" if tabela in GRAOS_EM_TRATAMENTO else "ERRO",
            "tabela": tabela,
            "descricao": f"Grão: {', '.join(colunas)}",
            "sql": sql_unicidade(tabela, colunas, FILTRO_GRAO.get(tabela)),
        }
        for tabela, colunas in GRAOS.items()
    ]
    + [
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_convenio_geral",
            "descricao": (
                "Colisões de cd_plano_trabalho só nos planos compartilhados conhecidos "
                f"({len(PLANOS_COMPARTILHADOS_CONHECIDOS)} códigos; ver "
                "PLANOS_COMPARTILHADOS_CONHECIDOS): código novo aparece aqui"
            ),
            "sql": f"""
                SELECT cd_plano_trabalho, COUNT(*) AS qt
                FROM sigcon_convenio_geral
                WHERE cd_plano_trabalho IS NOT NULL
                  AND cd_plano_trabalho NOT IN (
                      {", ".join(f"'{c}'" for c in PLANOS_COMPARTILHADOS_CONHECIDOS)}
                  )
                GROUP BY cd_plano_trabalho
                HAVING COUNT(*) > 1
            """,
        }
    ],
)

# --- T-D: completude da chave ------------------------------------------------
# (tabela, coluna, chave em LIM ou None, motivo). Com chave: exceção conhecida
# com limite (ALERTA até o limite, ERRO acima); sem chave: ERRO.
CHAVES_OBRIGATORIAS = [
    ("sigcon_convenio", "siafi_uo", "convenios_sem_siafi_uo",
     "convênios sem SIAFI ficam sem chave (T1); 3 são registros de teste"),
    ("sigcon_convenio_geral", "cd_convenio_sequencial", None, None),
    ("sigcon_plano_trabalho", "cd_plano_trabalho", None, None),
    ("sigcon_termo_aditivo", "cd_termo_aditivo", None, None),
    ("sigcon_prorrogacao_oficio", "cd_prorrogacao_oficio", None, None),
    ("sigcon_declaracao_contrapartida", "cd_declaracao_contrapartida", None, None),
    ("sigcon_plano_aplicacao", "cd_plano_trabalho", None, None),
    ("sigcon_unidade_executora", "siafi_uo", "unidade_executora_sem_siafi_uo",
     "convênios sem SIAFI não geram siafi_uo"),
    ("sigcon_unidade_executora", "cd_unidade_executora", None, None),
    ("sigcon_nt_emenda", "cd_plano_trabalho", "nt_emenda_sem_plano",
     "emendas com o sentinela 99999999 ficam sem plano (T4)"),
    ("sigcon_chave_convenio", "cd_convenio_sequencial", None, None),
    ("sigcon_chave_termo_aditivo", "cd_termo_aditivo", None, None),
    ("sigcon_chave_plano_trabalho", "siafi_uo", "chave_plano_trabalho_sem_siafi_uo",
     "convênios sem SIAFI ficam sem chave"),
    ("sigcon_chave_declaracao", "siafi_uo", "chave_declaracao_sem_siafi_uo",
     "convênios sem SIAFI ficam sem chave"),
    ("sigcon_concedente", "nr_cnpj_concedente", None, None),
    ("sigcon_tabela_uo", "cd_uo", None, None),
]


def _teste_chave_obrigatoria(tabela, coluna, chave_limite, motivo):
    teste = {
        "severidade": "ERRO",
        "tabela": tabela,
        "descricao": f"{coluna} preenchido" + (f" ({motivo})" if motivo else ""),
        "sql": sql_nao_nulo(tabela, coluna),
    }
    return _limitado(teste, chave_limite) if chave_limite else teste


TESTES_D = _numerar(
    "D",
    [_teste_chave_obrigatoria(*c) for c in CHAVES_OBRIGATORIAS]
    + [
        {
            # No cronograma as linhas marcadas não têm plano por definição.
            "severidade": "ERRO",
            "tabela": "sigcon_cronograma_desembolso",
            "descricao": "cd_plano_trabalho preenchido nas linhas válidas (sem ds_alerta_linha)",
            "sql": sql_nao_nulo(
                "sigcon_cronograma_desembolso",
                "cd_plano_trabalho",
                FILTRO_GRAO["sigcon_cronograma_desembolso"],
            ),
        }
    ],
)

# --- T-E: formato, domínio numérico e encoding ---------------------------------

# (tabela, coluna, chave em LIM ou None). Erros da fonte, que não é corrigida.
CNPJS = [
    ("sigcon_plano_trabalho", "nr_cnpj_concedente", None),
    ("sigcon_plano_trabalho", "nr_cnpj_proponente", "cnpj_proponente_invalido"),
    ("sigcon_concedente", "nr_cnpj_concedente", "cnpj_concedente_invalido"),
]

# V2/P2: cd_uo tem sempre 4 caracteres; sem isso, a concatenação nr_siafi||cd_uo
# do siafi_uo pode colidir.
TABELAS_COM_UO = [
    "sigcon_convenio",
    "sigcon_plano_aplicacao",
    "sigcon_unidade_executora",
    "sigcon_nt_emenda",
    "sigcon_chave_convenio",
    "sigcon_chave_termo_aditivo",
    "sigcon_chave_plano_trabalho",
    "sigcon_chave_declaracao",
    "sigcon_tabela_uo",
]
# O sentinela 99999999 (plano/declaração "inexistente") traz cd_uo = 9999999999.
LIMITE_CD_UO = {"sigcon_plano_aplicacao": "cd_uo_com_tamanho_errado"}

# Tabelas que trazem as três colunas da chave composta (siafi_uo = nr_siafi||cd_uo).
TABELAS_COM_SIAFI_UO = [
    "sigcon_convenio",
    "sigcon_unidade_executora",
    "sigcon_chave_convenio",
    "sigcon_chave_termo_aditivo",
    "sigcon_chave_plano_trabalho",
    "sigcon_chave_declaracao",
]

# O ano 9999 vem da mesma linha sentinela 99999999; por isso estes ficam em ALERTA.
COLUNAS_ANO = [
    ("sigcon_convenio_geral", "nr_ano_convenio"),
    ("sigcon_plano_trabalho", "nr_ano_plano_trabalho"),
    ("sigcon_termo_aditivo", "nr_ano_termo_aditivo"),
    ("sigcon_declaracao_contrapartida", "nr_ano_declaracao"),
    ("sigcon_cronograma_desembolso", "nr_ano_desembolso"),
    ("sigcon_plano_aplicacao", "nr_ano_exercicio"),
    ("sigcon_tabela_uo", "nr_ano_exercicio"),
]


def _teste_cnpj(tabela, coluna, chave_limite):
    teste = {
        "severidade": "ERRO",
        "tabela": tabela,
        "descricao": f"{coluna}: CNPJ com 14 dígitos",
        "sql": sql_formato(tabela, coluna, r"^\d{14}$"),
    }
    return _limitado(teste, chave_limite) if chave_limite else teste


def _teste_cd_uo(tabela):
    teste = {
        "severidade": "ERRO",
        "tabela": tabela,
        "descricao": "cd_uo com 4 caracteres (P2/V2)",
        "sql": sql_formato(tabela, "cd_uo", r"^.{4}$"),
    }
    chave = LIMITE_CD_UO.get(tabela)
    return _limitado(teste, chave) if chave else teste


TESTES_E = _numerar(
    "E",
    [_teste_cnpj(*c) for c in CNPJS]
    + [_teste_cd_uo(t) for t in TABELAS_COM_UO]
    + [
        {
            "severidade": "ERRO",
            "tabela": t,
            "descricao": "siafi_uo = nr_siafi || cd_uo (sem separador)",
            "sql": f"""
                SELECT nr_siafi, cd_uo, siafi_uo
                FROM {t}
                WHERE siafi_uo IS NOT NULL
                  AND siafi_uo <> nr_siafi || cd_uo
            """,
        }
        for t in TABELAS_COM_SIAFI_UO
    ]
    + [
        {
            "severidade": "ERRO",
            "tabela": "sigcon_cronograma_desembolso",
            "descricao": "nr_mes_desembolso entre 1 e 12 nas linhas válidas (V7)",
            "sql": sql_valores_aceitos(
                "sigcon_cronograma_desembolso",
                "nr_mes_desembolso",
                range(1, 13),
                FILTRO_GRAO["sigcon_cronograma_desembolso"],
            ),
        },
        {
            "severidade": "ERRO",
            "tabela": "sigcon_concedente",
            "descricao": "ds_esfera sem espaço nas pontas — o trim da silver funcionou (V13)",
            "sql": """
                SELECT ds_esfera
                FROM sigcon_concedente
                WHERE ds_esfera <> BTRIM(ds_esfera)
            """,
        },
    ]
    + [
        {
            "severidade": "ALERTA",
            "tabela": t,
            "descricao": f"{c}: ano entre 1950 e 2050",
            "sql": sql_valores_aceitos(t, c, range(1950, 2051), FILTRO_GRAO.get(t)),
        }
        for t, c in COLUNAS_ANO
    ]
    + [
        {
            "severidade": "ERRO",
            "tabela": "sigcon_* (colunas de texto)",
            "descricao": (
                "Sem mojibake (UTF-8 lido como cp1252, ex.: 'Ã§', 'Ã£', 'Â', 'â€') em colunas de texto"
            ),
            "funcao": teste_mojibake,
        }
    ],
)

# --- T-F: órfãos (integridade referencial que o banco não impõe) -------------
# O SIGCON não tem FK: as tabelas se ligam por siafi_uo / códigos. Cada teste
# lista linhas da tabela "filha" cujo valor não existe na "pai".
# (filha, col_filha, pai, col_pai, severidade, descrição, filtro_filha, chave em LIM)
# Com chave em LIM a severidade é a do limite (ALERTA até ele, ERRO acima).
LIGACOES = [
    (
        "sigcon_convenio_geral", "cd_convenio_sequencial",
        "sigcon_chave_convenio", "cd_convenio_sequencial",
        "ERRO", "cobertura de 100% da ponte 11 sobre a tabela 02 (T10)", None, None,
    ),
    (
        "sigcon_chave_convenio", "cd_convenio_sequencial",
        "sigcon_convenio_geral", "cd_convenio_sequencial",
        "ERRO", "toda linha da ponte 11 tem convênio na tabela 02", None, None,
    ),
    (
        "sigcon_prorrogacao_oficio", "cd_convenio_sequencial",
        "sigcon_chave_convenio", "cd_convenio_sequencial",
        "ERRO", "447 de 448 sequenciais casam; 1 órfão conhecido (P7)", None,
        "prorrogacao_orfa",
    ),
    (
        "sigcon_termo_aditivo", "cd_termo_aditivo",
        "sigcon_chave_termo_aditivo", "cd_termo_aditivo",
        "ALERTA", "7.113 aditivos contra 7.105 na ponte 12: pequena diferença conhecida", None, None,
    ),
    (
        "sigcon_chave_termo_aditivo", "cd_termo_aditivo",
        "sigcon_termo_aditivo", "cd_termo_aditivo",
        "ALERTA", "todo aditivo da ponte 12 existe na tabela 04", None, None,
    ),
    (
        "sigcon_chave_termo_aditivo", "siafi_uo",
        "sigcon_convenio", "siafi_uo",
        "ALERTA", "o convênio do aditivo existe na tabela 01", None, None,
    ),
    (
        "sigcon_chave_plano_trabalho", "siafi_uo",
        "sigcon_convenio", "siafi_uo",
        "ALERTA", "o convênio da ponte 13 existe na tabela 01", None, None,
    ),
    (
        "sigcon_chave_declaracao", "siafi_uo",
        "sigcon_convenio", "siafi_uo",
        "ALERTA", "o convênio da ponte 14 existe na tabela 01", None, None,
    ),
    (
        "sigcon_unidade_executora", "siafi_uo",
        "sigcon_convenio", "siafi_uo",
        "ALERTA", "o convênio da unidade executora existe na tabela 01", None, None,
    ),
    (
        "sigcon_cronograma_desembolso", "cd_plano_trabalho",
        "sigcon_plano_trabalho", "cd_plano_trabalho",
        "ALERTA", "o plano do cronograma existe na tabela 03 (linhas válidas)",
        FILTRO_GRAO["sigcon_cronograma_desembolso"], None,
    ),
    (
        "sigcon_plano_aplicacao", "cd_plano_trabalho",
        "sigcon_plano_trabalho", "cd_plano_trabalho",
        "ERRO", "o plano do plano de aplicação existe na tabela 03", None,
        "plano_aplicacao_sem_plano_trabalho",
    ),
    (
        "sigcon_nt_emenda", "cd_plano_trabalho",
        "sigcon_plano_trabalho", "cd_plano_trabalho",
        "ALERTA", "o plano da nota técnica de emenda existe na tabela 03", None, None,
    ),
    (
        "sigcon_declaracao_contrapartida", "cd_declaracao_contrapartida",
        "sigcon_chave_declaracao", "cd_declaracao_contrapartida",
        "ERRO", "declarações sem ponte esperadas (61,6%, P5/V9)", None,
        "declaracoes_sem_ponte",
    ),
    (
        "sigcon_plano_trabalho", "nr_cnpj_concedente",
        "sigcon_concedente", "nr_cnpj_concedente",
        "ALERTA", "o CNPJ do concedente existe na dimensão de esferas", None, None,
    ),
    (
        "sigcon_convenio", "cd_uo",
        "sigcon_tabela_uo", "cd_uo",
        "ALERTA", "a UO do convênio existe na tabela de UOs", None, None,
    ),
]


def _teste_ligacao(filha, col_filha, pai, col_pai, severidade, motivo, filtro, chave_limite):
    teste = {
        "severidade": severidade,
        "tabela": filha,
        "descricao": f"{col_filha} existe em {pai}.{col_pai}: {motivo}",
        "sql": sql_orfaos(filha, col_filha, pai, col_pai, filtro),
    }
    return _limitado(teste, chave_limite) if chave_limite else teste


TESTES_F = _numerar("F", [_teste_ligacao(*lig) for lig in LIGACOES])

# --- T-G: reconciliação entre tabelas ----------------------------------------
# Tolerância de R$ 0,01 nas somas. Diferenças são pergunta para a equipe do
# SIGCON, não defeito de carga.


def _soma_por_plano(modelo, coluna_valor, filtro=None):
    onde = f"WHERE {filtro}" if filtro else ""
    return f"""
        SELECT cd_plano_trabalho, SUM({coluna_valor}) AS vl_soma
        FROM {modelo}
        {onde}
        GROUP BY cd_plano_trabalho
    """


def _reconciliacao_desembolso_aplicacao(parte):
    """Soma do desembolso x soma do plano de aplicação, por plano (V11)."""
    return f"""
        WITH desembolso AS (
            {_soma_por_plano("sigcon_cronograma_desembolso", f"vl_desembolso_{parte}",
                             FILTRO_GRAO["sigcon_cronograma_desembolso"])}
        ),
        aplicacao AS (
            {_soma_por_plano("sigcon_plano_aplicacao", f"vl_aplicacao_{parte}")}
        )
        SELECT COALESCE(d.cd_plano_trabalho, a.cd_plano_trabalho) AS cd_plano_trabalho,
               d.vl_soma AS vl_desembolso,
               a.vl_soma AS vl_aplicacao,
               COALESCE(d.vl_soma, 0) - COALESCE(a.vl_soma, 0) AS diferenca
        FROM desembolso d
        FULL JOIN aplicacao a ON a.cd_plano_trabalho = d.cd_plano_trabalho
        WHERE ABS(COALESCE(d.vl_soma, 0) - COALESCE(a.vl_soma, 0)) > 0.01
    """


# As dh_ (data-hora) estão em UTC e as dt_ (data) no horário de Brasília: o
# mesmo instante cai em dias diferentes à noite (00:51 UTC = 21:51 do dia
# anterior em Brasília). Comparar a data da dh_ em UTC dava falso positivo.
FUSO_DATAS = "America/Sao_Paulo"

TESTES_G = _numerar(
    "G",
    [
        _limitado(
            {
                "severidade": "ERRO",
                "tabela": "sigcon_cronograma_desembolso",
                "descricao": "Soma de vl_desembolso_concedente fecha com vl_aplicacao_concedente por plano (V11)",
                "sql": _reconciliacao_desembolso_aplicacao("concedente"),
            },
            "planos_desembolso_diferente_aplicacao_concedente",
        ),
        _limitado(
            {
                "severidade": "ERRO",
                "tabela": "sigcon_cronograma_desembolso",
                "descricao": "Soma de vl_desembolso_proponente fecha com vl_aplicacao_proponente por plano (V11)",
                "sql": _reconciliacao_desembolso_aplicacao("proponente"),
            },
            "planos_desembolso_diferente_aplicacao_proponente",
        ),
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_convenio",
            "descricao": "vl_convenio_total = vl_convenio_concedente + vl_convenio_proponente",
            "sql": """
                SELECT siafi_uo, vl_convenio_total,
                       COALESCE(vl_convenio_concedente, 0)
                           + COALESCE(vl_convenio_proponente, 0) AS vl_soma_partes
                FROM sigcon_convenio
                WHERE ABS(
                    COALESCE(vl_convenio_total, 0)
                    - COALESCE(vl_convenio_concedente, 0)
                    - COALESCE(vl_convenio_proponente, 0)
                ) > 0.01
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_convenio",
            "descricao": "vl_convenio_concedente = inicial + aditado (idem proponente)",
            "sql": """
                SELECT siafi_uo,
                       vl_convenio_concedente, vl_convenio_concedente_inicial,
                       vl_convenio_concedente_aditado,
                       vl_convenio_proponente, vl_convenio_proponente_inicial,
                       vl_convenio_proponente_aditado
                FROM sigcon_convenio
                WHERE ABS(
                        COALESCE(vl_convenio_concedente, 0)
                        - COALESCE(vl_convenio_concedente_inicial, 0)
                        - COALESCE(vl_convenio_concedente_aditado, 0)
                    ) > 0.01
                   OR ABS(
                        COALESCE(vl_convenio_proponente, 0)
                        - COALESCE(vl_convenio_proponente_inicial, 0)
                        - COALESCE(vl_convenio_proponente_aditado, 0)
                    ) > 0.01
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_unidade_executora",
            "descricao": "nr_convenio igual ao da tabela 01 para o mesmo siafi_uo (P9/V4)",
            "sql": """
                SELECT u.siafi_uo, u.nr_convenio AS nr_convenio_ue,
                       c.nr_convenio AS nr_convenio_convenio
                FROM (SELECT DISTINCT siafi_uo, nr_convenio
                      FROM sigcon_unidade_executora
                      WHERE siafi_uo IS NOT NULL) u
                JOIN sigcon_convenio c ON c.siafi_uo = u.siafi_uo
                WHERE u.nr_convenio IS DISTINCT FROM c.nr_convenio
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_chave_plano_trabalho",
            "descricao": "Ponte 13 igual a convenio_geral + chave_convenio por siafi_uo; se for, passa a Won't (P4/V5)",
            "sql": """
                WITH esperado AS (
                    SELECT k.siafi_uo, g.cd_plano_trabalho
                    FROM sigcon_convenio_geral g
                    JOIN sigcon_chave_convenio k
                      ON k.cd_convenio_sequencial = g.cd_convenio_sequencial
                )
                SELECT c.siafi_uo,
                       c.cd_plano_trabalho AS cd_plano_ponte,
                       e.cd_plano_trabalho AS cd_plano_geral
                FROM sigcon_chave_plano_trabalho c
                LEFT JOIN esperado e ON e.siafi_uo = c.siafi_uo
                WHERE c.siafi_uo IS NOT NULL
                  AND c.cd_plano_trabalho IS DISTINCT FROM e.cd_plano_trabalho
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_chave_declaracao",
            "descricao": "Ponte 14 igual a convenio_geral + chave_convenio por siafi_uo; se for, passa a Won't (P4/V5)",
            "sql": """
                WITH esperado AS (
                    SELECT k.siafi_uo, g.cd_declaracao_contrapartida
                    FROM sigcon_convenio_geral g
                    JOIN sigcon_chave_convenio k
                      ON k.cd_convenio_sequencial = g.cd_convenio_sequencial
                )
                SELECT c.siafi_uo,
                       c.cd_declaracao_contrapartida AS cd_declaracao_ponte,
                       e.cd_declaracao_contrapartida AS cd_declaracao_geral
                FROM sigcon_chave_declaracao c
                LEFT JOIN esperado e ON e.siafi_uo = c.siafi_uo
                WHERE c.siafi_uo IS NOT NULL
                  AND c.cd_declaracao_contrapartida IS DISTINCT FROM e.cd_declaracao_contrapartida
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_declaracao_contrapartida",
            "descricao": (
                f"Colunas dt_ iguais à data das dh_ correspondentes no fuso {FUSO_DATAS}; "
                "se forem, as redundantes saem (V8)"
            ),
            "sql": f"""
                SELECT cd_declaracao_contrapartida,
                       dh_emissao, dt_emissao,
                       dh_parecer_aprovacao, dt_parecer_aprovacao
                FROM sigcon_declaracao_contrapartida
                WHERE CAST(dh_emissao AT TIME ZONE '{FUSO_DATAS}' AS date)
                          IS DISTINCT FROM dt_emissao
                   OR CAST(dh_parecer_aprovacao AT TIME ZONE '{FUSO_DATAS}' AS date)
                          IS DISTINCT FROM dt_parecer_aprovacao
            """,
        },
    ],
)

# --- T-H: domínio dos valores de situação/tipo ----------------------------------
# Valores conhecidos em 2026-11-12. Valor novo é ALERTA, nunca correção: a fonte é
# preservada. "Não Informado" é o placeholder da linha sentinela 99999999.
NAO_INFORMADO = "Não Informado"

DOMINIOS = {
    ("sigcon_convenio", "ds_situacao_convenio"): ["VENCIDO", "VIGENTE", "BLOQUEADO"],
    ("sigcon_plano_trabalho", "ds_status_plano_trabalho"): [
        "Enviado para SEPLAG", "Momento UO", NAO_INFORMADO,
    ],
    ("sigcon_plano_trabalho", "tp_plano_trabalho"): [
        "Termo Aditivo", "Convênio Novo", "C", "M", NAO_INFORMADO,
    ],
    ("sigcon_plano_trabalho", "tp_instrumento_siafi"): [
        "Convênio de Entrada", "Portaria", "11", "15", "17", "99",
    ],
    ("sigcon_plano_trabalho", "ds_origem_cadastro"): [
        "Não importado do SIAFI", "Importado do SIAFI - passivo", NAO_INFORMADO,
    ],
    ("sigcon_plano_trabalho", "ds_caracteristica_contrapartida"): [
        "Sem contrapartida", "Contrapartida", "Contrapartida não financeira", NAO_INFORMADO,
    ],
    ("sigcon_plano_trabalho", "ds_alteracao_termo_aditivo"): [
        "TA de Vigência", "TA de Valor", "TA de Vigência e Valor", NAO_INFORMADO,
    ],
    ("sigcon_plano_trabalho", "ds_cancelamento_sccg"): [
        "Plano Trabalho cancelado pela SCCG/SEPLAG", NAO_INFORMADO,
    ],
    ("sigcon_termo_aditivo", "tp_termo_aditivo"): [
        "TA de Vigência", "TA de Valor", "TA de Vigência e Valor",
    ],
    ("sigcon_declaracao_contrapartida", "ds_status_declaracao"): [
        "Deferida", "Cancelada", "Indeferida", "Em Análise", NAO_INFORMADO,
    ],
    ("sigcon_declaracao_contrapartida", "ds_momento"): [
        "DC aprovada", "DC não aprovada", NAO_INFORMADO,
    ],
    ("sigcon_declaracao_contrapartida", "ds_parecer_aprovacao"): [
        "Favorável", "Desfavorável", NAO_INFORMADO,
    ],
    ("sigcon_concedente", "ds_esfera"): [
        "Municipal", "Privada", "Federal", "Estadual", NAO_INFORMADO,
    ],
}

TESTES_H = _numerar(
    "H",
    [
        {
            "severidade": "ALERTA",
            "tabela": tabela,
            "descricao": f"{coluna}: valor fora dos {len(valores)} conhecidos (DOMINIOS); valor novo, não corrigir",
            "sql": sql_valores_aceitos(tabela, coluna, valores),
        }
        for (tabela, coluna), valores in DOMINIOS.items()
    ],
)

# --- T-I: coerência de datas -----------------------------------------------------
# Todas ALERTA: datas incoerentes são pergunta para a equipe do SIGCON.
# "Término posterior ao original": violação = término menor ou igual ao término
# original do convênio (sigcon_convenio.dt_vigencia_termino_inicial). Aditivo só
# conta quando é de vigência (os de valor não prorrogam).

_ORIGINAL_DO_CONVENIO = {
    "prorrogacao": """
        FROM sigcon_prorrogacao_oficio p
        JOIN sigcon_chave_convenio k ON k.cd_convenio_sequencial = p.cd_convenio_sequencial
        JOIN sigcon_convenio c ON c.siafi_uo = k.siafi_uo
    """,
    "aditivo": """
        FROM sigcon_termo_aditivo t
        JOIN sigcon_chave_termo_aditivo k ON k.cd_termo_aditivo = t.cd_termo_aditivo
        JOIN sigcon_convenio c ON c.siafi_uo = k.siafi_uo
    """,
}

TESTES_I = _numerar(
    "I",
    [
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_convenio",
            "descricao": "Vigência coerente: término não anterior ao início",
            "sql": """
                SELECT siafi_uo, dt_vigencia_inicio, dt_vigencia_termino
                FROM sigcon_convenio
                WHERE dt_vigencia_termino < dt_vigencia_inicio
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_prorrogacao_oficio",
            "descricao": "Vigência da prorrogação coerente: término não anterior ao início",
            "sql": """
                SELECT cd_prorrogacao_oficio, dt_vigencia_inicio, dt_vigencia_termino
                FROM sigcon_prorrogacao_oficio
                WHERE dt_vigencia_termino < dt_vigencia_inicio
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_termo_aditivo",
            "descricao": "Vigência do termo aditivo coerente: término não anterior ao início",
            "sql": """
                SELECT cd_termo_aditivo, tp_termo_aditivo, dt_vigencia_inicio, dt_vigencia_termino
                FROM sigcon_termo_aditivo
                WHERE dt_vigencia_termino < dt_vigencia_inicio
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_prorrogacao_oficio",
            "descricao": "Término da prorrogação posterior ao término original do convênio",
            "sql": f"""
                SELECT p.cd_prorrogacao_oficio, c.siafi_uo,
                       c.dt_vigencia_termino_inicial, p.dt_vigencia_termino
                {_ORIGINAL_DO_CONVENIO["prorrogacao"]}
                WHERE p.dt_vigencia_termino <= c.dt_vigencia_termino_inicial
            """,
        },
        {
            "severidade": "ALERTA",
            "tabela": "sigcon_termo_aditivo",
            "descricao": "Término do aditivo de vigência posterior ao término original do convênio",
            "sql": f"""
                SELECT t.cd_termo_aditivo, t.tp_termo_aditivo, c.siafi_uo,
                       c.dt_vigencia_termino_inicial, t.dt_vigencia_termino
                {_ORIGINAL_DO_CONVENIO["aditivo"]}
                WHERE t.tp_termo_aditivo LIKE '%Vig%'
                  AND t.dt_vigencia_termino <= c.dt_vigencia_termino_inicial
            """,
        },
    ],
)

# Ordem de execução: de volumetria a coerência de datas.
TESTES = (
    TESTES_A + TESTES_B + TESTES_C + TESTES_D + TESTES_E
    + TESTES_F + TESTES_G + TESTES_H + TESTES_I
)
