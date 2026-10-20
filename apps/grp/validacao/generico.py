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

def sql_orfaos(filha, col_filha, pai, col_pai):
    """Linhas de 'filha' cujo valor em col_filha não existe em pai.col_pai."""
    return f"""
        SELECT f.*
        FROM {filha} f
        WHERE f.{col_filha} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM {pai} p
            WHERE p.{col_pai} = f.{col_filha}
          )
    """