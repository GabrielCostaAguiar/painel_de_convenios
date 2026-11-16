"""
Registro das fontes do GRP: cada fonte vira um `partial` do loader genérico
(core/carga/loader.py) e entra em `_LOADERS_GRP`.

A ordem de `_LOADERS_GRP` é a ordem de carga. Os models não têm ForeignKey
entre si, então a ordem não afeta a consistência; a tabela "mãe" vem primeiro
para que uma carga interrompida deixe o painel num estado mais útil.
"""

from functools import partial

from core.carga.loader import carregar_tabela_generica

from .models import (
    GrpInstrumento,
    GrpConcedente,
    GrpPrestacaoContas,
    GrpPlanejamentoObras,
    GrpPropostaMarcoLogico,
    GrpEmenda,
    GrpInterveniente,
    GrpUnidadeExecutora,
    GrpMunicipioAtendido,
    GrpRegiaoAtendida,
    GrpRecursoConcedente,
    GrpRecursoContrapartida,
    GrpDotacaoContrapartida,
    GrpAcaoOrcamentaria,
    GrpInstrumentoFinanciado,
    GrpItemExecutar,
    GrpCronogramaDesembolso,
    GrpCronogramaFisico,
    GrpEntregaProjeto,
    GrpAtividadeProjeto,
    GrpMatrizResponsabilidade,
    GrpTabelaUo,
)

carregar_grp_instrumento = partial(carregar_tabela_generica, "grp_instrumento", GrpInstrumento)
carregar_grp_concedente = partial(carregar_tabela_generica, "grp_concedente", GrpConcedente)
carregar_grp_prestacao_contas = partial(carregar_tabela_generica, "grp_prestacao_contas", GrpPrestacaoContas)
carregar_grp_planejamento_obras = partial(carregar_tabela_generica, "grp_planejamento_obras", GrpPlanejamentoObras)
carregar_grp_proposta_marco_logico = partial(carregar_tabela_generica, "grp_proposta_marco_logico", GrpPropostaMarcoLogico)
carregar_grp_emenda = partial(carregar_tabela_generica, "grp_emenda", GrpEmenda)
carregar_grp_interveniente = partial(carregar_tabela_generica, "grp_interveniente", GrpInterveniente)
carregar_grp_unidade_executora = partial(carregar_tabela_generica, "grp_unidade_executora", GrpUnidadeExecutora)
carregar_grp_municipio_atendido = partial(carregar_tabela_generica, "grp_municipio_atendido", GrpMunicipioAtendido)
carregar_grp_regiao_atendida = partial(carregar_tabela_generica, "grp_regiao_atendida", GrpRegiaoAtendida)
carregar_grp_recurso_concedente = partial(carregar_tabela_generica, "grp_recurso_concedente", GrpRecursoConcedente)
carregar_grp_recurso_contrapartida = partial(carregar_tabela_generica, "grp_recurso_contrapartida", GrpRecursoContrapartida)
carregar_grp_dotacao_contrapartida = partial(carregar_tabela_generica, "grp_dotacao_contrapartida", GrpDotacaoContrapartida)
carregar_grp_acao_orcamentaria = partial(carregar_tabela_generica, "grp_acao_orcamentaria", GrpAcaoOrcamentaria)
carregar_grp_instrumento_financiado = partial(carregar_tabela_generica, "grp_instrumento_financiado", GrpInstrumentoFinanciado)
carregar_grp_item_executar = partial(carregar_tabela_generica, "grp_item_executar", GrpItemExecutar)
carregar_grp_cronograma_desembolso = partial(carregar_tabela_generica, "grp_cronograma_desembolso", GrpCronogramaDesembolso)
carregar_grp_cronograma_fisico = partial(carregar_tabela_generica, "grp_cronograma_fisico", GrpCronogramaFisico)
carregar_grp_entrega_projeto = partial(carregar_tabela_generica, "grp_entrega_projeto", GrpEntregaProjeto)
carregar_grp_atividade_projeto = partial(carregar_tabela_generica, "grp_atividade_projeto", GrpAtividadeProjeto)
carregar_grp_matriz_responsabilidade = partial(carregar_tabela_generica, "grp_matriz_responsabilidade", GrpMatrizResponsabilidade)
carregar_grp_tabela_uo = partial(carregar_tabela_generica, "grp_tabela_uo", GrpTabelaUo)

_LOADERS_GRP = {
    "grp_instrumento": carregar_grp_instrumento,
    "grp_concedente": carregar_grp_concedente,
    "grp_prestacao_contas": carregar_grp_prestacao_contas,
    "grp_planejamento_obras": carregar_grp_planejamento_obras,
    "grp_proposta_marco_logico": carregar_grp_proposta_marco_logico,
    "grp_emenda": carregar_grp_emenda,
    "grp_interveniente": carregar_grp_interveniente,
    "grp_unidade_executora": carregar_grp_unidade_executora,
    "grp_municipio_atendido": carregar_grp_municipio_atendido,
    "grp_regiao_atendida": carregar_grp_regiao_atendida,
    "grp_recurso_concedente": carregar_grp_recurso_concedente,
    "grp_recurso_contrapartida": carregar_grp_recurso_contrapartida,
    "grp_dotacao_contrapartida": carregar_grp_dotacao_contrapartida,
    "grp_acao_orcamentaria": carregar_grp_acao_orcamentaria,
    "grp_instrumento_financiado": carregar_grp_instrumento_financiado,
    "grp_item_executar": carregar_grp_item_executar,
    "grp_cronograma_desembolso": carregar_grp_cronograma_desembolso,
    "grp_cronograma_fisico": carregar_grp_cronograma_fisico,
    "grp_entrega_projeto": carregar_grp_entrega_projeto,
    "grp_atividade_projeto": carregar_grp_atividade_projeto,
    "grp_matriz_responsabilidade": carregar_grp_matriz_responsabilidade,
    "grp_tabela_uo": carregar_grp_tabela_uo,
}

FONTES_GRP = tuple(_LOADERS_GRP)
