"""
Testes unitários dos serviços das abas de Consultas SIGCON.

Por que testar a camada de services e não a view?
  A view é apenas um roteador: recebe request, chama service, renderiza template.
  O service contém toda a lógica de join e filtragem — é o único lugar onde
  um bug de dado errado pode aparecer. Testar o service diretamente:
    - não precisa simular request/response nem cliente HTTP
    - cria dados de amostra diretamente no banco de testes
    - verifica os campos retornados, não o HTML renderizado
  Resultado: testes mais rápidos, isolados e reutilizáveis por qualquer consumidor
  dos serviços (views, commands de exportação, APIs futuras).

As tabelas do SIGCON são planas (sem ForeignKey) e se ligam por siafi_uo e pelos
códigos de plano, termo aditivo e convênio sequencial. Os testes montam essas
ligações pelas pontes sigcon_chave_*.

Fora do escopo deste arquivo (e do modelo SIGCON v1.0): SICONV, Controle SEI e
ConvenioIntegrado — saem como "—" em enrich_convenios_page.
"""

import datetime

from django.test import TestCase

from apps.sigcon.models import (
    SigconChaveConvenio,
    SigconChavePlanoTrabalho,
    SigconChaveTermoAditivo,
    SigconConcedente,
    SigconConvenio,
    SigconCronogramaDesembolso,
    SigconPlanoAplicacao,
    SigconPlanoTrabalho,
    SigconProrrogacaoOficio,
    SigconTermoAditivo,
    SigconUnidadeExecutora,
)
from apps.sigcon.services import (
    enrich_convenios_page,
    get_cronograma_qs,
    get_plano_aplicacao_qs,
    get_prorrogacao_qs,
    get_sigcon_qs,
    get_termos_aditivos_qs,
    get_unidades_executoras_qs,
)


# ---------------------------------------------------------------------------
# Dados de amostra reutilizáveis
# ---------------------------------------------------------------------------

SIAFI = "9309074"
UO = "1261"
SIAFI_UO = SIAFI + UO
NR_CONVENIO = "811906/2014"
SEQ = "1234"
PT = "PT-0001"

OUTRO_SIAFI = "999"
OUTRO_UO = "5555"


def _make_convenio(nr_convenio=NR_CONVENIO, nr_siafi=SIAFI, cd_uo=UO, **kwargs):
    """Convênio + as pontes de plano original e de convênio sequencial."""
    siafi_uo = f"{nr_siafi}{cd_uo}"
    conv = SigconConvenio.objects.create(
        nr_convenio=nr_convenio,
        nr_siafi=nr_siafi,
        cd_uo=cd_uo,
        siafi_uo=siafi_uo,
        ds_situacao_convenio=kwargs.pop("ds_situacao_convenio", "EM EXECUÇÃO"),
        **kwargs,
    )
    return conv


def _ponte_plano(cd_plano_trabalho=PT, nr_siafi=SIAFI, cd_uo=UO):
    SigconChavePlanoTrabalho.objects.create(
        cd_plano_trabalho=cd_plano_trabalho,
        nr_siafi=nr_siafi,
        cd_uo=cd_uo,
        siafi_uo=f"{nr_siafi}{cd_uo}",
    )


def _ponte_convenio(cd_convenio_sequencial=SEQ, nr_convenio=NR_CONVENIO, nr_siafi=SIAFI, cd_uo=UO):
    SigconChaveConvenio.objects.create(
        cd_convenio_sequencial=cd_convenio_sequencial,
        nr_convenio=nr_convenio,
        nr_siafi=nr_siafi,
        cd_uo=cd_uo,
        siafi_uo=f"{nr_siafi}{cd_uo}",
    )


def _ponte_termo(cd_termo_aditivo, cd_plano_trabalho=None, nr_siafi=SIAFI, cd_uo=UO):
    SigconChaveTermoAditivo.objects.create(
        cd_termo_aditivo=cd_termo_aditivo,
        cd_plano_trabalho=cd_plano_trabalho,
        nr_siafi=nr_siafi,
        cd_uo=cd_uo,
        siafi_uo=f"{nr_siafi}{cd_uo}",
    )


# ---------------------------------------------------------------------------
# Aba Convênios — enrich_convenios_page
# ---------------------------------------------------------------------------


