# Qualidade dos dados GRP: decisões sobre falhas conhecidas

Fase 1.5 a 1.8 da trilha de validação. Atualizado em: 22/10/2026.

Regra geral: nenhuma falha é corrigida apagando ou alterando dado na silver; o
tratamento é feito na gold ou na origem. Toda falha tem classificação, causa e
decisão registradas aqui.

---

## 1. Falhas de grão (T-C)

Resultado da fase 1.5: dos 22 testes de grão (T-C01 a T-C22), 19 passaram e 3
falharam. Linha de base da primeira execução: 8, 74 e 1 grupos respectivamente.
Uma alta nesses números indica falha nova e deve ser investigada.

| Teste | Tabela | Falhas | Classificação | Severidade |
|---|---|---|---|---|
| T-C04 | grp_emenda | 8 grupos | Duplicata pura na fonte | ALERTA |
| T-C18 | grp_cronograma_fisico | 74 grupos | Atributo G faltando na extração | ALERTA |
| T-C22 | grp_tabela_uo | 1 código | Conflito de nomes para o mesmo código | ALERTA |

### T-C04: grp_emenda

- **Evidência:** 8 combinações de nr_grp, cd_proposta, nr_ano_emenda e nr_emenda
  aparecem mais de uma vez no mesmo nr_grp.
- **Classificação:** duplicata pura (premissa P6 não se aplica).
- **Causa apurada:** registros criados em testes no sistema de origem (GRP).
- **Impacto:** a contagem de emendas por instrumento e o painel de emendas inflariam
  se as linhas fossem usadas sem tratamento.
- **Decisão:** manter as linhas na silver. Na gold, vw_emenda e a contagem de emendas
  do vw_instrumento devem deduplicar por nr_grp + ano + número.
- **Pendência:** verificar se os instrumentos afetados são de teste e devem ser
  excluídos do painel.
- **Volta a ERRO quando:** a fonte for corrigida e o teste passar com 0 grupos.

### T-C18: grp_cronograma_fisico

- **Evidência:** 74 combinações de nr_grp, cd_proposta, tp_meta_etapa,
  tx_meta_especificacao e tx_etapa_especificacao se repetem. Em todos os grupos,
  as linhas são diferentes entre si (linhas distintas = linhas totais): não são
  duplicatas puras.
- **Classificação:** atributo G faltando na extração.
- **Causa:** a fonte não traz número de meta nem de etapa; o grão depende de textos
  longos que podem se repetir.
- **Impacto:** somar vl_meta direto na tabela já é proibido pelo modelo; a numeração
  de metas e etapas na gold fica provisória até o campo chegar.
- **Decisão:** aguardar a inclusão do campo de número meta/etapa na extração
  (solicitado à equipe do GRP — Weslley/SEF — em 30/09/2026). Até lá, a gold numera
  metas e etapas por regra provisória documentada (fase 2.5).
- **Volta a ERRO quando:** o campo for incluído, o grão for trocado para
  nr_grp + número da meta + número da etapa e os textos longos saírem do grão.

### T-C22: grp_tabela_uo

- **Evidência:** o código 40121 aparece em 2 linhas com nomes diferentes:
  "FUNDO DE APOIO HABITACIONAL DA ASSEMBLEIA LEGISLATIVA DE MINAS GERAIS" e
  "FUNDO ESPECIAL DA ASSEMBLEIA LEGISLATIVA DO ESTADO DE MINAS GERAIS".
- **Classificação:** conflito de nomes. Provável renomeação, mas a tabela não tem
  data para confirmar qual nome vale.
- **Impacto:** qualquer junção direta com grp_tabela_uo multiplica as linhas do
  código afetado. As consultas 08, 11, 12 e 14 já trazem o nome da UO diretamente,
  então a gold não precisa dessa junção.
- **Decisão:** manter as duas linhas na silver. Na gold, expor uma dimensão com uma
  linha por cd_uo. Critério para escolher o nome: a definir com a SEF.
  Até a definição, nenhuma view faz junção direta com grp_tabela_uo.
- **Observação adicional:** a grp_tabela_uo também contém uma linha com cd_uo = 'S/C'
  e nm_uo = 'S/C', presente em todos os bronzes. Representa entidades sem código
  definido. Mantida na silver para decisão futura com a SEF.
- **Pendência:** confirmar com a SEF qual nome do código 40121 é o vigente.
- **Volta a ERRO quando:** o código tiver um único nome na fonte.

---

## 2. Completude e domínio (T-D, T-E)

### T-D23 (ALERTA): grp_convenente_cnpj — CNPJ preenchido
Revertido junto com a fonte grp_convenente_cnpj. Ver seção P5.

### T-E13: grp_cronograma_desembolso — faixa de anos
- **Decisão:** a faixa foi ampliada para 1950–2050 para abarcar convênios históricos
  legítimos e desembolsos futuros de longo prazo. O teste permanece como ALERTA.

---

## 3. Silver: linhas vazias descartadas

A partir da fase 1.6, o transformar_fonte descarta linhas 100% vazias (todos os
campos nulos após a limpeza de sentinelas), via dropna(how="all"), em todas as
fontes com bloco renomear. O descarte é registrado em log.

Fontes afetadas na primeira carga após a implementação:

| Fonte | Linhas descartadas | Causa |
|---|---|---|
| grp_instrumento_financiado | 1 | Linha vazia exportada pelo BusinessObjects |
| grp_tabela_uo | 1 | Linha vazia exportada pelo BusinessObjects |

Os testes T-D16 e T-D22 (chave preenchida nessas tabelas) passaram a verde após
o descarte.

