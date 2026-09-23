"""
Views do painel: indicadores (KPIs) e gráficos.
"""

from django.shortcuts import render

from apps.dashboard.services import get_anos_disponiveis, get_indicadores


# ---------------------------------------------------------------------------
# Indicadores — KPIs e tabela por situação
# ---------------------------------------------------------------------------

def indicadores(request):
    ano_str = request.GET.get("ano", "")
    ano = int(ano_str) if ano_str.isdigit() else None

    dados = get_indicadores(ano=ano)
    anos  = get_anos_disponiveis()

    if dados.get("vazio"):
        return render(request, "dashboard/indicadores.html", {
            "vazio": True,
            "anos":  anos,
            "ano_selecionado": ano,
            "secao_ativa": "indicadores",
        })

    return render(request, "dashboard/indicadores.html", {
        "vazio":        False,
        "anos":         anos,
        "ano_selecionado": ano,
        "resumo":       dados["resumo"],
        "por_situacao": dados["por_situacao"],
        "secao_ativa":  "indicadores",
    })


# ---------------------------------------------------------------------------
# Gráficos — dois painéis Chart.js
# ---------------------------------------------------------------------------

def graficos(request):
    ano_str = request.GET.get("ano", "")
    ano = int(ano_str) if ano_str.isdigit() else None

    dados = get_indicadores(ano=ano)

    if dados.get("vazio"):
        return render(request, "dashboard/graficos.html", {
            "vazio": True,
            "secao_ativa": "graficos",
        })

    return render(request, "dashboard/graficos.html", {
        "vazio":        False,
        "por_ano":      dados["por_ano"],
        "por_situacao": dados["por_situacao"],
        "secao_ativa":  "graficos",
    })
