"""
Ponto central de verdade para filtros, chaves e preparação dos dados
de relacionamento SIGCON↔SICONV.

Responsabilidades:
  - UOS_EXCLUIR     : frozenset de UOs não-operacionais a ignorar
  - marcar_uo_excluida : marca (NÃO remove) as linhas cuja UO está em UOS_EXCLUIR
  - montar_siafi_uo : constrói a chave composta SIAFI+UO (sem separador)
  - resolver_siafi_atual : de-para SIAFI_UO antigo → SIAFI_UO atual via depara_siafi
  - aplicar_deparas : aplica todos os mapeamentos de R1 (situação, tipo, UO nome, sigla)
  - aplicar_correcoes : aplica a tabela de exceções data-driven com log

Nota sobre UOS_EXCLUIR:
  Lista definida pela equipe DCGCE — equivalente ao `not match(...)` do QlikView.
  Inclui UOs de encargos gerais, transferências intragovernamentais e fundos
  que não representam convênios operacionais do Estado.
  Fonte: QlikView script lines 1627, 1785, 1825 (três pontos de aplicação idênticos).

Nota sobre zeros à esquerda e a chave SIAFI_UO:
  Os campos siafi e uo chegam como strings (Silver usa StringDtype nullable e _limpar_id
  remove o artefato ".0" mas preserva zeros). A concatenação deve ser feita SEMPRE com
  strings, nunca convertendo para int — ex.: uo="01261" e siafi="9309074" produz
  "930907401261", diferente de uo="1261" → "93090741261". O Silver garante que os
  valores já chegam como strings e sem espaços laterais, mas aplicamos strip() de
  segurança. Se qualquer dos dois for NA, a chave resultante fica NA.
"""

from __future__ import annotations

import logging

import pandas as pd

