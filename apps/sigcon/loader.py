"""
Loaders full-refresh para os models da app sigcon.

Cada função:
  1. Lê o Parquet Silver da fonte via pd.read_parquet
  2. Apaga todos os registros existentes no model
  3. Reconstrói via bulk_create(batch_size=500)
  4. Retorna dict com 'apagados' e 'inseridos'

Os passos 2 e 3 rodam sempre dentro de uma mesma transação (core.db.bulk_refresh):
ou a tabela inteira é substituída, ou nada muda.

Os models Sigcon* (apps/sigcon/models.py) têm os campos IGUAIS às colunas da
Silver (bloco "renomear" do YAML em core/transform/schemas/). Por isso a carga é
genérica: `_carregar_silver` converte cada coluna pelo tipo do campo do model,
sem de-para escrito à mão. Uma coluna da Silver sem campo correspondente é
ignorada; um campo sem coluna fica nulo.

REGRA: nenhuma linha da Silver é perdida na carga (linhas do model = linhas do
Parquet de origem). As linhas marcadas pelo motor (ds_alerta_linha) vão para o
banco marcadas e as consultas as filtram.

Tabelas do Gold/externas (ConvenioIntegrado, ControleSEI) não fazem parte do
modelo SIGCON v1.0 e não têm model atual: `carregar_tabela_integrada` e
`carregar_controle_sei` ficam no fim do arquivo, à espera dessas ondas.
"""
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db import models as dj_models
from django.utils import timezone

from core.db import bulk_refresh as _bulk_refresh

