"""
Leitor genérico de CSVs para a camada Bronze.

Regra de ouro do Bronze: NÃO interprete os dados — leia tudo como texto (dtype=str).
Tipos, datas e valores só serão convertidos na camada Silver.
"""

import logging
from pathlib import Path

import pandas as pd

from .sources import FonteDados

logger = logging.getLogger(__name__)


def ler_fonte(fonte: FonteDados, arquivo: Path | None = None) -> pd.DataFrame:
    """
    Lê o CSV de uma fonte e retorna um DataFrame com todas as colunas como string.

    Parâmetros
    ----------
    fonte   : definição da fonte (encoding, separador etc.)
    arquivo : caminho explícito para o arquivo; se None, busca em DATA_DIR/raw/
              (útil para apontar para fixtures em testes sem depender do ambiente)

    Raises
    ------
    FileNotFoundError : se o arquivo não existir no caminho esperado
    RuntimeError      : se o pandas falhar na leitura (encoding errado, arquivo corrompido etc.)
    """
    caminho = _resolver_caminho(fonte, arquivo)

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}\n"
            f"Copie o CSV da fonte '{fonte.nome}' para esse caminho antes de rodar a ingestão."
        )

    try:
        df = pd.read_csv(
            caminho,
            sep=fonte.separador,
            encoding=fonte.encoding,
            dtype=str,              # Bronze: sem conversão de tipos — preserva o dado bruto
            keep_default_na=False,  # "" vira "" em vez de NaN — evita perda silenciosa de dados
        )
    except Exception as exc:
        raise RuntimeError(
            f"Falha ao ler '{fonte.nome}' ({caminho}): {exc}"
        ) from exc

    logger.info(
        "Fonte '%s' lida: %d linhas × %d colunas",
        fonte.nome, len(df), len(df.columns),
    )
    return df


def _resolver_caminho(fonte: FonteDados, arquivo: Path | None) -> Path:
    """Retorna o caminho efetivo do arquivo, usando DATA_DIR quando não explicitado."""
    if arquivo is not None:
        return Path(arquivo)

    # Importação lazy: Django pode não estar inicializado quando este módulo é importado
    from django.conf import settings
    return Path(settings.DATA_DIR) / "raw" / fonte.arquivo
