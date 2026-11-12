"""
Regras do catálogo SIGCON acrescentadas na Fase 3: limites de exceção conhecida,
encoding (mojibake), volumetria histórica, arquivos de entrada, colisões de plano
compartilhado, domínio de valores, datas e o fuso das colunas dh_/dt_.

Linhas sintéticas apenas; nenhum dado real é tocado.
"""

import datetime
import os
import time
from unittest import mock

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.sigcon.management.commands import validar_sigcon as cmd_validar
from apps.sigcon.models import (
    ResultadoValidacao,
    SigconChaveConvenio,
    SigconConvenio,
    SigconConvenioGeral,
    SigconDeclaracaoContrapartida,
    SigconHistoricoCarga,
    SigconPlanoTrabalho,
    SigconProrrogacaoOficio,
    SigconTermoAditivo,
    SigconChaveTermoAditivo,
)
from apps.sigcon.validacao import arquivos, catalogo, limites, texto, volumetria
from apps.sigcon.validacao.generico import sql_valores_aceitos


def _executar(sql):
    return cmd_validar.Command()._rodar(sql)


def _por_descricao(lista, trecho, tabela=None):
    return next(
        t for t in lista
        if trecho in t["descricao"] and (tabela is None or t["tabela"] == tabela)
    )


# ---------------------------------------------------------------------------
# Limites de exceção conhecida
# ---------------------------------------------------------------------------


def test_severidade_efetiva_alerta_ate_o_limite_e_erro_acima():
    teste = {"severidade": "ERRO", "limite": 8}

    assert limites.severidade_efetiva(teste, 0) == "ERRO"  # nada falhou: vale a do catálogo
    assert limites.severidade_efetiva(teste, 1) == "ALERTA"
    assert limites.severidade_efetiva(teste, 8) == "ALERTA"
    assert limites.severidade_efetiva(teste, 9) == "ERRO"


def test_teste_sem_limite_mantem_a_severidade_do_catalogo():
    assert limites.severidade_efetiva({"severidade": "ALERTA"}, 500) == "ALERTA"
    assert limites.severidade_efetiva({"severidade": "ERRO"}, 500) == "ERRO"


def test_limites_usam_os_numeros_do_banco_real_e_nao_os_do_pdf():
    assert limites.LIMITES_CONHECIDOS["convenios_sem_siafi_uo"] == 8  # PDF: 4
    assert limites.LIMITES_CONHECIDOS["declaracoes_sem_ponte"] == 2438  # PDF: 2.437
    assert limites.LIMITES_CONHECIDOS["plano_aplicacao_sem_plano_trabalho"] == 842
    assert limites.LIMITES_CONHECIDOS["planos_desembolso_diferente_aplicacao_concedente"] == 484
    assert limites.LIMITES_CONHECIDOS["planos_desembolso_diferente_aplicacao_proponente"] == 248


def test_todo_limite_declarado_e_usado_no_catalogo_e_vice_versa():
    usadas = {t["chave_limite"] for t in catalogo.TESTES if "chave_limite" in t}

    assert usadas == set(limites.LIMITES_CONHECIDOS), (
        f"sem uso: {set(limites.LIMITES_CONHECIDOS) - usadas}; "
        f"sem limite declarado: {usadas - set(limites.LIMITES_CONHECIDOS)}"
    )
    for t in catalogo.TESTES:
        if "chave_limite" in t:
            assert t["limite"] == limites.LIMITES_CONHECIDOS[t["chave_limite"]], t["id"]
            assert "exceção conhecida" in t["descricao"], t["id"]


def test_teste_com_limite_e_sempre_declarado_como_erro():
    """A severidade do catálogo é a máxima; o ALERTA é calculado até o limite."""
    for t in catalogo.TESTES:
        if "limite" in t:
            assert t["severidade"] == "ERRO", t["id"]
            assert t["limite"] > 0, t["id"]


