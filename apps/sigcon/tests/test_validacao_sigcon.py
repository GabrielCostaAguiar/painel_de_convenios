"""
Catálogo de validação do SIGCON (`apps/sigcon/validacao/`) e o comando `validar_sigcon`.

Três famílias de teste:
  * consistência do catálogo, sem banco: ids únicos, grãos iguais ao YAML de
    cada fonte, colunas citadas existem no model;
  * construtores de SQL e o catálogo inteiro rodando no banco de teste: toda
    consulta tem de ser SQL válido contra o esquema real dos models;
  * o comportamento de cada regra com linhas sintéticas (o teste "enxerga" a
    violação) e o comando que grava os resultados.

Nenhum dado real é tocado.
"""

import re
import uuid
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
import yaml
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.sigcon.management.commands import validar_sigcon as cmd
from apps.sigcon.models import (
    ResultadoValidacao,
    SigconChaveConvenio,
    SigconConvenio,
    SigconConvenioGeral,
    SigconCronogramaDesembolso,
    SigconPlanoAplicacao,
    SigconTabelaUo,
)
from apps.sigcon.validacao import catalogo, volumetria
from apps.sigcon.validacao.limites import severidade_efetiva
from apps.sigcon.validacao.generico import (
    sql_formato,
    sql_nao_nulo,
    sql_orfaos,
    sql_unicidade,
    sql_valores_aceitos,
)

SCHEMAS = Path(__file__).resolve().parents[3] / "core" / "transform" / "schemas"


def _executar(sql):
    """Roda a consulta do catálogo do mesmo jeito que o comando."""
    return cmd.Command()._rodar(sql)


def _teste(id_teste):
    return next(t for t in catalogo.TESTES if t["id"] == id_teste)


def _id_do_grao(tabela):
    return next(
        t["id"]
        for t in catalogo.TESTES_C
        if t["tabela"] == tabela
    )


# ---------------------------------------------------------------------------
# Consistência do catálogo (sem banco)
# ---------------------------------------------------------------------------


def test_ids_unicos_e_bem_formados():
    ids = [t["id"] for t in catalogo.TESTES]

    assert len(ids) == len(set(ids)), "id repetido: um resultado sobrescreveria outro"
    assert all(re.fullmatch(r"T-[A-I]\d{2}", i) for i in ids)


def test_ids_sao_sequenciais_por_categoria():
    """Sem buracos nem saltos: o número é só a posição dentro da categoria."""
    for categoria in "ABCDEFGHI":
        numeros = [
            int(t["id"][3:]) for t in catalogo.TESTES if t["id"][2] == categoria
        ]
        assert numeros == list(range(1, len(numeros) + 1)), categoria


def test_todo_teste_tem_os_campos_obrigatorios():
    for t in catalogo.TESTES:
        assert t["severidade"] in {"ERRO", "ALERTA"}, t["id"]
        assert t["tabela"] and t["descricao"], t["id"]
        assert ("sql" in t) != ("funcao" in t), f"{t['id']}: sql OU funcao"


def test_nenhum_teste_do_grp_sobrou_no_catalogo():
    for t in catalogo.TESTES:
        texto = f"{t['tabela']} {t.get('sql', '')}"
        assert "grp_" not in texto and "nr_grp" not in texto, t["id"]


def _model_da_tabela(tabela):
    return next(m for m in apps.get_models() if m._meta.db_table == tabela)


def test_toda_tabela_do_grao_tem_model_e_colunas_existem():
    for tabela, colunas in catalogo.GRAOS.items():
        campos = {f.name for f in _model_da_tabela(tabela)._meta.concrete_fields}
        assert set(colunas) <= campos, f"{tabela}: {set(colunas) - campos}"


def test_toda_tabela_sigcon_tem_grao_declarado():
    """Tabela nova no models.py sem grão no catálogo ficaria sem teste de unicidade."""
    assert set(volumetria.tabelas_sigcon()) == set(catalogo.GRAOS)


