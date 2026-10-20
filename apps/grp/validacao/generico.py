"""
Arquivo voltado para Garantir que cada uma das 22 tabelas tem o grão declarado no modelo de extração. 
grão quebrado contamina tudo que vem depois.
"""

def sql_unicidade(tabela, colunas):
    """SQL que devolve as combinações de 'colunas' que se repetem em 'tabela'."""
    cols = ", ".join(colunas)
    return f"""
        SELECT {cols}, COUNT(*) AS qt
        FROM {tabela}
        GROUP BY {cols}
        HAVING COUNT(*) > 1
    """

def sql_nao_nulo(tabela, coluna):
    return f"""
        SELECT * 
        FROM {tabela} 
        WHERE {coluna} IS NULL
    """


def sql_valores_aceitos(tabela, coluna, valores):
    
    resultado = [repr(valor) for valor in valores]

    texto = ", ".join(resultado)
    
    return f"""
        SELECT *
        FROM {tabela}
        WHERE {coluna} NOT IN ({texto})
"""


def sql_formato(tabela, coluna, regex):
    return f"""
        SELECT *
        FROM {tabela}
        WHERE NOT ({coluna} ~ '{regex}')
"""

def sql_sem_chave(tabela):
    return f"""
        SELECT *
        FROM {tabela}
        WHERE COALESCE(nr_grp, cd_proposta) IS NULL
"""