@pytest.mark.django_db
def test_comando_grava_alerta_dentro_do_limite_e_erro_acima_dele():
    base = {
        "id": "T-X01", "tabela": "sigcon_convenio", "descricao": "d",
        "sql": "SELECT g FROM generate_series(1, 3) AS g", "severidade": "ERRO",
    }
    dentro = dict(base, limite=3)
    acima = dict(base, id="T-X02", limite=2)

    with mock.patch.object(cmd_validar, "TESTES", [dentro]):
        call_command("validar_sigcon")  # 3 <= 3: só ALERTA, não levanta
    assert ResultadoValidacao.objects.get(id_teste="T-X01").severidade == "ALERTA"

    with mock.patch.object(cmd_validar, "TESTES", [acima]):
        with pytest.raises(Exception, match="T-X02"):
            call_command("validar_sigcon")  # 3 > 2: ERRO bloqueante
    assert ResultadoValidacao.objects.get(id_teste="T-X02").severidade == "ERRO"


@pytest.mark.django_db
def test_erros_da_fonte_conhecidos_nao_bloqueiam_ate_o_limite():
    """CNPJ de proponente com o código da UO (4 dígitos): erro da fonte, 4 casos conhecidos."""
    teste = _por_descricao(catalogo.TESTES_E, "nr_cnpj_proponente", "sigcon_plano_trabalho")
    for i in range(4):
        SigconPlanoTrabalho.objects.create(cd_plano_trabalho=str(i), nr_cnpj_proponente="1231")
    qt = _executar(teste["sql"])[0]
    assert (qt, limites.severidade_efetiva(teste, qt)) == (4, "ALERTA")

    SigconPlanoTrabalho.objects.create(cd_plano_trabalho="novo", nr_cnpj_proponente="999")
    qt = _executar(teste["sql"])[0]
    assert (qt, limites.severidade_efetiva(teste, qt)) == (5, "ERRO")


# ---------------------------------------------------------------------------
# Encoding: mojibake
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "valor",
    ["Construção de UBS", "ConvÃªnio nÂº 923", "pontuaÃ§Ã£o", "traÃ§o â€“ meio", "NÃ¿CLEO"],
)
def test_mojibake_detecta_utf8_lido_como_cp1252(valor):
    valor = valor.replace("Construção de UBS", "ConstruÃ§Ã£o de UBS")
    SigconPlanoTrabalho.objects.create(cd_plano_trabalho="1", nm_plano_trabalho=valor)

    qt, amostra = texto.teste_mojibake()

    assert qt == 1
    assert amostra[0]["tabela"] == "sigcon_plano_trabalho"
    assert amostra[0]["coluna"] == "nm_plano_trabalho"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "valor",
    ["CONSTRUÇÃO DA UBS", "NÃO INFORMADO", "AÇÃO SOCIAL", "Convênio nº 923/2017", "Ministério – Saúde"],
)
def test_mojibake_nao_confunde_portugues_legitimo(valor):
    """'Ã' maiúsculo seguido de letra (NÃO, AÇÃO) é texto correto, não defeito."""
    SigconPlanoTrabalho.objects.create(cd_plano_trabalho="1", nm_plano_trabalho=valor)

    assert texto.teste_mojibake() == (0, [])


@pytest.mark.django_db
def test_mojibake_amostra_nao_copia_o_texto_da_celula():
    SigconPlanoTrabalho.objects.create(
        cd_plano_trabalho="1", tx_objeto="Obra de JoÃ£o da Silva, CPF 000.000.000-00"
    )

    _, amostra = texto.teste_mojibake()

    assert set(amostra[0]) == {"tabela", "coluna", "linhas", "ids"}
    assert "Silva" not in str(amostra)


@pytest.mark.django_db
def test_mojibake_varre_tabelas_diferentes_e_so_colunas_de_texto():
    SigconPlanoTrabalho.objects.create(cd_plano_trabalho="1", nm_plano_trabalho="ç mal Ã§")
    SigconTermoAditivo.objects.create(cd_termo_aditivo="1", tx_justificativa="JustificaÃ§Ã£o")

    qt, amostra = texto.teste_mojibake()

    assert qt == 2
    assert {(a["tabela"], a["coluna"]) for a in amostra} == {
        ("sigcon_plano_trabalho", "nm_plano_trabalho"),
        ("sigcon_termo_aditivo", "tx_justificativa"),
    }