---

## 4. Reconciliação financeira (T-G)

Linha de base da primeira execução. Todos com severidade ALERTA.

| Teste | Tabela | Falhas | Linha de base |
|---|---|---|---|
| T-G01 | grp_recurso_concedente | 9 linhas | 9 |
| T-G02 | grp_recurso_contrapartida | 3 linhas | 3 |
| T-G03 | grp_cronograma_desembolso | 39 linhas | 39 |
| T-G04 | grp_instrumento | 2 linhas | 2 |
| T-G05 | grp_instrumento | 13 linhas | 13 |
| T-G06 | grp_item_executar | 2019 linhas | 2019 |
| T-G07 | grp_cronograma_fisico | 4452 linhas | 4452 |

### T-G01: recurso concedente × valor concedente do instrumento

- **Decisão:** sem filtro de situação (ATIVO/INATIVO). A filtragem por ATIVO aumentou
  as divergências, sugerindo que recursos inativos compensam o total.
- **Divergências NULLs (soma nula):** instrumentos vencidos podem ter recursos
  desvinculados na fonte. Ausência de linha em grp_recurso_concedente é comportamento
  esperado nesses casos.
- **Divergências de centavo (R$ 0,02 e R$ -0,05):** arredondamento em ponto flutuante,
  não erro de dado.

### T-G02: recurso contrapartida × valor contrapartida financeira do instrumento

- **Decisão:** mesma lógica do T-G01. Divergências em instrumentos vencidos são
  esperadas.

### T-G03: desembolso × valor financeiro do instrumento

- **Decisão:** o desembolso cobre apenas a parte financeira (concedente +
  contrapartida financeira). Contrapartida não financeira e concedente executado
  não entram no cronograma de desembolso.
- **39 divergências:** a investigar. Instrumentos vencidos sem cronograma e
  diferenças de aditivo são as causas mais prováveis.

### T-G04: consistência interna do vl_instrumento_total

- **Regra:** vl_instrumento_total = concedente + contrapartida_fin +
  contrapartida_nao_fin.
- **2 divergências conhecidas:**
  1. Campo que compõe o total ausente na extração (reportado à equipe responsável
     pelo GRP em 22/10/2026).
  2. Erro no banco de origem que gera a fonte (reportado à mesma equipe).
- **Volta a ERRO quando:** as duas causas forem corrigidas e o teste passar com
  0 linhas.

### T-G06: vl_total_item × qt_item × vl_unitario_item

- **Regra:** vl_total_item ≈ qt_item × vl_unitario_item (tolerância R$ 0,01).
- **2019 divergências:** diferenças grandes (acima de R$ 100) indicam possível
  agregação silenciosa pelo BusinessObjects: linhas com atributos G iguais fundidas
  e vl_unitario_item somado indevidamente.
- **Pendência:** levar os casos com diferença acima de R$ 100 à equipe do GRP.
  Esses afetam diretamente o plano de aplicação.
- **Volta a ERRO quando:** a fonte for corrigida e a agregação silenciosa for
  eliminada.

### T-G07: soma de vl_etapa por meta × vl_meta

- **Regra:** a soma de vl_etapa das etapas de uma meta deve fechar com vl_meta.
- **4452 divergências:** parte expressiva são metas sem etapas registradas
  (vl_soma_etapas nulo tratado como zero pelo COALESCE). Esse comportamento
  é esperado no GRP: meta planejada sem detalhamento de etapas ainda.
- **Decisão:** manter o COALESCE e a linha de base de 4452. Se o número subir
  além de variações de carga, investigar.

### T-G05: fl_emenda_parlamentar × grp_emenda (ambos os sentidos)

- **4 casos:** flag TRUE mas sem linha em grp_emenda. Hipótese: emendas canceladas
  após a flag ser marcada.
- **9 casos:** linha em grp_emenda mas flag FALSE ou NULL. Hipótese: emendas
  vinculadas após o instrumento ser criado.
- **Pendência:** conferir um caso de cada grupo no GRP para confirmar as hipóteses
  antes de acionar a equipe.

---

## 5. Premissa P5: convenente do instrumento × UO

O de-para CNPJ × UO (premissa P5) não é implementado como tabela intermediária.
A ligação entre instrumentos e UOs é feita diretamente por nr_grp, pelas tabelas
grp_recurso_concedente, grp_recurso_contrapartida e grp_acao_orcamentaria.
A grp_tabela_uo serve como dimensão de apoio para filtros e nomes de órgãos.

A fonte grp_convenente_cnpj foi criada e depois revertida (commit 6e681f9) após
a decisão de usar nr_grp como chave de ligação, tornando desnecessária a tabela
intermediária de de-para por nome.

---

## 6. Controle geral

Os testes em ALERTA com linha de base definida são monitorados a cada carga.
Uma alta no número de falhas em relação à linha de base indica falha nova e
deve ser investigada antes de atualizar a camada gold.

| Teste | Linha de base | Tipo de variação que aciona investigação |
|---|---|---|
| T-C04 | 8 grupos | Aumento |
| T-C18 | 74 grupos | Aumento |
| T-C22 | 1 código | Qualquer mudança |
| T-G01 | 9 linhas | Aumento acima de 5 |
| T-G02 | 3 linhas | Aumento |
| T-G03 | 39 linhas | Aumento acima de 10 |
| T-G04 | 2 linhas | Qualquer aumento |
| T-G05 | 13 linhas | Qualquer aumento |
| T-G06 | 2019 linhas | Aumento acima de 50 |
| T-G07 | 4452 linhas | Aumento acima de 100 |