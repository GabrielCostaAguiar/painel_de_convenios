"""
Ponte entre a saída da extração (core/extract/) e a entrada do Bronze
(core/ingestion/bronze.py).

Os extratores pousam arquivos DATADOS em data/raw/<fonte_extracao>/ (zip do
transferegov; anexos sem extensão do gmail). O Bronze, por sua vez, espera um
caminho fixo por fonte (FONTES[nome].arquivo). Este módulo faz a ponte:
localiza o arquivo mais recente que a extração pousou e entrega para
bronze.ingerir() via o parâmetro `arquivo` (que já aceita um caminho
explícito — nenhum contrato existente precisou mudar).

Descompactação do .zip do transferegov acontece AQUI, nunca em data/raw/
(que é imutável): o membro do zip é extraído para um diretório temporário
efêmero, criado e destruído dentro da própria chamada.
"""

import logging
import re
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

from django.conf import settings

from .bronze import ingerir
from .sources import FONTES

logger = logging.getLogger(__name__)

_PADRAO_DATA = re.compile(r"(\d{4}-\d{2}-\d{2})")

# Mapeia assunto do Gmail (core.extract.gmail.GRUPOS_ASSUNTOS) -> chave em
# FONTES. Só inclui os que já têm FonteDados cadastrada (mesmos arquivos
# .xlsx que antes eram copiados manualmente para data/raw/sigcon/).
#
# TODO (decisão pendente, não mapeado por falta de amostra real):
#   - grupo "sigcon": "tabelauo2" e "dcgce_Chave" não têm FonteDados.
#   - grupo "siafi" (8 assuntos) e grupo "siad" (5 assuntos): nenhum tem
#     FonteDados. README.md já marca SIAD/SEI como previsto, não
#     implementado. Cadastrar uma fonte exige confirmar formato/separador/
#     encoding reais (ver "Adicionando uma Nova Fonte" no CLAUDE.md e
#     `gerar_schemas`) — não dá pra adivinhar sem um anexo real em mãos.
MAPA_GMAIL_PARA_FONTE: dict[str, str] = {
    "dcgce_Codigo_plano_de_trabalho": "dcgce_Codigo_plano_de_trabalho",
    "dcgce_Codigo_convenio": "dcgce_codigo_convenio",
    "dcgce_Codigo_dec_contrap": "dcgce_codigo_dec_contrap",
    "dcgce_unidades.executoras": "dcgce_unidades_executoras",
    "dcgce_termo.aditivo": "dcgce_termo_aditivo",
    "dcgce_plano.trabalho": "dcgce_plano_trabalho",
    "dcgce_prorrogacao_oficio": "dcgce_prorrogacao_oficio",
    "dcgce_plano_aplicacao": "dcgce_plano_aplicacao",
    "dcgce_Geral": "dcgce_geral",
    "dcgce_declaracao_contrapartida": "dcgce_declaracao_contrapartida",
    "dcgce_Cronograma_desembolso": "dcgce_cronograma_desembolso",
    "dcgce_convenio": "dcgce_convenio",
    "dcgce_Codigo_ta": "dcgce_codigo_ta",
    "dcgce_esfera": "dcgce_esfera",
    "dcgce_sigcon_nt_emenda": "dcgce_sigcon_nt_emenda",
}


def _localizar_mais_recente(diretorio: Path, prefixo: str) -> Path | None:
    if not diretorio.exists():
        return None
    candidatos = sorted(diretorio.glob(f"{prefixo}_*"))
    return candidatos[-1] if candidatos else None


