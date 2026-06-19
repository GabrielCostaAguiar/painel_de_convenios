"""
Baixar as bases de dados do bo, elas chegam pelo gmail.

Usar um GET simples para fazer a requesição no site e baixar o .zip
extrair() ; _autenticar()
"""

import base64
import logging
from pathlib import Path
from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .armazenamento import caminho_destino, ja_existe

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]   # só leitura: privilégio mínimo
CREDENCIAIS = Path(settings.BASE_DIR) / "secrets" / "credentials.json"
TOKEN = Path(settings.BASE_DIR) / "secrets" / "token.json"
REMETENTE = "bimg@prodemge.gov.br"
MAX_CANDIDATOS_BUSCA = 10   # subject: casa por substring (SIAD_contratos x SIAD_contratos1/2);
                            # pegamos varios candidatos pra achar o de Subject exato mais recente
GRUPOS_ASSUNTOS = {
    "sigcon": [
        "dcgce_Codigo_plano_de_trabalho", "dcgce_Codigo_convenio",
        "dcgce_Codigo_dec_contrap", "dcgce_unidades.executoras",
        "dcgce_termo.aditivo", "tabelauo2", "dcgce_plano.trabalho",
        "dcgce_prorrogacao_oficio", "dcgce_plano_aplicacao", "dcgce_Geral",
        "dcgce_declaracao_contrapartida", "dcgce_Cronograma_desembolso",
        "dcgce_convenio", "dcgce_Codigo_ta", "dcgce_Chave", "dcgce_esfera",
        "dcgce_sigcon_nt_emenda",
    ],
    "siafi": [
        "qv_arrecadacao_receitas_atual", "qv_despesa_ano_2019", "qv_despesa_rp",
        "contabilidade_grp", "qv_despesa_ano_73e74_2019",
        "qv_arrecadacao_receitas_73e74_2019", "qv_despesa_rp_73e74",
        "COTA_APROVADA_2022",
    ],
    "siad": [
        "Chave_SIAD", "SIAD_sem_contratos_2019", "SIAD_contratos",
        "SIAD_contratos1", "SIAD_contratos2",
    ],
}
def _autenticar():
    creds = None
    if TOKEN.exists():                                        # já consentiu antes?
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:                          # sem token válido...
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())                          # expirou → renova sozinho
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENCIAIS), SCOPES)
            creds = flow.run_local_server(port=0)             # abre o navegador (1ª vez)
        TOKEN.write_text(creds.to_json())                     # salva pra reusar
    return build("gmail", "v1", credentials=creds)            # o "serviço" que você vai consultar

def _assunto_exato(servico, msg_id: str, assunto_alvo: str) -> bool:
    mensagem = servico.users().messages().get(
        userId="me", id=msg_id, format="metadata", metadataHeaders=["Subject"]
    ).execute()
    headers = mensagem.get("payload", {}).get("headers", [])
    assunto_real = next((h["value"] for h in headers if h["name"] == "Subject"), "")
    return assunto_real.strip() == assunto_alvo


def _localizar_anexo(payload: dict) -> dict | None:
    for parte in payload.get("parts") or []:
        if parte.get("filename") and parte.get("body", {}).get("attachmentId"):
            return parte
        encontrada = _localizar_anexo(parte)
        if encontrada:
            return encontrada
    return None


def _tamanho_anexo(servico, msg_id: str) -> int:
    # format="full" traz o metadado de cada parte (inclusive body.size) sem
    # transferir o conteudo binario do anexo
    mensagem = servico.users().messages().get(userId="me", id=msg_id, format="full").execute()
    parte = _localizar_anexo(mensagem.get("payload", {}))
    if parte is None:
        raise ValueError(f"mensagem {msg_id} sem anexo localizavel")
    return parte.get("body", {}).get("size", 0)


