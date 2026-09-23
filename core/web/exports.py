"""Montagem das respostas de export."""

from django.http import HttpResponse

# Excel so reconhece o arquivo como UTF-8 se ele comecar com BOM; sem isso,
# acentos aparecem trocados ao abrir o CSV com duplo clique.
BOM_UTF8 = "\ufeff"

TIPO_CSV = "text/csv; charset=utf-8"


def resposta_csv(nome_arquivo: str) -> HttpResponse:
    """
    HttpResponse pronta para receber um CSV via csv.writer.

    Ja vem com o content-type, o cabecalho de download e o BOM escrito.
    `nome_arquivo` e o nome sugerido ao usuario, sem a extensao.
    """
    resposta = HttpResponse(content_type=TIPO_CSV)
    resposta["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.csv"'
    resposta.write(BOM_UTF8)
    return resposta