def _extrair_data(caminho: Path) -> date | None:
    # Busca o padrao AAAA-MM-DD direto no nome do arquivo (Path.stem/.suffix
    # NAO servem aqui: assuntos do Gmail podem ter ponto no nome, ex.
    # "dcgce_unidades.executoras_2026-06-19" - ver bugfix em armazenamento.py)
    match = _PADRAO_DATA.search(caminho.name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def _avisar_se_desatualizado(nome_fonte: str, caminho: Path) -> None:
    # NAO aborta - so deixa a defasagem visivel no log (auditoria da data
    # do dado realmente processado pelo Bronze).
    data_arquivo = _extrair_data(caminho)
    if data_arquivo is None:
        logger.warning(
            "bronze: nao foi possivel extrair a data do nome de %s (fonte %r)",
            caminho, nome_fonte,
        )
        return
    dias_atraso = (date.today() - data_arquivo).days
    if dias_atraso == 0:
        logger.info("bronze: %r usando arquivo de hoje (%s): %s", nome_fonte, data_arquivo, caminho)
    else:
        logger.warning(
            "bronze: %r DESATUALIZADO - usando arquivo de %s (%d dia(s) de atraso): %s",
            nome_fonte, data_arquivo, dias_atraso, caminho,
        )


def ingerir_gmail_mapeados() -> list[Path]:
    """Roda bronze.ingerir() para cada assunto do Gmail com FonteDados
    mapeada, usando o arquivo mais recente pousado em data/raw/gmail/.

    Assunto sem nenhum arquivo no disco (grupo pulado pela extração hoje E
    nunca baixado antes) é logado e pulado — não aborta os demais."""
    diretorio = Path(settings.DATA_DIR) / "raw" / "gmail"
    destinos: list[Path] = []
    for assunto, nome_fonte in MAPA_GMAIL_PARA_FONTE.items():
        caminho = _localizar_mais_recente(diretorio, assunto)
        if caminho is None:
            logger.warning(
                "bronze: nenhum arquivo gmail encontrado para %r (fonte %r), pulando",
                assunto, nome_fonte,
            )
            continue
        _avisar_se_desatualizado(nome_fonte, caminho)
        try:
            destino = ingerir(nome_fonte, arquivo=caminho)
        except Exception as exc:
            logger.error(
                "bronze: falha ao ingerir %r a partir de %s: %s", nome_fonte, caminho, exc
            )
            continue
        logger.info("bronze: %r ingerido a partir de %s -> %s", nome_fonte, caminho, destino)
        destinos.append(destino)
    return destinos


def ingerir_transferegov(
    nome_fonte: str = "siconv_convenio", prefixo_zip: str = "siconv"
) -> Path | None:
    """Localiza o .zip mais recente do transferegov, extrai (em diretório
    temporário, nunca em data/raw/) o membro correspondente ao arquivo
    configurado em FONTES[nome_fonte] e roda bronze.ingerir() sobre ele.

    Confirmado: o zip do Transferegov contém o membro "siconv_convenio.csv".
    O nome esperado continua derivado de FONTES[nome_fonte].arquivo (em vez
    de um literal fixo aqui) pra ter uma única fonte da verdade — se o zip
    real mudar de conteúdo no futuro, o erro abaixo aponta o descompasso
    em vez de falhar silenciosamente.
    """
    diretorio = Path(settings.DATA_DIR) / "raw" / "transferegov"
    zip_path = _localizar_mais_recente(diretorio, prefixo_zip)
    if zip_path is None:
        logger.warning("bronze: nenhum .zip do transferegov encontrado em %s, pulando", diretorio)
        return None
    _avisar_se_desatualizado(nome_fonte, zip_path)

    fonte = FONTES.get(nome_fonte)
    if fonte is None:
        logger.error("bronze: fonte %r não registrada em FONTES, pulando transferegov", nome_fonte)
        return None
    membro_esperado = Path(fonte.arquivo).name  # ex.: "siconv_convenio.csv"

    try:
        with zipfile.ZipFile(zip_path) as zf:
            nomes = zf.namelist()
            if membro_esperado not in nomes:
                logger.error(
                    "bronze: membro %r nao encontrado em %s (conteudo do zip: %s). "
                    "Esperado 'siconv_convenio.csv' confirmado previamente - "
                    "o zip do Transferegov mudou de formato? Confira FONTES[%r].arquivo.",
                    membro_esperado, zip_path, nomes, nome_fonte,
                )
                return None
            with tempfile.TemporaryDirectory() as tmp:
                caminho_extraido = Path(zf.extract(membro_esperado, path=tmp))
                destino = ingerir(nome_fonte, arquivo=caminho_extraido)
    except Exception as exc:
        logger.error("bronze: falha ao processar %s: %s", zip_path, exc)
        return None

    logger.info("bronze: %r ingerido a partir de %s (membro %r) -> %s",
                nome_fonte, zip_path, membro_esperado, destino)
    return destino