def test_mojibake_esta_no_catalogo_como_erro_sem_limite():
    teste = _por_descricao(catalogo.TESTES_E, "mojibake")

    assert teste["severidade"] == "ERRO" and "limite" not in teste
    assert teste["funcao"] is texto.teste_mojibake


# ---------------------------------------------------------------------------
# Volumetria histórica
# ---------------------------------------------------------------------------


def _historico(tabela, *contagens):
    """Grava cargas em ordem cronológica (a última é a mais recente)."""
    for qt in contagens:
        SigconHistoricoCarga.objects.create(tabela=tabela, qt_linhas=qt)


@pytest.mark.django_db
def test_primeira_carga_sem_historico_passa():
    assert volumetria.teste_variacao_volumetria(0.05, 0.30) == (0, [])
    _historico("sigcon_convenio", 5000)  # uma só carga: nada para comparar
    assert volumetria.teste_variacao_volumetria(0.05, 0.30) == (0, [])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "anterior,atual,alerta,erro",
    [
        (1000, 1000, 0, 0),    # igual
        (1000, 1050, 0, 0),    # exatamente 5%: não passa de 5%
        (1000, 1051, 1, 0),    # 5,1%: ALERTA
        (1000, 900, 1, 0),     # queda de 10%: ALERTA
        (1000, 1300, 1, 0),    # exatamente 30%: ainda ALERTA
        (1000, 1301, 0, 1),    # 30,1%: ERRO
        (1000, 100, 0, 1),     # queda de 90%: ERRO
        (0, 0, 0, 0),          # vazia nas duas
        (0, 10, 0, 1),         # nasceu: 100%
    ],
)
def test_faixas_de_variacao(anterior, atual, alerta, erro):
    _historico("sigcon_convenio", anterior, atual)

    assert volumetria.teste_variacao_volumetria(0.05, 0.30)[0] == alerta
    assert volumetria.teste_variacao_volumetria(0.30)[0] == erro


@pytest.mark.django_db
def test_compara_so_as_duas_cargas_mais_recentes():
    _historico("sigcon_convenio", 100, 5000, 5100)  # a de 100 já é história antiga

    qt, amostra = volumetria.teste_variacao_volumetria(0.05, 0.30)

    assert qt == 0 and amostra == []


@pytest.mark.django_db
def test_amostra_traz_as_duas_contagens_e_o_percentual():
    _historico("sigcon_tabela_uo", 1000, 1200)

    _, amostra = volumetria.teste_variacao_volumetria(0.05, 0.30)

    assert amostra == [
        {"fonte": "sigcon_tabela_uo", "linhas_anterior": 1000, "linhas_atual": 1200,
         "variacao_pct": 20.0}
    ]


def test_catalogo_tem_os_dois_testes_de_variacao_com_as_faixas_pedidas():
    alerta = _por_descricao(catalogo.TESTES_A, "5%")
    erro = _por_descricao(catalogo.TESTES_A, "mais de 30% em relação")

    assert (alerta["severidade"], erro["severidade"]) == ("ALERTA", "ERRO")
    assert (catalogo.VARIACAO_ALERTA, catalogo.VARIACAO_ERRO) == (0.05, 0.30)


@pytest.mark.django_db
def test_carregar_sigcon_registra_a_contagem_de_cada_carga_bem_sucedida():
    from apps.sigcon.management.commands import carregar_sigcon as cmd

    loaders = {
        "sigcon_tabela_uo": mock.Mock(return_value={"apagados": 0, "inseridos": 7}),
        "sigcon_concedente": mock.Mock(side_effect=ValueError("falhou")),
    }
    with mock.patch.object(cmd, "_LOADERS_SIGCON", loaders):
        with pytest.raises(Exception):
            call_command(
                "carregar_sigcon", "--fonte", "sigcon_tabela_uo", "--fonte", "sigcon_concedente"
            )

    assert list(SigconHistoricoCarga.objects.values_list("tabela", "qt_linhas")) == [
        ("sigcon_tabela_uo", 7)
    ], "só a carga que deu certo entra no histórico"


def test_historico_nao_entra_nos_testes_de_tabelas_sigcon():
    """dq_historico_carga_sigcon fica fora do prefixo sigcon_: não é tabela do modelo."""
    assert "dq_historico_carga_sigcon" not in volumetria.tabelas_sigcon()


