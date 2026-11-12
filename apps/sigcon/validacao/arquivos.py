"""
Arquivos de entrada: existem em data/raw e estão atualizados?

Cada tabela sigcon_* tem um arquivo esperado em data/raw/sigcon (campo `arquivo`
de FONTES). Arquivo ausente significa que a ingestão não tem o que ler: ERRO.
Arquivo antigo significa que o painel está mostrando um retrato velho: ALERTA.

O limite de idade é SIGCON_RAW_MAX_DIAS (config/settings/base.py, padrão 7).
"""

from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings

from apps.sigcon.validacao.volumetria import tabelas_sigcon

MAX_DIAS_PADRAO = 7


def max_dias():
    return getattr(settings, "SIGCON_RAW_MAX_DIAS", MAX_DIAS_PADRAO)


def arquivos_esperados():
    """{tabela: caminho do arquivo em data/raw} para cada tabela sigcon_* com fonte."""
    from core.ingestion.sources import FONTES

    raiz = Path(settings.DATA_DIR) / "raw"
    return {
        tabela: raiz / FONTES[tabela].arquivo
        for tabela in tabelas_sigcon()
        if tabela in FONTES
    }


def teste_arquivos_ausentes():
    """(qt, amostra): arquivos esperados que não existem."""
    ausentes = [
        {"fonte": tabela, "arquivo": str(caminho.relative_to(Path(settings.DATA_DIR)))}
        for tabela, caminho in arquivos_esperados().items()
        if not caminho.is_file()
    ]
    return len(ausentes), ausentes


def teste_arquivos_antigos(agora=None):
    """(qt, amostra): arquivos presentes com mais de `max_dias()` dias."""
    agora = agora or datetime.now()
    limite = agora - timedelta(days=max_dias())
    antigos = []
    for tabela, caminho in arquivos_esperados().items():
        if not caminho.is_file():
            continue  # ausência é do outro teste
        modificado = datetime.fromtimestamp(caminho.stat().st_mtime)
        if modificado < limite:
            antigos.append(
                {
                    "fonte": tabela,
                    "arquivo": caminho.name,
                    "modificado_em": modificado.date().isoformat(),
                    "dias": (agora - modificado).days,
                }
            )
    return len(antigos), antigos
