"""
Camada Silver genérica: limpeza estrutural, conversão de tipos e validação
para qualquer fonte registrada em core/ingestion/sources.py.

Pipeline (transformar_fonte / _transformar):
  1. Leitura do CSV Bronze mais recente (tudo texto, keep_default_na=False)
  2. Remoção de colunas fantasma (Unnamed — artefato do Excel exportado)
  3. Normalização de nomes para snake_case sem acentos
  4. Carregamento do schema YAML em core/transform/schemas/<nome>.yaml
  5. Remoção das linhas 100% vazias — ÚNICA remoção de linha do motor. "Vazia"
     = todas as células, inclusive as das colunas Unnamed, "" ou "N/A" depois
     de strip(), avaliadas no texto bruto ANTES de qualquer tratamento. Linha
     com qualquer outro texto (0, 9999...) NÃO é vazia e fica. Duplicatas
     ficam todas.
  6. Marcação de linhas (nada é excluído): em tabelas que declaram
     'marcar_linhas_se_nulo:' ou 'quarentena:', a coluna `ds_alerta_linha`
     recebe o motivo ('cabecalho_repetido', 'chave_obrigatoria_vazia:<col>',
     'quarentena:grao_divergente', separados por ';') e `tx_linha_bruta` o
     texto original da linha (JSON). 'marcar_linhas_se_nulo:' (chaves = nomes
     BRUTOS) roda ANTES da tipagem: identifica blocos desalinhados do
     relatório do BO (ex.: tabela 07) e, nas linhas marcadas, a tipagem não
     quebra — valor que não converte vira nulo. Em tabelas sem marcação, linha
     que repete o cabeçalho só gera ALERTA no log.
  7. Conversão por categoria declarada no schema (chaves = nomes BRUTOS,
     pré-renomear — mesma convenção do bloco 'colunas'):
       data          → datetime64[us], hora zerada (errors="coerce" → NaT)
       data_hora     → datetime64[us], mantém a hora (errors="coerce" → NaT)
                       (ambos decidem o formato por valor: ISO `aaaa-mm-dd`
                       ou dd/mm/aaaa — ver _converter_datas)
       valor         → float64              (errors="coerce" → NaN)
       inteiro       → Int64                (errors="raise"; sentinelas → <NA>)
       identificador → StringDtype nullable (strip + remoção de artefato ".0")
       texto         → StringDtype nullable (strip)
     'sentinelas:' (chaves = nomes BRUTOS) sobrescreve, por coluna, o conjunto
     global SENTINELAS usado nessa etapa.
  8. Renomeação (bloco 'renomear': bruto → final)
  9. 'desdobrar:' — gera a saída longa (outro DataFrame) a partir de colunas
     ainda presentes neste ponto (mistura de nomes finais e brutos ainda não
     descartados)
  10. 'descartar:' — remove colunas (nomes finais) após o desdobramento
  11. Limpeza de texto (strip) e 'booleanos:' (chaves = nomes FINAIS;
      default = convenção de prefixo fl_ + MAPA_BOOLEANO)
  12. 'derivadas:' — colunas calculadas por função registrada (nomes finais)
  13. Linhas 100% idênticas: só ALERTA com a contagem — todas ficam
  14. 'quarentena:' — MARCA (não separa) as linhas cujo grão se repete com
      destino divergente; `transformar_fonte_completo()["quarentena"]` devolve
      uma cópia delas, só para relatório
  15. Colunas ds_alerta_linha/tx_linha_bruta (só nas tabelas com marcação)
  16. 'grao:' — verifica unicidade (nomes finais); só loga ALERTA, nunca
      interrompe
  17. Relatório de qualidade (apenas log; nunca interrompe o fluxo)

Divergência deliberada da ordem descrita na especificação (que pede
renomear → desdobrar → descartar → sentinelas → tipos → booleanos →
derivadas → descartar linhas): aqui a tipagem (passo 7) roda ANTES do
renomear, igual já funcionava para o GRP antes desta generalização — mudar
a ordem exigiria reescrever as chaves de 'colunas' nos 22 YAMLs do GRP para
nomes finais, o que violaria a regra de saída idêntica do GRP.
'marcar_linhas_se_nulo:' também roda antes (ver passo 6, motivo acima).
'sentinelas:' usa nomes BRUTOS (mesma convenção de 'colunas'); 'booleanos:',
'derivadas:', 'descartar:' e 'grao:'/'quarentena:' usam nomes FINAIS, por
rodarem depois do renomear.

Gravação (gravar_silver):
  - Formato: Parquet (preserva datetime, float e StringDtype sem reinterpretação)
  - Destino: DATA_DIR/silver/<nome>.parquet (sobrescrito a cada carga)
"""

