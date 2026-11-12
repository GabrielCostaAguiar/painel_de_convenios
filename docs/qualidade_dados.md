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
  Percebemos que existe em 'Desembolso - Mês' o mês 0
significa Janeiro, deve usar a tipificação do python/Java
onde o 1º começa em 0, acrescentei direto do BO a coluna
'Desembolso - Mês Descritivo' e mantive o cod do mês.

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

| Teste |           Tabela          |    Falhas   | Linha de base |
|-------|---------------------------|-------------|---------------|
| T-G01 | grp_recurso_concedente    | 9 linhas    | 9             |
| T-G02 | grp_recurso_contrapartida | 3 linhas    | 3             |
| T-G03 | grp_cronograma_desembolso | 39 linhas   | 39            |
| T-G04 | grp_instrumento           | 2 linhas    | 2             |
| T-G05 | grp_instrumento           | 13 linhas   | 13            |
| T-G06 | grp_item_executar         | 2019 linhas | 2019          |
| T-G07 | grp_cronograma_fisico     | 4452 linhas | 4452          |

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


---
---

# Qualidade dos dados SIGCON: exceções conhecidas

Catálogo: `apps/sigcon/validacao/catalogo.py` (comando `validar_sigcon`, resultados em
`dq_resultado_validacao_sigcon`). Limites: `apps/sigcon/validacao/limites.py`.
Medido no banco real em 12/11/2026, na primeira execução completa do catálogo
(111 testes; 24 falharam, 23 em ALERTA e 1 em ERRO).

Regra geral, igual à do GRP: a fonte não é corrigida. Cada exceção conhecida vira um
**limite**: até o número registrado o teste grava ALERTA; acima dele, ERRO. Uma contagem
que cai continua em ALERTA; uma que sobe é defeito novo e bloqueia a gold. Depois de
corrigir a fonte, baixe o limite em `limites.py` para a regressão voltar a ser pega.

## S1. Contagens reais x modelo de extração SIGCON v1.0

O PDF (`docs/modelo_extracao_sigcon.pdf`) cita contagens anteriores à carga atual. O PDF
é um documento fechado, não regenerável daqui: estas são as contagens a usar na próxima
revisão do modelo.

| Item | PDF v1.0 | Banco (12/11/2026) | Onde |
|---|---|---|---|
| Convênios sem SIAFI (sem `siafi_uo`) | 4 | **8** (3 são registros de teste) | T-D01 |
| Declarações sem ponte `chave_declaracao` | 2.437 | **2.438** | T-F13 |
| Pontes sem `siafi_uo`: chave_plano_trabalho / chave_declaracao | não cita | **8 / 7** | T-D13, T-D14 |
| Unidades executoras sem `siafi_uo` | não cita | **1** | T-D08 |
| Colisões de `cd_plano_trabalho` em convenio_geral | 38 | **18 códigos, 51 linhas** | T-C17 |
| Linhas do cronograma de desembolso | 48.394 | **48.392** | T-A01 |
| Linhas do plano de aplicação sem plano de trabalho | não cita | **842** | T-F11 |
| Planos com desembolso diferente da aplicação (concedente / proponente) | "diferenças explicáveis" | **484 / 248** | T-G01, T-G02 |
| Valores distintos de `ds_esfera` | 4 (V13) | **5** (o 5º é "Não Informado", da linha sentinela) | T-H13 |
| Prorrogação de ofício órfã | 1 | 1 | T-F03 |

## S2. Exceções com limite (ALERTA até o limite, ERRO acima)

