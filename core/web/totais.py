"""
Totais (soma das colunas monetárias) das telas de consulta, calculados no banco.

A soma é sobre TODO o queryset filtrado — o mesmo que alimenta a tabela e a
exportação —, nunca só sobre a página atual. Chame `calcular_totais` com o
queryset já filtrado e ANTES do Paginator.

Atenção a fan-out: se o queryset tiver JOIN 1:N, o Sum infla. Os querysets das
telas filtram por subquery (`__in`), que não duplica linhas.
"""

from django.db.models import Sum

# Colunas vl_ que são monetárias mas não fazem sentido somadas (preço unitário).
SEM_SOMA = ("vl_unitario_item",)

# Parâmetros da querystring que não são filtros.
_PARAMS_NAO_FILTRO = {"page", "export", "ordem", "order", "ordering", "sort"}


def campos_monetarios(campos):
    """Campos vl_ de `campos` que entram nos totais, na ordem da tela."""
    return [c for c in campos if c.startswith("vl_") and c not in SEM_SOMA]


def calcular_totais(qs, campos):
    """{campo: soma} das colunas monetárias de `campos`, numa única query."""
    monetarios = campos_monetarios(campos)
    if not monetarios:
        return {}
    # alias com prefixo: o nome do campo colide com o campo do model no aggregate
    bruto = qs.order_by().aggregate(**{f"t_{c}": Sum(c) for c in monetarios})
    return {c: bruto[f"t_{c}"] or 0 for c in monetarios}


def cards_totais(totais, colunas, campos):
    """Lista [{campo, label, valor}] para o template, na ordem das colunas."""
    return [
        {"campo": c, "label": colunas[i], "valor": totais[c]}
        for i, c in enumerate(campos)
        if c in totais
    ]


def filtros_ativos(get_params):
    """True se a querystring tem algum filtro com valor (ignora page/export/ordenação)."""
    return any(
        v.strip()
        for k, vals in get_params.lists()
        if k not in _PARAMS_NAO_FILTRO
        for v in vals
    )