class EnrichConveniosPageTest(TestCase):
    def test_lista_vazia_devolve_dict_vazio(self):
        self.assertEqual(enrich_convenios_page([]), {})

    def test_traz_plano_concedente_esfera_e_datas_pelo_siafi_uo(self):
        conv = _make_convenio(dt_vigencia_termino_inicial=datetime.date(2025, 12, 31))
        _ponte_plano()
        _ponte_convenio()
        SigconPlanoTrabalho.objects.create(
            cd_plano_trabalho=PT,
            nm_plano_trabalho="Plano de teste",
            tx_objeto="Obra",
            nm_concedente="Ministério X",
            nr_cnpj_concedente="11111111000111",
            nr_cnpj_proponente="22222222000122",
            tp_instrumento_siafi="Convênio",
        )
        SigconConcedente.objects.create(nr_cnpj_concedente="11111111000111", ds_esfera="Federal")

        extra = enrich_convenios_page([conv])[conv.pk]

        self.assertEqual(extra["plano_trabalho"], PT)
        self.assertEqual(extra["titulo"], "Plano de teste")
        self.assertEqual(extra["concedente"], "Ministério X")
        self.assertEqual(extra["esfera"], "Federal")
        self.assertEqual(extra["instrumento"], "Convênio")
        self.assertEqual(extra["proponente"], "22222222000122")
        self.assertEqual(extra["fim_vigencia_inicial"], datetime.date(2025, 12, 31))

    def test_sem_ligacoes_devolve_fallbacks(self):
        conv = _make_convenio(nr_convenio="SEM-LIGACAO/2024")

        extra = enrich_convenios_page([conv])[conv.pk]

        self.assertEqual(extra["proponente"], "—")
        self.assertEqual(extra["plano_trabalho"], "")
        self.assertEqual(extra["titulo"], "")
        self.assertIsNone(extra["fim_vigencia_inicial"])

    def test_siconv_e_sei_estao_fora_do_modelo_e_saem_como_traco(self):
        conv = _make_convenio()

        extra = enrich_convenios_page([conv])[conv.pk]

        self.assertEqual(extra["codigo_siconv"], "—")
        self.assertEqual(extra["no_sei"], "—")

    def test_convenio_sem_siafi_uo_nao_herda_dado_de_outro(self):
        """siafi_uo nulo não pode casar com ponte de siafi_uo nulo."""
        sem_chave = SigconConvenio.objects.create(nr_convenio="C-SEM-SIAFI", siafi_uo=None)
        SigconChavePlanoTrabalho.objects.create(cd_plano_trabalho="PT-ORFAO", siafi_uo=None)
        SigconPlanoTrabalho.objects.create(cd_plano_trabalho="PT-ORFAO", nm_plano_trabalho="Órfão")

        extra = enrich_convenios_page([sem_chave])[sem_chave.pk]

        self.assertEqual(extra["plano_trabalho"], "")
        self.assertEqual(extra["titulo"], "")


# ---------------------------------------------------------------------------
# Aba Plano de Aplicação — get_plano_aplicacao_qs
# ---------------------------------------------------------------------------


