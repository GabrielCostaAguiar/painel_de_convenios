from apps.grp.validacao.volumetria import (
    teste_volumetria,
)
from apps.grp.validacao.generico import (
    sql_formato,
    sql_nao_nulo,
    sql_unicidade,
    sql_valores_aceitos,
    sql_sem_chave,
    sql_orfaos,
)

GRAOS = {
    "grp_prestacao_contas": ["nr_grp", "cd_proposta"],
    "grp_concedente": ["nr_grp", "cd_proposta", "nr_cnpj_concedente"],
    "grp_emenda": ["nr_grp", "cd_proposta", "nr_ano_emenda", "nr_emenda"],
    "grp_planejamento_obras": ["nr_grp", "cd_proposta"],
    "grp_proposta_marco_logico": ["nr_grp", "cd_proposta"],
    "grp_interveniente": [
        "nr_grp",
        "cd_proposta",
        "cd_interveniente",
        "nr_cnpj_interveniente",
    ],
    "grp_unidade_executora": ["nr_grp", "cd_proposta", "cd_unidade_adm"],
    "grp_municipio_atendido": ["nr_grp", "cd_proposta", "cd_municipio"],
    "grp_regiao_atendida": [
        "nr_grp",
        "cd_proposta",
        "cd_regiao",
        "cd_municipio_regiao",
    ],
    "grp_recurso_concedente": [
        "nr_grp",
        "cd_proposta",
        "cd_uo_arrecadacao",
        "ds_situacao_recurso_concedente",
        "cd_fonte_recurso",
        "cd_ipu",
    ],
    "grp_recurso_contrapartida": [
        "nr_grp",
        "cd_proposta",
        "cd_uo_financiadora",
        "ds_situacao_contrapartida",
        "cd_fonte_recurso_contrapartida",
        "cd_ipu_contrapartida",
    ],
    "grp_dotacao_contrapartida": [
        "nr_grp",
        "cd_proposta",
        "cd_dotacao_contrapartida",
        "ds_situacao_dotacao",
    ],
    "grp_acao_orcamentaria": [
        "nr_grp",
        "cd_proposta",
        "cd_acao",
        "cd_uo_execucao",
        "ds_situacao_acao",
    ],
    "grp_instrumento_financiado": [
        "nr_grp",
        "cd_proposta",
        "nr_instrumento_financiado",
    ],
    "grp_item_executar": [
        "nr_grp",
        "cd_proposta",
        "cd_catmas",
        "tp_despesa",
        "nr_cnpj_beneficiario",
        "ds_item",
        "ds_origem_recurso",
        "ds_situacao_item",
        "cd_categoria_economica",
        "cd_grupo_despesa",
        "cd_modalidade_aplicacao",
        "cd_elemento_despesa",
        "cd_elemento_item",
    ],
    "grp_cronograma_desembolso": [
        "nr_grp",
        "cd_proposta",
        "nr_parcela",
        "ds_origem_recurso_parcela",
        "nr_ano_desembolso",
        "nr_mes_desembolso",
    ],
    "grp_cronograma_fisico": [
        "nr_grp",
        "cd_proposta",
        "tp_meta_etapa",
        "tx_meta_especificacao",
        "tx_etapa_especificacao",
    ],
    "grp_entrega_projeto": ["nr_grp", "cd_proposta", "tx_entrega"],
    "grp_atividade_projeto": ["nr_grp", "cd_proposta", "tx_atividade"],
    "grp_matriz_responsabilidade": [
        "nr_grp",
        "cd_proposta",
        "tp_gestor_participante",
        "nm_responsavel",
    ],
    "grp_tabela_uo": ["cd_uo"],
}

GRAOS_EM_TRATAMENTO = {"grp_emenda", "grp_cronograma_fisico", "grp_tabela_uo"}

CNPJS = [
    ("grp_instrumento", "nr_cnpj_proponente"),
    ("grp_instrumento", "nr_cnpj_convenente"),
]

