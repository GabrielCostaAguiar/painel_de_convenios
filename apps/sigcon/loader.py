"""
Registro das fontes do SIGCON: cada fonte vira um `partial` do loader genérico
(core/carga/loader.py) e entra em `_LOADERS_SIGCON`.

A ordem de `_LOADERS_SIGCON` é a ordem de carga. Os models não têm ForeignKey
entre si, então a ordem não afeta a consistência; a tabela "mãe" vem primeiro
para que uma carga interrompida deixe o painel num estado mais útil.
"""

from functools import partial

from core.carga.loader import carregar_tabela_generica

from .models import (
    SigconChaveConvenio,
    SigconChaveDeclaracao,
    SigconChavePlanoTrabalho,
    SigconChaveTermoAditivo,
    SigconConcedente,
    SigconConvenio,
    SigconConvenioGeral,
    SigconCronogramaDesembolso,
    SigconDeclaracaoContrapartida,
    SigconNtEmenda,
    SigconPlanoAplicacao,
    SigconPlanoTrabalho,
    SigconProrrogacaoOficio,
    SigconTabelaUo,
    SigconTermoAditivo,
    SigconUnidadeExecutora,
)

carregar_sigcon_convenio = partial(carregar_tabela_generica, "sigcon_convenio", SigconConvenio)
carregar_sigcon_convenio_geral = partial(carregar_tabela_generica, "sigcon_convenio_geral", SigconConvenioGeral)
carregar_sigcon_plano_trabalho = partial(carregar_tabela_generica, "sigcon_plano_trabalho", SigconPlanoTrabalho)
carregar_sigcon_termo_aditivo = partial(carregar_tabela_generica, "sigcon_termo_aditivo", SigconTermoAditivo)
carregar_sigcon_prorrogacao_oficio = partial(carregar_tabela_generica, "sigcon_prorrogacao_oficio", SigconProrrogacaoOficio)
carregar_sigcon_declaracao_contrapartida = partial(carregar_tabela_generica, "sigcon_declaracao_contrapartida", SigconDeclaracaoContrapartida)
carregar_sigcon_cronograma_desembolso = partial(carregar_tabela_generica, "sigcon_cronograma_desembolso", SigconCronogramaDesembolso)
carregar_sigcon_plano_aplicacao = partial(carregar_tabela_generica, "sigcon_plano_aplicacao", SigconPlanoAplicacao)
carregar_sigcon_unidade_executora = partial(carregar_tabela_generica, "sigcon_unidade_executora", SigconUnidadeExecutora)
carregar_sigcon_nt_emenda = partial(carregar_tabela_generica, "sigcon_nt_emenda", SigconNtEmenda)
carregar_sigcon_chave_convenio = partial(carregar_tabela_generica, "sigcon_chave_convenio", SigconChaveConvenio)
carregar_sigcon_chave_termo_aditivo = partial(carregar_tabela_generica, "sigcon_chave_termo_aditivo", SigconChaveTermoAditivo)
carregar_sigcon_chave_plano_trabalho = partial(carregar_tabela_generica, "sigcon_chave_plano_trabalho", SigconChavePlanoTrabalho)
carregar_sigcon_chave_declaracao = partial(carregar_tabela_generica, "sigcon_chave_declaracao", SigconChaveDeclaracao)
carregar_sigcon_concedente = partial(carregar_tabela_generica, "sigcon_concedente", SigconConcedente)
carregar_sigcon_tabela_uo = partial(carregar_tabela_generica, "sigcon_tabela_uo", SigconTabelaUo)


_LOADERS_SIGCON = {
    "sigcon_convenio": carregar_sigcon_convenio,
    "sigcon_convenio_geral": carregar_sigcon_convenio_geral,
    "sigcon_plano_trabalho": carregar_sigcon_plano_trabalho,
    "sigcon_termo_aditivo": carregar_sigcon_termo_aditivo,
    "sigcon_prorrogacao_oficio": carregar_sigcon_prorrogacao_oficio,
    "sigcon_declaracao_contrapartida": carregar_sigcon_declaracao_contrapartida,
    "sigcon_cronograma_desembolso": carregar_sigcon_cronograma_desembolso,
    "sigcon_plano_aplicacao": carregar_sigcon_plano_aplicacao,
    "sigcon_unidade_executora": carregar_sigcon_unidade_executora,
    "sigcon_nt_emenda": carregar_sigcon_nt_emenda,
    "sigcon_chave_convenio": carregar_sigcon_chave_convenio,
    "sigcon_chave_termo_aditivo": carregar_sigcon_chave_termo_aditivo,
    "sigcon_chave_plano_trabalho": carregar_sigcon_chave_plano_trabalho,
    "sigcon_chave_declaracao": carregar_sigcon_chave_declaracao,
    "sigcon_concedente": carregar_sigcon_concedente,
    "sigcon_tabela_uo": carregar_sigcon_tabela_uo,
}

FONTES_SIGCON = tuple(_LOADERS_SIGCON)