from .models import (
    SigconChaveConvenio,
    SigconChaveDeclaracao,
    SigconChavePlanoTrabalho,
    SigconChaveTermoAditivo,
    SigconConcedente,
    SigconConvenio,
    SigconConvenioGeral,
    SigconCronogramaDesembolso,
    SigconDeclaracaoContrapartida,
    SigconNtEmenda,
    SigconPlanoAplicacao,
    SigconPlanoTrabalho,
    SigconProrrogacaoOficio,
    SigconTermoAditivo,
    SigconUnidadeExecutora,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------

def _silver_path(nome_fonte: str) -> Path:
    return Path(settings.DATA_DIR) / "silver" / f"{nome_fonte}.parquet"


def _eh_nulo(val) -> bool:
    try:
        return bool(pd.isna(val))
    except (TypeError, ValueError):
        return False


def _para_date(val):
    """pd.Timestamp → datetime.date; NaT/None/NA → None."""
    if _eh_nulo(val):
        return None
    if hasattr(val, "date"):
        return val.date()
    return None


def _para_datetime(val):
    """pd.Timestamp → datetime (aware, no fuso do projeto); NaT/None/NA → None."""
    if _eh_nulo(val):
        return None
    if isinstance(val, pd.Timestamp):
        val = val.to_pydatetime()
    if not isinstance(val, datetime):
        return None
    if settings.USE_TZ and timezone.is_naive(val):
        val = timezone.make_aware(val)
    return val


def _para_decimal(val):
    """float → Decimal via str(); NaN/NA → None."""
    if _eh_nulo(val):
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _para_str(val):
    """StringDtype <NA> / NaN / vazio → None; caso contrário, strip e retorna str."""
    if _eh_nulo(val):
        return None
    s = str(val).strip()
    return s or None


def _para_bool(val):
    """boolean nullable da Silver → bool; nulo → None."""
    if _eh_nulo(val):
        return None
    return bool(val)


def _para_int(val) -> int | None:
    """pandas Int64 / float / None → int ou None."""
    if _eh_nulo(val):
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _str_para_date(val):
    """String ISO / pd.Timestamp / NaT → datetime.date; erro ou NA → None."""
    if _eh_nulo(val):
        return None
    ts = pd.to_datetime(val, errors="coerce")
    if ts is pd.NaT or pd.isna(ts):
        return None
    return ts.date()


def _ler_parquet(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Parquet Silver não encontrado: {caminho}\n"
            "Rode antes: python manage.py rodar_silver <fonte>"
        )
    df = pd.read_parquet(caminho)
    logger.info("Parquet lido: %s (%d linhas × %d colunas)", caminho.name, *df.shape)
    return df


def _conversor(campo):
    """Função de conversão valor-da-Silver → valor-do-model, pelo tipo do campo."""
    # DateTimeField herda de DateField: testar o mais específico primeiro.
    if isinstance(campo, dj_models.DateTimeField):
        return _para_datetime
    if isinstance(campo, dj_models.DateField):
        return _para_date
    if isinstance(campo, dj_models.DecimalField):
        return _para_decimal
    if isinstance(campo, dj_models.BooleanField):
        return _para_bool
    if isinstance(campo, dj_models.IntegerField):
        return _para_int
    return _para_str


def _carregar_silver(model, fonte: str, silver_path: Path | None = None) -> dict:
    """
    Full refresh genérico: Silver `fonte` → `model`, coluna a coluna pelo nome.

    Uma linha do model por linha da Silver (nada é descartado).
    """
    df = _ler_parquet(silver_path or _silver_path(fonte))

    campos = [c for c in model._meta.concrete_fields if not c.primary_key]
    colunas = []
    for campo in campos:
        if campo.name in df.columns:
            colunas.append((campo.name, _conversor(campo), df[campo.name].tolist()))
        else:
            logger.warning("%s: coluna '%s' ausente na Silver %s — fica nula", model.__name__, campo.name, fonte)

    objetos = [
        model(**{nome: conv(valores[i]) for nome, conv, valores in colunas})
        for i in range(len(df))
    ]
    return _bulk_refresh(model, objetos)


# ---------------------------------------------------------------------------
# Loaders — um por model (os nomes são os usados por carregar_fonte e pelos comandos)
# ---------------------------------------------------------------------------

def carregar_convenios(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_convenio.parquet → SigconConvenio."""
    return _carregar_silver(SigconConvenio, "sigcon_convenio", silver_path)


def carregar_convenio_geral(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_convenio_geral.parquet → SigconConvenioGeral."""
    return _carregar_silver(SigconConvenioGeral, "sigcon_convenio_geral", silver_path)


def carregar_plano_trabalho(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_plano_trabalho.parquet → SigconPlanoTrabalho."""
    return _carregar_silver(SigconPlanoTrabalho, "sigcon_plano_trabalho", silver_path)


def carregar_cronograma_desembolso(silver_path: Path | None = None) -> dict:
    """
    Fonte: sigcon_cronograma_desembolso.parquet → SigconCronogramaDesembolso.

    TODAS as linhas entram, inclusive as marcadas pelo motor (bloco desalinhado
    do relatório do BO, sem plano de trabalho): o motivo vai para
    `ds_alerta_linha` e as telas filtram `ds_alerta_linha__isnull=True`.
    """
    return _carregar_silver(SigconCronogramaDesembolso, "sigcon_cronograma_desembolso", silver_path)


def carregar_plano_aplicacao(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_plano_aplicacao.parquet → SigconPlanoAplicacao."""
    return _carregar_silver(SigconPlanoAplicacao, "sigcon_plano_aplicacao", silver_path)


def carregar_termo_aditivo(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_termo_aditivo.parquet → SigconTermoAditivo."""
    return _carregar_silver(SigconTermoAditivo, "sigcon_termo_aditivo", silver_path)


def carregar_declaracao_contrapartida(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_declaracao_contrapartida.parquet → SigconDeclaracaoContrapartida."""
    return _carregar_silver(SigconDeclaracaoContrapartida, "sigcon_declaracao_contrapartida", silver_path)


def carregar_prorrogacao_oficio(silver_path: Path | None = None) -> dict:
    """
    Fonte: sigcon_prorrogacao_oficio.parquet → SigconProrrogacaoOficio.

    cd_convenio_sequencial é o código SEQUENCIAL do convênio, não o número
    legível: liga-se a sigcon_chave_convenio.
    """
    return _carregar_silver(SigconProrrogacaoOficio, "sigcon_prorrogacao_oficio", silver_path)


def carregar_nt_emenda(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_nt_emenda.parquet → SigconNtEmenda."""
    return _carregar_silver(SigconNtEmenda, "sigcon_nt_emenda", silver_path)


def carregar_esfera(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_concedente.parquet → SigconConcedente."""
    return _carregar_silver(SigconConcedente, "sigcon_concedente", silver_path)


def carregar_codigo_convenio(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_convenio.parquet → SigconChaveConvenio."""
    return _carregar_silver(SigconChaveConvenio, "sigcon_chave_convenio", silver_path)


def carregar_codigo_plano_trabalho(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_plano_trabalho.parquet → SigconChavePlanoTrabalho."""
    return _carregar_silver(SigconChavePlanoTrabalho, "sigcon_chave_plano_trabalho", silver_path)


def carregar_codigo_termo_aditivo(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_termo_aditivo.parquet → SigconChaveTermoAditivo."""
    return _carregar_silver(SigconChaveTermoAditivo, "sigcon_chave_termo_aditivo", silver_path)


def carregar_codigo_declaracao_contrapartida(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_chave_declaracao.parquet → SigconChaveDeclaracao."""
    return _carregar_silver(SigconChaveDeclaracao, "sigcon_chave_declaracao", silver_path)


def carregar_unidades_executoras(silver_path: Path | None = None) -> dict:
    """Fonte: sigcon_unidade_executora.parquet → SigconUnidadeExecutora."""
    return _carregar_silver(SigconUnidadeExecutora, "sigcon_unidade_executora", silver_path)


# ---------------------------------------------------------------------------
# Fora do modelo SIGCON v1.0 (sem model atual — aguardam as ondas SICONV/SEI)
# ---------------------------------------------------------------------------

def carregar_tabela_integrada(gold_path: Path | None = None) -> dict:
    """
    Full refresh do model ConvenioIntegrado a partir do Gold Parquet.

    Se gold_path não fornecido, constrói a tabela chamando
    construir_tabela_integrada() com os Silver files e grava em data/gold/.

    TODAS as linhas do Gold entram (uma por linha de sigcon_chave_siconv): UO
    excluída vai para fl_uo_excluida, linha sem datas para limpeza_g, e
    convênio sem SIAFI fica com siafi_uo nulo. As consultas filtram.

    Parâmetros
    ----------
    gold_path : caminho explícito para o Parquet Gold convenios_integrado.
                Se None, tenta data/gold/convenios_integrado.parquet;
                se não existir, constrói do zero. (O comando
                carregar_relacionamento remove o Gold antigo antes, para
                sempre reconstruir.)
    """
    from core.gold.relacionamento import construir_tabela_integrada, gravar_tabela_integrada

    from .models import ConvenioIntegrado  # sem model atual (fora do modelo SIGCON v1.0)

    caminho_gold = gold_path or (Path(settings.DATA_DIR) / "gold" / "convenios_integrado.parquet")

    if caminho_gold.exists():
        logger.info("Lendo Gold Parquet: %s", caminho_gold)
        df = pd.read_parquet(caminho_gold)
    else:
        logger.info("Gold Parquet não encontrado — construindo a partir dos Silver files...")
        df_chaves = _ler_parquet(_silver_path("sigcon_chave_siconv"))
        df_depara = _ler_parquet(_silver_path("depara_siafi"))
        df_conv = _ler_parquet(_silver_path("sigcon_convenio"))
        df_cod = _ler_parquet(_silver_path("sigcon_chave_convenio"))
        df_geral = _ler_parquet(_silver_path("sigcon_convenio_geral"))
        df_plano = _ler_parquet(_silver_path("sigcon_plano_trabalho"))
        df_esfera = _ler_parquet(_silver_path("sigcon_concedente"))

        # siconv_convenio é opcional
        siconv_p = _silver_path("siconv_convenio")
        df_siconv = pd.read_parquet(siconv_p) if siconv_p.exists() else None

        df = construir_tabela_integrada(
            df_chaves, df_depara, df_conv, df_cod, df_geral, df_plano, df_esfera,
            df_siconv=df_siconv,
        )
        gravar_tabela_integrada(df)

    logger.info("Construindo objetos ConvenioIntegrado: %d linhas", len(df))

    def _g(col):
        return row.get(col) if col in df.columns else None

    objetos = []
    for _, row in df.iterrows():
        objetos.append(ConvenioIntegrado(
            # bridge / chaves
            siafi_uo=_para_str(row["siafi_uo"]),  # nulo = convênio sem SIAFI
            siafi_uo_atual=_para_str(_g("siafi_uo_atual")),
            convenio_numero_sequencial_siafi=_para_str(_g("convenio_numero_sequencial_siafi")),
            unidade_orcamentaria_codigo=_para_str(_g("unidade_orcamentaria_codigo")),
            siafiatual=_para_str(_g("siafiatual")),
            uo_atual=_para_str(_g("uo_atual")),
            codigo_siconv=_para_str(_g("codigo_siconv")),
            # de-paras
            instrumento_chaves=_para_str(_g("instrumento_chaves")),
            situacao=_para_str(_g("situacao")),
            situacao_std=_para_str(_g("situacao_std")),
            uo_nome_std=_para_str(_g("uo_nome_std")),
            uo_sigla_std=_para_str(_g("uo_sigla_std")),
            uo_descricao_std=_para_str(_g("uo_descricao_std")),
            # G_ datas
            g_dia_assinatura=_str_para_date(_g("g_dia_assinatura")),
            g_inicio_vigencia=_str_para_date(_g("g_inicio_vigencia")),
            g_fim_vigencia=_str_para_date(_g("g_fim_vigencia")),
            g_fim_vigencia_inicial=_str_para_date(_g("g_fim_vigencia_inicial")),
            # G_ anos
            g_ano_assinatura=_para_int(_g("g_ano_assinatura")),
            g_ano_inicio_vigencia=_para_int(_g("g_ano_inicio_vigencia")),
            g_ano_convenio=_para_int(_g("g_ano_convenio")),
            # G_ texto
            g_situacao_convenio=_para_str(_g("g_situacao_convenio")),
            g_objeto_convenio=_para_str(_g("g_objeto_convenio")),
            g_proponente=_para_str(_g("g_proponente")),
            g_concedente=_para_str(_g("g_concedente")),
            g_instrumento=_para_str(_g("g_instrumento")),
            g_esfera=_para_str(_g("g_esfera")),
            g_uo=_para_str(_g("g_uo")),
            g_vigencia=_para_str(_g("g_vigencia")),
            g_situacao_convenio_categorizado=_para_str(_g("g_situacao_convenio_categorizado")),
            g_concedente_pad=_para_str(_g("g_concedente_pad")),
            g_proponente_pad=_para_str(_g("g_proponente_pad")),
            g_proponente_pad_siglas=_para_str(_g("g_proponente_pad_siglas")),
            g_uo_descricao=_para_str(_g("g_uo_descricao")),
            # G_ valores
            g_valor_concedente=_para_decimal(_g("g_valor_concedente")),
            g_valor_proponente=_para_decimal(_g("g_valor_proponente")),
            g_valor_global=_para_decimal(_g("g_valor_global")),
            # G_ flags
            g_periodo_nao_aditado=_para_int(_g("g_periodo_nao_aditado")),
            g_valor_nao_aditado=_para_int(_g("g_valor_nao_aditado")),
            limpeza_g=_para_int(_g("limpeza_g")),
            fl_uo_excluida=bool(_g("fl_uo_excluida")),
            # A_ datas
            a_dia_assinatura=_str_para_date(_g("a_dia_assinatura")),
            a_inicio_vigencia=_str_para_date(_g("a_inicio_vigencia")),
            a_fim_vigencia=_str_para_date(_g("a_fim_vigencia")),
            a_fim_vigencia_inicial=_str_para_date(_g("a_fim_vigencia_inicial")),
            # A_ anos
            a_ano_assinatura=_para_int(_g("a_ano_assinatura")),
            a_ano_inicio_vigencia=_para_int(_g("a_ano_inicio_vigencia")),
            a_ano_convenio=_para_int(_g("a_ano_convenio")),
            # A_ texto
            a_situacao_convenio=_para_str(_g("a_situacao_convenio")),
            a_objeto_convenio=_para_str(_g("a_objeto_convenio")),
            a_proponente=_para_str(_g("a_proponente")),
            a_concedente=_para_str(_g("a_concedente")),
            a_instrumento=_para_str(_g("a_instrumento")),
            a_esfera=_para_str(_g("a_esfera")),
            a_vigencia=_para_str(_g("a_vigencia")),
            a_situacao_convenio_categorizado=_para_str(_g("a_situacao_convenio_categorizado")),
            a_concedente_pad=_para_str(_g("a_concedente_pad")),
            a_proponente_pad=_para_str(_g("a_proponente_pad")),
            a_proponente_pad_siglas=_para_str(_g("a_proponente_pad_siglas")),
            # A_ valores
            a_valor_concedente=_para_decimal(_g("a_valor_concedente")),
            a_valor_proponente=_para_decimal(_g("a_valor_proponente")),
            a_valor_global=_para_decimal(_g("a_valor_global")),
            # A_ flags
            a_periodo_nao_aditado=_para_int(_g("a_periodo_nao_aditado")),
            a_valor_nao_aditado=_para_int(_g("a_valor_nao_aditado")),
        ))

    return _bulk_refresh(ConvenioIntegrado, objetos)


def carregar_controle_sei(silver_path: Path | None = None) -> dict:
    """
    Full refresh do model ControleSEI a partir do Silver controle_sei.parquet.

    TODAS as linhas entram (hoje 2.834). Antes a carga mantinha só o 1º SEI por
    SIAFI e apagava 334 linhas (326 sem SIAFI + 8 SIAFIs com 2 processos). A
    escolha de "um SEI por SIAFI" para a aba Convênios agora é feita na
    consulta (apps/sigcon/services.py::enrich_convenios_page), não na carga.

    Mapeamento de colunas (Parquet → model):
      nr_sei             → no_sei
      nr_siafi           → no_siafi_sigcon
      nr_proposta_siconv → no_proposta_siconv
    """
    from .models import ControleSEI  # sem model atual (fora do modelo SIGCON v1.0)

    caminho = silver_path or _silver_path("controle_sei")
    df = _ler_parquet(caminho)

    objetos = [
        ControleSEI(
            no_sei=_para_str(row["nr_sei"]),
            no_siafi_sigcon=_para_str(row["nr_siafi"]),
            no_proposta_siconv=_para_str(row["nr_proposta_siconv"]),
        )
        for _, row in df.iterrows()
    ]
    return _bulk_refresh(ControleSEI, objetos)
