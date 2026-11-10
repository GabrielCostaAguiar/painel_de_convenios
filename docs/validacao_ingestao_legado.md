# Validação da ingestão legada — Fase 6

Execução de `rodar_ingestao` + `rodar_silver` para as 20 fontes legadas
registradas em `sources.py`, contra os arquivos reais de `data/raw/`
(mesmos arquivos usados nas Fases 4/5, sem alteração). A tabela 21
(`controle_sei_documento`, desdobrada de `controle_sei`) e a quarentena da
tabela 16 (`depara_siafi`) foram geradas e gravadas em disco por um script
avulso que chama só `transformar_fonte_completo()` e `gravar_silver()` de
`core/transform/silver.py` (ambos em escopo) — **não** por `rodar_silver`,
que é um comando em `apps/pipeline/` (fora de escopo) e hoje só persiste a
tabela "principal". Ver "Gap de persistência" na seção 5.

Regressão do GRP: 22/22 hashes SHA-256 idênticos à linha de base
(`docs/_baseline_grp_silver.json`). Suíte completa: 641 passed, 1 failed e
130 errors — todos pré-existentes, zero diferença em relação ao baseline
pré-Fase-6.

## 1. Linhas por tabela

| # | Fonte | Bronze | Silver (principal) | Quarentena | Desdobrado | Esperado (spec) |
|---|---|---|---|---|---|---|
| 01 | sigcon_convenio | 5.353 | 5.353 | — | — | 5.353 ✅ |
| 02 | sigcon_convenio_geral | 5.353 | 5.353 | — | — | 5.353 ✅ |
| 03 | sigcon_plano_trabalho | 18.529 | 18.291 | — | — | 18.291 ✅ |
| 04 | sigcon_termo_aditivo | 7.113 | 7.113 | — | — | 7.113 ✅ |
| 05 | sigcon_prorrogacao_oficio | 660 | 660 | — | — | 660 ✅ |
| 06 | sigcon_declaracao_contrapartida | 3.970 | 3.957 | — | — | 3.957 ✅ |
| 07 | sigcon_cronograma_desembolso | 48.394 | 29.992 | — | — | 29.992 ✅ (exato) |
| 08 | sigcon_plano_aplicacao | 24.969 | 24.969 | — | — | 24.969 ✅ |
| 09 | sigcon_unidade_executora | 28.316 | 28.316 | — | — | 28.316 ✅ |
| 10 | sigcon_nt_emenda | 14.520 | 14.519 | — | — | 14.520 (bronze) ✅ |
| 11 | sigcon_chave_convenio | 5.353 | 5.353 | — | — | 5.353 ✅ |
| 12 | sigcon_chave_termo_aditivo | 7.105 | 7.105 | — | — | 7.105 ✅ |
| 13 | sigcon_chave_plano_trabalho | 5.353 | 5.353 | — | — | 5.353 ✅ |
| 14 | sigcon_chave_declaracao | 5.352 | 5.352 | — | — | 5.352 ✅ |
| 15 | sigcon_chave_siconv | 6.086 | 6.086 | — | — | 6.086 ✅ |
| 16 | depara_siafi | 12.009 | 11.989 | 8 | — | 12.009 (bronze) ✅ — ver DIVERGÊNCIA abaixo |
| 17 | sigcon_concedente | 1.283 | 1.283 | — | — | 1.283 ✅ |
| 18 | depara_parlamentar | 289 | 287 | — | — | 289 (bronze) ✅ |
| 19 | siconv_convenio | 282.968 | 282.968 | — | — | 282.968 ✅ |
| 20 | controle_sei | 2.857 | 2.834 | — | 1.954 | 2.834 (silver) ✅ |

Todos os volumes batem com a especificação (bronze "cru" inclui linhas
descartadas depois — blocos desalinhados, cabeçalho repetido, linha
100% vazia — então a contagem de bronze é sempre ≥ a de silver, como
esperado). O caso mais sensível, a tabela 07, bateu exatamente com o
número fino da especificação (29.992), confirmando o ajuste de ordem do
`descartar_linhas_se_nulo` feito na Fase 4.

## 2. Grão e ALERTAs (V1)

`COUNT(*)` vs `COUNT(DISTINCT grão)`, excluindo linhas com grão nulo
(essas já geram ALERTA de nulo, não de duplicidade):

