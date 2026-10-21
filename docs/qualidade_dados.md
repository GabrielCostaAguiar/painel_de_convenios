# Qualidade dos dados GRP: decisões sobre falhas de grão

Fase 1.5 da trilha de validação. Data: 20/10/2026.
Resultado: dos 22 testes de grão (T-C01 a T-C22), 19 passaram e 3 falharam.
Regra: nenhuma falha é corrigida apagando ou alterando dado na silver; o tratamento
é feito na gold ou na origem. Toda falha tem classificação, causa e decisão.

## Resumo

| Teste | Tabela | Falhas | Classificação | Decisão | Severidade |
|---|---|---|---|---|---|
| T-C04 | grp_emenda | 8 grupos | Duplicata pura na fonte | Deduplicar na gold; avisar a equipe do GRP | ALERTA |
| T-C18 | grp_cronograma_fisico | 74 grupos | Atributo G faltando na extração | Aguardar o campo número meta/etapa; gold com regra provisória | ALERTA |
| T-C22 | grp_tabela_uo | 1 código | Conflito de nomes para o mesmo código | Dimensão deduplicada na gold; regra do nome a definir | ALERTA |

## T-C04: grp_emenda

- **Evidência:** 8 combinações de nr_grp, cd_proposta, nr_ano_emenda e nr_emenda aparecem
  mais de uma vez no mesmo nr_grp.
- **Classificação:** duplicata pura (premissa P6 não se aplica: não há linhas legítimas iguais).
- **Causa apurada:** registros criados em testes no sistema de origem (GRP).
- **Impacto:** a contagem de emendas por instrumento e o painel de emendas inflariam
  se as linhas fossem usadas sem tratamento.
- **Decisão:** manter as linhas na silver. Na gold, a vw_emenda e a contagem
  de emendas do vw_instrumento devem deduplicar por nr_grp + ano + número.
- **Pendência:** verificar se os instrumentos afetados são de teste e devem ser excluídos do painel.
- **Volta a ERRO quando:** a fonte for corrigida e o teste passar com 0 grupos.

## T-C18: grp_cronograma_fisico

- **Evidência:** 74 combinações de nr_grp, cd_proposta, tp_meta_etapa, tx_meta_especificacao
  e tx_etapa_especificacao se repetem. Em todos os grupos, as linhas são diferentes
  entre si (linhas distintas = linhas totais), ou seja, não são duplicatas puras.
- **Classificação:** atributo G faltando na extração. O grão declarado não identifica
  uma linha, e dois itens diferentes são tratados como iguais.
- **Causa:** a fonte não traz um número de meta nem de etapa; o grão depende de textos longos.
- **Impacto:** o grão está incompleto. Somar vl_meta direto na tabela já é proibido
  (a meta se repete em cada etapa); a numeração de metas e etapas na gold fica provisória.
- **Decisão:** aguardar a inclusão do campo de número meta/etapa na extração (solicitado
  à equipe do GRP [Weslley/SEF], em [30/09/2026]). Até lá, a gold numera metas e etapas por
  regra provisória e documentada (fase 2.5).
- **Quando o campo chegar:** trocar o grão para nr_grp + número da meta + número da etapa,
  tirar os textos longos do grão e subir o teste para ERRO.

## T-C22: grp_tabela_uo

- **Evidência:** 1 código de UO ([40121]) aparece em 2 linhas, com 2 nomes diferentes
  ([nome 1] e [nome 2]).
- **Classificação:** conflito de nomes (não é duplicata pura). Provável renomeação
  de UO, mas a tabela não tem data para confirmar qual nome vale.
- **Impacto:** qualquer junção direta com a tabela multiplica as linhas do código afetado.
  As consultas 08, 11, 12 e 14 já trazem o nome da UO, então a gold não precisa dessa junção.
- **Decisão:** manter as duas linhas na silver. Na gold, expor uma dimensão com
  uma linha por cd_uo. Critério para escolher o nome: [definir com a área de negócio].
  Até a definição, nenhuma view faz junção direta com grp_tabela_uo.
- **Pendência:** Aguardar confirmação com [SEF] qual nome é o vigente.
- **Volta a ERRO quando:** o código tiver um único nome na fonte.

## T-E13: grp_cronograma_desembolso
- **Decisão:** Temos testes com anos antigos e por motivos de potencial do sistema o recorte de anos dessa tabela foi de 1950 a 2050

## Premissa P5: convenente do instrumento x UO

- **Objetivo:** ligar o CNPJ do convenente de cada instrumento (grp_instrumento.nr_cnpj_convenente) a uma UO.
- **Por que a chave é o nome:** não existe consulta no GRP que traga UO e CNPJ juntos. A
  consulta nova grp_convenente_cnpj traz só nome e CNPJ do convenente, e a grp_tabela_uo
  traz só código e nome da UO. A única chave comum entre as duas é o nome.
