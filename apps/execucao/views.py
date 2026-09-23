"""
Views da aba Execução Estadual.

Enquanto a aba nao tem tela, a unica view e a de "Em construcao", montada pelo
helper de core/web — o mesmo que as outras secoes ainda nao implementadas usam.
"""

from core.web import view_em_construcao

execucao = view_em_construcao("execucao", "Execução Estadual")