| Fonte | Linhas | Grão não-nulo distinto | Repetidos | Linhas c/ grão nulo |
|---|---|---|---|---|
| sigcon_convenio | 5.353 | 5.345 | 0 | 8 |
| sigcon_convenio_geral | 5.353 | 5.353 | 0 | 0 |
| sigcon_plano_trabalho | 18.291 | 18.291 | 0 | 0 |
| sigcon_termo_aditivo | 7.113 | 7.113 | 0 | 0 |
| sigcon_prorrogacao_oficio | 660 | 660 | 0 | 0 |
| sigcon_declaracao_contrapartida | 3.957 | 3.957 | 0 | 0 |
| sigcon_cronograma_desembolso | 29.992 | 29.992 | 0 | 0 |
| sigcon_plano_aplicacao | 24.969 | 24.969 | 0 | 0 |
| sigcon_unidade_executora | 28.316 | 28.315 | 0 | 1 |
| sigcon_nt_emenda | 14.519 | 14.304 | 0 | 215 |
| sigcon_chave_convenio | 5.353 | 5.353 | 0 | 0 |
| sigcon_chave_termo_aditivo | 7.105 | 7.105 | 0 | 0 |
| sigcon_chave_plano_trabalho | 5.353 | 5.345 | 0 | 8 |
| sigcon_chave_declaracao | 5.352 | 5.345 | 0 | 7 |
| sigcon_chave_siconv | 6.086 | 6.082 | 0 | 4 |
| **depara_siafi** | 11.989 | 6.203 | **5.786** | 0 |
| sigcon_concedente | 1.283 | 1.283 | 0 | 0 |
| depara_parlamentar | 287 | 287 | 0 | 0 |
| siconv_convenio | 282.968 | 282.968 | 0 | 0 |
| **controle_sei** | 2.834 | 2.810 | **24** | 0 |

**Conclusões em uma linha:**
- 17 das 20 tabelas: grão limpo, exatamente como a especificação previu.
- `sigcon_unidade_executora`/`sigcon_chave_*`/`sigcon_convenio`: nulos de
  grão esperados (convênios sem SIAFI/UO cadastrado) — comportamento
  previsto pelo próprio enunciado ("ALERTA, não descartar").
- `depara_siafi`: **DIVERGÊNCIA de volume** — ver seção 4.
- `controle_sei`: **ALERTA real** — 19 processos SEI (24 linhas) com mais
  de um `nr_siafi`/`nr_proposta_siconv` associado. O enunciado assume
  grão único por `nr_sei`; a planilha real tem SEI que acompanham mais de
  um instrumento. Não é erro de carga — é o dado de origem. Registrado
  para o relatório de impacto (Fase 7): quem usar `controle_sei` como
  "1 linha = 1 processo" precisa saber que ~0,7% dos processos têm mais
  de uma linha.

## 3. Checks V2–V16

