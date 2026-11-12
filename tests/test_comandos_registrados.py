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

# Carga Silver → banco e validação de qualidade do SIGCON (pacote apps.sigcon,
# label "convenios").
COMANDOS_SIGCON = [
    "carregar_sigcon",
    "validar_sigcon",
]

# Comandos de carga antigos, removidos na refatoração dos models Sigcon*. Se
# voltarem a existir, alguém recriou código morto.
COMANDOS_REMOVIDOS = [
    "carregar_convenios",
    "carregar_fonte",
    "carregar_cronograma",
    "carregar_unidades_executoras",
    "carregar_controle_sei",
    "carregar_relacionamento",
    "carregar_silver",
    "rodar_transformacao",
]


@pytest.mark.parametrize("comando", COMANDOS_PIPELINE)
def test_comandos_de_pipeline_vivem_em_apps_pipeline(comando):
    assert get_commands()[comando] == "apps.pipeline"


@pytest.mark.parametrize("comando", COMANDOS_SIGCON)
def test_comandos_do_sigcon_vivem_em_apps_sigcon(comando):
    assert get_commands()[comando] == "apps.sigcon"


@pytest.mark.parametrize("comando", COMANDOS_REMOVIDOS)
def test_comandos_antigos_nao_existem_mais(comando):
    assert comando not in get_commands()


def test_painel_nao_expoe_nenhum_comando():
    """
    O painel é camada de apresentação: não deve registrar comandos. Pega
    sobras de uma cópia não removida na mudança para apps.pipeline.
    """
    do_painel = [
        nome for nome, app in get_commands().items() if app == "apps.painel"
    ]
    assert do_painel == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Pendência: CARGAS_ORM do rodar_pipeline ainda chama carregar_convenios / "
        "carregar_fonte, removidos. Ver docs/pendencias.md. Quando o pipeline "
        "passar a usar carregar_sigcon, este teste passa e o xfail deve sair."
    ),
)
def test_cargas_orm_do_pipeline_apontam_para_comandos_existentes():
    """Sem isso o rodar_pipeline falha só na etapa de carga, depois de extrair e ingerir."""
    from core.pipeline import CARGAS_ORM

    existentes = get_commands()
    assert CARGAS_ORM
    for comando, _args, _kwargs in CARGAS_ORM:
        assert comando in existentes, f"{comando} não existe"
