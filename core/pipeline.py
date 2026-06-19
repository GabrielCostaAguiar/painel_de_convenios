"""
Orquestrador do pipeline completo: extracao+bronze -> silver -> gold/carga ORM.

Fat service, thin command: toda a logica de orquestracao vive aqui;
apps/dashboard/management/commands/rodar_pipeline.py so chama atualizar_painel().

Contrato entre etapas: a etapa N so roda se a etapa N-1 produziu alguma
saida (pelo menos um arquivo Bronze; pelo menos uma fonte Silver). Se uma
etapa nao produz nada, o pipeline para ali, loga e retorna - nao roda as
proximas etapas em cima de dado incompleto.

Dentro de uma mesma etapa, a falha de um item (um duto de extracao, uma
fonte do Silver, um loader do Gold) e logada e nao aborta os demais itens -
mesma semantica ja usada em core/ingestion/ponte_extracao.py.
"""

import io
import logging
import re

from django.core.management import call_command
from django.core.management.base import CommandError

from core.extract import gmail, transferegov
from core.ingestion.ponte_extracao import ingerir_gmail_mapeados, ingerir_transferegov

logger = logging.getLogger(__name__)

# Fontes Silver necessarias para a carga Gold/ORM completa (chaves de
# core.ingestion.sources.FONTES). Nao inclui qv_despesa_* e parlamentares -
# nenhum loader atual as consome.
FONTES_SILVER = [
    "dcgce_convenio",
    "dcgce_geral",
    "dcgce_plano_trabalho",
    "dcgce_esfera",
    "dcgce_codigo_convenio",
    "dcgce_cronograma_desembolso",
    "dcgce_plano_aplicacao",
    "dcgce_termo_aditivo",
    "dcgce_declaracao_contrapartida",
    "dcgce_prorrogacao_oficio",
    "dcgce_sigcon_nt_emenda",
    "dcgce_unidades_executoras",
    "dcgce_codigo_ta",
    "dcgce_Codigo_plano_de_trabalho",
    "dcgce_codigo_dec_contrap",
    "chaves_convenio",
    "siafi2",
    "controle_sei",
    "siconv_convenio",
]

# Comandos de carga Gold/ORM, na ordem documentada no CLAUDE.md.
# (comando, args posicionais, kwargs de flags)
CARGAS_ORM = [
    ("carregar_convenios", [], {}),
    ("carregar_fonte", ["dcgce_geral"], {}),
    ("carregar_fonte", ["dcgce_plano.trabalho"], {}),
    ("carregar_fonte", ["dcgce_Cronograma_desembolso"], {}),
    ("carregar_fonte", ["dcgce_plano_aplicacao"], {}),
    ("carregar_fonte", ["dcgce_termo.aditivo"], {}),
    ("carregar_fonte", ["dcgce_declaracao_contrapartida"], {}),
    ("carregar_fonte", ["dcgce_prorrogacao_oficio"], {}),
    ("carregar_fonte", ["dcgce_sigcon_nt_emenda"], {}),
    ("carregar_fonte", ["dcgce_esfera"], {}),
    ("carregar_fonte", ["dcgce_Codigo_convenio"], {}),
    ("carregar_fonte", ["dcgce_Codigo_plano_de_trabalho"], {}),
    ("carregar_fonte", ["dcgce_Codigo_ta"], {}),
    ("carregar_fonte", ["dcgce_Codigo_dec_contrap"], {}),
    ("carregar_cronograma", [], {}),
    ("carregar_unidades_executoras", [], {}),
    ("carregar_controle_sei", [], {}),
    ("carregar_relacionamento", [], {"construir": True}),
]

_PADRAO_CONTAGEM = re.compile(r"Apagados:\s*(\d+)\s*\|\s*Inseridos:\s*(\d+)")


def _extrair_contagem(saida: str) -> dict:
    match = _PADRAO_CONTAGEM.search(saida)
    if not match:
        return {}
    return {"apagados": int(match.group(1)), "inseridos": int(match.group(2))}


