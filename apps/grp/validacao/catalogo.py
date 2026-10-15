from apps.grp.validacao.volumetria import (
    teste_volumetria,
)

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
        "descricao": "Linhas do parquet iguais às da tabela no banco, nas 22 fontes",
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
        "severidade": "ALERTA",
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
