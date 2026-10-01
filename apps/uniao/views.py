"""
Views da aba Consultas União.

Enquanto a aba nao tem tela, a unica view e a de "Em construcao", montada pelo
helper de core/web — o mesmo que as outras secoes ainda nao implementadas usam.
"""

from django.shortcuts import render

# uniao = view_em_construcao("uniao", "Consultas União")

def consultas_uniao(request):
    """View de Consultas União."""
    return render(request, "uniao/consultas_uniao.html")