# ---------------------------------------------------------------------------
# Arquivos de entrada
# ---------------------------------------------------------------------------


@pytest.fixture
def raw_sigcon(tmp_path):
    """DATA_DIR com todos os arquivos esperados, modificados agora."""
    with override_settings(DATA_DIR=str(tmp_path)):
        for caminho in arquivos.arquivos_esperados().values():
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(b"x")
        yield tmp_path


def test_arquivos_esperados_vem_de_fontes_e_cobrem_as_tabelas_sigcon(tmp_path):
    with override_settings(DATA_DIR=str(tmp_path)):
        esperados = arquivos.arquivos_esperados()

    assert set(esperados) == set(volumetria.tabelas_sigcon())
    assert esperados["sigcon_convenio"] == tmp_path / "raw" / "sigcon" / "dcgce_convenio.xlsx"


def test_todos_presentes_e_recentes_passa(raw_sigcon):
    assert arquivos.teste_arquivos_ausentes() == (0, [])
    assert arquivos.teste_arquivos_antigos() == (0, [])


def test_arquivo_ausente_e_listado(raw_sigcon):
    (raw_sigcon / "raw" / "sigcon" / "dcgce_convenio.xlsx").unlink()

    qt, amostra = arquivos.teste_arquivos_ausentes()

    assert qt == 1
    assert amostra[0]["fonte"] == "sigcon_convenio"
    assert amostra[0]["arquivo"].endswith("dcgce_convenio.xlsx")


def test_arquivo_ausente_nao_conta_como_antigo(raw_sigcon):
    (raw_sigcon / "raw" / "sigcon" / "dcgce_convenio.xlsx").unlink()

    assert arquivos.teste_arquivos_antigos() == (0, [])


def _envelhecer(caminho, dias):
    t = time.time() - dias * 86400
    os.utime(caminho, (t, t))


def test_arquivo_com_mais_de_n_dias_e_alerta(raw_sigcon):
    _envelhecer(raw_sigcon / "raw" / "sigcon" / "dcgce_Geral.xlsx", 10)

    qt, amostra = arquivos.teste_arquivos_antigos()  # padrão: 7 dias

    assert qt == 1
    assert amostra[0]["fonte"] == "sigcon_convenio_geral"
    assert amostra[0]["dias"] == 10


def test_limite_de_dias_e_configuravel_por_setting(raw_sigcon):
    _envelhecer(raw_sigcon / "raw" / "sigcon" / "dcgce_Geral.xlsx", 10)

    with override_settings(SIGCON_RAW_MAX_DIAS=30):
        assert arquivos.teste_arquivos_antigos() == (0, [])
    with override_settings(SIGCON_RAW_MAX_DIAS=5):
        assert arquivos.teste_arquivos_antigos()[0] == 1


def test_setting_padrao_e_7_dias():
    from django.conf import settings

    assert settings.SIGCON_RAW_MAX_DIAS == 7
    assert arquivos.MAX_DIAS_PADRAO == 7


def test_catalogo_arquivo_ausente_e_erro_e_antigo_e_alerta():
    ausente = _por_descricao(catalogo.TESTES_A, "existe em data/raw")
    antigo = _por_descricao(catalogo.TESTES_A, "SIGCON_RAW_MAX_DIAS")

    assert (ausente["severidade"], antigo["severidade"]) == ("ERRO", "ALERTA")


# ---------------------------------------------------------------------------
# Colisões de plano compartilhado
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_colisao_em_plano_compartilhado_conhecido_nao_alerta():
    teste = _por_descricao(catalogo.TESTES_C, "planos compartilhados conhecidos")
    for seq in ("1", "2"):
        SigconConvenioGeral.objects.create(cd_convenio_sequencial=seq, cd_plano_trabalho="7964")

    assert _executar(teste["sql"])[0] == 0


@pytest.mark.django_db
def test_colisao_em_plano_novo_alerta_com_o_codigo():
    teste = _por_descricao(catalogo.TESTES_C, "planos compartilhados conhecidos")
    for seq in ("1", "2"):
        SigconConvenioGeral.objects.create(cd_convenio_sequencial=seq, cd_plano_trabalho="55555")

    qt, amostra = _executar(teste["sql"])

    assert teste["severidade"] == "ALERTA"
    assert qt == 1 and amostra[0] == {"cd_plano_trabalho": "55555", "qt": 2}


