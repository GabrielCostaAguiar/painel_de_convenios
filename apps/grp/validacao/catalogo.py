from apps.grp.validacao.volumetria import (
    teste_volumetria,
)
from apps.grp.validacao.generico import (
    sql_unicidade
)


GRAOS = {
    "grp_prestacao_contas": ["nr_grp", "cd_proposta"],
    "grp_concedente":       ["nr_grp", "cd_proposta", "nr_cnpj_concedente"],
    "grp_emenda":           ["nr_grp", "cd_proposta", "nr_ano_emenda", "nr_emenda"],
    "grp_planejamento_obras":      ["nr_grp", "cd_proposta"],
    "grp_proposta_marco_logico":      ["nr_grp", "cd_proposta"],
    "grp_interveniente":      ["nr_grp", "cd_proposta", "cd_interveniente", "nr_cnpj_interveniente"],
    "grp_unidade_executora":      ["nr_grp", "cd_proposta", "cd_unidade_adm"],
    "grp_municipio_atendido":      ["nr_grp", "cd_proposta", "cd_municipio"],
    "grp_regiao_atendida":      ["nr_grp", "cd_proposta", "cd_regiao", "cd_municipio_regiao"],
    "grp_recurso_concedente":      ["nr_grp", "cd_proposta", "cd_uo_arrecadacao", "ds_situacao_recurso_concedente", "cd_fonte_recurso", "cd_ipu"],
    "grp_recurso_contrapartida":      ["nr_grp", "cd_proposta", "cd_uo_financiadora", "ds_situacao_contrapartida", "cd_fonte_recurso_contrapartida", "cd_ipu_contrapartida"],
    "grp_dotacao_contrapartida":      ["nr_grp", "cd_proposta", "cd_dotacao_contrapartida", "ds_situacao_dotacao"],
    "grp_acao_orcamentaria":      ["nr_grp", "cd_proposta", "cd_acao", "cd_uo_execucao", "ds_situacao_acao"],
    "grp_instrumento_financiado":      ["nr_grp", "cd_proposta", "nr_instrumento_financiado"],
    "grp_item_executar":      ["nr_grp", "cd_proposta", "cd_catmas", "tp_despesa", "nr_cnpj_beneficiario", "ds_item", "ds_origem_recurso", "ds_situacao_item", "cd_categoria_economica", "cd_grupo_despesa", "cd_modalidade_aplicacao", "cd_elemento_despesa", "cd_elemento_item"],
    "grp_cronograma_desembolso":      ["nr_grp", "cd_proposta", "nr_parcela", "ds_origem_recurso_parcela", "nr_ano_desembolso", "nr_mes_desembolso"],
    "grp_cronograma_fisico":      ["nr_grp", "cd_proposta", "tp_meta_etapa", "tx_meta_especificacao", "tx_etapa_especificacao",],
    "grp_entrega_projeto":      ["nr_grp", "cd_proposta", "tx_entrega"],
    "grp_atividade_projeto":      ["nr_grp", "cd_proposta", "tx_atividade"],
    "grp_matriz_responsabilidade":      ["nr_grp", "cd_proposta", "tp_gestor_participante", "nm_responsavel"],
    "grp_tabela_uo":      ["cd_uo"]
}

GRAOS_EM_TRATAMENTO = {"grp_emenda", "grp_cronograma_fisico", "grp_tabela_uo"}



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

TESTES += [    {   
        "id": f"T-C{i:02d}",
        "severidade": "ALERTA" if tabela in GRAOS_EM_TRATAMENTO else "ERRO", 
        "tabela": tabela, 
        "descricao": f"Grão: {', '.join(colunas)}" ,
        "sql": sql_unicidade(tabela, colunas)
    }
        for i, (tabela, colunas) in enumerate(GRAOS.items(), start=2)
]