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