| Check | Resultado | Conclusão |
|---|---|---|
| **V2** `cd_uo` com 4 caracteres | 9/9 fontes com `cd_uo`: 100% com 4 chars, **exceto** 1 linha em `sigcon_plano_aplicacao` (`cd_uo='9999999999'`, `cd_plano_trabalho='99999999'`) | Linha-sentinela (todos 9) que a especificação não cobriu com `sentinelas:` para a tabela 08 — vazou. 1 linha em 24.969 (0,004%). Registrado, não corrigido (fora do que a spec pediu para essa tabela). |
| **V4** 09.nr_convenio == 01.nr_convenio (mesmo `siafi_uo`) | 28.315 linhas comparadas, **0 divergentes** | Perfeito. |
| **V5a** 13.cd_plano_trabalho == (02+11 por `siafi_uo`) | 5.345 chaves comparadas, **0 divergentes** | Perfeito. |
| **V5b** 14.cd_declaracao_contrapartida == (02+11 por `siafi_uo`) | 5.345 chaves comparadas, **0 divergentes** | Perfeito. |
| **V6** `nr_siafi` da 20 com >1 `siafi_uo` na 01 | 255 `nr_siafi` da 01 têm mais de um `siafi_uo`; só 1 linha da 20 é afetada | Risco baixo — registrado para quem for ligar `controle_sei` à 01 só por `nr_siafi` (perde a UO). |
| **V7** na 16, `nr_siafi_1==nr_siafi_origem` e `cd_uo_1==cd_uo_origem` | `nr_siafi_1` bate em 8.364/11.989 (69,8%); `cd_uo_1` bate em 8.997/11.989 (75,0%) | **DIVERGÊNCIA** — ver seção 4. As colunas marcadas "R" (redundantes) na especificação NÃO são cópia fiel de SIAFI2/UO2 em ~30% das linhas. |
| **V8** órfãos da 15 na 01 (após resolver pela 16); `nr_convenio_siconv` repetido | 592/6.082 linhas da 15 (9,7%) não encontram `siafi_uo` na 01 mesmo após o de-para; 431 linhas (171 chaves) de `nr_convenio_siconv` repetido após resolver | Taxa de órfãos real e relevante para a Fase 7 — registrado no mapa de impacto (afeta quem for ligar SICONV↔SIGCON por essa ponte). |
| **V9** cronograma: 29.992, grão único, mês 1–12 | 29.992 linhas, grão único (29.992/29.992), 0 fora de 1–12 | Perfeito — bate exatamente com a especificação. |
| **V10** declaração: `dh_emissao`.date == `dt_emissao`; `dh_parecer_aprovacao`.date == `dt_parecer_aprovacao` | 1.408/1.408 (100%) e 2.894/2.894 (100%), nos pares não-nulos | Perfeito — as colunas "R" desta tabela são de fato redundantes. |
| **V12** siconv: BOM, acentos, DIA/MES/ANO == partes de `dt_assinatura` | Bronze sem BOM (`utf-8-sig` funcionou — 3 primeiros bytes são `NR_`, não `\xef\xbb\xbf`); acentos corretos (`Análise`, `Execução`, …); DIA/MES/ANO batem em 232.705/232.705 (100%) linhas com `dt_assinatura` válida | Perfeito — confirma que descartar DIA/MES/ANO é seguro. |
| **V13** soma `vl_desembolso_concedente` (07) vs `vl_aplicacao_concedente` (08) por plano | 9.068 planos em comum; 9.005 (99,3%) com diferença < R$0,01; 63 (0,7%) com diferença relevante (média R$335 mil, máx. R$2,29 bi) | **ALERTA** — ver seção 4 (padrão de fator ~100 em boa parte dos 63 casos). |
| **V14** nenhuma coluna de texto com `'null'`/`'NULL'`/`'?'`/`'-'`/`' '` | 1 ocorrência: `sigcon_convenio_geral.tx_justificativa_alteracao` tem 1 `'null'` literal | A especificação não pediu `sentinelas:` para essa coluna nessa tabela — por fidelidade ao enunciado, não inventamos a regra. 1 linha em 5.353. Achado separado sobre string vazia: ver seção 4. |
| **V15** `ds_esfera` com 4 valores distintos | `Municipal` (861), `Privada` (226), `Federal` (127), `Estadual` (68) + `Não Informado` (1) | **5 valores**, não 4 — ver seção 4. |
| **V16** grão do plano de aplicação com `nr_ano_exercicio` | 24.969 linhas, grão (15 colunas + `nr_ano_exercicio`) único, 0 duplicadas | Perfeito. |

## 4. Divergências encontradas (regra 6 do prompt — registrar, não inventar)

**D1 — `depara_siafi`: volume de chaves repetidas muito maior que o esperado.**
A especificação previa, após remover linhas 100% idênticas (esperado 12) e
isolar destinos divergentes (esperado 2 chaves), sobrarem ~1.878 chaves
`siafi_uo_origem` únicas. Na base real: linhas 100% idênticas removidas
(confirmado, log do motor), 2 chaves com destino divergente isoladas em
quarentena (8 linhas — ver D-nota abaixo), mas **6.203 pares únicos
(`siafi_uo_origem`, `siafi_uo_atual`)** sobrevivem, com 5.786 linhas
repetindo um par já visto (colunas "R" `nr_siafi_1`/`cd_uo_1` diferentes
impedem a deduplicação de linha inteira). Ou seja: o motor está se
comportando como projetado (ALERTA, não bloqueia); o número absoluto é
que não bate com a expectativa original — a base de referência da
especificação está desatualizada frente ao arquivo atual. Não foi
implementada uma nova regra de "colapsar por (grão, destino) ignorando
colunas R" para forçar o número ~1.878, porque isso mudaria o contrato já
testado da Fase 2 sem necessidade comprovada — fica registrado para quem
avaliar o uso de `depara_siafi` na Fase 7 saber que a maioria das 11.989
linhas tem uma contraparte "irmã" diferindo só nas colunas redundantes
SIAFI1/UO1.
*Nota sobre quarentena:* os "2" da especificação são 2 **chaves**
`siafi_uo_origem` com destino divergente, não 2 linhas — cada chave tem
várias linhas-irmãs (SIAFI1/UO1 diferentes), por isso a quarentena tem 8
linhas, não 2. Está correto; é só uma ambiguidade da redação original.