@pytest.mark.parametrize("tabela", sorted(catalogo.GRAOS))
def test_grao_do_catalogo_e_o_do_yaml(tabela):
    """O grão tem uma única fonte da verdade: o `grao:` do YAML do modelo."""
    esquema = yaml.safe_load((SCHEMAS / f"{tabela}.yaml").read_text(encoding="utf-8"))
    if not esquema.get("grao"):
        # Só a sigcon_tabela_uo (fora do modelo v1.0): grão ainda não fechado.
        assert tabela in catalogo.GRAOS_EM_TRATAMENTO
        return
    assert catalogo.GRAOS[tabela] == esquema["grao"]


def test_graos_corrigidos_nao_repetem_o_catalogo_antigo():
    """Regressão: antes o grão era SIAFI+UO+siafi_uo (redundante) e incluía
    sigcon_chave_siconv, que está fora do modelo SIGCON e não tem model."""
    assert catalogo.GRAOS["sigcon_convenio"] == ["siafi_uo"]
    assert catalogo.GRAOS["sigcon_cronograma_desembolso"] == [
        "cd_plano_trabalho", "nr_ano_desembolso", "nr_mes_desembolso",
    ]
    assert "sigcon_chave_siconv" not in catalogo.GRAOS
    assert "sigcon_concedente" in catalogo.GRAOS


def test_grao_em_tratamento_gera_alerta_e_os_demais_erro():
    for t in catalogo.TESTES_C[: len(catalogo.GRAOS)]:
        esperado = "ALERTA" if t["tabela"] in catalogo.GRAOS_EM_TRATAMENTO else "ERRO"
        assert t["severidade"] == esperado, t["tabela"]


# ---------------------------------------------------------------------------
# Construtores de SQL
# ---------------------------------------------------------------------------


def test_sql_unicidade_agrupa_pelas_colunas_do_grao():
    sql = sql_unicidade("t", ["a", "b"])

    assert "GROUP BY a, b" in sql and "HAVING COUNT(*) > 1" in sql
    assert "WHERE" not in sql


def test_sql_unicidade_com_filtro_filtra_antes_de_agrupar():
    sql = sql_unicidade("t", ["a"], "x IS NULL")

    assert sql.index("WHERE (x IS NULL)") < sql.index("GROUP BY")


def test_sql_orfaos_sem_e_com_filtro_tem_where_valido():
    sem = sql_orfaos("f", "c", "p", "k")
    com = sql_orfaos("f", "c", "p", "k", "f.x IS NULL")

    assert sem.count("WHERE (f.c IS NOT NULL)") == 1
    assert "(f.x IS NULL)" in com and "NOT EXISTS" in com
    assert com.count("WHERE ") == 2  # o do filtro + o da subconsulta


def test_sql_valores_aceitos_e_formato_ignoram_nulos():
    assert "c IS NOT NULL" in sql_valores_aceitos("t", "c", [1, 2])
    assert "c IS NOT NULL" in sql_formato("t", "c", r"^\d$")


# ---------------------------------------------------------------------------
# O catálogo contra o esquema real (banco de teste)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "teste", [t for t in catalogo.TESTES if "sql" in t], ids=lambda t: t["id"]
)
def test_toda_consulta_do_catalogo_e_sql_valido(teste):
    """Coluna ou tabela com nome errado estoura aqui, não na primeira validação real."""
    qt, amostra = _executar(teste["sql"])

    assert isinstance(qt, int) and isinstance(amostra, list)


@pytest.mark.django_db
def test_banco_vazio_so_reprova_o_teste_de_tabelas_must():
    """Sem dados nenhuma regra é violada, exceto 'Must não vazia' — que é o ponto dela."""
    reprovados = [
        t["id"]
        for t in catalogo.TESTES
        if "sql" in t and _executar(t["sql"])[0] > 0
    ]

    assert reprovados == ["T-A02"]


@pytest.mark.django_db
def test_tabelas_must_lista_cada_tabela_vazia():
    qt, amostra = _executar(_teste("T-A02")["sql"])

    assert qt == len(catalogo.TABELAS_MUST)
    assert {a["tabela"] for a in amostra} <= set(catalogo.TABELAS_MUST)


# ---------------------------------------------------------------------------
# As regras enxergam a violação
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_grao_detecta_codigo_sequencial_repetido():
    # sigcon_convenio.siafi_uo é UNIQUE no model, então o banco já barra a
    # duplicata ali; as demais tabelas só contam com este teste.
    for _ in range(2):
        SigconChaveConvenio.objects.create(cd_convenio_sequencial="42")

    qt, amostra = _executar(_teste(_id_do_grao("sigcon_chave_convenio"))["sql"])

    assert qt == 1 and amostra[0]["qt"] == 2


