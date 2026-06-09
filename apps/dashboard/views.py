import json

from django.shortcuts import render

from apps.dashboard.services import get_anos_disponiveis, get_indicadores


def _df_para_lista(df) -> list[dict]:
    """Converte um DataFrame para lista de dicts serializável em JSON."""
    return json.loads(df.to_json(orient="records"))


def painel(request):
    anos_disponiveis = get_anos_disponiveis()

    ano_str = request.GET.get("ano", "")
    ano = int(ano_str) if ano_str.isdigit() else None

    indicadores = get_indicadores(ano=ano)

    if indicadores.get("vazio"):
        return render(request, "dashboard/painel.html", {
            "vazio": True,
            "anos": anos_disponiveis,
            "ano_selecionado": ano,
        })

    resumo = indicadores["resumo"]
    por_situacao = _df_para_lista(indicadores["por_situacao"])
    por_ano = _df_para_lista(indicadores["por_ano"])
    por_concedente = _df_para_lista(indicadores["por_concedente"])

    return render(request, "dashboard/painel.html", {
        "vazio": False,
        "anos": anos_disponiveis,
        "ano_selecionado": ano,
        "resumo": resumo,
        "por_situacao": por_situacao,
        "por_ano": por_ano,
        "por_concedente": por_concedente,
    })
