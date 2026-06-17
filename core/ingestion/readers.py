"""
Leitor genérico de arquivos (CSV e Excel) para a camada Bronze.

Regra de ouro do Bronze: NÃO interprete os dados — leia tudo como texto (dtype=str).
Tipos, datas e valores só serão convertidos na camada Silver.
"""

import logging
from pathlib import Path

import pandas as pd

from .sources import FonteDados

logger = logging.getLogger(__name__)

# Opções fixas do Bronze: preserva dado bruto sem coerção de tipos
_OPCOES_BRONZE = {"dtype": str, "keep_default_na": False}

_FORMATOS_VALIDOS = {"csv", "excel"}


def ler_fonte(fonte: FonteDados, arquivo: Path | None = None) -> pd.DataFrame:
    """
    Lê o arquivo de uma fonte (CSV ou Excel) e retorna um DataFrame com todas as colunas como string.

    Parâmetros
    ----------
    fonte   : definição da fonte (formato, opcoes_leitura etc.)
    arquivo : caminho explícito para o arquivo; se None, busca em DATA_DIR/raw/
              (útil para apontar para fixtures em testes sem depender do ambiente)

    Raises
    ------
    ValueError        : se fonte.formato não for "csv" ou "excel"
    FileNotFoundError : se o arquivo não existir no caminho esperado
    RuntimeError      : se o pandas falhar na leitura (arquivo corrompido, opções inválidas etc.)
    """
    if fonte.formato not in _FORMATOS_VALIDOS:
        raise ValueError(
            f"Formato inválido '{fonte.formato}' para a fonte '{fonte.nome}'. "
            f"Valores aceitos: {sorted(_FORMATOS_VALIDOS)}"
        )

    caminho = _resolver_caminho(fonte, arquivo)

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}\n"
            f"Copie o arquivo da fonte '{fonte.nome}' para esse caminho antes de rodar a ingestão."
        )

    opcoes = {**_OPCOES_BRONZE, **fonte.opcoes_leitura}

    try:
        if fonte.formato == "csv":
            df = pd.read_csv(caminho, **opcoes)
        else:  # "excel"
            df = pd.read_excel(caminho, **opcoes)
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
