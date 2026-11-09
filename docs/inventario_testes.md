# Inventário — Parte B: Testes pontuais

> Testes somente-leitura sobre os arquivos brutos mais recentes em `data/raw/`
> (lidos com pandas, usando os mesmos parâmetros de `core/ingestion/sources.py`/
> `core/ingestion/readers.py`, em script Python temporário fora do repositório).
> Chaves derivadas (`siafi_uo`) foram construídas chamando a função real
> `core/transform/chaves.py::montar_siafi_uo` (importada, não reimplementada).
> Nomes de pessoas físicas aparecem mascarados como `[LGPD]`.

---

## T1 — `dcgce_convenio`

- Total de linhas: **5.353**
- Distintos de `siafi_uo` (via `montar_siafi_uo`, não-nulos): **5.349**
- Distintos de pares (SIAFI, UO) com ambos preenchidos: **5.349** (idêntico ao anterior — `montar_siafi_uo` e a contagem de pares batem)
- Linhas com SIAFI nulo: **4**
- Distintos de `Convênio Código`: **4.660**

**Conclusão:** `siafi_uo` é quase-chave (5.349/5.353, 4 linhas sem SIAFI ficam sem chave), e `Convênio Código` tem 4.660 valores distintos para 5.353 linhas — bem menos chave que `siafi_uo`.

---

## T2 — `siafi2`

- Chaves (SIAFI2, UO2) duplicadas: **1.880**
- Dessas, com mais de um destino distinto (SIAFIATUAL, UOATUAL): **2**
- Linhas 100% idênticas (todas as colunas): **12**
- 10 exemplos de chave com destinos divergentes (só existem 2 no arquivo todo):
  - SIAFI2=9427781, UO2=1451 → destinos encontrados: (9427781,1451) e (9433735,4691)
  - SIAFI2=9428079, UO2=1451 → destinos encontrados: (9428079,1451) e (9433736,4691)

**Conclusão:** das 1.880 chaves duplicadas em `(SIAFI2,UO2)`, só 2 têm destino realmente divergente (as outras 1.878 são redundância segura, mesmo destino) — o risco de ambiguidade do `resolver_siafi_atual` descrito no inventário anterior é real mas afeta só 2 chaves, não o conjunto inteiro.

---

## T3 — `dcgce_codigo_dec_contrap`

- 5 valores mais frequentes de `Declaração Contrapartida Código`: `99999999`=3.828; `79`=2; `244`=2; `1823`=2; `1935`=2
- Distintos de `Convênio Número Sequencial SIAFI` (não há coluna "Convênio Código Sequencial" nesta fonte — ela não existe no arquivo; usado o campo SIAFI mais próximo do pedido): **4.823**
- Diferença de linhas entre `dcgce_codigo_convenio` (5.353) e `dcgce_codigo_dec_contrap` (5.352): **1**. Comparando por `siafi_uo` (via `montar_siafi_uo`), **4** linhas de `dcgce_codigo_convenio` não casam com nenhuma linha de `dcgce_codigo_dec_contrap` — mas as 4 têm SIAFI vazio (não é uma chave real ausente, é ausência de chave nos dois lados). Duas delas são registros de teste manifestamente espúrios: `Convênio Código` = "Te DUPLITESTE" (seq. 9003699) e "Te TESTEDupli" (seq. 9003697/9003698); a quarta é "042/06" (seq. 1240). Não foi possível isolar de forma inequívoca QUAL sequencial específico está "ausente" por posição 1-a-1, porque `dcgce_codigo_dec_contrap` não traz a coluna `Convênio Código Sequencial` — **NÃO EXECUTADO** nesse ponto exato (comparação direta por sequencial), motivo: coluna ausente na fonte-ponte.

**Conclusão:** `99999999` domina 3.828/5.352 linhas (71,5%) como sentinela de "sem declaração"; a diferença de 1 linha entre as duas pontes coincide com a presença de registros de teste/dummy ("Te DUPLITESTE", "Te TESTEDupli") e convênios sem SIAFI no arquivo-base, não uma declaração real perdida.

---

## T4 — `dcgce_sigcon_nt_emenda`

- `Plano Trabalho Código` que se repetem (>1 linha): **1 código**, totalizando **216 linhas**
- Esse único código repetido é o sentinela `99999999` (UO=9999) — "sem plano de trabalho/sem emenda vinculada"
- As 216 linhas NÃO são idênticas entre si: diferem em `nt_emenda_no`, `nt_emenda_nome` e `nota_tecnica_emenda_parlamentar_federal_situacao` (cada linha é uma emenda/NT distinta associada ao mesmo sentinela)
- 5 exemplos concretos (nomes mascarados): `nt_emenda_no` = "1403 0008/2015", "1403 0013/2016", "14080010", "1730 0001-2012", "19280013/2013"; `nt_emenda_nome` = `[LGPD]` em todos; situação = "Sim" em todos os 5

