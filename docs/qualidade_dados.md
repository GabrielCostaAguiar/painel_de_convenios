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

## Controle

Estes três testes ficam em ALERTA com o número de falhas de hoje como linha de base
(8, 74 e 1). Uma alta nesses números indica falha nova, e deve ser investigada.