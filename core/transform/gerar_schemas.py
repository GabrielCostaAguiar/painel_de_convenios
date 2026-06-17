"""
Gerador automático de schemas YAML para a camada Silver.

Para cada fonte em FONTES, amostra o Bronze (ou o arquivo raw) e classifica
cada coluna em um dos tipos: 'data', 'valor', 'identificador' ou 'texto'.

Heurística combinada (nome + valores):
  - data        : tokens de nome sugerem data E ≥50% dos valores convertem com
                  pd.to_datetime → 'data'; caso contrário → 'texto' (duvidoso)
  - valor       : tokens de nome sugerem valor E ≥70% dos valores convertem com
                  pd.to_numeric → 'valor'; caso contrário → 'texto' (duvidoso)
  - identificador: tokens de nome sugerem id OU coluna tem valores com zeros à
                  esquerda → 'identificador'
  - texto       : nenhum padrão identificado, ou padrão não confirmado pelos
                  valores → 'texto' + marcado como duvidoso para revisão

Uso via management command:
    python manage.py gerar_schemas                   # todas as fontes
    python manage.py gerar_schemas dcgce_convenios   # uma fonte
    python manage.py gerar_schemas --sobrescrever    # força regeneração
"""

import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from .utils import normalizar_coluna

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).parent / "schemas"

# ---------------------------------------------------------------------------
# Tokens para classificação por nome de coluna
# ---------------------------------------------------------------------------

_TOKENS_DATA = {
    "data", "dt", "vigencia", "prazo", "periodo",
    "inicio", "termino", "emissao", "encerramento",
    "assinatura", "publicacao", "vencimento",
}
_TOKENS_VALOR = {
    "valor", "vlr", "montante", "saldo",
}
_TOKENS_ID = {
    "codigo", "numero", "nr", "id", "siafi",
    "cnpj", "cpf", "processo", "sei", "chave",
    "cod", "num", "sequencial", "identificador",
}


# ---------------------------------------------------------------------------
# Modelo de saída
# ---------------------------------------------------------------------------

@dataclass
class ColInfo:
    nome: str
    tipo: str      # 'data' | 'valor' | 'identificador' | 'texto'
    duvidoso: bool # True → foi para 'texto' sem certeza; revisar o YAML


# ---------------------------------------------------------------------------
# Classificação de coluna
# ---------------------------------------------------------------------------

def _tokens(nome_norm: str) -> set[str]:
    """Extrai tokens apenas-letras do nome normalizado, dividindo em _, ., - etc."""
    return set(re.findall(r"[a-z]+", nome_norm))


def _classificar(nome_norm: str, serie: pd.Series) -> tuple[str, bool]:
    """
    Classifica uma coluna pelo par (nome normalizado, amostra de valores).
    Retorna (tipo, duvidoso).

    Regra de ouro: na dúvida → 'texto' com duvidoso=True.
    Nunca converte de forma 'achista'.
    """
    toks = _tokens(nome_norm)
    amostra = serie[serie.notna() & (serie != "")].head(200)

    sugere_data = bool(toks & _TOKENS_DATA)
    sugere_valor = bool(toks & _TOKENS_VALOR)
    sugere_id = bool(toks & _TOKENS_ID)

    # --- data: nome + confirmação por valores ---
    if sugere_data:
        if len(amostra) == 0:
            return "data", False  # coluna vazia — confia no nome
        pct = pd.to_datetime(amostra, errors="coerce").notna().mean()
        if pct >= 0.5:
            return "data", False
        # Nome sugere data mas valores não convertem — duvidoso
        return "texto", True

    # --- valor: nome + confirmação por valores ---
    if sugere_valor:
        if len(amostra) == 0:
            return "valor", False
        pct = pd.to_numeric(amostra, errors="coerce").notna().mean()
        if pct >= 0.7:
            return "valor", False
        return "texto", True

    # --- identificador: nome suficiente (sem exigir confirmação por valor) ---
    if sugere_id:
        return "identificador", False

    # --- heurística extra: zeros à esquerda → identificador mesmo sem nome sugestivo ---
    if len(amostra) > 0 and amostra.str.match(r"^0\d").any():
        return "identificador", False

    # --- nenhum padrão identificado → texto (duvidoso, para revisão) ---
    return "texto", True


# ---------------------------------------------------------------------------
# Amostragem da fonte
# ---------------------------------------------------------------------------