from core.transform.referencias import (
    situacoes_padronizadas,
    tipos_siafi,
    uo_nomes,
    uo_siglas,
    uo_descricoes,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Filtro de UOs não-operacionais
# ---------------------------------------------------------------------------

UOS_EXCLUIR: frozenset[str] = frozenset({
    "5131",  # FUNDO ESPECIAL DE CREDITOS INADIMPLIDOS E DIVIDA ATIVA
    "9801",  # RESERVA DE CONTINGENCIA (conta contábil genérica)
    "4611",  # FUNDO DE GARANTIAS DE PARCERIAS PUBLICO-PRIVADAS
    "4441",  # FUNDO DE PREVIDENCIA DO ESTADO DE MINAS GERAIS
    "4451",  # FUNDO FINANCEIRO DE PREVIDENCIA
    "2361",  # AGENCIA REGULADORA DE ABASTECIMENTO DE AGUA E ESGOTO
    "4121",  # FUNDO DE PREVIDENCIA - exclusão por encargo previdenciário
    "1041",  # encargo geral
    "1031",  # encargo geral
    "1051",  # encargo geral
    "4031",  # encargo geral
})


def marcar_uo_excluida(df: pd.DataFrame, coluna_uo: str = "unidade_orcamentaria_codigo") -> pd.Series:
    """
    Máscara (bool) das linhas cujo código de UO pertence a UOS_EXCLUIR.

    NÃO remove nenhuma linha: regra do dono dos dados, nenhuma linha com dado é
    excluída. O chamador grava a máscara em `fl_uo_excluida` e quem não quer
    essas UOs numa tela filtra na consulta. (O QlikView as removia com
    `not match(UO, '5131', ...)`.)
    """
    if coluna_uo not in df.columns:
        raise KeyError(
            f"Coluna '{coluna_uo}' não encontrada. Disponíveis: {list(df.columns)}"
        )
    mascara = df[coluna_uo].astype(str).str.strip().isin(UOS_EXCLUIR)
    n_marcadas = int(mascara.sum())
    if n_marcadas:
        logger.info(
            "marcar_uo_excluida: %d linha(s) com UO em UOS_EXCLUIR (marcadas, mantidas)", n_marcadas
        )
    return mascara


# ---------------------------------------------------------------------------
# Construção da chave SIAFI_UO
# ---------------------------------------------------------------------------

def montar_siafi_uo(
    siafi: pd.Series,
    uo: pd.Series,
    coluna_resultado: str = "siafi_uo",
) -> pd.Series:
    """
    Monta a chave composta SIAFI_UO = siafi + uo (concatenação direta, sem separador).

    Regras:
      - Ambos os lados recebem strip() antes de concatenar.
      - Se qualquer dos dois for NA/None/vazio, o resultado é pd.NA.
        Motivo: uma chave parcialmente nula causaria match espúrio em joins.
      - Zeros à esquerda são preservados (ex.: uo="01261" fica "01261").
        NUNCA converter para int — o tipo define o resultado do join.

    Exemplos:
      siafi="9309074", uo="1261"  → "93090741261"
      siafi="9309074", uo=None   → pd.NA
      siafi=None,      uo="1261" → pd.NA

    Parameters
    ----------
    siafi : Series com o número sequencial SIAFI (string nullable)
    uo    : Series com o código UO (string nullable)
    coluna_resultado : nome da Series resultante (para rastreabilidade)
    """
    s = siafi.astype(str).str.strip()
    u = uo.astype(str).str.strip()

    # Marca como NA onde o valor original era NA ou string vazia
    siafi_nulo = siafi.isna() | (s == "") | (s.str.lower() == "none") | (s.str.lower() == "<na>")
    uo_nulo = uo.isna() | (u == "") | (u.str.lower() == "none") | (u.str.lower() == "<na>")

    resultado = s + u
    resultado = resultado.where(~(siafi_nulo | uo_nulo), other=pd.NA)
    return resultado.rename(coluna_resultado).astype("string")


# ---------------------------------------------------------------------------
# De-para SIAFI_UO antigo → atual
# ---------------------------------------------------------------------------

def resolver_siafi_atual(
    df_chaves: pd.DataFrame,
    df_depara: pd.DataFrame,
    coluna_siafi_uo: str = "siafi_uo",
) -> pd.DataFrame:
    """
    Enriquece df_chaves com as colunas siafi_uo_atual, siafiatual e uo_atual.

    `df_depara` é o Silver `depara_siafi` (ex-SIAFI2.csv), que representa a
    cadeia de substituições de números SIAFI ao longo do tempo. A chave de
    look-up é `siafi_uo_origem` (SIAFI2+UO2) e o resultado é `siafi_uo_atual`
    (SIAFI atual + UO atual) — ambos já montados no YAML da fonte. A lógica do
    QlikView (linha 2830) é a mesma.

    Se um convênio não tiver correspondência (LEFT JOIN → NaN), o siafi_uo_atual
    fica igual ao siafi_uo original. Isso é o comportamento correto: sem
    substituição conhecida, o "atual" é o próprio valor.

    A tabela `depara_siafi` mantém TODAS as linhas do arquivo de origem. Aqui,
    só na consulta, usamos um subconjunto de look-up:
      - linhas marcadas em `ds_alerta_linha` (quarentena: a chave de origem
        aponta para destinos diferentes) são ignoradas, porque não há como saber
        qual destino vale — essas chaves caem no fallback;
      - chave de origem nula não entra (o pandas casaria nulo com nulo);
      - a mesma origem repetida com o MESMO destino colapsa numa linha (a
        origem é uma chave de look-up; as colunas redundantes SIAFI1/UO1 é que
        faziam as linhas diferirem). Origem repetida com destinos DIFERENTES que
        não esteja marcada gera ALERTA.

    Parameters
    ----------
    df_chaves : DataFrame com coluna siafi_uo já montada
    df_depara : Silver depara_siafi (colunas: siafi_uo_origem, siafi_uo_atual,
                nr_siafi_atual, cd_uo_atual; opcional: ds_alerta_linha)
    coluna_siafi_uo : nome da coluna de chave em df_chaves

    Returns
    -------
    df_chaves enriquecido com:
      siafi_uo_atual  — chave atual; fallback = siafi_uo original
      siafiatual      — número SIAFI atual
      uo_atual        — código UO atual
    """
    colunas_necessarias = {"siafi_uo_origem", "siafi_uo_atual", "nr_siafi_atual", "cd_uo_atual"}
    ausentes = colunas_necessarias - set(df_depara.columns)
    if ausentes:
        raise KeyError(f"depara_siafi Silver está faltando colunas: {ausentes}")

    dim = df_depara
    if "ds_alerta_linha" in dim.columns:
        n_quarentena = int(dim["ds_alerta_linha"].notna().sum())
        if n_quarentena:
            logger.warning(
                "resolver_siafi_atual: %d linha(s) do depara_siafi em quarentena ignoradas "
                "na consulta (as chaves delas usam o próprio siafi_uo como atual)",
                n_quarentena,
            )
        dim = dim[dim["ds_alerta_linha"].isna()]
    dim = dim[["siafi_uo_origem", "siafi_uo_atual", "nr_siafi_atual", "cd_uo_atual"]].dropna(
        subset=["siafi_uo_origem"]
    )

    destinos_distintos = dim.groupby("siafi_uo_origem")["siafi_uo_atual"].nunique(dropna=False)
    n_ambiguas = int((destinos_distintos > 1).sum())
    if n_ambiguas:
        logger.warning(
            "ALERTA resolver_siafi_atual: %d chave(s) de origem com mais de um destino "
            "fora da quarentena; vale a primeira linha",
            n_ambiguas,
        )

    n_antes = len(dim)
    dim = dim.drop_duplicates(subset=["siafi_uo_origem"])
    if len(dim) < n_antes:
        logger.info(
            "resolver_siafi_atual: %d linhas repetidas da dimensão colapsadas na consulta",
            n_antes - len(dim),
        )

    dim = dim.rename(columns={
        "siafi_uo_origem": "_origem_depara",
        "nr_siafi_atual": "siafiatual",
        "cd_uo_atual": "uo_atual",
    })

    antes = len(df_chaves)
    resultado = df_chaves.merge(
        dim,
        left_on=coluna_siafi_uo,
        right_on="_origem_depara",
        how="left",
    ).drop(columns=["_origem_depara"])
    assert len(resultado) == antes, "resolver_siafi_atual: o join mudou o número de linhas"

    # Fallback: sem match no depara → atual = original
    sem_match = resultado["siafi_uo_atual"].isna()
    resultado.loc[sem_match, "siafi_uo_atual"] = resultado.loc[sem_match, coluna_siafi_uo]
    n_sem_match = int(sem_match.sum())
    if n_sem_match:
        logger.info(
            "resolver_siafi_atual: %d convênios sem correspondência no depara_siafi "
            "(siafi_uo_atual = siafi_uo original)", n_sem_match,
        )

    return resultado


# ---------------------------------------------------------------------------
# Aplicação de de-paras (padronização)
# ---------------------------------------------------------------------------

def aplicar_deparas(df: pd.DataFrame, obrigatorias: tuple[str, ...] = ()) -> pd.DataFrame:
    """
    Aplica os de-paras de R1 a um DataFrame que contenha colunas pertinentes.

    Regra: nunca sobrescreve originais — cria colunas novas com sufixo _std.
    Colunas de origem e suas novas versões padronizadas:

      situacao                  → situacao_std       (Mapa2)
      plano_trabalho_tipo_siafi → instrumento_chaves (Map_Tipo_SIAFI)
      unidade_orcamentaria_codigo → uo_nome_std      (MapaG_UO)
      uo_nome_std               → uo_sigla_std       (Mapa5, aplicado após uo_nome_std)
      uo_nome_std               → uo_descricao_std   (Mapa4, aplicado após uo_nome_std)

    As colunas listadas em `obrigatorias` têm de existir (KeyError explícito — o
    de-para sumir em silêncio por causa de um nome de coluna errado foi o que
    deixou campos do Gold vazios sem aviso). As demais são opcionais e, se
    ausentes, o de-para correspondente é pulado.
    """
    faltando = [c for c in obrigatorias if c not in df.columns]
    if faltando:
        raise KeyError(f"aplicar_deparas: coluna(s) obrigatória(s) ausente(s): {faltando}")
    df = df.copy()

    if "situacao" in df.columns:
        mapa = situacoes_padronizadas()
        df["situacao_std"] = df["situacao"].map(mapa).fillna(df["situacao"]).astype("string")

    if "plano_trabalho_tipo_siafi" in df.columns:
        mapa = tipos_siafi()
        df["instrumento_chaves"] = (
            df["plano_trabalho_tipo_siafi"].map(mapa)
            .fillna(df["plano_trabalho_tipo_siafi"])
            .astype("string")
        )

    if "unidade_orcamentaria_codigo" in df.columns:
        mapa_nomes = uo_nomes()
        df["uo_nome_std"] = (
            df["unidade_orcamentaria_codigo"].map(mapa_nomes)
            .fillna(df["unidade_orcamentaria_codigo"])
            .astype("string")
        )
        mapa_siglas = uo_siglas()
        df["uo_sigla_std"] = (
            df["uo_nome_std"].map(mapa_siglas)
            .fillna(pd.NA)
            .astype("string")
        )
        mapa_desc = uo_descricoes()
        df["uo_descricao_std"] = (
            df["uo_nome_std"].map(mapa_desc)
            .fillna(pd.NA)
            .astype("string")
        )

    return df


# ---------------------------------------------------------------------------
# Aplicação de correções data-driven
# ---------------------------------------------------------------------------

def aplicar_correcoes(
    df: pd.DataFrame,
    nome_tabela: str,
) -> pd.DataFrame:
    """
    Aplica as correções da tabela core/referencia/correcoes.csv ao DataFrame.

    Cada correção é localizada por (campo_chave == valor_chave) e o campo
    campo_corrigido é substituído de valor_errado para valor_correto.

    Toda substituição efetiva é logada em WARNING para rastreabilidade.

    Parameters
    ----------
    df           : DataFrame Silver da tabela de origem
    nome_tabela  : nome da tabela conforme coluna 'tabela' em correcoes.csv
                   (ex.: "sigcon_convenio")

    Returns
    -------
    Cópia do df com correções aplicadas.
    """
    from core.transform.referencias import correcoes as _correcoes

    df = df.copy()
    tab_correcoes = _correcoes()
    filtro = tab_correcoes["tabela"] == nome_tabela
    minhas = tab_correcoes.loc[filtro]

    if minhas.empty:
        return df

    for _, linha in minhas.iterrows():
        campo_chave = linha["campo_chave"]
        valor_chave = linha["valor_chave"]
        campo_corr = linha["campo_corrigido"]
        valor_errado = linha["valor_errado"]
        valor_correto = linha["valor_correto"]
        motivo = linha["motivo"]
        qv_linha = linha["qlikview_linha"]

        if campo_chave not in df.columns or campo_corr not in df.columns:
            logger.warning(
                "Correção ignorada (coluna ausente): tabela=%s campo_chave=%s campo_corrigido=%s",
                nome_tabela, campo_chave, campo_corr,
            )
            continue

        # Localiza linhas candidatas pela chave
        mascara_chave = df[campo_chave].astype(str).str.strip() == str(valor_chave).strip()

        # Aplica apenas onde o campo a corrigir ainda tem o valor errado esperado
        # (idempotência: rodar N vezes não aplica a mesma correção duas vezes)
        if str(valor_errado).strip():
            mascara_valor = df[campo_corr].astype(str).str.strip() == str(valor_errado).strip()
            mascara = mascara_chave & mascara_valor
        else:
            # valor_errado vazio = a correção se aplica sempre que a chave bater
            mascara = mascara_chave

        n = int(mascara.sum())
        if n > 0:
            df.loc[mascara, campo_corr] = valor_correto
            logger.warning(
                "CORREÇÃO APLICADA [QlikView linha %s] tabela=%s | %s=%s | %s: %r → %r | "
                "registros=%d | motivo: %s",
                qv_linha, nome_tabela, campo_chave, valor_chave,
                campo_corr, valor_errado, valor_correto, n, motivo,
            )
        else:
            logger.debug(
                "Correção sem match [QlikView linha %s]: %s=%s/%s=%r",
                qv_linha, campo_chave, valor_chave, campo_corr, valor_errado,
            )

    return df
