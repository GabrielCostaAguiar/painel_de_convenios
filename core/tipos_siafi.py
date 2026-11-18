"""
Mapeamento global do Tipo SIAFI (código → descrição do instrumento).

Fonte única: core/referencia/tipos_siafi.csv (o mesmo CSV que o ETL lê via
core.transform.referencias.tipos_siafi). Este módulo é a porta de entrada para
quem roda no servidor web (views, templates, apps): usa só a biblioteca padrão,
sem pandas, e guarda o resultado em cache.

Uso:
    from core.tipos_siafi import descricao_tipo_siafi, TIPOS_SIAFI
    descricao_tipo_siafi("15")      # "Transferência Especial"
    descricao_tipo_siafi("99")      # "99" (código desconhecido volta como veio)

Template:
    {% load painel_filters %}  {{ valor|tipo_siafi }}

Atenção: não é o mesmo domínio de tipos_instrumento_entrada (Mapa1), apesar de
códigos em comum (4, 5, 8, 11).
"""

import csv
from functools import lru_cache
from pathlib import Path

_CSV = Path(__file__).parent / "referencia" / "tipos_siafi.csv"


@lru_cache(maxsize=1)
def carregar_tipos_siafi() -> dict[str, str]:
    """{codigo: descricao}, lido uma vez por processo."""
    with _CSV.open(encoding="utf-8", newline="") as f:
        return {
            r["codigo_tipo_siafi"].strip(): r["descricao_instrumento"].strip()
            for r in csv.DictReader(f)
        }


def descricao_tipo_siafi(codigo) -> str:
    """Descrição do tipo SIAFI. Valor vazio → ""; código fora do mapa → o próprio valor.

    Aceita também texto já descritivo ('Convênio de Entrada', 'Portaria'), que o
    SIGCON mistura com códigos em tp_instrumento_siafi.
    """
    if codigo is None:
        return ""
    texto = str(codigo).strip()
    return carregar_tipos_siafi().get(texto, texto)
