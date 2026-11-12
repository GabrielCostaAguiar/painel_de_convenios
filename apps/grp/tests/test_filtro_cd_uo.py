"""
O filtro de UO do GRP usa exatamente `cd_uo` em todos os pontos.

O nome passa por quatro lugares que precisam concordar: o `name=` do campo no
formulário, a leitura da querystring (_ler_filtros_grp), a propagação entre as
sub-abas (GRP_PARAMS) e o filtro do ORM (services.py). O renome uo_cod -> cd_uo
já ficou pela metade uma vez: a view lia cd_uo e o formulário mandava uo_cod,
e o filtro era ignorado sem erro nenhum. Estes testes não precisam de banco
(a gold.vw_instrumento é view e não existe no banco de teste): conferem o SQL
gerado e o texto do template.
"""

from pathlib import Path

from apps.grp import services
from apps.grp.views._filtros import _ler_filtros_grp
from apps.painel.templatetags.painel_filters import GRP_PARAMS

TEMPLATE = (
    Path(__file__).resolve().parents[1] / "templates" / "grp" / "grp_generico.html"
)


def test_querystring_e_lida_pela_chave_cd_uo():
    filtros = _ler_filtros_grp({"cd_uo": "1261", "uo_cod": "9999"})

    assert filtros["cd_uo"] == "1261"
    assert "uo_cod" not in filtros


def test_formulario_envia_cd_uo_e_marca_a_opcao_escolhida():
    html = TEMPLATE.read_text(encoding="utf-8")

    assert 'name="cd_uo"' in html
    assert "cd_uo_sel" in html
    assert "uo_cod" not in html


def test_filtro_propagado_entre_as_sub_abas_e_cd_uo():
    assert "cd_uo" in GRP_PARAMS
    assert "uo_cod" not in GRP_PARAMS


def test_aba_dados_filtra_por_igualdade_exata_em_cd_uo():
    qs = services.get_grp_dados_qs({"cd_uo": "1261"})
    sql = str(qs.query)

    assert '"cd_uo" = 1261' in sql or "\"cd_uo\" = '1261'" in sql
    assert "LIKE" not in sql.split("WHERE", 1)[1], "UO não pode ser busca parcial"


def test_sub_abas_filtram_pelo_cd_uo_do_instrumento():
    """Nas sub-abas o cd_uo é resolvido no instrumento e vira nr_grp IN (...)."""
    qs = services.get_grp_cronograma_qs({"cd_uo": "1261"})
    sql = str(qs.query)

    assert "vw_instrumento" in sql
    assert '"cd_uo" = 1261' in sql or "\"cd_uo\" = '1261'" in sql


def test_sem_cd_uo_nao_ha_filtro_de_uo():
    sql = str(services.get_grp_dados_qs({}).query)

    assert "cd_uo" not in sql.split("WHERE", 1)[-1] or "WHERE" not in sql
