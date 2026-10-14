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
    }
]