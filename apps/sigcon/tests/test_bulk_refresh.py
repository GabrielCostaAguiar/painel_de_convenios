"""
Testes do helper de full refresh (apps.sigcon.loader._bulk_refresh).

O que está sob teste é a garantia transacional: o par delete + bulk_create
precisa ser tudo-ou-nada. Sem isso, uma falha no meio da carga deixa a tabela
vazia — os dados antigos já foram apagados e os novos não entraram.

Usa SigconChaveConvenio por ser um dos models mais simples da app (ponte de
chave, sem FKs), com dados sintéticos.
"""
from unittest import mock

import pytest

from apps.sigcon.loader import _bulk_refresh
from apps.sigcon.models import SigconChaveConvenio


def _objs(codigos):
    """Constrói instâncias não salvas de SigconChaveConvenio a partir dos códigos."""
    return [
        SigconChaveConvenio(
            cd_convenio_sequencial=c,
            nr_convenio=f"conv-{c}",
            nr_siafi=f"siafi-{c}",
            cd_uo="1234",
            siafi_uo=f"siafi-{c}1234",
        )
        for c in codigos
    ]


def _codigos_no_banco():
    return sorted(
        SigconChaveConvenio.objects.values_list("cd_convenio_sequencial", flat=True)
    )


@pytest.mark.django_db
def test_caminho_feliz_substitui_todo_o_conteudo():
    """3 registros antigos → refresh com 5 novos → sobram exatamente os 5."""
    SigconChaveConvenio.objects.bulk_create(_objs(["A1", "A2", "A3"]))

    resultado = _bulk_refresh(SigconChaveConvenio, _objs(["N1", "N2", "N3", "N4", "N5"]))

    assert SigconChaveConvenio.objects.count() == 5
    assert _codigos_no_banco() == ["N1", "N2", "N3", "N4", "N5"]
    assert resultado == {"apagados": 3, "inseridos": 5}


@pytest.mark.django_db
def test_falha_no_insert_faz_rollback_e_preserva_os_dados_antigos():
    """
    Se o bulk_create estourar, a exceção propaga E os registros originais
    continuam no banco — é exatamente isso que transaction.atomic compra.
    """
    SigconChaveConvenio.objects.bulk_create(_objs(["A1", "A2", "A3"]))

    with mock.patch.object(
        SigconChaveConvenio.objects,
        "bulk_create",
        side_effect=RuntimeError("falha simulada no meio da carga"),
    ):
        with pytest.raises(RuntimeError, match="falha simulada"):
            _bulk_refresh(SigconChaveConvenio, _objs(["N1", "N2"]))

    assert SigconChaveConvenio.objects.count() == 3
    assert _codigos_no_banco() == ["A1", "A2", "A3"]


@pytest.mark.django_db
def test_refresh_e_idempotente():
    """Rodar o mesmo refresh duas vezes produz o mesmo estado final."""
    SigconChaveConvenio.objects.bulk_create(_objs(["A1"]))

    primeiro = _bulk_refresh(SigconChaveConvenio, _objs(["X1", "X2"]))
    estado_apos_primeiro = _codigos_no_banco()

    segundo = _bulk_refresh(SigconChaveConvenio, _objs(["X1", "X2"]))

    assert _codigos_no_banco() == estado_apos_primeiro == ["X1", "X2"]
    assert primeiro["inseridos"] == segundo["inseridos"] == 2
    # o segundo apaga o que o primeiro inseriu
    assert segundo["apagados"] == 2


@pytest.mark.django_db
def test_batch_size_e_repassado_ao_bulk_create():
    """O batch_size existente (500) continua sendo o default do helper."""
    with mock.patch.object(SigconChaveConvenio.objects, "bulk_create") as fake:
        _bulk_refresh(SigconChaveConvenio, _objs(["Z1"]))

    _, kwargs = fake.call_args
    assert kwargs["batch_size"] == 500