@pytest.mark.django_db
def test_grao_ignora_convenios_sem_siafi_uo():
    """Os 4 convênios sem SIAFI (T1) não são duplicata entre si: NULL = NULL no GROUP BY."""
    SigconConvenio.objects.create(siafi_uo=None)
    SigconConvenio.objects.create(siafi_uo=None)

    assert _executar(_teste(_id_do_grao("sigcon_convenio"))["sql"])[0] == 0


@pytest.mark.django_db
def test_chave_nula_do_convenio_e_excecao_conhecida_com_limite():
    teste = next(
        t for t in catalogo.TESTES_D
        if t["tabela"] == "sigcon_convenio" and "siafi_uo" in t["descricao"]
    )
    SigconConvenio.objects.create(siafi_uo=None)
    qt = _executar(teste["sql"])[0]

    assert qt == 1
    assert teste["limite"] == 8
    assert severidade_efetiva(teste, qt) == "ALERTA"


@pytest.mark.django_db
def test_grao_do_cronograma_ignora_linhas_marcadas_pelo_bloco_desalinhado():
    """Linhas com ds_alerta_linha ficam no banco (a carga não descarta) mas não
    reprovam o grão: o bloco do BO é artefato, não duplicata (P6)."""
    for _ in range(2):
        SigconCronogramaDesembolso.objects.create(
            cd_plano_trabalho=None, ds_alerta_linha="bloco desalinhado do BO"
        )
    teste = _teste(_id_do_grao("sigcon_cronograma_desembolso"))

    assert _executar(teste["sql"])[0] == 0


@pytest.mark.django_db
def test_grao_do_cronograma_detecta_duplicata_real():
    for _ in range(2):
        SigconCronogramaDesembolso.objects.create(
            cd_plano_trabalho="100", nr_ano_desembolso=2024, nr_mes_desembolso=3
        )
    teste = _teste(_id_do_grao("sigcon_cronograma_desembolso"))

    assert _executar(teste["sql"])[0] == 1


@pytest.mark.django_db
def test_grao_do_plano_aplicacao_inclui_o_ano():
    """Mesma classificação em anos diferentes não é duplicata (P8/V14)."""
    for ano in (2023, 2024):
        SigconPlanoAplicacao.objects.create(
            cd_plano_trabalho="100", cd_uo="1261", nr_ano_exercicio=ano
        )
    teste = _teste(_id_do_grao("sigcon_plano_aplicacao"))
    assert _executar(teste["sql"])[0] == 0

    SigconPlanoAplicacao.objects.create(
        cd_plano_trabalho="100", cd_uo="1261", nr_ano_exercicio=2024
    )
    assert _executar(teste["sql"])[0] == 1


@pytest.mark.django_db
def test_grao_em_tratamento_da_tabela_uo_aceita_o_mesmo_codigo_em_anos_diferentes():
    SigconTabelaUo.objects.create(cd_uo="1261", nm_uo="A", nr_ano_exercicio=2023)
    SigconTabelaUo.objects.create(cd_uo="1261", nm_uo="B", nr_ano_exercicio=2024)

    assert _executar(_teste(_id_do_grao("sigcon_tabela_uo"))["sql"])[0] == 0


@pytest.mark.django_db
def test_formato_do_cd_uo_exige_4_caracteres():
    SigconConvenio.objects.create(siafi_uo="x", cd_uo="126")
    teste = next(
        t for t in catalogo.TESTES_E
        if t["tabela"] == "sigcon_convenio" and "cd_uo" in t["descricao"]
    )

    assert _executar(teste["sql"])[0] == 1


@pytest.mark.django_db
def test_siafi_uo_deve_ser_a_concatenacao_sem_separador():
    SigconChaveConvenio.objects.create(nr_siafi="123", cd_uo="4567", siafi_uo="1234567")
    SigconChaveConvenio.objects.create(nr_siafi="123", cd_uo="4567", siafi_uo="123-4567")
    teste = next(
        t for t in catalogo.TESTES_E
        if t["tabela"] == "sigcon_chave_convenio" and "siafi_uo" in t["descricao"]
    )

    qt, amostra = _executar(teste["sql"])

    assert qt == 1 and amostra[0]["siafi_uo"] == "123-4567"


