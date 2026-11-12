"""
Construtores de SQL genéricos do catálogo de validação do SIGCON.

Cada função devolve o texto de uma consulta que lista as linhas que VIOLAM a
regra: teste que passa = consulta sem linhas. Nomes de tabela e coluna vêm
sempre de constantes do catálogo (nunca de entrada de usuário).

O parâmetro `filtro` (condição SQL em texto) restringe quais linhas entram no
teste. Existe por causa de linhas que a Silver MARCA em vez de excluir — hoje,
as do bloco desalinhado do cronograma (`ds_alerta_linha IS NOT NULL`), que por
definição não têm plano, ano nem valor e não devem reprovar o grão.
"""


def _onde(*condicoes):
    """Junta as condições não vazias num WHERE; devolve '' se não houver nenhuma."""
    ativas = [c for c in condicoes if c]
    if not ativas:
        return ""
    return "WHERE " + "\n          AND ".join(f"({c})" for c in ativas)


def _literal(valor):
    """Literal SQL: número sem aspas; texto entre aspas simples, com ' duplicada.
    (repr() de um texto com apóstrofo usa aspas duplas, que no SQL são identificador.)"""
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, (int, float)):
        return repr(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def sql_unicidade(tabela, colunas, filtro=None):
    """SQL que devolve as combinações de 'colunas' que se repetem em 'tabela'."""
    cols = ", ".join(colunas)
    return f"""
        SELECT {cols}, COUNT(*) AS qt
        FROM {tabela}
        {_onde(filtro)}
        GROUP BY {cols}
        HAVING COUNT(*) > 1
    """


def sql_nao_nulo(tabela, coluna, filtro=None):
    """Linhas de 'tabela' em que 'coluna' está nula."""
    return f"""
        SELECT *
        FROM {tabela}
        {_onde(f"{coluna} IS NULL", filtro)}
    """


def sql_valores_aceitos(tabela, coluna, valores, filtro=None):
    """Linhas cujo valor (não nulo) de 'coluna' não está em 'valores'."""
    lista = ", ".join(_literal(valor) for valor in valores)
    return f"""
        SELECT *
        FROM {tabela}
        {_onde(f"{coluna} IS NOT NULL", f"{coluna} NOT IN ({lista})", filtro)}
    """


def sql_formato(tabela, coluna, regex, filtro=None):
    """Linhas cujo valor (não nulo) de 'coluna' não casa com a expressão regular."""
    return f"""
        SELECT *
        FROM {tabela}
        {_onde(f"{coluna} IS NOT NULL", f"NOT ({coluna} ~ '{regex}')", filtro)}
    """


def sql_orfaos(filha, col_filha, pai, col_pai, filtro=None):
    """Linhas de 'filha' cujo valor em col_filha não existe em pai.col_pai."""
    sem_pai = f"""NOT EXISTS (
                SELECT 1
                FROM {pai} p
                WHERE p.{col_pai} = f.{col_filha}
            )"""
    return f"""
        SELECT f.*
        FROM {filha} f
        {_onde(f"f.{col_filha} IS NOT NULL", filtro, sem_pai)}
    """