def _validar_assunto(servico, assunto: str) -> tuple[str | None, str | None]:
    # FASE 1: busca, valida subject exato e tamanho do anexo, sem baixar nada.
    # Retorna (msg_id, None) se passou nos 3 checks, ou (None, motivo) se reprovou.
    query = f"from:{REMETENTE} subject:{assunto} has:attachment"
    try:
        resposta = servico.users().messages().list(
            userId="me", q=query, maxResults=MAX_CANDIDATOS_BUSCA, includeSpamTrash=True
        ).execute()
    except Exception as exc:
        return None, f"falha na busca: {exc}"

    candidatos = resposta.get("messages", [])
    if not candidatos:
        return None, "mensagem nao localizada"

    msg_id_exato = None
    for candidato in candidatos:  # ordem padrao da API: mais recente primeiro
        msg_id = candidato["id"]
        try:
            if _assunto_exato(servico, msg_id, assunto):
                msg_id_exato = msg_id
                break
        except Exception as exc:
            logger.error("falha ao validar subject da mensagem %s (%r): %s", msg_id, assunto, exc)
    if msg_id_exato is None:
        return None, f"subject nao bate exatamente em nenhum dos {len(candidatos)} candidato(s)"

    try:
        tamanho = _tamanho_anexo(servico, msg_id_exato)
    except Exception as exc:
        return None, f"falha ao checar tamanho do anexo: {exc}"
    if tamanho == 0:
        return None, "anexo vazio (0 bytes)"

    return msg_id_exato, None


def _baixar_anexo(servico, msg_id: str, destino: Path) -> None:
    mensagem = servico.users().messages().get(userId="me", id=msg_id, format="full").execute()
    parte = _localizar_anexo(mensagem.get("payload", {}))
    if parte is None:
        raise ValueError(f"mensagem {msg_id} sem anexo localizavel")
    anexo = servico.users().messages().attachments().get(
        userId="me", messageId=msg_id, id=parte["body"]["attachmentId"]
    ).execute()
    dados = base64.urlsafe_b64decode(anexo["data"])
    destino.write_bytes(dados)


def extrair() -> list[Path]:
    logger.info("iniciando extracao gmail (%d grupo(s))", len(GRUPOS_ASSUNTOS))
    try:
        servico = _autenticar()
    except Exception as exc:
        logger.error("falha na autenticacao gmail: %s", exc)
        raise

    arquivos: list[Path] = []
    for grupo, assuntos in GRUPOS_ASSUNTOS.items():
        logger.info("validando grupo %r (%d assunto(s))", grupo, len(assuntos))

        # FASE 1 - validacao (sem baixar): localizado + subject exato + anexo > 0
        validados: dict[str, str] = {}
        falhas: dict[str, str] = {}
        for assunto in assuntos:
            msg_id, motivo = _validar_assunto(servico, assunto)
            if motivo is not None:
                falhas[assunto] = motivo
            else:
                validados[assunto] = msg_id

        if falhas:
            for assunto, motivo in falhas.items():
                logger.warning("grupo %r: assunto %r reprovado na validacao (%s)", grupo, assunto, motivo)
            logger.warning(
                "grupo %r incompleto, pulando (%d de %d assunto(s) reprovado(s))",
                grupo, len(falhas), len(assuntos),
            )
            continue

        # FASE 2 - download (so roda se o grupo passou inteiro na validacao)
        logger.info("grupo %r validado por completo, baixando anexos", grupo)
        for assunto, msg_id in validados.items():
            try:
                destino = caminho_destino("gmail", assunto, extensao="")
                if ja_existe(destino):
                    logger.info("arquivo do dia ja existe para %r, pulando: %s", assunto, destino)
                    continue
                _baixar_anexo(servico, msg_id, destino)
                if destino.stat().st_size == 0:
                    destino.unlink()
                    logger.warning("anexo vazio (0 bytes) para %r, ignorado", assunto)
                    continue
                logger.info("anexo de %r pousado em %s", assunto, destino)
                arquivos.append(destino)
            except Exception as exc:
                logger.error("falha ao baixar o assunto %r (grupo %r): %s", assunto, grupo, exc)
                continue

    logger.info("extracao gmail concluida: %d arquivo(s) novo(s)", len(arquivos))
    return arquivos

