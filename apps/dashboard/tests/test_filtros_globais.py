"""
Testes da persistência de filtros globais (cod_sigcon, cod_siafi) entre as
6 abas de Consultas SIGCON.

Cobre dois pontos que não aparecem nos testes de services.py:
  - a tag querystring_global só propaga as chaves globais, nunca as locais;
  - os links das sub-abas renderizados de fato carregam essa querystring.
"""

import re

from django.test import RequestFactory, TestCase

from apps.dashboard.templatetags.painel_filters import querystring_global
from apps.dashboard.views import sigcon


class QuerystringGlobalTagTest(TestCase):
    def _ctx(self, get_params):
        request = RequestFactory().get("/", get_params)
        return {"request": request}

    def test_propaga_apenas_chaves_globais(self):
        resultado = self._chamar({"cod_sigcon": "811906/2014", "situacao": "VIGENTE", "ano": "2024"})
        self.assertEqual(resultado, "cod_sigcon=811906%2F2014")

    def test_propaga_os_dois_globais_quando_presentes(self):
        resultado = self._chamar({"cod_sigcon": "811906/2014", "cod_siafi": "9032193"})
        self.assertIn("cod_sigcon=811906%2F2014", resultado)
        self.assertIn("cod_siafi=9032193", resultado)

    def test_vazio_quando_so_ha_filtros_locais(self):
        resultado = self._chamar({"situacao": "VIGENTE", "instrumento": "Convênio"})
        self.assertEqual(resultado, "")

    def test_ignora_parametro_global_vazio(self):
        resultado = self._chamar({"cod_sigcon": "", "cod_siafi": "9032193"})
        self.assertEqual(resultado, "cod_siafi=9032193")

    def _chamar(self, get_params):
        return querystring_global(self._ctx(get_params))


class SubtabsLinksTest(TestCase):
    """Renderiza a view Convênios e confere os hrefs das sub-abas de fato geradas."""

    def _links_das_subabas(self, get_params):
        request = RequestFactory().get("/", get_params)
        response = sigcon(request)
        html = response.content.decode("utf-8")
        return dict(re.findall(r'<a href="([^"]*)" class="subtab[^"]*">([^<]+)</a>', html))

    def test_filtro_global_persiste_nos_links_das_6_abas(self):
        links = self._links_das_subabas({"cod_siafi": "9032193"})
        self.assertEqual(len(links), 6)
        for href in links:
            self.assertIn("cod_siafi=9032193", href)

    def test_filtro_local_nao_vaza_para_as_outras_abas(self):
        links = self._links_das_subabas({"situacao": "VIGENTE", "ano": "2024"})
        for href in links:
            self.assertNotIn("situacao", href)
            self.assertNotIn("ano=", href)

    def test_sem_filtro_links_sem_querystring(self):
        links = self._links_das_subabas({})
        for href in links:
            self.assertNotIn("?", href)
