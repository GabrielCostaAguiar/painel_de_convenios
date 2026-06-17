"""
Camada Silver genérica: limpeza estrutural, conversão de tipos e validação
para qualquer fonte registrada em core/ingestion/sources.py.

Pipeline (transformar_fonte):
  1. Leitura do CSV Bronze mais recente (tudo texto, keep_default_na=False)
  2. Remoção de colunas fantasma (Unnamed — artefato do Excel exportado)
  3. Normalização de nomes para snake_case sem acentos
  4. Carregamento do schema YAML em core/transform/schemas/<nome>.yaml
  5. Conversão por categoria declarada no schema:
       data         → datetime64[us]      (errors="coerce" → NaT)
       valor        → float64             (errors="coerce" → NaN)
       identificador → StringDtype nullable (strip + remoção de artefato ".0")
       texto        → StringDtype nullable (strip)
  6. Relatório de qualidade (apenas log; nunca interrompe o fluxo)

Gravação (gravar_silver):
  - Formato: Parquet (preserva datetime, float e StringDtype sem reinterpretação)
  - Destino: DATA_DIR/silver/<nome>.parquet (sobrescrito a cada carga)
"""

import logging
from pathlib import Path

import pandas as pd
import yaml

from .utils import normalizar_coluna

logger = logging.getLogger(__name__)

# Diretório dos schemas YAML — relativo a este arquivo
SCHEMAS_DIR = Path(__file__).parent / "schemas"


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _limpar_id(val: str) -> str | None:
    """
    Limpa um identificador textual:
    - vazio → None (vira <NA> após astype("string"))
    - artefato de float "102.0" → "102"  (preserva zeros à esquerda: "0000102" inalterado)
    """
    if not val:
        return None
    if val.endswith(".0") and val[:-2].isdigit():
        return val[:-2]
    return val


def _bronze_mais_recente(nome_fonte: str) -> Path:
    from django.conf import settings
    bronze_dir = Path(settings.DATA_DIR) / "bronze" / nome_fonte
    arquivos = sorted(bronze_dir.glob(f"{nome_fonte}_*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo Bronze encontrado em {bronze_dir}.\n"
            f"Rode antes: python manage.py rodar_ingestao {nome_fonte}"
        )
    return arquivos[-1]


def _carregar_schema(nome_fonte: str) -> dict:
    schema_path = SCHEMAS_DIR / f"{nome_fonte}.yaml"
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Schema não encontrado: {schema_path}\n"
            f"Rode antes: python manage.py gerar_schemas {nome_fonte}"
        )
    with schema_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Validação de qualidade (apenas log)
# ---------------------------------------------------------------------------

def _validar(df: pd.DataFrame, nome_fonte: str) -> None:
    try:
        n, c = df.shape
        logger.info("=== Relatório Silver '%s' ===", nome_fonte)
        logger.info("  Shape: %d linhas × %d colunas", n, c)
        for col in df.columns:
            qtd = int(df[col].isna().sum())
            pct = qtd / n * 100 if n > 0 else 0.0
            nivel = logging.WARNING if qtd > 0 else logging.INFO
            logger.log(nivel, "  Nulos  %-45s  %4d  (%.1f%%)", col, qtd, pct)
        logger.info("=== fim do relatório ===")
    except Exception as exc:
        logger.error("Validação falhou inesperadamente: %s", exc)


# ---------------------------------------------------------------------------
# Ponto de entrada — transformação
# ---------------------------------------------------------------------------

def transformar_fonte(nome: str, bronze_path: Path | None = None) -> pd.DataFrame:
    """
    Lê o Bronze de <nome>, aplica tipagem via schema YAML e executa validação.
    Não grava nenhum arquivo.

    Parâmetros
    ----------
    nome        : chave da fonte em FONTES (ex: "dcgce_convenios")
    bronze_path : caminho explícito para o CSV Bronze; se None, usa o mais
                  recente em DATA_DIR/bronze/<nome>/

    Retorna
    -------
    pd.DataFrame com tipos convertidos conforme o schema
    """
    schema = _carregar_schema(nome)
    colunas: dict[str, list[str]] = schema.get("colunas", {})

    cols_data = colunas.get("data", [])
    cols_valor = colunas.get("valor", [])
    cols_id = colunas.get("identificador", [])

    caminho = bronze_path if bronze_path is not None else _bronze_mais_recente(nome)
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False)

    n_original = len(df.columns)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = [normalizar_coluna(c) for c in df.columns]

    logger.info(
        "Silver '%s': %d → %d colunas, %d linhas",
        nome, n_original, len(df.columns), len(df),
    )

    # --- datas ---
    logger.info("Datas:")
    for col in cols_data:
        if col not in df.columns:
            logger.warning("  Coluna data '%s' ausente no Bronze de '%s'", col, nome)
            continue
        convertida = pd.to_datetime(df[col], errors="coerce")
        logger.info("  %-45s  NaT: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- valores monetários ---
    logger.info("Valores:")
    for col in cols_valor:
        if col not in df.columns:
            logger.warning("  Coluna valor '%s' ausente no Bronze de '%s'", col, nome)
            continue
        convertida = pd.to_numeric(df[col], errors="coerce")
        logger.info("  %-45s  NaN: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- identificadores ---
    logger.info("Identificadores:")
    for col in cols_id:
        if col not in df.columns:
            logger.warning("  Coluna id '%s' ausente no Bronze de '%s'", col, nome)
            continue
        convertida = df[col].str.strip().apply(_limpar_id).astype("string")
        logger.info("  %-45s  <NA>: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- texto: todas as colunas não tipadas acima ---
    cols_tipadas = set(cols_data) | set(cols_valor) | set(cols_id)
    for col in df.columns:
        if col not in cols_tipadas:
            df[col] = df[col].str.strip().astype("string")

    _validar(df, nome)
    return df


# ---------------------------------------------------------------------------
# Gravação Silver
# ---------------------------------------------------------------------------

def gravar_silver(nome: str, df: pd.DataFrame, destino: Path | None = None) -> Path:
    """
    Grava o DataFrame Silver em Parquet.

    Parâmetros
    ----------
    nome    : nome da fonte (usado para o nome do arquivo quando destino é None)
    df      : DataFrame já transformado (tipos convertidos)
    destino : caminho explícito; se None, usa DATA_DIR/silver/<nome>.parquet

    Retorna
    -------
    Path : caminho do arquivo gravado
    """
    if destino is None:
        from django.conf import settings
        silver_dir = Path(settings.DATA_DIR) / "silver"
        silver_dir.mkdir(parents=True, exist_ok=True)
        destino = silver_dir / f"{nome}.parquet"

    df.to_parquet(destino, index=False)
    logger.info("Silver gravado: %s (%d linhas, %d colunas)", destino, *df.shape)
    return Path(destino)
