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
