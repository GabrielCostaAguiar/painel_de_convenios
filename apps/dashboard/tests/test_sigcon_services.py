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

Um teste por aba que tenha fonte. Aba Unidades Executoras não tem fonte — sem teste.
"""

import datetime

from django.test import TestCase

from apps.convenios.models import (
    Convenio,
    ConvenioIntegrado,
    CodigoPlanoTrabalho,
    CodigoTermoAditivo,
    CronogramaDesembolso,
    PlanoAplicacao,
    PlanoTrabalho,
    ProrrogacaoOficio,
    TermoAditivo,
    UnidadesExecutoras,
)
from apps.dashboard.services import (
    enrich_convenios_page,
    get_cronograma_qs,
    get_plano_aplicacao_qs,
    get_prorrogacao_qs,
    get_sigcon_qs,
    get_termos_aditivos_qs,
    get_unidades_executoras_qs,
)


# ---------------------------------------------------------------------------
# Fixtures de amostra reutilizáveis
# ---------------------------------------------------------------------------

SIAFI = "9309074"
UO = "1261"
COD_SIGCON = "811906/2014"
PT_CODIGO = "PT-0001"
COD_SICONV = "SICONV-123"


def _make_convenio(**kwargs):
    defaults = dict(
        convenio_codigo=COD_SIGCON,
        convenio_numero_sequencial_siafi=SIAFI,
        unidade_orcamentaria_codigo=UO,
        plano_trabalho_codigo=PT_CODIGO,
        situacao="EM EXECUÇÃO",
    )
    defaults.update(kwargs)
    return Convenio.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Aba Convênios — enrich_convenios_page
# ---------------------------------------------------------------------------

class EnrichConveniosPageTest(TestCase):
    def test_retorna_codigo_siconv_e_proponente(self):
        conv = _make_convenio()
        ConvenioIntegrado.objects.create(
            siafi_uo=SIAFI + UO,
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_orcamentaria_codigo=UO,
            codigo_siconv=COD_SICONV,
            g_proponente_pad="Prefeitura de Teste",
            g_fim_vigencia_inicial=datetime.date(2025, 12, 31),
        )

        resultado = enrich_convenios_page([conv])

        self.assertIn(conv.pk, resultado)
        extra = resultado[conv.pk]
        self.assertEqual(extra["codigo_siconv"], COD_SICONV)
        self.assertEqual(extra["proponente"], "Prefeitura de Teste")
        self.assertEqual(extra["fim_vigencia_inicial"], datetime.date(2025, 12, 31))

    def test_retorna_fallback_quando_sem_integrado(self):
        conv = _make_convenio(convenio_codigo="SEM-INTEGRADO/2024")
        resultado = enrich_convenios_page([conv])
        extra = resultado[conv.pk]
        self.assertEqual(extra["codigo_siconv"], "—")
        self.assertEqual(extra["proponente"], "—")
        self.assertIsNone(extra["fim_vigencia_inicial"])


# ---------------------------------------------------------------------------
# Aba Plano de Aplicação — get_plano_aplicacao_qs
# ---------------------------------------------------------------------------

class PlanoAplicacaoQsTest(TestCase):
    def test_filtra_por_plano_trabalho_codigo(self):
        _make_convenio()
        PlanoAplicacao.objects.create(
            codigo_plano_trabalho=PT_CODIGO,
            ano_exercicio_programa_trabalho="2024",
            valor_concedente=1000,
        )
        # registro de outro convênio — não deve aparecer
        PlanoAplicacao.objects.create(
            codigo_plano_trabalho="OUTRO-PT",
            ano_exercicio_programa_trabalho="2024",
        )

        qs, ctx = get_plano_aplicacao_qs(cod_sigcon=COD_SIGCON)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().codigo_plano_trabalho, PT_CODIGO)
        self.assertEqual(ctx["siafi"], SIAFI)
        self.assertEqual(ctx["plano_trabalho_codigo"], PT_CODIGO)

    def test_convenio_inexistente_retorna_vazio(self):
        qs, ctx = get_plano_aplicacao_qs(cod_sigcon="INEXISTENTE/9999")
        self.assertEqual(qs.count(), 0)

    def test_sem_filtro_retorna_todos(self):
        PlanoAplicacao.objects.create(codigo_plano_trabalho="A")
        PlanoAplicacao.objects.create(codigo_plano_trabalho="B")
        qs, _ = get_plano_aplicacao_qs()
        self.assertEqual(qs.count(), 2)


# ---------------------------------------------------------------------------
# Aba Cronograma — get_cronograma_qs
# ---------------------------------------------------------------------------

class CronogramaQsTest(TestCase):
    def test_filtra_por_siafi_uo_no_modo_detalhe(self):
        _make_convenio()
        CronogramaDesembolso.objects.create(
            plano_trabalho_codigo=PT_CODIGO,
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_orcamentaria_codigo=UO,
            mes_cronograma_desembolso="01",
            ano_cronograma_desembolso="2024",
        )
        # registro de outro convênio
        CronogramaDesembolso.objects.create(
            plano_trabalho_codigo="OUTRO-PT",
            convenio_numero_sequencial_siafi="9999999",
            unidade_orcamentaria_codigo="9999",
            mes_cronograma_desembolso="02",
            ano_cronograma_desembolso="2024",
        )

        qs, ctx = get_cronograma_qs(cod_sigcon=COD_SIGCON)

        self.assertEqual(qs.count(), 1)
        item = qs.first()
        self.assertEqual(item.convenio_numero_sequencial_siafi, SIAFI)

    def test_modo_standalone_sem_filtro(self):
        CronogramaDesembolso.objects.create(
            plano_trabalho_codigo="X",
            mes_cronograma_desembolso="03",
            ano_cronograma_desembolso="2023",
        )
        qs, _ = get_cronograma_qs()
        self.assertGreaterEqual(qs.count(), 1)


# ---------------------------------------------------------------------------
# Aba Prorrogação de Ofício — get_prorrogacao_qs
# ---------------------------------------------------------------------------

class ProrrogacaoQsTest(TestCase):
    def test_filtra_direto_por_convenio_codigo(self):
        _make_convenio()
        ProrrogacaoOficio.objects.create(
            prorrogacao_oficio_codigo="PRORROGA-001",
            prorrogacao_oficio_codigo_convenio=COD_SIGCON,
            prorrogacao_oficio_data_publicacao=datetime.date(2024, 6, 1),
            prorrogacao_oficio_data_termino_vigencia=datetime.date(2025, 6, 1),
        )
        # prorrogação de outro convênio
        ProrrogacaoOficio.objects.create(
            prorrogacao_oficio_codigo="PRORROGA-002",
            prorrogacao_oficio_codigo_convenio="OUTRO/2010",
        )

        qs, ctx = get_prorrogacao_qs(cod_sigcon=COD_SIGCON)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().prorrogacao_oficio_codigo, "PRORROGA-001")
        self.assertEqual(ctx["convenio_codigo"], COD_SIGCON)
        self.assertEqual(ctx["plano_trabalho_codigo"], PT_CODIGO)

    def test_convenio_sem_prorrogacao_retorna_vazio(self):
        _make_convenio()
        qs, _ = get_prorrogacao_qs(cod_sigcon=COD_SIGCON)
        self.assertEqual(qs.count(), 0)


# ---------------------------------------------------------------------------
# Aba Termo Aditivo — get_termos_aditivos_qs
# ---------------------------------------------------------------------------

class TermoAditivoQsTest(TestCase):
    def test_filtra_via_codigo_ta(self):
        _make_convenio()
        # ponte: SIAFI+UO → código do TA
        CodigoTermoAditivo.objects.create(
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_orcamentaria_codigo=UO,
            termo_aditivo_codigo_sequencial="TA-SEQ-001",
            plano_trabalho_codigo=PT_CODIGO,
        )
        TermoAditivo.objects.create(
            termo_aditivo_codigo_sequencial="TA-SEQ-001",
            termo_aditivo_numero_termo_aditivo="1",
            termo_aditivo_tipo="Prazo",
        )
        # TA de outro convênio — não deve aparecer
        TermoAditivo.objects.create(
            termo_aditivo_codigo_sequencial="TA-SEQ-999",
            termo_aditivo_numero_termo_aditivo="99",
        )

        qs, ctx = get_termos_aditivos_qs(cod_sigcon=COD_SIGCON)

        self.assertEqual(qs.count(), 1)
        ta = qs.first()
        self.assertEqual(ta.termo_aditivo_codigo_sequencial, "TA-SEQ-001")
        self.assertEqual(ctx["convenio_codigo"], COD_SIGCON)
        self.assertEqual(ctx["ta_pt_map"]["TA-SEQ-001"], PT_CODIGO)

    def test_convenio_sem_ta_retorna_vazio(self):
        _make_convenio()
        qs, _ = get_termos_aditivos_qs(cod_sigcon=COD_SIGCON)
        self.assertEqual(qs.count(), 0)


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
        _make_convenio(convenio_codigo="OUTRO/2024", convenio_numero_sequencial_siafi="999")
        qs = get_sigcon_qs(_filtros())
        self.assertEqual(qs.count(), 2)

    def test_filtra_por_cod_siafi(self):
        _make_convenio()
        _make_convenio(convenio_codigo="OUTRO/2024", convenio_numero_sequencial_siafi="999")
        qs = get_sigcon_qs(_filtros(cod_siafi=SIAFI))
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().convenio_codigo, COD_SIGCON)

    def test_filtra_por_concedente_icontains(self):
        _make_convenio(concedente="Ministério da Saúde")
        _make_convenio(convenio_codigo="OUTRO/2024", concedente="Ministério da Educação")
        qs = get_sigcon_qs(_filtros(concedente="saúde"))
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().concedente, "Ministério da Saúde")

    def test_filtra_por_termo_aditivo_sem_crashar(self):
        """
        Regressão: tipo_termo_aditivo não é campo de Convenio (é de TermoAditivo).
        Filtrar direto via qs.filter(tipo_termo_aditivo=...) levanta FieldError.
        """
        conv = _make_convenio()
        CodigoTermoAditivo.objects.create(
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_orcamentaria_codigo=UO,
            termo_aditivo_codigo_sequencial="TA-SEQ-001",
        )
        TermoAditivo.objects.create(
            termo_aditivo_codigo_sequencial="TA-SEQ-001",
            tipo_termo_aditivo="Prazo",
        )
        # outro convênio, sem esse tipo de termo aditivo
        _make_convenio(convenio_codigo="OUTRO/2024", convenio_numero_sequencial_siafi="999")

        qs = get_sigcon_qs(_filtros(termo_aditivo="Prazo"))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, conv.pk)

    def test_filtra_por_proponente(self):
        _make_convenio()
        ConvenioIntegrado.objects.create(
            siafi_uo=SIAFI + UO,
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_orcamentaria_codigo=UO,
            g_proponente_pad="Prefeitura de Teste",
        )
        _make_convenio(convenio_codigo="OUTRO/2024", convenio_numero_sequencial_siafi="999")

        qs = get_sigcon_qs(_filtros(proponente="prefeitura"))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().convenio_codigo, COD_SIGCON)

    def test_filtra_por_tipo_contrapartida(self):
        _make_convenio()
        PlanoTrabalho.objects.create(
            plano_trabalho_codigo=PT_CODIGO,
            plano_trabalho_caracteristica="Contrapartida",
        )
        CodigoPlanoTrabalho.objects.create(
            conveno_codigo_plano_trabalho=PT_CODIGO,
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_orcamentaria_codigo=UO,
        )
        _make_convenio(convenio_codigo="OUTRO/2024", convenio_numero_sequencial_siafi="999",
                        plano_trabalho_codigo="PT-OUTRO")

        qs = get_sigcon_qs(_filtros(tipo_contrapartida="Contrapartida financeira"))

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().convenio_codigo, COD_SIGCON)


# ---------------------------------------------------------------------------
# Filtro global cod_siafi nas 4 abas-detalhe (sem cod_sigcon)
#
# Essas abas não têm SIAFI nem plano_trabalho_codigo de forma autoexplicativa
# em todos os models — os testes abaixo cobrem a resolução via Convenio (ou,
# quando o model já tem o campo, o caminho direto) descrita nos docstrings
# de cada get_*_qs em services.py.
# ---------------------------------------------------------------------------

class FiltroGlobalCodSiafiTest(TestCase):
    def test_plano_aplicacao_resolve_via_convenio(self):
        _make_convenio()
        PlanoAplicacao.objects.create(codigo_plano_trabalho=PT_CODIGO)
        PlanoAplicacao.objects.create(codigo_plano_trabalho="OUTRO-PT")

        qs, ctx = get_plano_aplicacao_qs(cod_siafi=SIAFI)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().codigo_plano_trabalho, PT_CODIGO)
        self.assertEqual(ctx["siafi"], SIAFI)

    def test_prorrogacao_resolve_via_convenio(self):
        _make_convenio()
        ProrrogacaoOficio.objects.create(
            prorrogacao_oficio_codigo="PRORROGA-001",
            prorrogacao_oficio_codigo_convenio=COD_SIGCON,
        )
        ProrrogacaoOficio.objects.create(
            prorrogacao_oficio_codigo="PRORROGA-002",
            prorrogacao_oficio_codigo_convenio="OUTRO/2010",
        )

        qs, _ = get_prorrogacao_qs(cod_siafi=SIAFI)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().prorrogacao_oficio_codigo, "PRORROGA-001")

    def test_termo_aditivo_resolve_direto_via_bridge(self):
        _make_convenio()
        CodigoTermoAditivo.objects.create(
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_orcamentaria_codigo=UO,
            termo_aditivo_codigo_sequencial="TA-SEQ-001",
            plano_trabalho_codigo=PT_CODIGO,
        )
        TermoAditivo.objects.create(termo_aditivo_codigo_sequencial="TA-SEQ-001")
        TermoAditivo.objects.create(termo_aditivo_codigo_sequencial="TA-SEQ-999")

        qs, ctx = get_termos_aditivos_qs(cod_siafi=SIAFI)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().termo_aditivo_codigo_sequencial, "TA-SEQ-001")
        self.assertEqual(ctx["ta_pt_map"]["TA-SEQ-001"], PT_CODIGO)

    def test_unidades_executoras_filtra_direto_por_siafi(self):
        UnidadesExecutoras.objects.create(
            convenio_codigo=COD_SIGCON,
            convenio_numero_sequencial_siafi=SIAFI,
            unidade_executora="Secretaria de Teste",
        )
        UnidadesExecutoras.objects.create(
            convenio_codigo="OUTRO/2024",
            convenio_numero_sequencial_siafi="999",
        )

        qs, _ = get_unidades_executoras_qs(cod_siafi=SIAFI)

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().convenio_codigo, COD_SIGCON)

    def test_cod_sigcon_tem_prioridade_sobre_cod_siafi(self):
        """Quando os dois vêm na querystring (navegação entre abas), cod_sigcon decide."""
        _make_convenio()
        _make_convenio(convenio_codigo="OUTRO/2024", convenio_numero_sequencial_siafi="999")
        UnidadesExecutoras.objects.create(convenio_codigo=COD_SIGCON, convenio_numero_sequencial_siafi=SIAFI)
        UnidadesExecutoras.objects.create(convenio_codigo="OUTRO/2024", convenio_numero_sequencial_siafi="999")

        qs, _ = get_unidades_executoras_qs(cod_sigcon=COD_SIGCON, cod_siafi="999")

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().convenio_codigo, COD_SIGCON)
