"""
Severidade efetiva de um teste do catálogo de validação.

Os limites em si (exceções conhecidas, medidas no banco real) são dados do app
e ficam em `apps/<app>/validacao/limites.py`; aqui só mora a regra que os usa.
"""


def severidade_efetiva(teste, qt):
    """
    Severidade com que o resultado deve ser gravado.

    Teste sem `limite`: a do catálogo. Com `limite`: ALERTA se 0 < qt <= limite,
    ERRO se qt > limite; com qt == 0 nada falhou, vale a do catálogo.
    """
    limite = teste.get("limite")
    if limite is None or qt == 0:
        return teste["severidade"]
    return "ALERTA" if qt <= limite else "ERRO"
