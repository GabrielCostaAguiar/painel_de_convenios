"""
Camada Bronze: ingestão de dados brutos.

Responsabilidade única: ler o CSV original e gravá-lo em data/bronze/
sem nenhuma transformação. O que chegar, fica — erros, duplicatas,
colunas com nome errado, tudo. A Silver que vai limpar.
"""

import logging
from datetime import datetime
from pathlib import Path

from django.conf import settings

from .readers import ler_fonte
from .sources import FONTES

logger = logging.getLogger(__name__)


def ingerir(nome_fonte: str, arquivo: Path | None = None) -> Path:
    """
    Lê a fonte e persiste o dado bruto em data/bronze/<nome_fonte>/.

    Parâmetros
    ----------
    nome_fonte : chave em FONTES (ex: "convenios")
    arquivo    : caminho customizado para o CSV de entrada;
                 se None, usa DATA_DIR/raw/<fonte.arquivo>

    Retorna
    -------
    Path : caminho do arquivo gravado em bronze

    Por que CSV e não Parquet?
    --------------------------
    Bronze preserva o dado o mais próximo possível da fonte original.
    CSV garante que nenhum valor sofra coerção silenciosa de tipo
    (ex.: "01/01/2024" vira string, não datetime — isso é trabalho da Silver).
    Parquet fará sentido na Silver e Gold, onde os tipos já estão validados
    e precisamos de performance de leitura.
    """
    fonte = FONTES.get(nome_fonte)
    if fonte is None:
        disponiveis = ", ".join(FONTES)
        raise ValueError(
            f"Fonte '{nome_fonte}' não registrada em FONTES. "
            f"Disponíveis: {disponiveis}"
        )

    df = ler_fonte(fonte, arquivo=arquivo)

    # Subpasta por nome de fonte: data/bronze/convenios/
    destino_dir = Path(settings.DATA_DIR) / "bronze" / nome_fonte
    destino_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp no nome garante histórico de cargas sem sobrescrever runs anteriores
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = destino_dir / f"{nome_fonte}_{timestamp}.csv"

    df.to_csv(destino, index=False, encoding="utf-8")

    logger.info("Bronze salvo: %s (%d linhas)", destino, len(df))
    return destino