**D2 — `depara_siafi`: colunas "R" (`nr_siafi_1`/`cd_uo_1`) não são cópia fiel de SIAFI2/UO2 em ~30% das linhas (V7).**
A especificação marca `siafi1`/`uo1` como "R" (redundante) em relação a
`siafi2`/`uo2` (o grão). Na prática, `nr_siafi_1` só bate com
`nr_siafi_origem` em 69,8% das linhas e `cd_uo_1` com `cd_uo_origem` em
75,0%. Isso é coerente com D1: a tabela de origem acumula várias
"snapshots" históricas do de-para SIAFI, com o SIAFI1/UO1 original da
época de cada atualização, não um valor sempre igual ao SIAFI2/UO2 atual
daquela linha. Mantido como veio (marca "R" preservada, nenhuma coluna
descartada nesta fase) — registrado para quem decidir, na próxima fase,
se `nr_siafi_1`/`cd_uo_1` têm valor histórico próprio ou devem ser
descartados.

**D3 — `sigcon_plano_aplicacao`: 1 linha-sentinela "9999999999"/"99999999" sem regra de sentinela.**
A especificação não listou `sentinelas:` para a tabela 08. Uma linha com
`cd_uo`, `cd_plano_trabalho` e várias outras colunas de grão todas em
"9999999999"/"99999999" (claramente um placeholder) passa sem ser
anulada, e por isso aparece no V2 com `cd_uo` de 10 caracteres. Mantido
como veio, por fidelidade ao enunciado (regra 6 — não inventar regra que
a especificação não pediu). Registrado para decisão futura.

**D4 — `sigcon_concedente.ds_esfera` tem 5 valores distintos, não 4 (V15).**
A especificação esperava 4 valores após o `trim`. O quinto valor é
`'Não Informado'` (1 ocorrência em 1.283 linhas) — provavelmente uma
linha de cadastro incompleto, não um problema de normalização (o `trim`
já está correto: não há `'Federal '` com espaço sobrando nos 4 valores
esperados). Registrado; não é um bug do motor.

**D5 — Colunas com `sentinelas:` customizado perdem o "string vazia → nulo" implícito do padrão global.**
Achado não pedido por nenhum V-check, mas relevante: `valores_sentinela()`
substitui a lista padrão inteira quando a coluna tem override (ex.:
`tx_objeto: ['null']`) — comportamento deliberado e testado desde a Fase 2
(`TestSentinelas.test_override_anula_valor_que_nao_e_sentinela_global`).
Efeito colateral real nos dados: colunas de texto longo com override
(`tx_objeto`: 295 linhas, `tx_justificativa` de `sigcon_plano_trabalho`:
8.251 linhas, `tx_justificativa` de `sigcon_termo_aditivo`: 179 linhas,
`tx_observacao` de `sigcon_declaracao_contrapartida`: 3.581 linhas) ficam
com string vazia `''` em vez de nulo, porque a string vazia só é
sentinela pelo conjunto *global* (`SENTINELAS = {"N/A", "-3", ""}`), que o
override substitui. Isso **não** é o que o V14 pediu (`'null'`, `'NULL'`,
`'?'`, `'-'`, `' '` — não `''`), então o V14 "passa"; mas é uma
inconsistência de comportamento entre colunas com e sem override que vale
revisitar: o ideal seria a string vazia ser sempre sentinela, override ou
não. Não corrigido aqui (mudaria um contrato já testado, sem pedido
explícito do enunciado) — registrado para a Fase 7.

**D6 — `sigcon_cronograma_desembolso` x `sigcon_plano_aplicacao`: 63 planos com soma divergente, padrão de fator ~100 (V13).**
Dos 9.068 planos em comum, 63 (0,7%) têm diferença relevante entre a soma
de `vl_desembolso_concedente` (07) e `vl_aplicacao_concedente` (08). Em
vários dos maiores (`cd_plano_trabalho` 14334, 16069, 7499, …) a razão
entre os dois valores é exatamente ~100 — assinatura clássica de
separador decimal trocado (vírgula/ponto) em algum ponto da origem dos
dados, não do motor (a conversão de valor já foi validada linha a linha
no GRP e nestas mesmas fontes sem outro sintoma). 2 planos têm valor
negativo em uma das colunas. Não há como saber, sem a fonte autoritativa,
qual dos dois valores está certo — registrado para a Fase 7 como ponto de
atenção antes de usar essas colunas em indicadores financeiros agregados.