TESTES = [
    {
        "id": "T-C01",
        "severidade": "ERRO",
        "tabela": "grp_instrumento",
        "descricao": "Uma linha por nr_grp (P3)",
        "sql": """
            SELECT nr_grp, COUNT(*) AS qt
            FROM grp_instrumento
            WHERE nr_grp IS NOT NULL
            GROUP BY nr_grp
            HAVING COUNT(*) > 1
        """,
    },
    {
        "id": "T-D01",
        "severidade": "ERRO",
        "tabela": "grp_instrumento",
        "descricao": "Toda linha tem nr_grp ou cd_proposta",
        "sql": """
            SELECT 
                nr_grp, 
                tp_proposta_instrumento, 
                nr_instrumento, 
                nr_instrumento_transferegov, 
                ds_situacao_proposta, 
                ds_situacao_instrumento, 
                ds_status_instrumento
            FROM grp_instrumento
            WHERE COALESCE(nr_grp, cd_proposta) IS NULL
        """,
    },
    {
        "id": "T-D02",
        "severidade": "ERRO",
        "tabela": "grp_instrumento",
        "descricao": "linhas sem nr_grp são sempre propostas (P4)",
        "sql": """
            SELECT 
                nr_grp, 
                cd_proposta, 
                tp_proposta_instrumento, 
                nr_instrumento, 
                nr_instrumento_transferegov, 
                ds_situacao_proposta, 
                ds_situacao_instrumento, 
                ds_status_instrumento
            FROM grp_instrumento
            WHERE nr_grp IS NULL 
            AND tp_proposta_instrumento IS DISTINCT FROM 'PROPOSTA'
        """,
    },
    {
        "id": "T-A01",
        "severidade": "ERRO",
        "tabela": "grp_*",
        "descricao": "Linhas do parquet iguais às da tabela no banco, nas fontes grp_*",
        "funcao": teste_volumetria,
    },
    {
        "id": "T-A02",
        "severidade": "ERRO",
        "tabela": "8 tabelas Must",
        "descricao": "Tabelas Must não podem estar vazias",
        "sql": """
            SELECT 'grp_instrumento' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_instrumento)
            UNION ALL
            SELECT 'grp_concedente' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_concedente)
            UNION ALL
            SELECT 'grp_emenda' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_emenda)
            UNION ALL
            SELECT 'grp_recurso_concedente' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_recurso_concedente)
            UNION ALL
            SELECT 'grp_recurso_contrapartida' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_recurso_contrapartida)
            UNION ALL
            SELECT 'grp_acao_orcamentaria' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_acao_orcamentaria)
            UNION ALL
            SELECT 'grp_cronograma_desembolso' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_cronograma_desembolso)
            UNION ALL
            SELECT 'grp_tabela_uo' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_tabela_uo)
        """,
    },
    {
        "id": "T-B01",
        "severidade": "ERRO",
        "tabela": "grp_* (colunas por prefixo)",
        "descricao": "O prefixo da coluna define o tipo: vl_ numérico, dt_ data, fl_ booleano, códigos texto",
        "sql": r"""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name LIKE 'grp\_%'
            AND (
                (column_name LIKE 'vl\_%' AND data_type <> 'numeric')
                OR (column_name LIKE 'dt\_%' AND data_type <> 'date')   
                OR (column_name LIKE 'fl\_%' AND data_type <> 'boolean')  
                OR (column_name ~ '^(cd|sg|nr_cnpj|nr_cpf)_' AND data_type NOT IN ('character varying', 'text'))
            )
        """,
    },
    {
        "id": "T-B02",
        "severidade": "ERRO",
        "tabela": "grp_emenda, grp_cronograma_desembolso",
        "descricao": "Anos, meses e parcelas devem ser inteiros, não texto",
        "sql": """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND (table_name, column_name) IN (
                  ('grp_emenda', 'nr_ano_emenda'),
                  ('grp_cronograma_desembolso', 'nr_parcela'),
                  ('grp_cronograma_desembolso', 'nr_ano_desembolso'),
                  ('grp_cronograma_desembolso', 'nr_mes_desembolso')
              )
              AND data_type NOT IN ('integer', 'bigint', 'smallint')
        """,
    },
]

TESTES += [
    {
        "id": f"T-C{i:02d}",
        "severidade": "ALERTA" if tabela in GRAOS_EM_TRATAMENTO else "ERRO",
        "tabela": tabela,
        "descricao": f"Grão: {', '.join(colunas)}",
        "sql": sql_unicidade(tabela, colunas),
    }
    for i, (tabela, colunas) in enumerate(GRAOS.items(), start=2)
]

# --- T-D: completude ---
# tabela_uo é dimensão (sem nr_grp); a matriz tem dados pessoais e a amostra
# gravaria CPF e e-mail em dq_resultado_validacao
SEM_NR_GRP = {"grp_tabela_uo", "grp_matriz_responsabilidade"}