@pytest.mark.django_db
def test_orfao_detecta_convenio_geral_sem_ponte():
    SigconChaveConvenio.objects.create(cd_convenio_sequencial="1")
    SigconConvenioGeral.objects.create(cd_convenio_sequencial="1")
    SigconConvenioGeral.objects.create(cd_convenio_sequencial="2")
    teste = next(
        t for t in catalogo.TESTES_F
        if t["tabela"] == "sigcon_convenio_geral"
    )

    qt, amostra = _executar(teste["sql"])

    assert teste["severidade"] == "ERRO"
    assert qt == 1 and amostra[0]["cd_convenio_sequencial"] == "2"


@pytest.mark.django_db
def test_orfao_do_cronograma_ignora_linhas_marcadas():
    SigconCronogramaDesembolso.objects.create(
        cd_plano_trabalho="999", ds_alerta_linha="bloco desalinhado do BO"
    )
    teste = next(
        t for t in catalogo.TESTES_F if t["tabela"] == "sigcon_cronograma_desembolso"
    )
    assert _executar(teste["sql"])[0] == 0

    SigconCronogramaDesembolso.objects.create(cd_plano_trabalho="999")
    assert _executar(teste["sql"])[0] == 1


@pytest.mark.django_db
def test_mes_do_cronograma_fora_de_1_a_12_reprova_so_nas_linhas_validas():
    SigconCronogramaDesembolso.objects.create(
        cd_plano_trabalho="1", nr_ano_desembolso=2024, nr_mes_desembolso=13
    )
    SigconCronogramaDesembolso.objects.create(
        cd_plano_trabalho=None, nr_mes_desembolso=99, ds_alerta_linha="bloco"
    )
    teste = next(t for t in catalogo.TESTES_E if "nr_mes_desembolso" in t["descricao"])

    assert _executar(teste["sql"])[0] == 1


# ---------------------------------------------------------------------------
# Volumetria
# ---------------------------------------------------------------------------


@pytest.fixture
def silver_sintetica(tmp_path):
    (tmp_path / "silver").mkdir()
    with override_settings(DATA_DIR=str(tmp_path)):
        yield tmp_path / "silver"


def _gravar(silver, tabela, linhas):
    pd.DataFrame({"cd_uo": [str(i) for i in range(linhas)]}).to_parquet(
        silver / f"{tabela}.parquet", index=False
    )


@pytest.mark.django_db
def test_volumetria_aponta_so_as_tabelas_que_divergem(silver_sintetica):
    for tabela in volumetria.tabelas_sigcon():
        _gravar(silver_sintetica, tabela, 0)
    _gravar(silver_sintetica, "sigcon_tabela_uo", 3)  # parquet 3, banco 0
    SigconConvenio.objects.create(siafi_uo="1")  # parquet 0, banco 1

    qt, amostra = volumetria.teste_volumetria()

    assert qt == 2
    assert {a["fonte"]: (a["linhas_parquet"], a["linhas_banco"]) for a in amostra} == {
        "sigcon_tabela_uo": (3, 0),
        "sigcon_convenio": (0, 1),
    }


@pytest.mark.django_db
def test_volumetria_sem_divergencia(silver_sintetica):
    for tabela in volumetria.tabelas_sigcon():
        _gravar(silver_sintetica, tabela, 0)

    assert volumetria.teste_volumetria() == (0, [])


@pytest.mark.django_db
def test_volumetria_parquet_ausente_e_divergencia_nao_excecao(silver_sintetica):
    """Uma fonte sem Silver não pode impedir a checagem das outras."""
    for tabela in volumetria.tabelas_sigcon():
        if tabela != "sigcon_concedente":
            _gravar(silver_sintetica, tabela, 0)

    qt, amostra = volumetria.teste_volumetria()

    assert qt == 1
    assert amostra == [
        {"fonte": "sigcon_concedente", "linhas_parquet": None, "linhas_banco": 0}
    ]