@pytest.mark.django_db
def test_planos_nulos_nao_sao_colisao():
    teste = _por_descricao(catalogo.TESTES_C, "planos compartilhados conhecidos")
    for seq in ("1", "2"):
        SigconConvenioGeral.objects.create(cd_convenio_sequencial=seq, cd_plano_trabalho=None)

    assert _executar(teste["sql"])[0] == 0


def test_lista_de_planos_conhecidos_tem_os_18_codigos_medidos():
    assert len(catalogo.PLANOS_COMPARTILHADOS_CONHECIDOS) == 18
    assert len(set(catalogo.PLANOS_COMPARTILHADOS_CONHECIDOS)) == 18
    assert "7964" in catalogo.PLANOS_COMPARTILHADOS_CONHECIDOS


# ---------------------------------------------------------------------------
# Domínio de valores
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_situacao_nova_e_alerta_e_valor_conhecido_passa():
    teste = _por_descricao(catalogo.TESTES_H, "ds_situacao_convenio")
    SigconConvenio.objects.create(siafi_uo="1", ds_situacao_convenio="VIGENTE")
    SigconConvenio.objects.create(siafi_uo="2", ds_situacao_convenio=None)  # nulo não é valor novo
    assert _executar(teste["sql"])[0] == 0

    SigconConvenio.objects.create(siafi_uo="3", ds_situacao_convenio="SUSPENSO")
    qt, amostra = _executar(teste["sql"])

    assert teste["severidade"] == "ALERTA"
    assert qt == 1 and amostra[0]["ds_situacao_convenio"] == "SUSPENSO"


def test_todo_dominio_tem_um_teste_alerta_e_nenhum_corrige_dado():
    assert len(catalogo.TESTES_H) == len(catalogo.DOMINIOS)
    for t in catalogo.TESTES_H:
        assert t["severidade"] == "ALERTA"
        assert t["sql"].lstrip().upper().startswith("SELECT")


def test_dominios_cobrem_as_situacoes_de_cada_tabela_com_status():
    tabelas = {tabela for tabela, _ in catalogo.DOMINIOS}
    assert {
        "sigcon_convenio", "sigcon_plano_trabalho", "sigcon_termo_aditivo",
        "sigcon_declaracao_contrapartida", "sigcon_concedente",
    } <= tabelas


def test_valores_com_apostrofo_viram_literal_sql_valido():
    sql = sql_valores_aceitos("t", "c", ["D'Ouro", "ok", 3, True])

    assert "'D''Ouro'" in sql and "'ok'" in sql and "3" in sql and "TRUE" in sql
    assert '"D' not in sql  # repr() usaria aspas duplas, que no SQL são identificador


@pytest.mark.django_db
def test_valor_com_apostrofo_nao_quebra_a_consulta():
    SigconConvenio.objects.create(siafi_uo="1", ds_situacao_convenio="D'Ouro")

    qt, _ = _executar(sql_valores_aceitos("sigcon_convenio", "ds_situacao_convenio", ["D'Ouro"]))

    assert qt == 0


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------


def _convenio_com_ponte(termo_inicial, seq="10", siafi_uo="1001261"):
    SigconConvenio.objects.create(
        siafi_uo=siafi_uo, dt_vigencia_termino_inicial=termo_inicial
    )
    SigconChaveConvenio.objects.create(cd_convenio_sequencial=seq, siafi_uo=siafi_uo)
    SigconChaveTermoAditivo.objects.create(cd_termo_aditivo=f"TA-{seq}", siafi_uo=siafi_uo)