**Conclusão:** a DÚVIDA do inventário anterior está resolvida — `Plano Trabalho Código` é chave perfeita para todo código real; a única repetição é o sentinela `99999999`, que concentra 216 NTs de emenda sem plano de trabalho vinculado.

---

## T5 — `dcgce_cronograma_desembolso`

- Linhas SEM `Plano Trabalho Código` preenchido: **18.402** de 48.394 (**38,0%**)
- Dessas, também com `Ano Cronograma Desembolso` e os dois campos de valor vazios: **18.402** (100% delas)
- Valores distintos de `Mês Cronograma Desembolso` nessas linhas: **9.200** — **achado**: esses valores NÃO são meses (1 a 12); são, em 9.199 de 9.199 casos não-vazios/não-cabeçalho, códigos de `Plano Trabalho Código` válidos e existentes em `dcgce_plano_trabalho` (ex.: 10000, 10001, 10002, 10003, 10004). Uma das 18.402 linhas ainda traz o próprio texto do cabeçalho ("Plano Trabalho Código") vazado como dado nessa coluna, e 2 linhas têm `Mês` vazio também. Nenhuma linha tem mês válido (1–12).
- Dessas (sem PT), linhas 100% idênticas entre si: **9.201**
- Para a chave (`Plano Trabalho Código`, Mês, Ano), só nas linhas com PT preenchido: total = **29.992** linhas, combinações distintas = **29.992** (chave perfeita)

**Conclusão:** as 18.402 linhas "sem PT" não são um cronograma incompleto — são um bloco de dados desalinhado/concatenado ao final do arquivo bruto (a coluna `Mês` carrega, na prática, códigos de plano de trabalho, inclusive um cabeçalho literal vazado), enquanto as 29.992 linhas restantes formam um cronograma real com chave (PT, Mês, Ano) perfeitamente única.

---

## T6 — `dcgce_geral` × `dcgce_Codigo_plano_de_trabalho` (colisões de código de plano de trabalho)

- `dcgce_geral`: 5.353 linhas, 5.315 distintos de `Convêno Código Plano Trabalho` → **38 colisões** (confirma exatamente o número do inventário anterior), em 19 códigos repetidos
- `dcgce_Codigo_plano_de_trabalho`: 5.353 linhas, 5.315 distintos, mesmos 19 códigos repetidos
- Top 5 código×contagem (`dcgce_geral`): `7964`=8; `0`=6; `1663`=5; `9240`=5; `3655`=3
- Top 5 código×contagem (`dcgce_Codigo_plano_de_trabalho`): `7964`=8; `0`=6; `1663`=5; `9240`=5; `1709`=3

**Conclusão:** confirmadas as 38 colisões; só o valor `0` (6 ocorrências) é sentinela — os demais 4 do top 5 (`7964`, `1663`, `9240`, `3655`/`1709`) são planos de trabalho reais genuinamente compartilhados por vários convênios, não sentinelas.

---

## T7 — `dcgce_plano_aplicacao`

- Colunas de classificação orçamentária usadas (14, todas contendo "código" no nome, exceto `Código Plano Trabalho`): código UO, função, subfunção, programa, identificador projeto/atividade, projeto/atividade, subprojeto/subatividade, categoria econômica, grupo de despesa, modalidade de aplicação, elemento de despesa, identificador orçamento, fonte de recurso, procedência
- Total de linhas: **24.969** | combinações distintas de (`Código Plano Trabalho` + as 14 colunas de classificação): **24.966** (ou seja, 3 linhas duplicadas nessa chave composta — não é 100% única)
- `Funcional Programática Formatado` comparada à concatenação direta das 14 colunas de código: bateu em **0/24.969 (0,0%)**; comparada à concatenação separada por "." (mimetizando o formato visual): também **0/24.969 (0,0%)**. Exemplo bruto: `"04.571.322.4.730.0001"` vs. concatenação direta `"20614571322473013390140241"` — os comprimentos e agrupamentos de dígitos não coincidem com a concatenação ingênua das colunas de código.

**Conclusão:** a chave (`Código Plano Trabalho` + classificação orçamentária completa) é quase, mas não perfeitamente, única (24.966/24.969); `Funcional Programática Formatado` não é a simples concatenação das colunas de código do arquivo — usa uma formatação/agrupamento próprio que não foi possível reproduzir por concatenação direta (não investigado o algoritmo exato, por não ter sido pedido além desta comparação).