class PlanoAplicacaoQsTest(TestCase):
    def test_filtra_pelos_planos_do_convenio(self):
        _make_convenio()
        _ponte_plano()
        SigconPlanoAplicacao.objects.create(
            cd_plano_trabalho=PT, nr_ano_exercicio=2024, vl_aplicacao_concedente=1000
        )
        # plano de outro convênio — não deve aparecer
        SigconPlanoAplicacao.objects.create(cd_plano_trabalho="OUTRO-PT", nr_ano_exercicio=2024)

        qs, ctx = get_plano_aplicacao_qs(nr_convenio=NR_CONVENIO)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().cd_plano_trabalho, PT)
        self.assertEqual(ctx["siafi"], SIAFI)
        self.assertEqual(ctx["uo"], UO)
        self.assertEqual(ctx["cd_plano_trabalho"], PT)

    def test_inclui_o_plano_dos_termos_aditivos(self):
        _make_convenio()
        _ponte_plano()
        _ponte_termo("TA-1", cd_plano_trabalho="PT-ADITIVO")
        SigconPlanoAplicacao.objects.create(cd_plano_trabalho=PT)
        SigconPlanoAplicacao.objects.create(cd_plano_trabalho="PT-ADITIVO")

        qs, _ = get_plano_aplicacao_qs(nr_convenio=NR_CONVENIO)

        self.assertEqual(
            sorted(qs.values_list("cd_plano_trabalho", flat=True)), [PT, "PT-ADITIVO"]
        )

    def test_convenio_inexistente_retorna_vazio(self):
        qs, _ = get_plano_aplicacao_qs(nr_convenio="INEXISTENTE/9999")

        self.assertEqual(qs.count(), 0)

    def test_sem_filtro_retorna_todos(self):
        SigconPlanoAplicacao.objects.create(cd_plano_trabalho="A")
        SigconPlanoAplicacao.objects.create(cd_plano_trabalho="B")

        qs, _ = get_plano_aplicacao_qs()

        self.assertEqual(qs.count(), 2)

    def test_filtro_global_por_siafi_resolve_via_convenio(self):
        _make_convenio()
        _ponte_plano()
        SigconPlanoAplicacao.objects.create(cd_plano_trabalho=PT)
        SigconPlanoAplicacao.objects.create(cd_plano_trabalho="OUTRO-PT")

        qs, ctx = get_plano_aplicacao_qs(nr_siafi=SIAFI)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().cd_plano_trabalho, PT)
        self.assertEqual(ctx["siafi"], SIAFI)


# ---------------------------------------------------------------------------
# Aba Cronograma — get_cronograma_qs
# ---------------------------------------------------------------------------


class CronogramaQsTest(TestCase):
    def test_filtra_pelos_planos_do_convenio_no_modo_detalhe(self):
        _make_convenio()
        _ponte_plano()
        SigconCronogramaDesembolso.objects.create(
            cd_plano_trabalho=PT, nr_mes_desembolso=1, nr_ano_desembolso=2024
        )
        SigconCronogramaDesembolso.objects.create(
            cd_plano_trabalho="OUTRO-PT", nr_mes_desembolso=2, nr_ano_desembolso=2024
        )

        qs, ctx = get_cronograma_qs(nr_convenio=NR_CONVENIO)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().cd_plano_trabalho, PT)
        self.assertEqual(ctx["siafi"], SIAFI)

    def test_modo_standalone_sem_filtro(self):
        SigconCronogramaDesembolso.objects.create(
            cd_plano_trabalho="X", nr_mes_desembolso=3, nr_ano_desembolso=2023
        )

        qs, _ = get_cronograma_qs()

        self.assertEqual(qs.count(), 1)

    def test_linhas_marcadas_pelo_motor_silver_nao_entram_na_tela(self):
        """O bloco desalinhado do BO fica no banco, mas fora da tela, dos exports e das somas."""
        SigconCronogramaDesembolso.objects.create(cd_plano_trabalho="X", nr_mes_desembolso=3)
        SigconCronogramaDesembolso.objects.create(
            cd_plano_trabalho=None, nr_mes_desembolso=684, ds_alerta_linha="bloco desalinhado"
        )

        qs, _ = get_cronograma_qs()

        self.assertEqual(qs.count(), 1)
        self.assertEqual(SigconCronogramaDesembolso.objects.count(), 2)

    def test_filtro_por_plano(self):
        SigconCronogramaDesembolso.objects.create(cd_plano_trabalho="ABC-1")
        SigconCronogramaDesembolso.objects.create(cd_plano_trabalho="XYZ-2")

        qs, _ = get_cronograma_qs(plano="abc")

        self.assertEqual(qs.count(), 1)


# ---------------------------------------------------------------------------
# Aba Prorrogação de Ofício — get_prorrogacao_qs
# ---------------------------------------------------------------------------


