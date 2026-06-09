"""
Registro declarativo de todas as fontes de dados do projeto.

Para adicionar uma nova fonte:
  1. Crie uma instância de FonteDados com o nome, arquivo e encoding corretos.
  2. Adicione-a ao dicionário FONTES com a chave sendo o identificador da fonte.
  3. Coloque o arquivo CSV em data/raw/<arquivo> antes de rodar a ingestão.

Não importe Django aqui — este módulo é carregado antes do setup do Django
em alguns contextos (ex.: testes unitários puros).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FonteDados:
    nome: str        # identificador único; usado como chave em FONTES e como nome de pasta em bronze/
    arquivo: str     # nome do arquivo esperado em data/raw/
    separador: str   # delimitador de colunas do CSV
    encoding: str    # encoding do arquivo original
    descricao: str   # texto livre para documentação


# ---------------------------------------------------------------------------
# Registro central de fontes
# Cada entrada aqui habilita: leitura, ingestão Bronze e comando de gerência.
# ---------------------------------------------------------------------------
FONTES: dict[str, FonteDados] = {
    "convenios": FonteDados(
        nome="convenios",
        arquivo="convenios.csv",
        separador=";",
        encoding="latin-1",   # arquivos SIGCON-MG exportados do Business Objects
        descricao="Convênios do SIGCON-MG (exportação Business Objects / PRODEMGE)",
    ),
    "arrecadacao": FonteDados(
        nome="arrecadacao",
        arquivo="arrecadacao.csv",
        separador=";",
        encoding="utf-8",
        descricao="Arrecadação e despesa do SIAFI / SIAFI2 (chega por e-mail como CSV)",
    ),
}