def test_volumetria_le_o_data_dir_no_momento_da_chamada(tmp_path):
    with override_settings(DATA_DIR=str(tmp_path)):
        assert volumetria.pasta_silver() == tmp_path / "silver"


# ---------------------------------------------------------------------------
# O comando
# ---------------------------------------------------------------------------


def _catalogo_curto(*testes):
    return mock.patch.object(cmd, "TESTES", list(testes))


_PASSA = {
    "id": "T-X01", "severidade": "ERRO", "tabela": "sigcon_tabela_uo",
    "descricao": "sem linhas", "sql": "SELECT 1 AS a WHERE FALSE",
}
_ALERTA_FALHA = {
    "id": "T-X02", "severidade": "ALERTA", "tabela": "sigcon_tabela_uo",
    "descricao": "uma linha", "sql": "SELECT 1 AS a",
}
_ERRO_FALHA = {
    "id": "T-X03", "severidade": "ERRO", "tabela": "sigcon_tabela_uo",
    "descricao": "uma linha", "sql": "SELECT 2 AS a",
}


@pytest.mark.django_db
def test_comando_grava_um_resultado_por_teste_com_a_mesma_execucao():
    with _catalogo_curto(_PASSA, _ALERTA_FALHA):
        call_command("validar_sigcon")

    resultados = {r.id_teste: r for r in ResultadoValidacao.objects.all()}
    assert set(resultados) == {"T-X01", "T-X02"}
    assert len({r.execucao for r in resultados.values()}) == 1
    assert isinstance(resultados["T-X01"].execucao, uuid.UUID)
    assert resultados["T-X01"].status == "PASSOU" and resultados["T-X01"].qt_falhas == 0
    assert resultados["T-X02"].status == "FALHOU" and resultados["T-X02"].qt_falhas == 1
    assert resultados["T-X02"].amostra == [{"a": 1}]


@pytest.mark.django_db
def test_alerta_que_falha_nao_derruba_o_comando():
    with _catalogo_curto(_PASSA, _ALERTA_FALHA):
        call_command("validar_sigcon")  # não levanta


@pytest.mark.django_db
def test_erro_que_falha_levanta_command_error_depois_de_gravar_tudo():
    with _catalogo_curto(_ERRO_FALHA, _PASSA):
        with pytest.raises(CommandError) as excinfo:
            call_command("validar_sigcon")

    assert "T-X03" in str(excinfo.value) and "T-X01" not in str(excinfo.value)
    assert ResultadoValidacao.objects.count() == 2, "o teste seguinte também rodou"


@pytest.mark.django_db
def test_execucoes_diferentes_tem_uuids_diferentes():
    with _catalogo_curto(_PASSA):
        call_command("validar_sigcon")
        call_command("validar_sigcon")

    assert ResultadoValidacao.objects.values("execucao").distinct().count() == 2


@pytest.mark.django_db
def test_teste_por_funcao_entra_no_resultado():
    funcao = mock.Mock(return_value=(2, [{"fonte": "x"}]))
    teste = {
        "id": "T-X04", "severidade": "ALERTA", "tabela": "sigcon_*",
        "descricao": "por função", "funcao": funcao,
    }

    with _catalogo_curto(teste):
        call_command("validar_sigcon")

    funcao.assert_called_once_with()
    r = ResultadoValidacao.objects.get()
    assert (r.status, r.qt_falhas, r.amostra) == ("FALHOU", 2, [{"fonte": "x"}])


@pytest.mark.django_db
def test_amostra_limitada_a_5_linhas_mas_conta_todas():
    teste = {
        "id": "T-X05", "severidade": "ALERTA", "tabela": "t", "descricao": "d",
        "sql": "SELECT g AS n FROM generate_series(1, 12) AS g",
    }

    with _catalogo_curto(teste):
        call_command("validar_sigcon")

    r = ResultadoValidacao.objects.get()
    assert r.qt_falhas == 12 and len(r.amostra) == 5


def test_resultados_do_sigcon_nao_dividem_tabela_com_os_do_grp():
    """Regressão: as duas tabelas usavam 'dq_resultado_validacao' (models.E028)."""
    from apps.grp.models import ResultadoValidacao as ResultadoGrp

    assert ResultadoValidacao._meta.db_table != ResultadoGrp._meta.db_table