import json
import logging
from pathlib import Path

import pandas as pd
import yaml

from .chaves import montar_siafi_uo
from .utils import (
    MAPA_BOOLEANO,
    limpar_colunas_padronizadas,
    normalizar_coluna,
    valores_sentinela,
)

logger = logging.getLogger(__name__)

# Diretório dos schemas YAML — relativo a este arquivo
SCHEMAS_DIR = Path(__file__).parent / "schemas"

# Registro de funções chamáveis pelo bloco YAML 'derivadas:'. Única entrada
# hoje: siafi_uo = montar_siafi_uo(nr_siafi, cd_uo) — ver seção 9 do Modelo de
# Extração das Bases Legadas v1.0. Para uma nova função, implemente-a
# genericamente (não condicionada a nome de fonte) e registre aqui.
FUNCOES_DERIVADAS = {
    "montar_siafi_uo": montar_siafi_uo,
}


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


def _para_numero(val: str) -> str:
    """
    Converte valor no formato brasileiro para o americano, que o pandas entende.
    '13.334.172,00' -> '13334172.00'
    Só age se houver vírgula, para não estragar valores já no formato americano
    (ex.: '744684.0' das fontes antigas continua igual).
    """
    if not isinstance(val, str):
        return val
    if "," in val:
        return val.replace(".", "").replace(",", ".")
    if val.count(".") > 1:
        return val.replace(".", "")
    return val


_RE_DATA_ISO = r"^\d{4}-\d{2}-\d{2}"


def _converter_datas(serie: pd.Series) -> pd.Series:
    """
    Converte texto em datetime64[us], decidindo o formato POR VALOR.

    O pandas infere o formato da coluna inteira pela primeira data não-nula:
    com `dayfirst=True`, uma coluna ISO (`2003-02-14 00:00:00`, que é como o
    Excel exporta) cuja primeira data tem dia <= 12 vira `%Y-%d-%m` — dias <= 12
    saem com dia e mês trocados e dias > 12 viram NaT. Por isso valores ISO
    usam `format="ISO8601"` e o restante segue em `dayfirst=True` (dd/mm/aaaa,
    formato do GRP e do SICONV). Coluna sem nenhum valor ISO passa pela mesma
    chamada de antes, o que mantém a saída do GRP idêntica.
    """
    iso = serie.str.strip().str.match(_RE_DATA_ISO, na=False)
    if not iso.any():
        return pd.to_datetime(serie, errors="coerce", dayfirst=True)
    if iso.all():
        convertida = pd.to_datetime(serie, errors="coerce", format="ISO8601")
    else:
        parte_iso = pd.to_datetime(serie.where(iso), errors="coerce", format="ISO8601")
        parte_br = pd.to_datetime(serie.where(~iso), errors="coerce", dayfirst=True)
        convertida = parte_iso.fillna(parte_br)
    return convertida.astype("datetime64[us]")


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


# Texto que significa "não há dado" numa célula. "N/A" ("não se aplica") entra
# por decisão do dono dos dados (2026-11-10): linha com N/A em TODAS as colunas
# (ex.: grp_tabela_uo) é linha vazia. Outros marcadores ("0", "9999",
# "99999999", "-3") NÃO entram: têm texto, e a linha fica.
_SEM_DADO = frozenset({"", "N/A"})


