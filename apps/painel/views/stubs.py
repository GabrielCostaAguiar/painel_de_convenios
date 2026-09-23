"""
Views "Em construção" das seções de Acompanhamento ainda não implementadas.

União e Execução Estadual também são telas "Em construção", mas já têm app
próprio (apps.uniao, apps.execucao) — cada aba do menu é um app.
"""

from core.web import view_em_construcao


monitoramento = view_em_construcao("monitoramento", "Monitoramento")
relatorio     = view_em_construcao("relatorio",     "Relatório Individual")
alertas       = view_em_construcao("alertas",       "Alertas")
emendas       = view_em_construcao("emendas",       "Painel de Emendas")
