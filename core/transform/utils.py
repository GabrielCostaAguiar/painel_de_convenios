"""
Utilitários reutilizáveis para a camada Silver.
"""

import re
import unicodedata


def normalizar_coluna(nome: str) -> str:
    """
    Padroniza nome de coluna para snake_case sem acentos.

    Passos:
      1. Dots → espaços (exportações QlikView usam "." como separador de palavras)
      2. NFKD decomposition → descarta caracteres combinantes (acentos)
      3. strip nas bordas
      4. qualquer sequência de espaços/underscores → "_"
      5. tudo minúsculo
    """
    nome = nome.replace(".", " ")
    sem_acento = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    snake = re.sub(r"[\s_]+", "_", sem_acento.strip())
    return snake.lower()

# Valores que a fonte usa para dizer "não tem" (confirmados nos testes da consulta 01)
SENTINELAS = {"N/A", "-3", ""}

# De-para das flags S/N
MAPA_BOOLEANO = {"SIM": True, "NÃO": False, "NAO": False}


def limpar_colunas_padronizadas(df):
    """
    Limpeza da silver para fontes com nomes finais (bloco 'renomear').
    Usa os prefixos da convenção para decidir o que fazer em cada coluna.
    """
    # 1 e 2: textos -> tira espaços nas pontas e troca sentinelas por nulo
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
        df[col] = df[col].where(~df[col].isin(SENTINELAS))

    # 3: flags -> SIM/NÃO viram True/False (nulo continua nulo)
    for col in [c for c in df.columns if c.startswith("fl_")]:
        valores = df[col].dropna().unique()
        estranhos = set(valores) - set(MAPA_BOOLEANO)
        if estranhos:
            raise ValueError(f"Valores inesperados na flag '{col}': {estranhos}")
        df[col] = df[col].map(MAPA_BOOLEANO).astype("boolean")

    return df