TESTES += [
    {
        "id": f"T-D{i:02d}",
        "severidade": "ERRO",
        "tabela": tabela,
        "descricao": "nr_grp e/ou cd_proposta preenchidos",
        "sql": sql_sem_chave(tabela),
    }
    for i, tabela in enumerate([t for t in GRAOS if t not in SEM_NR_GRP], start=3)
]

TESTES += [
    {
        "id": "T-D22",
        "severidade": "ERRO",
        "tabela": "grp_tabela_uo",
        "descricao": "cd_uo preenchido",
        "sql": sql_nao_nulo("grp_tabela_uo", "cd_uo"),
    },
]

# --- grp_convenente_cnpj (ponte da premissa P5) ---
# Ids fixos: a fonte não entra em GRAOS nem em SEM_NR_GRP porque esses blocos
# numeram os ids pela posição, e isso mudaria ids que já têm histórico.
TESTES += [
    {
        "id": "T-C23",
        "severidade": "ERRO",
        "tabela": "grp_convenente_cnpj",
        "descricao": "Grão: uma linha por nr_cnpj_convenente (ignora os sem CNPJ)",
        # SQL próprio: o GROUP BY juntaria os nulos num grupo só e acusaria
        # uma duplicata falsa.
        "sql": """
            SELECT nr_cnpj_convenente, COUNT(*) AS qt
            FROM grp_convenente_cnpj
            WHERE nr_cnpj_convenente IS NOT NULL
            GROUP BY nr_cnpj_convenente
            HAVING COUNT(*) > 1
        """,
    },
    {
        "id": "T-D23",
        "severidade": "ALERTA",
        "tabela": "grp_convenente_cnpj",
        "descricao": "nr_cnpj_convenente preenchido (linha de base: 31 sem CNPJ, entes estaduais com N/A ou S/C no GRP)",
        "sql": sql_nao_nulo("grp_convenente_cnpj", "nr_cnpj_convenente"),
    },
    {
        "id": "T-C24",
        "severidade": "ALERTA",
        "tabela": "gold.vw_depara_convenente_uo",
        "descricao": "De-para: uma linha por nr_cnpj_convenente (um nome não pode casar com duas UOs)",
        "sql": sql_unicidade("gold.vw_depara_convenente_uo", ["nr_cnpj_convenente"]),
    },
]

# --- T-E: formato e domínio ---
CNPJS = [
    ("grp_instrumento", "nr_cnpj_proponente"),
    ("grp_instrumento", "nr_cnpj_convenente"),
    ("grp_instrumento", "nr_cnpj_mandataria"),
    ("grp_concedente", "nr_cnpj_concedente"),
    ("grp_interveniente", "nr_cnpj_interveniente"),
    ("grp_item_executar", "nr_cnpj_beneficiario"),
]
MUNICIPIOS = [
    ("grp_municipio_atendido", "cd_municipio"),
    ("grp_regiao_atendida", "cd_municipio_regiao"),
]
COLUNAS_UF = [
    ("grp_municipio_atendido", "sg_uf"),
    ("grp_regiao_atendida", "sg_uf_municipio_regiao"),
]
UFS = [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]
COLUNAS_ANO = [
    ("grp_emenda", "nr_ano_emenda"),
    ("grp_cronograma_desembolso", "nr_ano_desembolso"),
]

TESTES_E = (
    [
        {
            "severidade": "ERRO",
            "tabela": t,
            "descricao": f"{c}: CNPJ com 14 dígitos",
            "sql": sql_formato(t, c, r"^\d{14}$"),
        }
        for t, c in CNPJS
    ]
    + [
        {
            "severidade": "ERRO",
            "tabela": t,
            "descricao": f"{c}: código de município com 7 dígitos",
            "sql": sql_formato(t, c, r"^\d{7}$"),
        }
        for t, c in MUNICIPIOS
    ]
    + [
        {
            "severidade": "ERRO",
            "tabela": t,
            "descricao": f"{c}: UF válida",
            "sql": sql_valores_aceitos(t, c, UFS),
        }
        for t, c in COLUNAS_UF
    ]
    + [
        {
            "severidade": "ERRO",
            "tabela": "grp_cronograma_desembolso",
            "descricao": "nr_mes_desembolso entre 0 e 12 (0 = mês não informado na fonte)",
            "sql": sql_valores_aceitos(
                "grp_cronograma_desembolso", "nr_mes_desembolso", range(0, 13)
            ),
        }
    ]
    + [
        {
            "severidade": "ALERTA",
            "tabela": t,
            "descricao": f"{c}: ano entre 1950 e 2050",
            "sql": sql_valores_aceitos(t, c, range(1950, 2050)),
        }
        for t, c in COLUNAS_ANO
    ]
)

