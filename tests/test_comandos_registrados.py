"""
Garante em que app cada comando de gerência vive.

Por que testar isso: o Django resolve `manage.py <comando>` por nome. Se dois
apps instalados expuserem o mesmo nome de comando, vence o que vier primeiro no
INSTALLED_APPS — silenciosamente. Uma cópia esquecida de rodar_silver em
apps/painel passaria despercebida até alguém editar o arquivo errado.
"""
import pytest
from django.core.management import get_commands

# Orquestração do lakehouse — operam Bronze/Silver inteiros, não o painel.
COMANDOS_PIPELINE = [
    "rodar_pipeline",
    "rodar_ingestao",
    "rodar_silver",
    "gerar_schemas",
]

# Carga Silver → banco, dominio das Consultas SIGCON (pacote apps.sigcon,
# label "convenios").
COMANDOS_CONVENIOS = [
    "carregar_convenios",
    "carregar_fonte",
    "carregar_cronograma",
    "carregar_unidades_executoras",
    "carregar_controle_sei",
    "carregar_relacionamento",
]


@pytest.mark.parametrize("comando", COMANDOS_PIPELINE)
def test_comandos_de_pipeline_vivem_em_apps_pipeline(comando):
    assert get_commands()[comando] == "apps.pipeline"


@pytest.mark.parametrize("comando", COMANDOS_CONVENIOS)
def test_comandos_de_carga_vivem_em_apps_sigcon(comando):
    assert get_commands()[comando] == "apps.sigcon"


def test_painel_nao_expoe_nenhum_comando():
    """
    O painel é camada de apresentação: não deve registrar comandos. Pega
    sobras de uma cópia não removida na mudança para apps.pipeline.
    """
    do_painel = [
        nome for nome, app in get_commands().items() if app == "apps.painel"
    ]
    assert do_painel == []
