"""
Exceções conhecidas do SIGCON, transformadas em limites.

Regra: um teste com `limite` falha em ALERTA enquanto o número de violações for
menor ou igual ao limite, e em ERRO quando passar dele. O limite é a contagem
medida no banco real (carga de 2026-11-12), não a do PDF do modelo: o PDF
(docs/modelo_extracao_sigcon.pdf) cita números anteriores à carga atual.

Os limites NÃO aprovam o dado: eles dizem "este defeito da fonte já existe e
está registrado em docs/qualidade_dados.md, com os exemplos". Se a contagem
cair, o teste continua em ALERTA; se subir, é defeito novo e bloqueia (ERRO).
Depois de corrigir a fonte, baixe o limite (ou remova-o) para a regressão
voltar a ser pega.

Cada limite tem o nome do que ele conta. Para mudar um, edite aqui e atualize
a seção SIGCON de docs/qualidade_dados.md.
"""

LIMITES_CONHECIDOS = {
    # Convênios sem SIAFI: não geram siafi_uo. PDF: 4 (T1); banco: 8, dos quais
    # 3 são registros de teste ("Te DUPLITESTE", "Te TESTEDupli" x2).
    "convenios_sem_siafi_uo": 8,
    # Idem nas pontes e nas unidades executoras (derivam do mesmo SIAFI nulo).
    "unidade_executora_sem_siafi_uo": 1,
    "chave_plano_trabalho_sem_siafi_uo": 8,
    "chave_declaracao_sem_siafi_uo": 7,
    # Notas técnicas de emenda com o sentinela 99999999 (vira nulo na silver). PDF: 216.
    "nt_emenda_sem_plano": 216,
    # Prorrogação cujo sequencial não está na ponte sigcon_chave_convenio (P7). PDF: 447/448.
    "prorrogacao_orfa": 1,
    # Declarações sem ponte sigcon_chave_declaracao (P5/V9). PDF: 2.437; banco: 2.438.
    "declaracoes_sem_ponte": 2438,
    # Linhas do plano de aplicação cujo plano de trabalho não está em sigcon_plano_trabalho.
    "plano_aplicacao_sem_plano_trabalho": 842,
    # Planos com aplicação e sem cronograma de desembolso (concedente / proponente), V11.
    "planos_desembolso_diferente_aplicacao_concedente": 484,
    "planos_desembolso_diferente_aplicacao_proponente": 248,
    # Erros da fonte (não corrigidos: a fonte é preservada). Exemplos em qualidade_dados.md.
    "cnpj_proponente_invalido": 4,  # o campo traz o código da UO (4 dígitos)
    "cnpj_concedente_invalido": 1,  # 13 dígitos: o zero à esquerda se perdeu no Excel
    "cd_uo_com_tamanho_errado": 1,  # a linha sentinela 99999999 (cd_uo = 9999999999)
}


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