def _amostra_fonte(nome_fonte: str) -> pd.DataFrame | None:
    """
    Retorna um DataFrame de amostra (até 500 linhas) para classificação.
    Estratégia: Bronze primeiro; se não existir, raw file via reader.
    Retorna None se nenhuma das opções funcionar.
    """
    from django.conf import settings
    from core.ingestion.sources import FONTES

    # 1. Tenta Bronze
    bronze_dir = Path(settings.DATA_DIR) / "bronze" / nome_fonte
    if bronze_dir.exists():
        csvs = sorted(bronze_dir.glob(f"{nome_fonte}_*.csv"))
        if csvs:
            try:
                return pd.read_csv(csvs[-1], dtype=str, keep_default_na=False, nrows=500)
            except Exception as exc:
                logger.warning("Falha ao ler Bronze de '%s': %s", nome_fonte, exc)

    # 2. Tenta raw via reader
    fonte = FONTES.get(nome_fonte)
    if fonte is None:
        return None

    raw_path = Path(settings.DATA_DIR) / "raw" / fonte.arquivo
    if not raw_path.exists():
        logger.warning("Arquivo raw não encontrado: %s (fonte '%s' ignorada)", raw_path, nome_fonte)
        return None

    from core.ingestion.readers import ler_fonte
    try:
        df = ler_fonte(fonte)
        return df.head(500)
    except Exception as exc:
        # Fallback: CSV com encoding não-UTF-8 (ex.: latin-1/cp1252)
        if fonte.formato == "csv":
            for enc in ("latin-1", "cp1252"):
                try:
                    opcoes = {"dtype": str, "keep_default_na": False, "nrows": 500,
                              "encoding": enc, **fonte.opcoes_leitura}
                    return pd.read_csv(raw_path, **opcoes)
                except Exception:
                    continue
        logger.warning("Falha ao ler raw de '%s': %s", nome_fonte, exc)
        return None


# ---------------------------------------------------------------------------
# Geração de schema para uma fonte
# ---------------------------------------------------------------------------

def gerar_schema_fonte(nome_fonte: str) -> list[ColInfo] | None:
    """
    Classifica todas as colunas de <nome_fonte>.
    Retorna lista de ColInfo ou None se amostra indisponível.
    """
    df = _amostra_fonte(nome_fonte)
    if df is None:
        return None

    # Força todos os nomes para string antes de qualquer filtro.
    # Excel com células de cabeçalho vazias gera nomes float (nan),
    # o que quebra o operador ~ em Series de dtype object/float misto.
    df.columns = df.columns.astype(str)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.loc[:, df.columns != "nan"]
    df.columns = [normalizar_coluna(c) for c in df.columns]

    resultado = []
    for col in df.columns:
        tipo, duvidoso = _classificar(col, df[col])
        resultado.append(ColInfo(nome=col, tipo=tipo, duvidoso=duvidoso))

    return resultado


def salvar_schema(nome_fonte: str, colunas: list[ColInfo], sobrescrever: bool = False) -> Path:
    """
    Grava o schema em SCHEMAS_DIR/<nome_fonte>.yaml.
    Pula se o arquivo já existir e sobrescrever=False.
    """
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    destino = SCHEMAS_DIR / f"{nome_fonte}.yaml"

    if destino.exists() and not sobrescrever:
        logger.info("Schema já existe (use --sobrescrever para regenerar): %s", destino)
        return destino

    por_tipo: dict[str, list[str]] = {
        "data": [], "valor": [], "identificador": [], "texto": [],
    }
    duvidosas: list[str] = []
    for c in colunas:
        por_tipo[c.tipo].append(c.nome)
        if c.duvidoso:
            duvidosas.append(c.nome)

    schema = {
        "fonte": nome_fonte,
        "gerado_em": str(date.today()),
        # Remove categorias vazias para manter o YAML limpo
        "colunas": {k: v for k, v in por_tipo.items() if v},
        "duvidoso": duvidosas,
    }

    with destino.open("w", encoding="utf-8") as f:
        yaml.dump(schema, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    logger.info("Schema salvo: %s (%d colunas, %d duvidosas)", destino, len(colunas), len(duvidosas))
    return destino


# ---------------------------------------------------------------------------
# Entrypoints
# ---------------------------------------------------------------------------

def gerar_um(nome_fonte: str, sobrescrever: bool = False) -> dict:
    """
    Gera schema para uma fonte. Retorna dict de resultado para o relatório.
    """
    from core.ingestion.sources import FONTES
    if nome_fonte not in FONTES:
        return {"fonte": nome_fonte, "status": "erro", "msg": "Fonte não registrada em FONTES"}

    colunas = gerar_schema_fonte(nome_fonte)
    if colunas is None:
        return {"fonte": nome_fonte, "status": "sem_dados", "total": 0, "por_tipo": {}, "duvidosas": []}

    salvar_schema(nome_fonte, colunas, sobrescrever=sobrescrever)

    por_tipo: dict[str, int] = {}
    for c in colunas:
        por_tipo[c.tipo] = por_tipo.get(c.tipo, 0) + 1

    return {
        "fonte": nome_fonte,
        "status": "ok",
        "total": len(colunas),
        "por_tipo": por_tipo,
        "duvidosas": [c.nome for c in colunas if c.duvidoso],
    }


def gerar_todos(sobrescrever: bool = False) -> list[dict]:
    """Gera schemas para todas as fontes registradas. Retorna lista de resultados."""
    from core.ingestion.sources import FONTES
    return [gerar_um(nome, sobrescrever=sobrescrever) for nome in FONTES]