def _remover_linhas_vazias(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    """
    ÚNICA remoção de linha do motor: a linha 100% vazia — todas as células,
    inclusive as das colunas `Unnamed`, são "" ou "N/A" depois de strip().
    Avaliada no texto bruto, antes de sentinela, tipagem, renomeação ou
    remoção de colunas.

    Linha com qualquer outro texto (inclusive só marcadores como "0" ou
    "9999") NÃO é vazia e fica. Regra do dono dos dados: nenhuma linha com
    algum dado é excluída.
    """
    vazia = df.apply(lambda coluna: coluna.str.strip().isin(_SEM_DADO)).all(axis=1)
    removidas = int(vazia.sum())
    if removidas:
        logger.info("Linhas 100%% vazias removidas em '%s': %d", nome, removidas)
    return df.loc[~vazia].reset_index(drop=True)


def _marcar(alertas: pd.Series, mascara: pd.Series, motivo: str) -> None:
    """Acrescenta `motivo` ao alerta das linhas em `mascara` (vários motivos
    na mesma linha ficam separados por ';')."""
    if not mascara.any():
        return
    alertas.loc[mascara] = alertas.loc[mascara].map(
        lambda atual: motivo if pd.isna(atual) else f"{atual};{motivo}"
    )


def _mascara_repetem_cabecalho(df: pd.DataFrame) -> pd.Series:
    """Alguns exports (ex.: relatórios paginados do BO) repetem a linha de
    cabeçalho como dado no meio do arquivo — com o texto original ("Plano
    Trabalho Código"), não o nome normalizado da coluna ("plano_trabalho_codigo").
    Devolve a máscara das linhas cujo valor em TODAS as colunas, depois de
    normalizado do mesmo jeito que o nome da coluna, é igual ao próprio nome da
    coluna. Não remove nada."""
    if df.empty:
        return pd.Series(False, index=df.index)
    normalizado = df.astype(str).map(normalizar_coluna)
    return (normalizado == pd.Series(df.columns, index=df.columns)).all(axis=1)


# ---------------------------------------------------------------------------
# Blocos declarativos novos (Fase 2 do Modelo de Extração das Bases Legadas)
# ---------------------------------------------------------------------------


def _aplicar_desdobrar(df: pd.DataFrame, regra: dict | None, nome: str) -> pd.DataFrame | None:
    """
    Gera uma segunda saída em formato longo a partir de colunas da mesma
    fonte (ex.: tabela 21, controle_sei_documento).

    Schema esperado:
        desdobrar:
          chave: [nr_sei]            # colunas repetidas em toda linha gerada
          valor: nr_documento_sei    # nome da coluna de saída com o conteúdo
          mapa:
            - coluna: instrumento
              tp_documento: Instrumento
              nr_ordem: 1
            - coluna: ta_1
              tp_documento: Termo Aditivo
              nr_ordem: 1

    Uma linha de saída por célula preenchida (célula vazia/nula não gera linha).
    Retorna None se a fonte não declara 'desdobrar'.
    """
    if not regra:
        return None

    chave = regra["chave"]
    coluna_valor = regra["valor"]
    partes = []
    for item in regra["mapa"]:
        coluna_origem = item["coluna"]
        if coluna_origem not in df.columns:
            logger.warning("desdobrar: coluna '%s' ausente em '%s'", coluna_origem, nome)
            continue
        extras = {k: v for k, v in item.items() if k != "coluna"}
        preenchida = df[coluna_origem].notna()
        bloco = df.loc[preenchida, chave].copy()
        bloco[coluna_valor] = df.loc[preenchida, coluna_origem].astype(str).str.strip()
        bloco = bloco[bloco[coluna_valor] != ""]
        for campo, valor in extras.items():
            bloco[campo] = valor
        partes.append(bloco)

    if not partes:
        return pd.DataFrame(columns=[*chave, coluna_valor])

    resultado = pd.concat(partes, ignore_index=True)
    logger.info("desdobrar '%s': %d linha(s) geradas", nome, len(resultado))
    return resultado


def _aplicar_descartar(df: pd.DataFrame, colunas: list[str], nome: str) -> pd.DataFrame:
    presentes = [c for c in colunas if c in df.columns]
    ausentes = set(colunas) - set(presentes)
    if ausentes:
        logger.warning("descartar: coluna(s) ausente(s) em '%s': %s", nome, ausentes)
    return df.drop(columns=presentes)


def _aplicar_derivadas(df: pd.DataFrame, regras: dict, nome: str) -> pd.DataFrame:
    """
    Schema esperado:
        derivadas:
          siafi_uo:
            funcao: montar_siafi_uo
            args: [nr_siafi, cd_uo]
    """
    for destino, spec in regras.items():
        funcao = FUNCOES_DERIVADAS.get(spec["funcao"])
        if funcao is None:
            raise ValueError(f"Função derivada desconhecida: {spec['funcao']!r}")
        args_nomes = spec.get("args", [])
        faltando = [a for a in args_nomes if a not in df.columns]
        if faltando:
            raise ValueError(
                f"derivadas: coluna(s) ausente(s) para '{destino}' em '{nome}': {faltando}"
            )
        args = [df[a] for a in args_nomes]
        df[destino] = funcao(*args, destino)
    return df


def _marcar_linhas_se_nulo(df: pd.DataFrame, colunas: list[str], alertas: pd.Series, nome: str) -> None:
    """
    Marca (não remove) as linhas com "" numa das colunas BRUTAS listadas,
    tratando "" como nulo — nesse ponto do pipeline nada foi convertido ainda,
    então um bronze com keep_default_na=False só tem string, nunca NaN de
    verdade. Roda antes da tipagem porque existe pra identificar blocos
    desalinhados do relatório do BO (ex.: tabela 07): a linha continua na
    tabela, com `ds_alerta_linha` preenchido e o texto original em
    `tx_linha_bruta`, e a tipagem não quebra nela.
    """
    presentes = [c for c in colunas if c in df.columns]
    ausentes = set(colunas) - set(presentes)
    if ausentes:
        logger.warning("marcar_linhas_se_nulo: coluna(s) ausente(s) em '%s': %s", nome, ausentes)
    for coluna in presentes:
        vazio = df[coluna].str.strip().eq("")
        if vazio.any():
            logger.info(
                "Linhas marcadas por nulo em '%s' ('%s'): %d", coluna, nome, int(vazio.sum())
            )
        _marcar(alertas, vazio, f"chave_obrigatoria_vazia:{coluna}")


def _verificar_grao(df: pd.DataFrame, colunas: list[str], nome: str) -> None:
    presentes = [c for c in colunas if c in df.columns]
    ausentes = set(colunas) - set(presentes)
    if ausentes:
        logger.warning("grao: coluna(s) ausente(s) em '%s': %s", nome, ausentes)
        return
    if not presentes:
        return
    sem_nulo = df.dropna(subset=presentes)
    duplicadas = sem_nulo.duplicated(subset=presentes, keep=False)
    n_duplicadas = int(duplicadas.sum())
    if n_duplicadas:
        logger.warning(
            "ALERTA grão %s em '%s': %d linha(s) com chave repetida (de %d não-nulas)",
            presentes,
            nome,
            n_duplicadas,
            len(sem_nulo),
        )
    else:
        logger.info("grão %s em '%s': único (%d linhas não-nulas)", presentes, nome, len(sem_nulo))


def _mascara_quarentena(df: pd.DataFrame, regra: dict | None, nome: str) -> pd.Series | None:
    """
    Identifica as linhas cujo grão se repete com destino divergente (ex.:
    tabela 16 — depara_siafi: SIAFI de origem repetido apontando para destinos
    diferentes). Não remove nada: devolve a máscara, e o chamador MARCA essas
    linhas e devolve uma cópia delas em `transformar_fonte_completo`.

    Schema esperado:
        quarentena:
          grao: [siafi_uo_origem]
          destino: [siafi_uo_atual]

    Todas as linhas da chave divergente são marcadas — inclusive as que
    apontam para o destino "certo" —, porque não há como saber qual vale.
    Linhas com o mesmo grão e o MESMO destino não são divergentes.
    """
    if not regra:
        return None

    grao = regra["grao"]
    destino = regra["destino"]
    faltando = [c for c in (*grao, *destino) if c not in df.columns]
    if faltando:
        logger.warning("quarentena: coluna(s) ausente(s) em '%s': %s", nome, faltando)
        return None

    contagem = df.dropna(subset=grao).groupby(grao)[destino].nunique()
    diverge = (contagem > 1).any(axis=1) if len(destino) > 1 else (contagem[destino[0]] > 1)
    divergentes = contagem.index[diverge]

    if len(grao) > 1:
        chave_df = pd.MultiIndex.from_frame(df[grao])
    else:
        chave_df = df[grao[0]]
    mascara = pd.Series(chave_df.isin(divergentes), index=df.index)

    if mascara.any():
        logger.warning(
            "quarentena '%s': %d linha(s) com grão %s divergente em %s, marcadas",
            nome,
            int(mascara.sum()),
            grao,
            destino,
        )
    return mascara


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


def _transformar(nome: str, bronze_path: Path | None = None) -> dict:
    """
    Faz todo o trabalho de transformar_fonte e devolve os três resultados
    possíveis num dict: {"principal": DataFrame, "quarentena": DataFrame|None,
    "desdobrado": DataFrame|None}. transformar_fonte (contrato público,
    estável) só expõe "principal" — quem precisa dos outros dois usa esta
    função ou transformar_fonte_completo.
    """
    schema = _carregar_schema(nome)
    colunas: dict[str, list[str]] = schema.get("colunas", {})

    cols_data = colunas.get("data", [])
    cols_data_hora = colunas.get("data_hora", [])
    cols_valor = colunas.get("valor", [])
    cols_inteiro = colunas.get("inteiro", [])
    cols_id = colunas.get("identificador", [])
    sentinelas: dict[str, list[str]] = schema.get("sentinelas", {})

    if "descartar_linhas_se_nulo" in schema:
        raise ValueError(
            f"'{nome}': o bloco 'descartar_linhas_se_nulo' não existe mais — o motor "
            "não exclui linhas com dado. Use 'marcar_linhas_se_nulo' (a linha fica, "
            "marcada em ds_alerta_linha)."
        )
    # Só as tabelas que declaram marcação ganham ds_alerta_linha/tx_linha_bruta
    # (o schema do GRP não muda).
    marcacao_ativa = bool(schema.get("marcar_linhas_se_nulo") or schema.get("quarentena"))

    caminho = bronze_path if bronze_path is not None else _bronze_mais_recente(nome)
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False)

    n_bruto = len(df)
    df = _remover_linhas_vazias(df, nome)  # antes de tirar as colunas Unnamed

    n_original = len(df.columns)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = [normalizar_coluna(c) for c in df.columns]

    logger.info(
        "Silver '%s': %d → %d colunas, %d → %d linhas",
        nome,
        n_original,
        len(df.columns),
        n_bruto,
        len(df),
    )

    # --- marcação de linhas (nomes BRUTOS, antes da tipagem; nenhuma sai) ---
    alertas = pd.Series([None] * len(df), index=df.index, dtype="object")
    linha_bruta = None
    if marcacao_ativa:
        linha_bruta = pd.Series(
            [json.dumps(r, ensure_ascii=False) for r in df.to_dict("records")], index=df.index
        )

    cabecalho = _mascara_repetem_cabecalho(df)
    if cabecalho.any():
        if marcacao_ativa:
            _marcar(alertas, cabecalho, "cabecalho_repetido")
        else:
            logger.warning(
                "ALERTA '%s': %d linha(s) repetem o cabeçalho e foram mantidas "
                "(a tabela não declara marcação)",
                nome,
                int(cabecalho.sum()),
            )
    if schema.get("marcar_linhas_se_nulo"):
        _marcar_linhas_se_nulo(df, schema["marcar_linhas_se_nulo"], alertas, nome)
    marcadas = alertas.notna()  # a tipagem tolera valores ruins nestas linhas

    # --- datas (só data, sem hora: datetime vindo do Excel passa direto,
    # mas a parte de hora é zerada — "data" guarda só a data) ---
    logger.info("Datas:")
    for col in cols_data:
        if col not in df.columns:
            logger.warning("  Coluna data '%s' ausente no Bronze de '%s'", col, nome)
            continue
        convertida = _converter_datas(df[col]).dt.normalize()
        logger.info("  %-45s  NaT: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- data_hora (mantém a hora, quando houver) ---
    logger.info("Datas com hora:")
    for col in cols_data_hora:
        if col not in df.columns:
            logger.warning("  Coluna data_hora '%s' ausente no Bronze de '%s'", col, nome)
            continue
        convertida = _converter_datas(df[col])
        logger.info("  %-45s  NaT: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- valores monetários ---
    logger.info("Valores:")
    for col in cols_valor:
        if col not in df.columns:
            logger.warning("  Coluna valor '%s' ausente no Bronze de '%s'", col, nome)
            continue
        # float64 explícito: to_numeric devolve int64 numa série vazia (ou só de
        # inteiros), e o tipo da coluna não pode depender do conteúdo.
        convertida = pd.to_numeric(df[col].map(_para_numero), errors="coerce").astype("float64")
        logger.info("  %-45s  NaN: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- inteiros (ano, mês, parcela, duração) ---
    # errors="raise" é proposital: valor não numérico deve quebrar, nunca virar
    # nulo em silêncio. Sentinelas viram nulo antes, senão "-3" passaria como número.
    logger.info("Inteiros:")
    for col in cols_inteiro:
        if col not in df.columns:
            logger.warning("  Coluna inteiro '%s' ausente no Bronze de '%s'", col, nome)
            continue
        aparada = df[col].str.strip()
        limpa = aparada.where(~aparada.isin(valores_sentinela(col, sentinelas)))
        # Em colunas inteiras, "1.827" é milhar (1827), não decimal: o export do
        # GRP usa ponto como separador de milhares. Só remove os pontos quando o
        # valor casa exatamente com o padrão de milhar. Outros formatos seguem
        # direto: "2020.0" vira 2020 e "1.5" quebra no astype("Int64").
        milhar = limpa.str.fullmatch(r"\d{1,3}(\.\d{3})+", na=False)
        limpa = limpa.where(~milhar, limpa.str.replace(".", "", regex=False))
        if marcadas.any():
            # Linha marcada não quebra a tipagem: o que não converte vira nulo
            # (o texto original está em tx_linha_bruta). Linha não marcada
            # mantém errors="raise".
            normais = pd.to_numeric(limpa.where(~marcadas), errors="raise")
            ruins = pd.to_numeric(limpa.where(marcadas), errors="coerce")
            convertida = normais.fillna(ruins).astype("Int64")
        else:
            convertida = pd.to_numeric(limpa, errors="raise").astype("Int64")
        logger.info("  %-45s  <NA>: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- identificadores ---
    logger.info("Identificadores:")
    for col in cols_id:
        if col not in df.columns:
            logger.warning("  Coluna id '%s' ausente no Bronze de '%s'", col, nome)
            continue
        convertida = df[col].str.strip().apply(_limpar_id).astype("string")
        for valor in valores_sentinela(col, sentinelas):
            alvo = convertida == valor
            n_anulados = int(alvo.sum())
            if n_anulados:
                logger.info("  %-45s  anulados %r: %d", col, valor, n_anulados)
            convertida = convertida.mask(alvo)
        logger.info("  %-45s  <NA>: %d", col, convertida.isna().sum())
        df[col] = convertida

    # --- texto: todas as colunas não tipadas acima ---
    cols_tipadas = set(cols_data) | set(cols_data_hora) | set(cols_valor) | set(cols_inteiro) | set(cols_id)
    for col in df.columns:
        if col not in cols_tipadas:
            limpa = df[col].str.strip()
            limpa = limpa.where(~limpa.isin(valores_sentinela(col, sentinelas)))
            df[col] = limpa.astype("string")

    # --- renomeação para os nomes finais (bloco "renomear" do YAML) ---
    mapa = {
        normalizar_coluna(original): final
        for original, final in schema.get("renomear", {}).items()
    }
    faltando = set(mapa) - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas do 'renomear' que não existem na fonte: {faltando}")
    df = df.rename(columns=mapa)

    # --- desdobrar (gera a saída longa antes de descartar as colunas-fonte) ---
    desdobrado = _aplicar_desdobrar(df, schema.get("desdobrar"), nome)

    # --- descartar colunas (nomes finais) ---
    if schema.get("descartar"):
        df = _aplicar_descartar(df, schema["descartar"], nome)

    if mapa:  # só fontes com bloco 'renomear' (as novas)
        df = limpar_colunas_padronizadas(
            df, booleanos=schema.get("booleanos"), ignorar=marcadas if marcadas.any() else None
        )

    # --- derivadas (colunas calculadas por função registrada) ---
    if schema.get("derivadas"):
        df = _aplicar_derivadas(df, schema["derivadas"], nome)

    # Nenhuma linha sai a partir daqui. Duplicatas 100% idênticas ficam todas:
    # só o ALERTA com a contagem (hoje depara_siafi e depara_parlamentar).
    idem = int(df.duplicated().sum())
    if idem:
        logger.warning("ALERTA '%s': %d linha(s) 100%% idênticas a outra, mantidas", nome, idem)

    mascara_q = _mascara_quarentena(df, schema.get("quarentena"), nome)
    if mascara_q is not None:
        _marcar(alertas, mascara_q, "quarentena:grao_divergente")

    if marcacao_ativa:
        assert df.index.equals(alertas.index), "índice mudou: linha perdida ou reordenada"
        df["ds_alerta_linha"] = alertas.astype("string")
        df["tx_linha_bruta"] = linha_bruta.where(alertas.notna()).astype("string")

    quarentena = None
    if mascara_q is not None and mascara_q.any():
        quarentena = df.loc[mascara_q].reset_index(drop=True)

    if schema.get("grao"):
        _verificar_grao(df, schema["grao"], nome)

    _validar(df, nome)
    return {"principal": df, "quarentena": quarentena, "desdobrado": desdobrado}


def transformar_fonte(nome: str, bronze_path: Path | None = None) -> pd.DataFrame:
    """
    Lê o Bronze de <nome>, aplica tipagem via schema YAML e executa validação.
    Não grava nenhum arquivo. Contrato estável: sempre devolve só a tabela
    principal — quem precisa de quarentena/desdobramento usa
    transformar_fonte_completo.

    Parâmetros
    ----------
    nome        : chave da fonte em FONTES (ex: "sigcon_convenio")
    bronze_path : caminho explícito para o CSV Bronze; se None, usa o mais
                  recente em DATA_DIR/bronze/<nome>/

    Retorna
    -------
    pd.DataFrame com tipos convertidos conforme o schema
    """
    return _transformar(nome, bronze_path)["principal"]


def transformar_fonte_completo(nome: str, bronze_path: Path | None = None) -> dict:
    """
    Como transformar_fonte, mas devolve os três resultados possíveis:
    {"principal": DataFrame, "quarentena": DataFrame|None, "desdobrado": DataFrame|None}.
    "quarentena" e "desdobrado" só vêm preenchidos quando o schema declara,
    respectivamente, 'quarentena:' e 'desdobrar:' — caso contrário, None.
    """
    return _transformar(nome, bronze_path)


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