| Teste | Tabela | Limite | Classificação |
|---|---|---|---|
| T-D01 | sigcon_convenio | 8 | Convênio sem SIAFI |
| T-D08 | sigcon_unidade_executora | 1 | Derivado do SIAFI nulo |
| T-D10 | sigcon_nt_emenda | 216 | Sentinela 99999999 vira nulo (T4) |
| T-D13 / T-D14 | sigcon_chave_plano_trabalho / chave_declaracao | 8 / 7 | Derivado do SIAFI nulo |
| T-E02 | sigcon_plano_trabalho | 4 | Erro da fonte: UO no campo de CNPJ |
| T-E03 | sigcon_concedente | 1 | Erro da fonte: zero à esquerda perdido |
| T-E05 | sigcon_plano_aplicacao | 1 | Linha sentinela 99999999 |
| T-F03 | sigcon_prorrogacao_oficio | 1 | Órfão conhecido (P7) |
| T-F11 | sigcon_plano_aplicacao | 842 | Plano de aplicação sem plano de trabalho |
| T-F13 | sigcon_declaracao_contrapartida | 2.438 | Declaração sem ponte (P5/V9) |
| T-G01 / T-G02 | sigcon_cronograma_desembolso | 484 / 248 | Desembolso diferente da aplicação (V11) |

### T-D01 (+ T-D08, T-D13, T-D14): convênios sem SIAFI

- **Evidência:** 8 convênios sem `nr_siafi`, logo sem `siafi_uo`. Pelo `nr_convenio` e UO:
  `019/2011 (764558/2011)` (2421), `042/06` (2311), `240/2009` (1481),
  `2606.0276497-23/2008` (2321), `2606027670104` (1451), `Te DUPLITESTE` (1501),
  `Te TESTEDupli` (1501) e `Te TESTEDupli` (4691).
- **Classificação:** 3 são registros de teste criados no SIGCON; os outros 5 são convênios
  antigos sem número SIAFI.
- **Impacto:** não entram nas ligações por `siafi_uo`; ficam sem plano, aditivo e contrapartida.
- **Decisão:** manter na silver. Registros de teste: pedir a exclusão à equipe do SIGCON.
- **Volta a ERRO quando:** a origem corrigir os 8 e o limite for zerado.

### T-D10: notas técnicas de emenda sem plano

- **Evidência:** 216 linhas com o sentinela `99999999`, que a silver converte em nulo (T4).
- **Decisão:** manter. São emendas sem plano de trabalho vinculado.

### T-E02: CNPJ do proponente com 4 dígitos

- **Evidência:** 4 planos com o código da UO no campo de CNPJ: plano `9624` ("1231"),
  `8819` ("1471"), `9719` ("1691") e `14051` ("1401").
- **Decisão:** manter. Quem usar o CNPJ do proponente deve ignorar valores de 4 dígitos.

### T-E03: CNPJ do concedente com 13 dígitos

- **Evidência:** `0161248000181` (concedente municipal), 13 dígitos. O CNPJ válido tem 14,
  o que sugere um zero à esquerda perdido na exportação para Excel. Não foi corrigido.
- **Decisão:** manter; confirmar o CNPJ correto com a equipe do SIGCON.

### T-E05 (+ T-E22, T-E24, T-E26): a linha sentinela 99999999

- **Evidência:** o plano `99999999` aparece em `sigcon_plano_trabalho`,
  `sigcon_declaracao_contrapartida` e `sigcon_plano_aplicacao`, com `cd_uo = 9999999999`
  (T-E05) e ano `9999` (T-E22, E24, E26, em ALERTA). Os textos vêm como "Não Informado".
- **Classificação:** registro de "sem plano / sem declaração" criado pelo SIGCON.
- **Decisão:** manter. Na gold, excluir `99999999` das somas e contagens.

### T-F03: prorrogação órfã

- **Evidência:** prorrogação `45`, convênio sequencial `1234`, sem linha em `sigcon_chave_convenio`.
- **Decisão:** manter; já listada na premissa P7 do modelo.

### T-F11: plano de aplicação sem plano de trabalho (842)

- **Evidência:** 842 linhas, por exemplo planos `1222`, `1225` e `1230`, exercício 2006.
- **Classificação:** planos antigos que não existem em `sigcon_plano_trabalho`. A hipótese
  (planos de 2006 anteriores ao cadastro) não foi confirmada.
- **Decisão:** manter. Na gold, a ligação plano de aplicação → convênio é LEFT.

### T-F13: declarações sem ponte (2.438)

