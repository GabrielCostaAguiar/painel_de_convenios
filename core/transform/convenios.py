"""
Camada Silver: transformações para a fonte 'convenios'.

Filosofia:
  - Cada função transforma exatamente uma coisa — fácil de ler, testar e depurar.
  - Funções de transformação são puras (input → output, sem side effects).
  - Somente transformar_bronze() acessa o sistema de arquivos.

Diferença Bronze × Silver em uma frase:
  Bronze  = fotografia fiel do dado original (CSV como veio da fonte)
  Silver  = dado limpo, tipado e padronizado (pronto para o banco ou para análise)
  A Silver nunca descarta linhas — apenas corrige e padroniza;
  quem decide o que "vale" é a Gold (filtros e agregações para KPIs).
"""

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# Funções puras de transformação de valor (uma coluna por vez)
# =============================================================================

def _limpar_texto(valor: str) -> str:
    """Remove espaços extras; garante que nunca retorna None."""
    return valor.strip() if isinstance(valor, str) else ""


def _parse_data_br(valor: str) -> date | None:
    """
    DD/MM/AAAA → date.
    Retorna None silenciosamente para campos vazios; loga aviso para valores inválidos.
    """
    limpo = valor.strip() if isinstance(valor, str) else ""
    if not limpo:
        return None
    try:
        return datetime.strptime(limpo, "%d/%m/%Y").date()
    except ValueError:
        logger.warning("Data em formato inesperado ignorada: %r", valor)
        return None


def _parse_valor_br(valor: str) -> Decimal | None:
    """
    Formato brasileiro (ex: "1.234.567,89") → Decimal.
    Regra: remove separador de milhar (.) e troca vírgula decimal por ponto.
    Retorna None para campos vazios ou inválidos.
    """
    limpo = valor.strip() if isinstance(valor, str) else ""
    if not limpo:
        return None
    try:
        normalizado = limpo.replace(".", "").replace(",", ".")
        return Decimal(normalizado)
    except InvalidOperation:
        logger.warning("Valor monetário inválido ignorado: %r", valor)
        return None


def _decimal_para_str(v: Decimal | None) -> str:
    """Decimal → string com ponto decimal (ex: '500000.00'). Vazio se None."""
    return str(v) if v is not None else ""


def _data_para_str(v: date | None) -> str:
    """date → ISO 8601 (ex: '2024-01-01'). Vazio se None."""
    return v.isoformat() if v is not None else ""


# =============================================================================
# Transformação do DataFrame completo
# =============================================================================

def transformar_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recebe o DataFrame Bronze (tudo string) e retorna o DataFrame Silver:
      - textos limpos (strip)
      - datas em ISO 8601 (string no CSV, para preservar null como "")
      - valores monetários com ponto decimal

    Não filtra linhas — linhas com dados inválidos entram com campos vazios.
    """
    silver = pd.DataFrame()

    # --- identificação ---
    silver["nr_convenio"] = df["nr_convenio"].apply(_limpar_texto)
    silver["nr_processo"] = df["nr_processo"].apply(_limpar_texto)
    silver["objeto"] = df["objeto"].apply(_limpar_texto)

    # --- partes ---
    silver["concedente"] = df["concedente"].apply(_limpar_texto)
    silver["convenente"] = df["convenente"].apply(_limpar_texto)

    # --- status ---
    silver["situacao"] = df["situacao"].apply(_limpar_texto)

    # --- financeiro (BR → ponto decimal) ---
    silver["valor_global"] = df["valor_global"].apply(
        lambda v: _decimal_para_str(_parse_valor_br(v))
    )

    # --- datas (BR → ISO 8601) ---
    silver["data_inicio"] = df["data_inicio"].apply(
        lambda v: _data_para_str(_parse_data_br(v))
    )
    silver["data_termino"] = df["data_termino"].apply(
        lambda v: _data_para_str(_parse_data_br(v))
    )

    logger.info("Silver: %d linhas transformadas, %d colunas", len(silver), len(silver.columns))
    return silver


# =============================================================================
# Orquestração: Bronze → Silver (acessa sistema de arquivos)
# =============================================================================

def _bronze_mais_recente(nome_fonte: str) -> Path:
    """Retorna o arquivo Bronze mais recente para a fonte (ordena por nome/timestamp)."""
    from django.conf import settings  # lazy: Django pode não estar pronto ao importar
    bronze_dir = Path(settings.DATA_DIR) / "bronze" / nome_fonte
    arquivos = sorted(bronze_dir.glob(f"{nome_fonte}_*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo Bronze encontrado em {bronze_dir}.\n"
            f"Rode antes: python manage.py rodar_ingestao {nome_fonte}"
        )
    return arquivos[-1]  # o mais recente pelo timestamp no nome


def transformar_bronze(nome_fonte: str) -> Path:
    """
    Carrega o Bronze mais recente, transforma e salva em data/silver/<nome_fonte>/.
    Retorna o caminho do arquivo Silver gerado.
    """
    from datetime import datetime as dt
    from django.conf import settings

    bronze_path = _bronze_mais_recente(nome_fonte)
    logger.info("Transformando Bronze: %s", bronze_path)

    df_bronze = pd.read_csv(bronze_path, dtype=str, keep_default_na=False)
    df_silver = transformar_df(df_bronze)

    destino_dir = Path(settings.DATA_DIR) / "silver" / nome_fonte
    destino_dir.mkdir(parents=True, exist_ok=True)

    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    destino = destino_dir / f"{nome_fonte}_silver_{timestamp}.csv"

    df_silver.to_csv(destino, index=False, encoding="utf-8")
    logger.info("Silver salvo: %s", destino)
    return destino