def _etapa_extracao_bronze() -> dict:
    """Extrai (Gmail + Transferegov) e ingere o Bronze das fontes mapeadas.

    Sucesso = pelo menos um arquivo Bronze foi gerado. O Bronze processa o
    arquivo mais recente disponivel em data/raw/ por fonte mesmo que a
    extracao de hoje tenha falhado (semantica ja documentada em
    ponte_extracao.py) - por isso contamos bronze_gerados, nao extraidos,
    como sinal de sucesso da etapa.
    """
    erros = []
    extraidos = {}

    for nome, extrair in (("transferegov", transferegov.extrair), ("gmail", gmail.extrair)):
        try:
            arquivos = extrair()
        except Exception as exc:
            logger.error("extracao: duto %r falhou: %s", nome, exc)
            erros.append(f"extracao/{nome}: {exc}")
            arquivos = []
        extraidos[nome] = len(arquivos)

    bronze_gerados = []
    try:
        bronze_gerados += ingerir_gmail_mapeados()
    except Exception as exc:
        logger.error("bronze: ingerir_gmail_mapeados falhou: %s", exc)
        erros.append(f"bronze/gmail: {exc}")

    try:
        destino = ingerir_transferegov()
        if destino is not None:
            bronze_gerados.append(destino)
    except Exception as exc:
        logger.error("bronze: ingerir_transferegov falhou: %s", exc)
        erros.append(f"bronze/transferegov: {exc}")

    sucesso = len(bronze_gerados) > 0
    if not sucesso:
        erros.append("nenhum arquivo Bronze foi gerado - nada para a etapa Silver processar")

    logger.info(
        "etapa extracao_bronze: %d arquivo(s) novo(s) em raw/, %d bronze gerado(s), sucesso=%s",
        sum(extraidos.values()), len(bronze_gerados), sucesso,
    )

    return {
        "nome": "extracao_bronze",
        "sucesso": sucesso,
        "contagens": {"extraidos_raw": extraidos, "bronze_gerados": len(bronze_gerados)},
        "erros": erros,
    }


def _etapa_silver() -> dict:
    """Roda rodar_silver para cada fonte de FONTES_SILVER.

    Sucesso = pelo menos uma fonte gerou Silver. Fonte sem Bronze disponivel
    falha individualmente (rodar_silver levanta CommandError) e e logada,
    sem abortar as demais.
    """
    erros = []
    gerados = 0

    for fonte in FONTES_SILVER:
        buffer = io.StringIO()
        try:
            call_command("rodar_silver", fonte, stdout=buffer)
            gerados += 1
        except CommandError as exc:
            logger.warning("silver: %r falhou: %s", fonte, exc)
            erros.append(f"silver/{fonte}: {exc}")

    sucesso = gerados > 0
    if not sucesso:
        erros.append("nenhuma fonte Silver foi gerada - nada para a etapa Gold/ORM carregar")

    logger.info("etapa silver: %d/%d fonte(s) geradas, sucesso=%s", gerados, len(FONTES_SILVER), sucesso)

    return {
        "nome": "silver",
        "sucesso": sucesso,
        "contagens": {"gerados": gerados, "total": len(FONTES_SILVER)},
        "erros": erros,
    }


def _etapa_gold_orm() -> dict:
    """Roda os comandos de carga Gold/ORM de CARGAS_ORM.

    Sucesso da etapa = carregar_convenios (tabela principal do painel) rodou
    sem erro. Os demais loaders sao independentes entre si: falha de um nao
    impede os outros de rodar, mas e registrada em erros.
    """
    erros = []
    contagens = {}

    for comando, args, kwargs in CARGAS_ORM:
        chave = comando if not args else f"{comando}:{args[0]}"
        buffer = io.StringIO()
        try:
            call_command(comando, *args, stdout=buffer, **kwargs)
            contagens[chave] = _extrair_contagem(buffer.getvalue())
        except CommandError as exc:
            logger.warning("gold: %r falhou: %s", chave, exc)
            erros.append(f"gold/{chave}: {exc}")

    sucesso = "carregar_convenios" in contagens
    if not sucesso:
        erros.append("carregar_convenios falhou - tabela principal do painel nao foi atualizada")

    logger.info("etapa gold_orm: %d/%d comando(s) ok, sucesso=%s", len(contagens), len(CARGAS_ORM), sucesso)

    return {
        "nome": "gold_orm",
        "sucesso": sucesso,
        "contagens": contagens,
        "erros": erros,
    }


def atualizar_painel() -> dict:
    """Orquestra o pipeline completo: extracao+bronze -> silver -> gold/carga ORM.

    Para na primeira etapa que nao produzir saida - nao roda as proximas
    etapas em cima de dado incompleto. Invalida o cache de indicadores
    (apps/dashboard/services.py) somente se o pipeline completar com sucesso.

    Retorna {"sucesso": bool, "etapas": [dict, ...]} - uma entrada por etapa
    realmente executada (etapas nao alcancadas, por uma etapa anterior ter
    falhado, nao aparecem na lista).
    """
    resultado = {"sucesso": True, "etapas": []}

    for etapa_fn in (_etapa_extracao_bronze, _etapa_silver, _etapa_gold_orm):
        etapa = etapa_fn()
        resultado["etapas"].append(etapa)
        if not etapa["sucesso"]:
            resultado["sucesso"] = False
            logger.error("pipeline interrompido na etapa %r - ver erros acima", etapa["nome"])
            break

    if resultado["sucesso"]:
        from apps.dashboard.services import invalidar_cache
        invalidar_cache()

    return resultado
