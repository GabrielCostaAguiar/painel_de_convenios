"""
Camada Silver — fonte 'dcgce_convenios'.

Thin wrapper que delega toda a lógica ao transformer genérico (silver.py).
A configuração de colunas (datas, valores, identificadores) agora reside em
core/transform/schemas/dcgce_convenios.yaml — gere-o com:

    python manage.py gerar_schemas dcgce_convenios

A API pública (transformar_convenios / gravar_silver / NOME_FONTE) é mantida
para compatibilidade com código que ainda a importa diretamente.
"""

from pathlib import Path

from .silver import gravar_silver as _gravar
from .silver import transformar_fonte as _transformar

NOME_FONTE = "dcgce_convenios"


def transformar_convenios(bronze_path: Path | None = None):
    """Lê o Bronze de dcgce_convenios, converte tipos e valida. Não grava."""
    return _transformar(NOME_FONTE, bronze_path)


def gravar_silver(df, destino: Path | None = None):
    """Grava o DataFrame Silver em DATA_DIR/silver/dcgce_convenios.parquet."""
    return _gravar(NOME_FONTE, df, destino)
