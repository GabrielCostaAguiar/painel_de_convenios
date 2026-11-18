"""
Filtros multivalorados das telas de consulta — um módulo para todos os apps.

Cada app declara uma SPEC (tupla de `Filtro`) e usa as duas funções abaixo:

    SPEC = (
        Filtro("situacao", "ds_situacao"),                         # select múltiplo, exato
        Filtro("nr_siafi", "nr_siafi", texto=True),                # digitado: 9999; 8888
        Filtro("proponente", "nm_uo", "contem", texto=True),       # OR de icontains
        Filtro("ano", "nr_ano", "inteiro"),
    )
    filtros = ler_filtros(request.GET, SPEC)        # {chave: [valores]}
    qs = aplicar_filtros(qs, filtros, SPEC)

Regra: OR entre os valores de UM campo, AND entre campos diferentes. Com um só
valor o SQL é o mesmo de antes (`campo = valor`); com vários vira `IN (...)`.
Nenhum JOIN é criado, então o Sum dos totais e o export seguem corretos.

Filtro sem `campo` (campo=None) é só lido: o app aplica à mão (ex.: subquery).
Não pode importar apps.* nem pandas.
"""

import logging
import re
from dataclasses import dataclass
from functools import reduce
from operator import or_

from django.db.models import Q

logger = logging.getLogger(__name__)

LIMITE_VALORES = 200

_SEP_TEXTO = re.compile(r"[,;\r\n]+")
_SEP_TEXTO_ESPACO = re.compile(r"[,;\s]+")


@dataclass(frozen=True)
class Filtro:
    chave: str                  # name= do campo no formulário / querystring
    campo: str | None = None    # campo do model; None = aplicado pelo app
    tipo: str = "exato"         # "exato" | "contem" (icontains) | "inteiro"
    texto: bool = False         # campo digitado: separa por vírgula, ; e quebra de linha
    espaco: bool = False        # com texto=True, também separa por espaço (códigos sem espaço)


def como_lista(valor):
    """Normaliza str, lista ou None para lista de strings sem vazios."""
    if valor is None:
        return []
    if isinstance(valor, str):
        valor = [valor]
    return [str(v).strip() for v in valor if str(v).strip()]


def _brutos(get_params, chave):
    if hasattr(get_params, "getlist"):
        return get_params.getlist(chave)
    return como_lista(get_params.get(chave))


def ler_filtros(get_params, specs):
    """{chave: [valores]} lido da querystring (QueryDict ou dict simples)."""
    filtros = {}
    for f in specs:
        valores = []
        for bruto in _brutos(get_params, f.chave):
            bruto = (bruto or "").strip()
            if f.texto:
                partes = (_SEP_TEXTO_ESPACO if f.espaco else _SEP_TEXTO).split(bruto)
            else:
                partes = [bruto]
            valores.extend(p.strip() for p in partes if p.strip())
        valores = list(dict.fromkeys(valores))
        if len(valores) > LIMITE_VALORES:
            logger.warning("%s: %d valores recebidos, usando os %d primeiros",
                           f.chave, len(valores), LIMITE_VALORES)
            valores = valores[:LIMITE_VALORES]
        filtros[f.chave] = valores
    return filtros


def _condicao(f, valores):
    if not valores:
        return None
    if f.tipo == "contem":
        return reduce(or_, (Q(**{f"{f.campo}__icontains": v}) for v in valores))
    if f.tipo == "inteiro":
        valores = [int(v) for v in valores if v.isdigit()]
        if not valores:
            return None  # lixo digitado é ignorado, como antes
    if len(valores) == 1:
        return Q(**{f.campo: valores[0]})
    return Q(**{f"{f.campo}__in": valores})


def aplicar_filtros(qs, filtros, specs):
    """Aplica ao queryset os filtros de `specs` que tenham `campo`."""
    for f in specs:
        if f.campo is None:
            continue
        cond = _condicao(f, como_lista(filtros.get(f.chave)))
        if cond is not None:
            qs = qs.filter(cond)
    return qs


def querystring_de(get_params, chaves):
    """Querystring só com as `chaves` presentes (mantém todos os valores repetidos)."""
    from urllib.parse import urlencode

    pares = [
        (k, v)
        for k, vals in get_params.lists()
        if k in chaves
        for v in vals
        if v
    ]
    return urlencode(pares)