**D7 — `sigcon_chave_siconv`/`sigcon_convenio`: "4 linhas sem SIAFI" da especificação (tabela 01) é 8 na base real.**
Pequena divergência de volume (8 vs. 4), mesma direção do D1: a base real
é mais nova/maior que a referência original da especificação. Mantido
como ALERTA (grão nulo, não descartado), igual ao previsto.

## 5. Gap de persistência encontrado nesta fase (fora de escopo, `apps/`)

`rodar_silver` (`apps/pipeline/management/commands/rodar_silver.py`) só
grava a tabela "principal" (`transformar_fonte(nome)` → `data/silver/<fonte>.parquet`).
Ele nunca grava `quarentena` nem `desdobrado`, mesmo quando o schema YAML
declara `quarentena:` (tabela 16) ou `desdobrar:` (tabela 20 → 21),
porque usa `transformar_fonte()` (contrato que devolve só a tabela
principal), não `transformar_fonte_completo()`. Isso significa que, até
hoje, **ninguém roda `rodar_silver depara_siafi` ou `rodar_silver
controle_sei` e obtém os 3 arquivos esperados** — só o principal.

Para esta Fase 6, os dois artefatos que faltavam foram gerados e
persistidos por um script avulso (não comitado — roda fora do CLI) que
chama só `transformar_fonte_completo()` e `gravar_silver()`, ambos de
`core/transform/silver.py` (em escopo):
- `data/silver/controle_sei_documento.parquet` (tabela 21) — 1.954 linhas.
- `data/silver/depara_siafi/quarentena.parquet` (tabela 16, quarentena) — 8 linhas.

Isso cobre a "Definição de pronto" ("21 tabelas geradas na silver") para
efeitos desta fase, mas a lacuna do comando persiste: estender
`rodar_silver` para gravar `quarentena.parquet`/`desdobrado.parquet`
quando o schema os declarar é uma mudança em `apps/pipeline/`, portanto
fora do escopo desta tarefa — registrada no mapa de impacto da Fase 7.

## 6. Regressão

- GRP: 22/22 arquivos Parquet com hash SHA-256 idêntico à linha de base
  (`docs/_baseline_grp_silver.json`).
- Suíte completa: `641 passed, 1 failed, 1 skipped, 130 errors` — idêntico
  ao baseline pré-Fase-6 (mesmo 1 failed e mesmo conjunto de errors,
  todos pré-existentes e fora do escopo desta tarefa: `test_rotas_smoke`
  e `django.db.utils.ProgrammingError` do Postgres de teste).

## 7. Correção posterior à Fase 6 — datas ISO (Fase 8, etapa 0.1)

A conferência da Fase 8 encontrou um bug que esta validação não pegou: as
fontes legadas vindas de Excel entregam datas em ISO (`2003-02-14 00:00:00`) e
o motor as lia com `pd.to_datetime(..., dayfirst=True)`. No pandas 3.0.3 o
formato é inferido pela **primeira** data da coluna; quando ela tem dia ≤ 12,
a coluna inteira é lida como `aaaa-dd-mm`. Efeito medido no Bronze: de 109.935
datas válidas, **32.062 viraram nulo (29,2%)** e **18.446 saíram com dia e mês
trocados (16,8%)**, em 9 colunas (`sigcon_convenio_geral.dt_publicacao` e
`dh_cadastramento`, `sigcon_declaracao_contrapartida.dt_emissao` e
`dh_emissao`, `sigcon_plano_trabalho.dh_cadastro`/`dh_envio_sccg`/
`dh_cancelamento_sccg`, `sigcon_prorrogacao_oficio.dt_envio`/`dt_parecer`).
O GRP e o SICONV não foram afetados (datas em `dd/mm/aaaa`).

Correção: `core/transform/silver.py::_converter_datas` decide o formato por
valor (ISO → `format="ISO8601"`; o resto → `dayfirst=True`). Verificação:
- GRP: 22/22 hashes idênticos à linha de base.
- 24 colunas ISO comparadas com o texto do Bronze: 0 diferenças.
- Comparação com a Silver antiga (`dcgce_*`, que estava correta): 0
  diferenças nas 11 colunas de data que a antiga cobre.

**V10 refeito:** o resultado "1.408/1.408 e 2.894/2.894 (100%)" da seção 3 era
falso-positivo — as duas colunas estavam erradas do mesmo jeito. Depois da
correção: `dh_emissao` = `dt_emissao` em 3.956/3.956 linhas com as duas
preenchidas (das 3.957; 1 linha sem data), e `dh_parecer_aprovacao` =
`dt_parecer_aprovacao` em 2.894/2.894. Agora é uma conclusão válida: as colunas
"R" da declaração são de fato redundantes.