for i, teste in enumerate(TESTES_E, start=1):
    teste["id"] = f"T-E{i:02d}"

TESTES += TESTES_E

# Bloco próprio, fora de CNPJS: acrescentar o par lá renumeraria os T-E07 a T-E13.
# sql_formato ignora nulos, então só acusa formato errado de verdade.
TESTES += [
    {
        "id": "T-E14",
        "severidade": "ERRO",
        "tabela": "grp_convenente_cnpj",
        "descricao": "nr_cnpj_convenente: CNPJ com 14 dígitos",
        "sql": sql_formato("grp_convenente_cnpj", "nr_cnpj_convenente", r"^\d{14}$"),
    },
]

# --- T-F: Caçador de órfãos ---

TESTES += [
    {
        "id": f"T-F{i:02d}",
        "severidade": "ERRO",
        "tabela": tabela,
        "descricao": "nr_grp existe em grp_instrumento",
        "sql": sql_orfaos(
            filha=tabela, col_filha="nr_grp", pai="grp_instrumento", col_pai="nr_grp"
        ),
    }
    for i, tabela in enumerate([t for t in GRAOS if t not in SEM_NR_GRP], start=1)
]

TESTES += [
    {
        "id": f"T-F{i:02d}",
        "severidade": "ERRO",
        "tabela": tabela,
        "descricao": "cd_proposta existe em grp_instrumento",
        "sql": sql_orfaos(
            filha=tabela,
            col_filha="cd_proposta",
            pai="grp_instrumento",
            col_pai="cd_proposta",
        ),
    }
    for i, tabela in enumerate([t for t in GRAOS if t not in SEM_NR_GRP], start=20)
]

UOS = [
    ("grp_recurso_concedente", "cd_uo_arrecadacao"),
    ("grp_acao_orcamentaria", "cd_uo_execucao"),
    ("grp_recurso_contrapartida", "cd_uo_financiadora"),
]

TESTES += [
    {
        "id": f"T-F{i:02d}",
        "severidade": "ERRO",
        "tabela": t,
        "descricao": f"{c} existe em grp_tabela_uo",
        "sql": sql_orfaos(filha=t, col_filha=c, pai="grp_tabela_uo", col_pai="cd_uo"),
    }
    for i, (t, c) in enumerate(UOS, start=39)
]

TESTES += [
    {
        "id": "T-F42",
        "severidade": "ALERTA",
        "tabela": "grp_instrumento_financiado",
        "descricao": "nr_instrumento_financiado existe em grp_instrumento, porém não existe registro nessa tabela ainda",
        "sql": sql_orfaos(
            filha="grp_instrumento_financiado",
            col_filha="nr_instrumento_financiado",
            pai="grp_instrumento",
            col_pai="nr_grp",
        ),
    },
]

# --- P5: convenente do instrumento -> UO ---
TESTES += [
    {
        "id": "T-F43",
        "severidade": "ALERTA",
        "tabela": "grp_instrumento",
        "descricao": "nr_cnpj_convenente tem UO no de-para gold.vw_depara_convenente_uo (P5)",
        # SQL próprio (não é sql_orfaos): o CNPJ pode existir na view e mesmo
        # assim estar SEM_UO; o que importa é ter cd_uo preenchido.
        "sql": """
            SELECT i.nr_grp, i.nr_cnpj_convenente, i.nm_convenente
            FROM grp_instrumento i
            WHERE i.nr_cnpj_convenente IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM gold.vw_depara_convenente_uo d
                WHERE d.nr_cnpj_convenente = i.nr_cnpj_convenente
                  AND d.cd_uo IS NOT NULL
              )
        """,
    },
    {
        "id": "T-F44",
        "severidade": "ALERTA",
        "tabela": "grp_instrumento",
        "descricao": "nr_cnpj_convenente existe em grp_convenente_cnpj (cobertura da consulta de convenentes)",
        "sql": sql_orfaos(
            filha="grp_instrumento",
            col_filha="nr_cnpj_convenente",
            pai="grp_convenente_cnpj",
            col_pai="nr_cnpj_convenente",
        ),
    },
]
