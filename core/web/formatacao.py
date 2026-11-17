"""Formatação de células de tabela nas telas (padrão brasileiro)."""

from django.template.defaultfilters import date as format_date


def fmt_data(v):
    return format_date(v, "d/m/Y") if v else None


def fmt_valor(v):
    if v is None:
        return None
    formatado = f"{v:,.2f}"
    return formatado.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_celula(campo, valor):
    """Formata pelo prefixo do campo: fl_ (Sim/Não), vl_ (valor) e dt_ (data)."""
    if campo.startswith("fl_"):
        if valor is None:
            return None
        return "Sim" if valor else "Não"
    if campo.startswith("vl_"):
        return fmt_valor(valor)
    if campo.startswith("dt_"):
        return fmt_data(valor)
    return valor