- **Evidência:** declarações `1`, `10` e `100` entre outras (61,6% do total).
- **Classificação:** declarações de propostas não conveniadas; premissa P5, a confirmar
  com a equipe do SIGCON (V9).
- **Decisão:** manter; não são perda de dado.

### T-G01 / T-G02: desembolso x aplicação

- **Evidência:** 484 planos (concedente) e 248 (proponente) com soma diferente. Os primeiros
  casos são planos com aplicação e **sem nenhum cronograma de desembolso**: `5510`
  (450.000,00 do concedente), `3202` (719.200,78) e `6064` (312.555,20).
- **Decisão:** manter. O desembolso é fluxo previsto, não igual ao plano de aplicação.

## S3. Falhas sem limite: exceção documentada, mas ainda não calibrada (ALERTA)

| Teste | Falhas | Observação |
|---|---|---|
| T-F04 | 8 | Termos aditivos sem linha na ponte 12 (TAs 294, 520, 600; 2007 a 2009) |
| T-F06 | 7 | Ponte de aditivo cujo convênio não está na tabela 01 (siafi_uo 90006592411, 90012621581) |
| T-I01 | 8 | Vigência com término anterior ao início (siafi_uo 982101, 65772271, 25314291) |
| T-I03 | 2 | Aditivo com término anterior ao início |
| T-I04 | 65 | Prorrogação que não termina depois do término original do convênio |
| T-I05 | 282 | Aditivo de vigência que não termina depois do término original |
| T-A06 | 15 | Arquivos de data/raw/sigcon com mais de 7 dias (156 dias; só `sigcon_tabela_uo.csv` é novo) |

## S4. Falha em ERRO sem exceção aceita

### T-E28: mojibake em colunas de texto

- **Evidência:** 5.009 células com UTF-8 lido como cp1252 ("ConstruÃ§Ã£o", "nÂº", "Ã¿"):
  `sigcon_plano_trabalho.nm_plano_trabalho` (1.638), `.tx_objeto` (1.927),
  `.tx_justificativa` (2) e `sigcon_termo_aditivo.tx_justificativa` (1.442).
- **Causa:** não apurada. Os dados já chegam assim na silver; pode ser do relatório do BO
  ou do Excel. O padrão ignora "NÃO", "AÇÃO" e demais maiúsculas legítimas.
- **Decisão pendente:** é ERRO sem limite e bloqueia a gold. Decidir entre limite
  temporário (a contagem atual) ou corrigir na origem.

## S5. Falsos positivos resolvidos

- **T-G09 (dt_ x dh_ da declaração; hoje T-G08, pois a vigência foi para T-I01):** 5 divergências desapareceram ao comparar no fuso
  America/Sao_Paulo. As `dh_` estão em UTC e as `dt_` no horário de Brasília (00:51 UTC de
  08/02/2011 é 22:51 de 07/02 em Brasília). As colunas `dt_` são redundantes e podem sair (V8).

## S6. Referências medidas para os próximos testes

- **Domínios (T-H):** os valores de situação e tipo de cada tabela estão em `DOMINIOS`,
  incluindo "Não Informado" (placeholder da linha 99999999) e `tp_instrumento_siafi` com
  os códigos `11`, `15`, `17` e `99` ao lado dos nomes. `ds_situacao_convenio` inclui
  `BLOQUEADO` (715 convênios).
- **Planos compartilhados (T-C17):** 18 códigos em `PLANOS_COMPARTILHADOS_CONHECIDOS`,
  todos colisões legítimas (T6). Código novo gera ALERTA.
- **Prorrogação de ofício:** a tabela não tem coluna de plano de trabalho. Nenhum
  `cd_convenio_sequencial` é "0" ou "999999". 205 de 660 (31%) têm 7 dígitos (formato de
  SIAFI) e são legítimos: casam com `sigcon_chave_convenio`.
- **Volumetria histórica (T-A03, T-A04):** o histórico começa na primeira `carregar_sigcon`
  depois da migration 0021. A primeira carga só registra; a comparação vale a partir da segunda.
