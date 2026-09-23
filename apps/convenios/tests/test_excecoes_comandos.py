"""
Tratamento de exceção nos comandos de carga.

Antes, todos capturavam `except (FileNotFoundError, Exception)` — tupla
redundante, já que FileNotFoundError é subclasse de Exception — e convertiam
tudo em `CommandError(str(exc))`. O efeito prático: erro esperado (o arquivo
da fonte ainda não chegou) e erro inesperado (bug, dado corrompido) saíam
iguais, e o traceback original se perdia.

O que estes testes fixam:
  - arquivo ausente → mensagem curta e acionável, sem traceback;
  - erro inesperado → CommandError com __cause__ preservado e traceback no log;
  - o pipeline continua isolando a falha de uma carga das demais.
"""
import logging
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

# (nome do comando, função do loader que ele chama, args extras)
COMANDOS_DE_CARGA = [
    ("carregar_convenios", "apps.convenios.management.commands.carregar_convenios.carregar_convenios", []),
    ("carregar_cronograma", "apps.convenios.management.commands.carregar_cronograma.carregar_cronograma_desembolso", []),
    ("carregar_unidades_executoras", "apps.convenios.management.commands.carregar_unidades_executoras.carregar_unidades_executoras", []),
    ("carregar_controle_sei", "apps.convenios.management.commands.carregar_controle_sei.carregar_controle_sei", []),
    ("carregar_relacionamento", "apps.convenios.management.commands.carregar_relacionamento.carregar_tabela_integrada", []),
]

IDS = [nome for nome, _, _ in COMANDOS_DE_CARGA]


@pytest.mark.django_db
@pytest.mark.parametrize("comando,alvo,extra", COMANDOS_DE_CARGA, ids=IDS)
def test_arquivo_ausente_vira_mensagem_amigavel(comando, alvo, extra):
    """
    FileNotFoundError é o caso esperado: a fonte ainda não foi ingerida. Vira
    CommandError (código de saída != 0, que o agendador precisa) com a
    mensagem do loader, que já diz o que rodar antes.
    """
    erro = FileNotFoundError(
        "Parquet Silver não encontrado: data/silver/x.parquet\n"
        "Rode antes: python manage.py rodar_silver <fonte>"
    )

    with mock.patch(alvo, side_effect=erro):
        with pytest.raises(CommandError) as excinfo:
            call_command(comando, *extra)

    mensagem = str(excinfo.value)
    assert "Parquet Silver não encontrado" in mensagem
    assert "rodar_silver" in mensagem
    assert excinfo.value.__cause__ is erro


@pytest.mark.django_db
@pytest.mark.parametrize("comando,alvo,extra", COMANDOS_DE_CARGA, ids=IDS)
def test_erro_inesperado_preserva_a_causa_e_loga_o_traceback(
    comando, alvo, extra, caplog,
):
    """
    Erro inesperado precisa deixar rastro: traceback completo no log e a
    exceção original encadeada em __cause__, para o diagnóstico não sumir
    atrás da mensagem genérica.
    """
    erro = ValueError("coluna 'valor_concedente' veio como texto")

    with mock.patch(alvo, side_effect=erro):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(CommandError) as excinfo:
                call_command(comando, *extra)

    assert excinfo.value.__cause__ is erro
    assert "coluna 'valor_concedente' veio como texto" in str(excinfo.value)

    # logger.exception grava o traceback junto do registro
    registros = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert registros, "nenhum log de erro emitido"
    assert any(r.exc_info for r in registros), "traceback não foi registrado"


@pytest.mark.django_db
def test_carregar_fonte_tambem_segue_o_padrao(caplog):
    """carregar_fonte recebe a fonte por argumento; o rótulo entra na mensagem."""
    erro = ValueError("parquet corrompido")

    with mock.patch(
        "apps.convenios.loader.carregar_convenio_geral", side_effect=erro,
    ):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(CommandError) as excinfo:
                call_command("carregar_fonte", "dcgce_geral")

    assert excinfo.value.__cause__ is erro
    assert "dcgce_geral" in str(excinfo.value)
    assert any(r.exc_info for r in caplog.records if r.levelno >= logging.ERROR)


@pytest.mark.django_db
def test_fonte_desconhecida_continua_listando_as_validas():
    """Validação de argumento não passa pelo novo bloco — segue como estava."""
    with pytest.raises(CommandError) as excinfo:
        call_command("carregar_fonte", "fonte_que_nao_existe")

    mensagem = str(excinfo.value)
    assert "fonte_que_nao_existe" in mensagem
    assert "dcgce_geral" in mensagem, "deveria listar as fontes válidas"


# ---------------------------------------------------------------------------
# Semântica do pipeline: a falha de uma carga não aborta as demais
# ---------------------------------------------------------------------------

def _etapa(nome, sucesso, contagens):
    return {"nome": nome, "sucesso": sucesso, "contagens": contagens, "erros": []}


def test_pipeline_segue_para_as_proximas_cargas_apos_uma_falhar(caplog):
    """
    Contrato da etapa gold_orm: cada carga é independente. Uma que estoure —
    inclusive com exceção que não seja CommandError — não pode impedir as
    outras de rodar.
    """
    from core import pipeline

    chamados = []

    def fake_call_command(comando, *args, **kwargs):
        chamados.append(comando if not args else f"{comando}:{args[0]}")
        if comando == "carregar_cronograma":
            raise RuntimeError("estouro inesperado no meio da carga")
        buffer = kwargs.get("stdout")
        if buffer is not None:
            buffer.write("Concluído! Apagados: 1 | Inseridos: 2\n")

    with mock.patch.object(pipeline, "call_command", side_effect=fake_call_command):
        with caplog.at_level(logging.ERROR):
            etapa = pipeline._etapa_gold_orm()

    # todas as cargas de CARGAS_ORM foram tentadas, apesar da que estourou
    assert len(chamados) == len(pipeline.CARGAS_ORM)
    assert "carregar_cronograma" in chamados
    # a que falhou não entra nas contagens, as outras sim
    assert "carregar_cronograma" not in etapa["contagens"]
    assert "carregar_convenios" in etapa["contagens"]
    assert any("carregar_cronograma" in e for e in etapa["erros"])
    # traceback registrado para o erro inesperado
    assert any(r.exc_info for r in caplog.records if r.levelno >= logging.ERROR)


def test_pipeline_invalida_cache_quando_alguma_carga_teve_sucesso():
    """Mesmo com uma carga falhando, o banco mudou — o cache precisa cair."""
    from core import pipeline

    with mock.patch.object(pipeline, "_etapa_extracao_bronze",
                           return_value=_etapa("extracao_bronze", True, {})), \
         mock.patch.object(pipeline, "_etapa_silver",
                           return_value=_etapa("silver", True, {"gerados": 2})), \
         mock.patch.object(pipeline, "_etapa_gold_orm",
                           return_value=_etapa("gold_orm", False,
                                               {"carregar_convenios": {"inseridos": 3}})), \
         mock.patch.object(pipeline, "invalidar_cache_indicadores") as invalidar:

        pipeline.atualizar_painel()

    invalidar.assert_called_once()