class ProrrogacaoQsTest(TestCase):
    def test_filtra_pelo_sequencial_do_convenio(self):
        _make_convenio()
        _ponte_plano()
        _ponte_convenio()
        SigconProrrogacaoOficio.objects.create(
            cd_prorrogacao_oficio="PRORROGA-001",
            cd_convenio_sequencial=SEQ,
            dt_publicacao=datetime.date(2024, 6, 1),
            dt_vigencia_termino=datetime.date(2025, 6, 1),
        )
        SigconProrrogacaoOficio.objects.create(
            cd_prorrogacao_oficio="PRORROGA-002", cd_convenio_sequencial="9999"
        )

        qs, ctx = get_prorrogacao_qs(nr_convenio=NR_CONVENIO)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().cd_prorrogacao_oficio, "PRORROGA-001")
        self.assertEqual(ctx["convenio_codigo"], NR_CONVENIO)
        self.assertEqual(ctx["cd_plano_trabalho"], PT)

    def test_convenio_sem_prorrogacao_retorna_vazio(self):
        _make_convenio()
        _ponte_convenio()

        qs, _ = get_prorrogacao_qs(nr_convenio=NR_CONVENIO)

        self.assertEqual(qs.count(), 0)

    def test_filtro_global_por_siafi_resolve_via_ponte(self):
        _ponte_convenio()
        SigconProrrogacaoOficio.objects.create(
            cd_prorrogacao_oficio="PRORROGA-001", cd_convenio_sequencial=SEQ
        )
        SigconProrrogacaoOficio.objects.create(
            cd_prorrogacao_oficio="PRORROGA-002", cd_convenio_sequencial="9999"
        )

        qs, _ = get_prorrogacao_qs(nr_siafi=SIAFI)

        self.assertEqual(
            list(qs.values_list("cd_prorrogacao_oficio", flat=True)), ["PRORROGA-001"]
        )


# ---------------------------------------------------------------------------
# Aba Termo Aditivo — get_termos_aditivos_qs
# ---------------------------------------------------------------------------


class TermoAditivoQsTest(TestCase):
    def test_filtra_via_ponte_do_termo_aditivo(self):
        _make_convenio()
        _ponte_plano()
        _ponte_termo("TA-001", cd_plano_trabalho=PT)
        SigconTermoAditivo.objects.create(
            cd_termo_aditivo="TA-001", nr_termo_aditivo="1", tp_termo_aditivo="Prazo"
        )
        # TA de outro convênio — não deve aparecer
        SigconTermoAditivo.objects.create(cd_termo_aditivo="TA-999", nr_termo_aditivo="99")

        qs, ctx = get_termos_aditivos_qs(nr_convenio=NR_CONVENIO)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().cd_termo_aditivo, "TA-001")
        self.assertEqual(ctx["convenio_codigo"], NR_CONVENIO)
        self.assertEqual(ctx["ta_pt_map"]["TA-001"], PT)

    def test_convenio_sem_ta_retorna_vazio(self):
        _make_convenio()

        qs, _ = get_termos_aditivos_qs(nr_convenio=NR_CONVENIO)

        self.assertEqual(qs.count(), 0)

    def test_filtro_global_por_siafi_resolve_direto_pela_ponte(self):
        _ponte_termo("TA-001", cd_plano_trabalho=PT)
        SigconTermoAditivo.objects.create(cd_termo_aditivo="TA-001")
        SigconTermoAditivo.objects.create(cd_termo_aditivo="TA-999")

        qs, ctx = get_termos_aditivos_qs(nr_siafi=SIAFI)

        self.assertEqual(list(qs.values_list("cd_termo_aditivo", flat=True)), ["TA-001"])
        self.assertEqual(ctx["ta_pt_map"]["TA-001"], PT)


# ---------------------------------------------------------------------------
# Aba Unidades Executoras — get_unidades_executoras_qs
# ---------------------------------------------------------------------------


class UnidadesExecutorasQsTest(TestCase):
    def test_filtra_direto_por_siafi(self):
        SigconUnidadeExecutora.objects.create(
            nr_convenio=NR_CONVENIO, nr_siafi=SIAFI, cd_unidade_executora="UE-1"
        )
        SigconUnidadeExecutora.objects.create(
            nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI, cd_unidade_executora="UE-2"
        )

        qs, _ = get_unidades_executoras_qs(nr_siafi=SIAFI)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().nr_convenio, NR_CONVENIO)

    def test_nr_convenio_tem_prioridade_sobre_nr_siafi(self):
        """Com os dois na querystring (navegação entre abas), o convênio decide."""
        SigconUnidadeExecutora.objects.create(nr_convenio=NR_CONVENIO, nr_siafi=SIAFI)
        SigconUnidadeExecutora.objects.create(nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI)

        qs, _ = get_unidades_executoras_qs(nr_convenio=NR_CONVENIO, nr_siafi=OUTRO_SIAFI)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().nr_convenio, NR_CONVENIO)