- **Como funciona o casamento:** a view gold.vw_depara_convenente_uo
  (apps/grp/sql/gold/003_gold_depara_convenente_uo.sql) normaliza o nome dos dois lados:
  maiúsculas, sem acento (translate, sem extensão do Postgres), sem espaços nas pontas e
  com espaços repetidos reduzidos a um. Nome normalizado igual = vínculo `AUTOMATICO`. Sem par =
  `SEM_UO`, com cd_uo nulo (a linha não é descartada).
- **Ajustes manuais:** a CTE `ajuste_manual` da view mapeia nome normalizado do convenente
  para cd_uo, tem prioridade sobre o casamento automático e gera `MANUAL`. Começa vazia. O
  SQL traz um comentário mostrando como acrescentar um ajuste (VALUES, com o nome já
  normalizado), e depois é só reaplicar o arquivo.
- **Convenentes sem CNPJ ficam fora da view:** sem chave, não servem ao de-para CNPJ x UO.
  São 31 linhas na grp_convenente_cnpj (o GRP grava `N/A` ou `S/C` no lugar do CNPJ): entes
  estaduais como Cemig, Copasa, Companhia de Gás, Encargos Gerais do Estado, Reserva de
  Contingência e secretarias antigas. O CSV traz 113 linhas; a silver tem 112, porque a linha
  em que nome e CNPJ são `N/A` fica 100% vazia e é descartada. O `N/A` vira nulo pelo
  SENTINELAS global. O `S/C` vira nulo por uma lista explícita no YAML da fonte
  (bloco `anular`), só na coluna do CNPJ, porque `S/C` é dado válido em outras fontes.
  A lista é explícita, não um regex: qualquer outro formato errado chega ao banco e o T-E14 acusa.
- **Convenente com dois CNPJs:** a SECRETARIA DE ESTADO DE JUSTIÇA E SEGURANÇA PÚBLICA aparece
  com dois CNPJs válidos. É legítimo: duas linhas na view, cada uma com o seu CNPJ,
  podendo apontar para a mesma UO. Não é falha do T-C24.
- **Pendência na grp_tabela_uo:** existe uma linha com cd_uo = 'S/C' e nome 'S/C', presente em
  todos os bronzes. Não foi alterada, e fica para decisão futura. Pôr `S/C` no SENTINELAS global a apagaria.

### Resultado da primeira execução (21/10/2026)

- **Convenentes com CNPJ:** 81. Na view, 86 linhas: 73 CNPJs `AUTOMATICO`, 8 `SEM_UO` e nenhum `MANUAL`.
- **Ambíguos (T-C24, ALERTA, 5 CNPJs):** o mesmo nome existe em duas UOs diferentes na
  grp_tabela_uo, e o CNPJ vira duas linhas: Secretaria de Estado de Esportes (10281 e 10671),
  de Desenvolvimento Econômico (10221 e 10461), de Comunicação Social (10711 e 10712),
  Companhia de Desenvolvimento Econômico de Minas Gerais (50011 e 50012) e Agência Reguladora de
  Transportes (10302 e 20471). Decisão sobre a UO vigente: [definir com a área de negócio];
  o ajuste manual resolve cada caso.
- **SEM_UO (8 CNPJs):** quase todos por diferença de grafia. Nome mais próximo da grp_tabela_uo:
  - Agência de Desenvolvimento da Região Metropolitana do Vale do Aço: o nome da fonte vem sem o "Ê" ("AGNCIA").
  - DER-MG: "Departamento de Estradas de Rodagem" x "Departamento de Edificações e Estradas de Rodagem".
  - Encargos Gerais do Estado Secretaria de Estado de Fazenda: falta o hífen.
  - Escola de Saúde Pública: falta "do Estado de Minas Gerais".
  - Minas Gerais Administração e Serviços SA e Minas Gerais Participações SA: "S.A" na tabela de UO.
  - Secretaria de Estado de Infraestrutura, Mobilidade e Parcerias: vírgula.
  - Ministério Público do Estado de Minas Gerais: sem sugestão confiável; o mais próximo é o Fundo Especial do Ministério Público, que é outra UO.
- **T-F43 (ALERTA):** falhou com 570 instrumentos de 5 convenentes, todos já na view como
  `SEM_UO` (de 4.691 instrumentos com CNPJ de convenente). Os maiores: 18715615000160 (269),
  18715581000103 Infraestrutura, Mobilidade e Parcerias (195), 17309790000194 DER-MG (98),
  08715327000151 Escola de Saúde Pública (4) e 15438067000180 Agência do Vale do Aço (4).
  Cinco ajustes manuais resolveriam o caso.
- **T-F44 (ALERTA):** passou. Todo CNPJ de convenente dos instrumentos existe na grp_convenente_cnpj.
- **T-D23 (ALERTA):** 31 linhas sem CNPJ, linha de base. Uma alta indica falha nova.
- **T-C23 e T-E14 (ERRO):** passaram. O T-F43 deixou de ser bloqueado.

## Controle

Estes três testes ficam em ALERTA com o número de falhas de hoje como linha de base
(8, 74 e 1). Uma alta nesses números indica falha nova, e deve ser investigada.