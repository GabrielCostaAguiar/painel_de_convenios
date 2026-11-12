"""
Encoding: detecta mojibake (UTF-8 lido como cp1252/latin-1) nas colunas de texto.

Exemplos do defeito: "ConstruÃ§Ã£o" (Construção), "nÂº" (nº), "â€“" (–).

O padrão procura 'Ã' ou 'Â' seguidos de um caractere de continuação típico do
mojibake (a faixa 0x80–0xBF lida como cp1252) e a sequência 'â€'. Ele NÃO pega
'Ã' seguido de letra, que é português legítimo em maiúsculas ("NÃO", "AÇÃO").

A amostra traz só tabela, coluna e ids: o texto das colunas pode ter dado
pessoal e não deve ser copiado para a tabela de resultados.
"""

from django.apps import apps
from django.db import models

# Continuação do mojibake: U+0080–U+00BF e os símbolos do cp1252 que ocupam 0x80–0x9F.
_CONTINUACAO = (
    "\u0080-¿"
    "€‚ƒ„…†‡ˆ‰Š‹Œ"
    "Ž‘’“”•–—˜™š›"
    "œžŸ"
)
PADRAO_MOJIBAKE = f"[ÃÂ][{_CONTINUACAO}]|â€"

IDS_NA_AMOSTRA = 3


def colunas_de_texto():
    """(model, nome do campo) de todo CharField/TextField dos models sigcon_*."""
    for modelo in apps.get_models():
        if not modelo._meta.db_table.startswith("sigcon_"):
            continue
        for campo in modelo._meta.concrete_fields:
            if isinstance(campo, (models.CharField, models.TextField)):
                yield modelo, campo.name


def teste_mojibake():
    """(qt_celulas_afetadas, amostra por tabela/coluna)."""
    total, amostra = 0, []
    for modelo, campo in colunas_de_texto():
        afetadas = modelo.objects.filter(**{f"{campo}__regex": PADRAO_MOJIBAKE})
        n = afetadas.count()
        if n:
            total += n
            amostra.append(
                {
                    "tabela": modelo._meta.db_table,
                    "coluna": campo,
                    "linhas": n,
                    "ids": list(afetadas.order_by("pk").values_list("pk", flat=True)[:IDS_NA_AMOSTRA]),
                }
            )
    return total, amostra
