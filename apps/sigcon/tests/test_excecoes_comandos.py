"""
Tratamento de exceção nos comandos de carga.

Antes, todos capturavam `except (FileNotFoundError, Exception)` — tupla
redundante, já que FileNotFoundError é subclasse de Exception — e convertiam
tudo em `CommandError(str(exc))`. O efeito prático: erro esperado (o arquivo
da fonte ainda não chegou) e erro inesperado (bug, dado corrompido) saíam
iguais, e o traceback original se perdia.

O que estes testes fixam: o pipeline continua isolando a falha de uma carga das
demais. O tratamento de arquivo ausente e de erro inesperado do comando
`carregar_sigcon` (que substituiu os comandos `carregar_*` antigos) está em
apps/sigcon/tests/test_carregar_sigcon.py.
"""
import logging
from unittest import mock


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
