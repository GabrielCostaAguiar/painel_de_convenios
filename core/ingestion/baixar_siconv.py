"""Baixa e extrai o pacote de dados abertos do Transferegov (SICONV/União)."""
import os
import zipfile
import urllib.request
from pathlib import Path

from django.conf import settings

URL = "http://repositorio.dados.gov.br/seges/detru/siconv.zip"

def baixar_siconv():
    # destino dinâmico: camada raw, domínio união
    destino = Path(settings.DATA_DIR) / "raw" / "uniao"
    destino.mkdir(parents=True, exist_ok=True)
    zip_path = destino / "siconv.zip"

    # proxy lido do ambiente (.env), nunca escrito no código
    proxy_url = os.environ.get("PRODEMGE_PROXY")  # ex.: http://usuario:senha@proxycamg.prodemge.gov.br:8080
    if proxy_url:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        )
        urllib.request.install_opener(opener)

    print(f"Baixando {URL} ...")
    urllib.request.urlretrieve(URL, zip_path)

    print(f"Extraindo em {destino} ...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(destino)

    zip_path.unlink()
    print(f"ZIP removido: {zip_path}")

    print(f"Concluído. Arquivos em: {destino}")
    return destino

if __name__ == "__main__":
    baixar_siconv()