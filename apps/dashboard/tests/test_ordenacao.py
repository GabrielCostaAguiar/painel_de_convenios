"""
Ordenação determinística das telas paginadas.

Paginar sem `order_by` faz o banco devolver "as linhas 51 a 100" sem ordem
definida — o mesmo registro pode aparecer em duas páginas enquanto outro nunca
aparece. O Django sinaliza isso com `UnorderedObjectListWarning`, que o
pytest.ini trata como erro para impedir regressão.

Além de exigir que o queryset esteja ordenado, cada teste confere que o
`order_by` **termina em `pk`**: as chaves de negócio do SIGCON-MG admitem
empate (várias linhas do mesmo convênio, do mesmo exercício), e sem uma coluna
única a ordem continua ambígua mesmo com `ordered = True`.
"""
import pytest

from apps.dashboard import services

# (nome do serviço, função, constante de ordenação esperada)
SERVICOS_PAGINADOS = [
    ("plano_aplicacao", services.get_plano_aplicacao_qs, services.ORDENACAO_PLANO_APLICACAO),
    ("cronograma", services.get_cronograma_qs, services.ORDENACAO_CRONOGRAMA),
    ("prorrogacao", services.get_prorrogacao_qs, services.ORDENACAO_PRORROGACAO),
    ("termo_aditivo", services.get_termos_aditivos_qs, services.ORDENACAO_TERMO_ADITIVO),
    ("unidades_executoras", services.get_unidades_executoras_qs,
     services.ORDENACAO_UNIDADES_EXECUTORAS),
]

IDS = [nome for nome, _, _ in SERVICOS_PAGINADOS]


@pytest.mark.django_db
@pytest.mark.parametrize("nome,servico,ordenacao", SERVICOS_PAGINADOS, ids=IDS)
def test_queryset_da_tela_esta_ordenado(nome, servico, ordenacao):
    qs, _ = servico()

    assert qs.ordered, f"{nome}: queryset sem ordenação — paginação fica instável"
    assert tuple(qs.query.order_by) == tuple(ordenacao)


@pytest.mark.django_db
@pytest.mark.parametrize("nome,servico,ordenacao", SERVICOS_PAGINADOS, ids=IDS)
def test_ordenacao_termina_em_pk(nome, servico, ordenacao):
    """Desempate final numa coluna única — sem isso a ordem segue ambígua."""
    qs, _ = servico()

    assert ordenacao[-1] == "pk", f"{nome}: ordenação não termina em pk"
    assert tuple(qs.query.order_by)[-1] == "pk"


@pytest.mark.django_db
@pytest.mark.parametrize("nome,servico,ordenacao", SERVICOS_PAGINADOS, ids=IDS)
def test_ordenacao_vale_tambem_com_filtro_aplicado(nome, servico, ordenacao):
    """
    Os exports e a tela filtrada passam pelos mesmos serviços. Um filtro não
    pode descartar o order_by — senão o arquivo baixado sai fora de ordem.
    """
    qs, _ = servico(cod_sigcon="INEXISTENTE-123")

    assert qs.ordered
    assert tuple(qs.query.order_by) == tuple(ordenacao)


@pytest.mark.django_db
@pytest.mark.parametrize("nome,servico,ordenacao", SERVICOS_PAGINADOS, ids=IDS)
def test_campos_da_ordenacao_existem_no_model(nome, servico, ordenacao):
    """
    Um nome de campo errado no order_by só estoura quando o queryset é
    avaliado — que, numa tela sem dados, pode demorar a acontecer.
    """
    qs, _ = servico()

    list(qs[:1])  # força a avaliação: FieldError aqui se algum campo não existir