@pytest.mark.django_db
def test_prorrogacao_deve_terminar_depois_do_termino_original():
    teste = _por_descricao(catalogo.TESTES_I, "prorrogação posterior ao término original")
    _convenio_com_ponte(datetime.date(2020, 12, 31))
    SigconProrrogacaoOficio.objects.create(
        cd_prorrogacao_oficio="ok", cd_convenio_sequencial="10",
        dt_vigencia_termino=datetime.date(2021, 6, 30),
    )
    assert _executar(teste["sql"])[0] == 0

    SigconProrrogacaoOficio.objects.create(
        cd_prorrogacao_oficio="igual", cd_convenio_sequencial="10",
        dt_vigencia_termino=datetime.date(2020, 12, 31),
    )
    SigconProrrogacaoOficio.objects.create(
        cd_prorrogacao_oficio="antes", cd_convenio_sequencial="10",
        dt_vigencia_termino=datetime.date(2020, 1, 1),
    )
    qt, amostra = _executar(teste["sql"])

    assert teste["severidade"] == "ALERTA"
    assert qt == 2
    assert {a["cd_prorrogacao_oficio"] for a in amostra} == {"igual", "antes"}


@pytest.mark.django_db
def test_so_aditivo_de_vigencia_precisa_terminar_depois_do_original():
    teste = _por_descricao(catalogo.TESTES_I, "aditivo de vigência posterior")
    _convenio_com_ponte(datetime.date(2020, 12, 31))
    SigconTermoAditivo.objects.create(
        cd_termo_aditivo="TA-10", tp_termo_aditivo="TA de Valor",
        dt_vigencia_termino=datetime.date(2019, 1, 1),  # de valor: não prorroga, não conta
    )
    assert _executar(teste["sql"])[0] == 0

    SigconTermoAditivo.objects.filter(cd_termo_aditivo="TA-10").update(
        tp_termo_aditivo="TA de Vigência e Valor"
    )
    assert _executar(teste["sql"])[0] == 1


@pytest.mark.django_db
def test_vigencia_inicio_nao_pode_passar_do_termino():
    SigconConvenio.objects.create(
        siafi_uo="1", dt_vigencia_inicio=datetime.date(2020, 5, 31),
        dt_vigencia_termino=datetime.date(2020, 5, 30),
    )
    SigconConvenio.objects.create(
        siafi_uo="2", dt_vigencia_inicio=datetime.date(2020, 1, 1),
        dt_vigencia_termino=datetime.date(2020, 12, 31),
    )
    SigconConvenio.objects.create(siafi_uo="3")  # sem datas: nada a comparar

    teste = _por_descricao(catalogo.TESTES_I, "Vigência coerente", "sigcon_convenio")
    qt, amostra = _executar(teste["sql"])

    assert qt == 1 and amostra[0]["siafi_uo"] == "1"


def test_todo_teste_de_data_e_alerta():
    assert catalogo.TESTES_I and all(t["severidade"] == "ALERTA" for t in catalogo.TESTES_I)


# ---------------------------------------------------------------------------
# dh_ x dt_ no fuso de Brasília (T-G09)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dh_na_madrugada_utc_e_o_dia_anterior_em_brasilia_nao_e_divergencia():
    """00:51 UTC de 08/02/2011 são 22:51 de 07/02 em Brasília: dt_emissao = 07/02 está certo."""
    teste = _por_descricao(catalogo.TESTES_G, "fuso America/Sao_Paulo")
    SigconDeclaracaoContrapartida.objects.create(
        cd_declaracao_contrapartida="2050",
        dh_emissao=datetime.datetime(2011, 2, 8, 0, 51, 12, tzinfo=datetime.timezone.utc),
        dt_emissao=datetime.date(2011, 2, 7),
        dh_parecer_aprovacao=datetime.datetime(2011, 4, 11, 15, 0, tzinfo=datetime.timezone.utc),
        dt_parecer_aprovacao=datetime.date(2011, 4, 11),
    )

    assert _executar(teste["sql"])[0] == 0


@pytest.mark.django_db
def test_dh_e_dt_realmente_diferentes_continuam_sendo_divergencia():
    teste = _por_descricao(catalogo.TESTES_G, "fuso America/Sao_Paulo")
    SigconDeclaracaoContrapartida.objects.create(
        cd_declaracao_contrapartida="1",
        dh_emissao=datetime.datetime(2011, 2, 8, 15, 0, tzinfo=datetime.timezone.utc),
        dt_emissao=datetime.date(2011, 2, 20),
    )

    qt, amostra = _executar(teste["sql"])

    assert qt == 1 and amostra[0]["cd_declaracao_contrapartida"] == "1"