# ---------------------------------------------------------------------------
# Aba Convênios — get_sigcon_qs (filtros da tela mestre)
# ---------------------------------------------------------------------------


def _filtros(**kwargs):
    base = dict(
        ano="", situacao="", cod_sigcon="", cod_siafi="", instrumento="",
        termo_aditivo="", concedente="", proponente="", tipo_contrapartida="",
    )
    base.update(kwargs)
    return base


class GetSigconQsTest(TestCase):
    def test_sem_filtro_retorna_todos(self):
        _make_convenio()
        _make_convenio(nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI, cd_uo=OUTRO_UO)

        self.assertEqual(get_sigcon_qs(_filtros()).count(), 2)

    def test_filtra_por_cod_siafi(self):
        _make_convenio()
        _make_convenio(nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI, cd_uo=OUTRO_UO)

        qs = get_sigcon_qs(_filtros(cod_siafi=SIAFI))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().nr_convenio, NR_CONVENIO)

    def test_filtra_por_situacao_e_por_ano(self):
        _make_convenio(dt_vigencia_inicio=datetime.date(2024, 3, 1))
        _make_convenio(
            nr_convenio="OUTRO/2023", nr_siafi=OUTRO_SIAFI, cd_uo=OUTRO_UO,
            dt_vigencia_inicio=datetime.date(2023, 3, 1), ds_situacao_convenio="ENCERRADO",
        )

        self.assertEqual(get_sigcon_qs(_filtros(ano="2024")).count(), 1)
        self.assertEqual(get_sigcon_qs(_filtros(situacao="ENCERRADO")).first().nr_convenio, "OUTRO/2023")

    def test_filtra_por_concedente_icontains(self):
        _make_convenio()
        _ponte_plano()
        SigconPlanoTrabalho.objects.create(cd_plano_trabalho=PT, nm_concedente="Ministério da Saúde")
        _make_convenio(nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI, cd_uo=OUTRO_UO)
        _ponte_plano("PT-OUTRO", OUTRO_SIAFI, OUTRO_UO)
        SigconPlanoTrabalho.objects.create(cd_plano_trabalho="PT-OUTRO", nm_concedente="Ministério da Educação")

        qs = get_sigcon_qs(_filtros(concedente="saúde"))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().nr_convenio, NR_CONVENIO)

    def test_filtra_por_proponente_pelo_cnpj(self):
        _make_convenio()
        _ponte_plano()
        SigconPlanoTrabalho.objects.create(cd_plano_trabalho=PT, nr_cnpj_proponente="22222222000122")
        _make_convenio(nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI, cd_uo=OUTRO_UO)

        qs = get_sigcon_qs(_filtros(proponente="22222222"))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().nr_convenio, NR_CONVENIO)

    def test_filtra_por_termo_aditivo_sem_crashar(self):
        """
        Regressão: tp_termo_aditivo não é campo de SigconConvenio (é de
        SigconTermoAditivo). Filtrar direto levantaria FieldError; o filtro tem
        de passar pela ponte sigcon_chave_termo_aditivo.
        """
        conv = _make_convenio()
        _ponte_termo("TA-001")
        SigconTermoAditivo.objects.create(cd_termo_aditivo="TA-001", tp_termo_aditivo="Prazo")
        _make_convenio(nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI, cd_uo=OUTRO_UO)

        qs = get_sigcon_qs(_filtros(termo_aditivo="Prazo"))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, conv.pk)

    def test_filtra_por_tipo_contrapartida(self):
        _make_convenio()
        _ponte_plano()
        SigconPlanoTrabalho.objects.create(
            cd_plano_trabalho=PT, ds_caracteristica_contrapartida="Contrapartida"
        )
        _make_convenio(nr_convenio="OUTRO/2024", nr_siafi=OUTRO_SIAFI, cd_uo=OUTRO_UO)
        _ponte_plano("PT-OUTRO", OUTRO_SIAFI, OUTRO_UO)

        qs = get_sigcon_qs(_filtros(tipo_contrapartida="Contrapartida financeira"))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().nr_convenio, NR_CONVENIO)
