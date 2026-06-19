"""
Armazena os arquivos fontes recuperados na web
"""

from django.conf import settings
from pathlib import Path
from datetime import date

def caminho_destino(fonte: str, arquivo: str, extensao: str | None = None) -> Path:
    # fonte = "transferegov" | "gmail"; arquivo = "siconv.zip" | "dcgce_convenio"
    #
    # extensao=None (padrao): infere de Path(arquivo).suffix — correto quando
    # "arquivo" tem uma unica extensao real no final (ex.: "siconv.zip").
    # extensao="" : usa "arquivo" por completo como base, sem tentar separar
    # extensao — necessario pros assuntos do Gmail, que podem ter ponto NO
    # NOME (ex.: "dcgce_unidades.executoras") e cuja extensao real so se
    # conhece depois do download (ver core/extract/gmail.py).
    data = date.today().isoformat()                          # "2026-06-12"
    if extensao is None:
        nome_arquivo = Path(arquivo)
        base, ext = nome_arquivo.stem, nome_arquivo.suffix
    else:
        base, ext = arquivo, extensao
    nome = f"{base}_{data}{ext}"
    destino_dir = Path(settings.BASE_DIR) / "data" / "raw" / fonte
    destino_dir.mkdir(parents=True, exist_ok=True)
    return destino_dir / nome

def ja_existe(caminho: Path) -> bool:
    return caminho.exists()


