"""
Baixar as bases de dados do transferegov, módulo discricionárias e legais.

Usar um GET simples para fazer a requesição no site e baixar o .zip
extrair() ; _baixar_zip()
"""
import logging
import requests
from pathlib import Path

from .armazenamento import caminho_destino, ja_existe

logger = logging.getLogger(__name__)

URL_BASE = "http://repositorio.dados.gov.br/seges/detru/"

def _baixar_zip(url: str, destino: Path) -> None:
    with requests.get(url, stream=True) as r:
        r.raise_for_status()                       # falha alto se vier erro HTTP
        with open(destino, "wb") as f:
            for pedaco in r.iter_content(chunk_size=8192):
                f.write(pedaco)

def extrair(arquivo: str = "siconv.zip"):
    logger.info("iniciando extracao transferegov: %s", arquivo)
    url = URL_BASE + arquivo
    destino = caminho_destino("transferegov", arquivo)
    if ja_existe(destino):
        logger.info("arquivo do dia ja existe para %s, pulando: %s", arquivo, destino)
        return []
    try:
        _baixar_zip(url, destino)
    except Exception as exc:
        logger.error("falha ao baixar %s de %s: %s", arquivo, url, exc)
        raise
    logger.info("extracao transferegov concluida: %s -> %s", arquivo, destino)
    return [destino]


