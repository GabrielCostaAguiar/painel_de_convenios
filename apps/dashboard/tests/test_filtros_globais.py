"""
Testes da persistência dos filtros entre as 4 abas de Consultas SIGCON
(todos os filtros do SIGCON valem para todas as golds).

Cobre dois pontos que não aparecem nos testes de services.py:
  - a tag querystring_global propaga os filtros do SIGCON, e só eles (nunca `page`);
  - os links das sub-abas renderizados de fato carregam essa querystring.
"""

import re

from django.test import RequestFactory, TestCase

from core.templatetags.painel_filters import querystring_global
from apps.sigcon import views as views_sigcon


class QuerystringGlobalTagTest(TestCase):
    def _ctx(self, get_params):
        request = RequestFactory().get("/", get_params)
        return {"request": request}

    def test_propaga_todos_os_filtros_do_sigcon(self):
        resultado = self._chamar({"nr_convenio": "811906/2014", "situacao": "VIGENTE", "ano": "2024"})
        self.assertIn("nr_convenio=811906%2F2014", resultado)
        self.assertIn("situacao=VIGENTE", resultado)
        self.assertIn("ano=2024", resultado)

    def test_nao_propaga_parametros_de_outra_natureza(self):
        resultado = self._chamar({"page": "3", "nr_siafi": "9032193"})
        self.assertEqual(resultado, "nr_siafi=9032193")

    def test_propaga_os_dois_globais_quando_presentes(self):
        resultado = self._chamar({"nr_convenio": "811906/2014", "nr_siafi": "9032193"})
        self.assertIn("nr_convenio=811906%2F2014", resultado)
        self.assertIn("nr_siafi=9032193", resultado)

    def test_vazio_quando_nao_ha_filtros(self):
        self.assertEqual(self._chamar({"page": "2"}), "")

    def test_ignora_parametro_global_vazio(self):
        resultado = self._chamar({"nr_convenio": "", "nr_siafi": "9032193"})
        self.assertEqual(resultado, "nr_siafi=9032193")

    def _chamar(self, get_params):
        return querystring_global(self._ctx(get_params))


class SubtabsLinksTest(TestCase):
    """Renderiza a view Convênios e confere os hrefs das sub-abas de fato geradas."""

    def _links_das_subabas(self, get_params):
        request = RequestFactory().get("/", get_params)
        response = views_sigcon.sigcon(request)
        html = response.content.decode("utf-8")
        return dict(re.findall(r'<a href="([^"]*)" class="subtab[^"]*">([^<]+)</a>', html))

    def setUp(self):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass('gold.vw_convenio_sigcon'), to_regclass('gold.vw_termo_aditivo_sigcon')")
            if not all(cur.fetchone()):
                self.skipTest("golds do SIGCON não existem no banco de teste")

    def test_filtro_persiste_nos_links_das_4_abas(self):
        links = self._links_das_subabas({"nr_siafi": "9032193", "situacao": "VIGENTE"})
        self.assertEqual(len(links), 4)
        for href in links:
            self.assertIn("nr_siafi=9032193", href)
            self.assertIn("situacao=VIGENTE", href)

    def test_sem_filtro_links_sem_querystring(self):
        links = self._links_das_subabas({})
        for href in links:
            self.assertNotIn("?", href)
