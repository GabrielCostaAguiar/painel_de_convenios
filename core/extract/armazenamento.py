"""
Armazena os arquivos fontes recuperados na web
"""

from django.conf import settings
from pathlib import Path
from datetime import date

def caminho_destino(fonte: str, arquivo: str) -> Path:
    # fonte = "transferegov" | "gmail"; arquivo = "siconv.zip" | "dcgce_convenio"
    data = date.today().isoformat()                          # "2026-06-12"
    nome_arquivo = Path(arquivo)
    nome = f"{nome_arquivo.stem}_{data}{nome_arquivo.suffix}"
    destino_dir = Path(settings.BASE_DIR) / "data" / "raw" / fonte
    destino_dir.mkdir(parents=True, exist_ok=True)
    return destino_dir / nome

def ja_existe(caminho: Path) -> bool:
    return caminho.exists()


