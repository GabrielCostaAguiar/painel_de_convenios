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


def valores_sentinela(coluna: str, overrides: dict | None) -> set:
    """
    Valores que viram nulo para `coluna`: a lista do bloco YAML 'sentinelas:'
    para essa coluna, se declarada: senão, SENTINELAS (o padrão do projeto).
    Declarar 'sentinelas:' substitui a lista inteira para a coluna — não soma
    com o padrão.
    """
    if overrides and coluna in overrides:
        return set(overrides[coluna])
    return SENTINELAS


def limpar_colunas_padronizadas(df, booleanos: dict | None = None):
    """
    Limpeza da silver para fontes com nomes finais (bloco 'renomear').

    O trim de texto roda sempre, para toda coluna texto/string (idempotente —
    a nulagem de sentinela em si já aconteceu antes do renomear, ver
    core/transform/silver.py). Os flags usam o prefixo 'fl_' da convenção,
    com MAPA_BOOLEANO como padrão; `booleanos` (bloco YAML 'booleanos:',
    chaves = nomes finais de coluna) sobrescreve o de-para por coluna —
    usado quando a fonte tem vocabulário SIM/NÃO diferente do GRP.
    """
    for col in df.select_dtypes(include=["object", "string"]).columns:
        # .astype("string") no final é obrigatorio, nao cosmetico: .map()
        # devolve dtype "string" quando ha pelo menos um valor de string real
        # no resultado, mas degrada pra "object" quando a coluna inteira ja
        # virou <NA> (ex.: sentinela nulada antes do renomear) - sem o cast
        # explicito, a mesma fonte grava parquet com dtype diferente so por
        # causa do CONTEUDO da coluna, nao da logica.
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v).astype("string")

    colunas_flag = {c for c in df.columns if c.startswith("fl_")} | set((booleanos or {}))
    for col in colunas_flag:
        if col not in df.columns:
            continue
        mapa = (booleanos or {}).get(col, MAPA_BOOLEANO)
        valores = df[col].dropna().unique()
        estranhos = set(valores) - set(mapa)
        if estranhos:
            raise ValueError(f"Valores inesperados na flag '{col}': {estranhos}")
        df[col] = df[col].map(mapa).astype("boolean")

    return df