---

## T8 — `dcgce_unidades_executoras`

- Linhas em que `Convênio Código` não é puramente numérico (parece texto de portaria/processo): **27.717 de 28.316 (97,9%)**
- Valores distintos de `Convênio Código`: **2.147**

**Conclusão:** quase todo o conteúdo de `Convênio Código` nesta fonte é texto de ato administrativo (portaria/processo), não um código numérico simples — confirma a observação do inventário anterior de que esta coluna tem semântica diferente da mesma coluna nas demais fontes SIGCON.

---

## T9 — Encoding dos CSVs

- `Chaves_convenio.csv`: decodifica como UTF-8 estrito sem erro = **Não**; tem BOM UTF-8 no início = **Não**
- `siconv_convenio.csv`: decodifica como UTF-8 estrito sem erro = **Sim**; tem BOM UTF-8 no início = **Sim**
- `SIAFI2.csv`: decodifica como UTF-8 estrito sem erro = **Sim**; tem BOM UTF-8 no início = **Não**
- `siconv_convenio.csv` relido com `encoding="utf-8-sig"` — 5 primeiros cabeçalhos normalizados: `nr_convenio`, `id_proposta`, `dia`, `mes`, `ano` (sem o prefixo corrompido `i»¿`)
- 3 valores distintos de `SIT_CONVENIO` (relido com utf-8-sig): "Proposta/Plano de Trabalho Complementado em Análise", "Prestação de Contas Aprovada", "Em execução" (acentos corretos, sem mojibake)

**Conclusão:** confirmado ponta-a-ponta — `siconv_convenio.csv` tem BOM UTF-8 e é lido com `encoding="latin-1"` em `sources.py`, corrompendo `NR_CONVENIO`→`i»¿nr_convenio` e todo texto acentuado; relendo com `utf-8-sig` o cabeçalho e os valores (`SIT_CONVENIO`) saem corretos, o que confirma que a correção sugerida no inventário anterior (trocar para `utf-8-sig`) resolve o problema.

---

## T10 — Órfãos entre fontes

- `dcgce_termo_aditivo` → `dcgce_codigo_ta`: **8 códigos** sem ponte (0,11% de 7.113), exatamente: 1219, 1344, 294, 520, 600, 717, 854, 963
- `dcgce_prorrogacao_oficio` (Código Convênio) → `dcgce_codigo_convenio` (sequencial): **1 órfão de 448 (0,22%)**
- `dcgce_declaracao_contrapartida` → sua ponte `dcgce_codigo_dec_contrap`: **2.437 órfãos de 3.957 (61,59%)**
- `dcgce_cronograma_desembolso` (linhas com PT preenchido) → `dcgce_plano_trabalho`: **0 órfãos de 9.199 (0,00%)**
- `dcgce_plano_aplicacao` → `dcgce_plano_trabalho`: **288 órfãos de 9.387 (3,07%)**
- `dcgce_plano_trabalho` (CNPJ concedente) → `dcgce_esfera`: **1 órfão de 1.234 (0,08%)**
- `dcgce_unidades_executoras` (SIAFI+UO) → `dcgce_convenio` (SIAFI+UO): **0 órfãos de 2.354 (0,00%)**
- `dcgce_geral` (sequencial) → `dcgce_codigo_convenio` (sequencial): **0 órfãos de 5.353 (0,00%)**

**Conclusão:** a ponte `dcgce_codigo_dec_contrap` é a única com órfãos massivos (61,6%) — reforça a DÚVIDA #5 do inventário anterior: o grão da ponte (1 por convênio, sentinela `99999999`) é incompatível com o grão real de `dcgce_declaracao_contrapartida` (1 por declaração); todas as demais pontes/joins SIGCON internos têm cobertura muito alta (≥96,9%, a maioria 100%).

---

## T11 — `chaves_convenio.siafi_uo` ausentes em `dcgce_convenio`, recuperáveis via `siafi2`

- Valores de `siafi_uo` de `chaves_convenio` ausentes em `dcgce_convenio`: **739** (recalculado — confirma exatamente o número do inventário anterior)
- Desses 739, aparecem como SIAFI antigo (campos `SIAFI2`/`UO2`, não os campos "atual") dentro de `siafi2`: **739 (100%)**

**Conclusão:** os 739 "órfãos" entre `chaves_convenio` e `dcgce_convenio` não são de fato convênios perdidos — são 100% recuperáveis como SIAFI antigo via `siafi2`/`resolver_siafi_atual`; a taxa de órfãos de 12,1% do inventário anterior deixa de ser um problema depois de aplicada a resolução de SIAFI atual.
