# Inventário das Fontes Legadas (não-GRP)

> Levantamento somente-leitura das fontes registradas em `core/ingestion/sources.py`,
> excluindo as fontes `grp_*` (pipeline novo, fora do escopo). Gerado inspecionando
> os arquivos em `data/raw/` com os mesmos parâmetros de leitura do Bronze
> (`core/ingestion/readers.py`), cruzados com os YAMLs em `core/transform/schemas/`
> e com o código em `core/`, `apps/sigcon/`, `apps/pipeline/`.
>
> Ambiente local no momento da inspeção: **todos os 20 arquivos brutos não-GRP
> existem em `data/raw/`**, exceto `qv_despesa_ano_2019` e `qv_despesa_ano_2020`
> (pasta `data/raw/execucao/` não existe). Nenhum arquivo foi alterado, movido
> ou apagado — leitura feita por um script Python temporário fora do repositório
> (`pandas`), nunca pelo pipeline Django.
>
> **Nota estrutural importante:** o CLAUDE.md do projeto descreve `apps/convenios/`
> como dono de `loader.py` e dos comandos `carregar_*`. Na árvore atual do
> repositório (branch `feat/validacao-grp`), `apps/convenios/` só contém
> `models/` e `migrations/` (provavelmente ligado ao GRP) — os loaders e
> comandos SIGCON reais vivem em `apps/sigcon/loader.py` e
> `apps/sigcon/management/commands/`. Este inventário usa os caminhos reais
> encontrados no código, não os do CLAUDE.md. **Marcado como DÚVIDA/divergência
> na seção 5.**

---

## 1. Resumo

| Chave (`sources.py`) | Arquivo (`data/raw/...`) | Origem | Linhas | Colunas | Grão proposto | Status |
|---|---|---|---|---|---|---|
| `dcgce_convenio` | `sigcon/dcgce_convenio.xlsx` | BO/SIGCON (manual ou Gmail) | 5.353 | 15 | 1 linha por `siafi_uo` (quase-chave) | Ativo — Convenio |
| `dcgce_geral` | `sigcon/dcgce_Geral.xlsx` | BO/SIGCON | 5.353 | 16 | 1 linha por `convenio_codigo_sequencial` (chave) | Ativo — enriquece Convenio |
| `dcgce_plano_trabalho` | `sigcon/dcgce_plano.trabalho.xlsx` | BO/SIGCON | 18.291 | 22 | 1 linha por `plano_trabalho_codigo` (chave) | Ativo |
| `dcgce_cronograma_desembolso` | `sigcon/dcgce_Cronograma_desembolso.xlsx` | BO/SIGCON | 48.394 | 6 | 1 linha por (`plano_trabalho_codigo`, mês, ano) | Ativo |
| `dcgce_plano_aplicacao` | `sigcon/dcgce_plano_aplicacao.xlsx` | BO/SIGCON | 24.969 | 20 | 1 linha por (`codigo_plano_trabalho`, rubrica orçamentária) | Ativo |
| `dcgce_termo_aditivo` | `sigcon/dcgce_termo.aditivo.xlsx` | BO/SIGCON | 7.113 | 15 | 1 linha por `termo_aditivo_codigo_sequencial` (chave) | Ativo |
| `dcgce_prorrogacao_oficio` | `sigcon/dcgce_prorrogacao_oficio.xlsx` | BO/SIGCON | 660 | 8 | 1 linha por `prorrogacao_oficio_codigo` (chave) | Ativo |
| `dcgce_declaracao_contrapartida` | `sigcon/dcgce_declaracao_contrapartida.xlsx` | BO/SIGCON | 3.957 | 14 | 1 linha por `declaracao_contrapartida_codigo` (chave) | Ativo |
| `dcgce_unidades_executoras` | `sigcon/dcgce_unidades.executoras.xlsx` | BO/SIGCON | 28.316 | 4 | 1 linha por (`UO`, `SIAFI`, `Unidade Executora`) — **não** 1 por convênio | Ativo |
| `dcgce_sigcon_nt_emenda` | `sigcon/dcgce_sigcon_nt_emenda.xlsx` | BO/SIGCON | 14.520 | 5 | DÚVIDA (ver §2.10) | Ativo |
| `dcgce_esfera` | `sigcon/dcgce_esfera.xlsx` | BO/SIGCON | 1.283 | 3 | 1 linha por `concedente_cnpj` (chave) | Ativo |
| `chaves_convenio` | `sigcon/Chaves_convenio.csv` | BO/SIGCON (CSV) | 6.086 | 6 | 1 linha por `siafi_uo` (chave) | Ativo — ponte SIGCON↔SICONV |
| `dcgce_Codigo_plano_de_trabalho` | `sigcon/dcgce_Codigo_plano_de_trabalho.xlsx` | BO/SIGCON | 5.353 | 4 | ~1 linha por `codigo_plano_trabalho` (38 colisões) | Ativo — ponte ETL |
| `dcgce_codigo_ta` | `sigcon/dcgce_Codigo_ta.xlsx` | BO/SIGCON | 7.105 | 5 | 1 linha por `termo_aditivo_codigo_sequencial` (chave) | Ativo — ponte ETL |
| `dcgce_codigo_dec_contrap` | `sigcon/dcgce_Codigo_dec_contrap.xlsx` | BO/SIGCON | 5.352 | 4 | DÚVIDA — parece 1 por convênio, não por declaração (ver §2.13) | Ativo — ponte ETL |
| `dcgce_codigo_convenio` | `sigcon/dcgce_Codigo_convenio.xlsx` | BO/SIGCON | 5.353 | 5 | 1 linha por `convenio_codigo_sequencial` (chave) | Ativo — ponte ETL central |
| `qv_despesa_ano_2019` | `execucao/qv_despesa_ano_2019.csv` | Export QlikView/BO | — | — | N/A | **Arquivo ausente** — nunca ingerido (sem Bronze/Silver). Confirmado morto por comentário em `core/pipeline.py`. |
| `qv_despesa_ano_2020` | `execucao/qv_despesa_ano_2020.csv` | Export QlikView/BO | — | — | N/A | **Arquivo ausente** — idem acima |
| `siconv_convenio` | `uniao/siconv_convenio.csv` | TransfereGov/SICONV (ZIP, download aberto) | 282.968 | 40 | 1 linha por `NR_CONVENIO` (chave) | Ativo, mas **com bug de encoding** (ver §2.17) |
| `controle_sei` | `Controle SEI.xlsx` (avulso) | Planilha interna DCGCE | 2.834 | 27 | ~1 linha por nº SEI (8 SIAFIs com 2 SEIs) | Ativo |
| `siafi2` | `SIAFI2.csv` (avulso) | Planilha interna / de-para | 12.009 | 6 | **Não é chave em (SIAFI2,UO2)** — 5.804 duplicatas (ver §2.19) | Ativo, com risco de ambiguidade |
| `parlamentares` | `De para nomes parlamentares.xlsx` (avulso) | Planilha interna / de-para | 289 | 2 | 1 linha por nome "De" | **Registrada mas não consumida por nenhum código** — candidata a remoção |

---

## 2. Detalhe por fonte

Convenções: "Preench." = % de linhas não vazias; "Dist." = valores distintos entre os não vazios.
Datas lidas como texto (dtype=str no Bronze) aparecem no formato devolvido pelo Excel
(`AAAA-MM-DD HH:MM:SS`) porque o Excel já armazena a célula como datetime — a camada
Silver é que faz `pd.to_datetime(..., dayfirst=True)` sobre isso.

### 2.1 `dcgce_convenio`
- Arquivo: `data/raw/sigcon/dcgce_convenio.xlsx` — Excel, `header=1`, `engine=openpyxl`. Existe no disco.
- Origem: Business Objects/PRODEMGE (manual) ou Gmail via `ponte_extracao.py`.
- Schema: `core/transform/schemas/dcgce_convenio.yaml` (sem `duvidoso`, sem bloco `renomear`).
- 5.353 linhas × 15 colunas (14 + 1 `Unnamed: 0` 100% vazia, descartada no Silver).

| # | Cabeçalho bruto | Nome Silver/YAML | Tipo YAML | Preench. | Dist. | Exemplos | Observação |
|---|---|---|---|---|---|---|---|
| 1 | Convênio Código | convenio_codigo | identificador | 100% | 4.671 | "-", "00", "000" | Valores sentinela textuais ("-", "00") coexistem com códigos reais — não é puramente numérico |
| 2 | Convênio Número Sequencial SIAFI | convenio_numero_sequencial_siafi | identificador | 99,9% | 4.823 | "34","718","776" | 4 linhas sem SIAFI |
| 3 | Unidade Orçamentária Código | unidade_orcamentaria_codigo | identificador | 100% | 79 | "1071","1251","4251" | — |
| 4 | Situação | situacao | texto | 100% | 3 | VENCIDO/BLOQUEADO/VIGENTE | — |
| 5 | Data Início Vigência | data_inicio_vigencia | data | 100% | 2.217 | 2001-10-29 | — |
| 6 | Data Término Vigência | data_termino_vigencia | data | 100% | 2.105 | — | — |
| 7 | Data Real Convênio | data_real_convenio | data | 100% | 2.146 | — | — |
| 8–14 | Valor* (7 colunas) | valor_* | valor | 99,7–100% | — | formato americano ("179371.54") | Já vem em ponto decimal — sem formato BR aqui |
| 15 | Unnamed: 0 | (descartada) | — | 0% | 0 | — | Artefato de export Excel |

Não há coluna no arquivo ausente do YAML nem vice-versa (além de `Unnamed: 0`, tratada
pela regra geral do Silver). Sem colunas duplicadas detectadas.

### 2.2 `dcgce_geral`
- `data/raw/sigcon/dcgce_Geral.xlsx`, Excel `header=1`. Schema: `dcgce_geral.yaml`.
- 5.353 × 16 (15 úteis + `Unnamed: 0`).
- Destaques: `Convênio Código Sequencial` é chave 1:1 (5.353 distintos). `Convêno Código Plano Trabalho`
  (nome com o typo de origem, preservado propositalmente) tem 5.315 distintos — **38 colisões**: mais de
  um convênio aponta para o mesmo plano de trabalho, ou há zeros/sentinelas repetidos.
- Colunas de baixíssimo preenchimento (4,5%): `Convênio Matrícula Técnico SCCG`, `Convênio Data Alteração SCCG`,
  `Convênio Justificativa da Alteração`, `Convênio Data Controle SCCG Convênio` — parecem só preenchidas
  quando houve alteração manual pela SCCG/SEPLAG.
- **LGPD**: `Convênio Matrícula Técnico SCCG` e `Convênio Matrícula Gestor` trazem matrícula funcional
  de servidor (ex.: `m***608`, `***5562`) — dado de agente público em exercício de função, mas ainda
  assim identificador pessoal; recomenda-se tratar como dado restrito.
- `Convênio Matrícula Gestor` tem só 4 valores distintos com 64,6% de preenchimento e um valor literal
  `"null"` como string (não como vazio) — sentinela textual que o Silver não trata (não está em
  `SENTINELAS = {"N/A","-3",""}`), então vira o texto `"null"` em produção em vez de nulo. **Possível bug
  de qualidade de dados.**

### 2.3 `dcgce_plano_trabalho`
- `data/raw/sigcon/dcgce_plano.trabalho.xlsx`, Excel `header=1`. Schema: `dcgce_plano.trabalho.yaml`
  (nome do YAML usa o nome do arquivo com pontos, não a chave `dcgce_plano_trabalho` do `sources.py` —
  **inconsistência de nomenclatura**, ver §5).
- 18.291 × 22. `Plano Trabalho Código` é chave perfeita (18.291 distintos).
- `Plano Trabalho Tipo SIAFI` mistura texto e código: exemplos "Convênio de Entrada", "11", "Portaria" —
  parece ser о campo que `relacionamento.py` usa como `g_instrumento`/fallback "Convênio de Entrada";
  merece checagem de domínio (6 valores distintos, mas heterogêneos em formato).
- `Plano Trabalho CNPJ Concedente`/`CNPJ Proponente`: identificadores de pessoa jurídica, não é LGPD
  (CNPJ é de empresa/órgão), mas full preenchidos.
- Texto longo sujeito a quebras de linha: `Plano Trabalho Justificativa` (7.386 distintos, inclui o
  sentinela textual `"null"` como exemplo, e também espaço único `" "` como "vazio disfarçado" —
  outro sentinela não tratado pelo `SENTINELAS` padrão).

### 2.4 `dcgce_cronograma_desembolso`
- `data/raw/sigcon/dcgce_Cronograma_desembolso.xlsx`, Excel `header=1`. Schema: `dcgce_Cronograma_desembolso.yaml`.
- 48.394 × 6. Grão: 1 linha por desembolso previsto (mês/ano) de um plano de trabalho — chave
  plausível (`plano_trabalho_codigo`, `mes_cronograma_desembolso`, `ano_cronograma_desembolso`) não
  testada exaustivamente (não há coluna de sequência própria).
- **38% das linhas têm `Ano Cronograma Desembolso`, valores e `Plano Trabalho Código` vazios** (preench.
  62% nessas 4 colunas, só `Mês Cronograma Desembolso` é 100%) — ou seja, quase 4 em cada 10 linhas do
  cronograma não têm como ser religadas a convênio nenhum. Isso é consistente com o log do loader
  (`carregar_cronograma_desembolso`), que já reporta "sem SIAFI" como métrica esperada.
- Valores no formato americano já convertido (ex.: "4181.1").

### 2.5 `dcgce_plano_aplicacao`
- `data/raw/sigcon/dcgce_plano_aplicacao.xlsx`, Excel `header=1`. Schema: `dcgce_plano_aplicacao.yaml`.
- 24.969 × 20, todas as colunas 100% preenchidas. É essencialmente a classificação orçamentária
  (função/subfunção/programa/projeto-atividade/categoria econômica/elemento de despesa) do plano de
  trabalho, 1 linha por rubrica. `Código Plano Trabalho` + rubrica completa parece ser o grão real;
  `Código Plano Trabalho` isolado tem 9.387 distintos para 24.969 linhas (≈2,7 rubricas por plano em
  média).
- `Funcional Programática Formatado` (1.328 distintos) é a concatenação textual das colunas de código —
  candidata a coluna redundante/derivada (não é um "de-para" novo, é a própria classificação formatada).

### 2.6 `dcgce_termo_aditivo`
- `data/raw/sigcon/dcgce_termo.aditivo.xlsx`, Excel `header=1`. Schema: `dcgce_termo.aditivo.yaml`
  (mesma inconsistência de nome do item 2.3).
- 7.113 × 15. `Termo Aditivo Código Sequencial` é chave perfeita.
- **Colunas totalmente vazias**: `Termo Aditivo Tipo` (0% preenchido, 0 distintos) — nunca é lida pelo
  Silver porque está fora do schema (schema não lista `termo_aditivo_tipo` entre as colunas tipadas,
  mas ela sobra como texto; é 100% nula na prática). O loader (`apps/sigcon/loader.py::carregar_termo_aditivo`)
  ainda lê `row["termo_aditivo_tipo"]` do Parquet — então o model grava sempre `None` nesse campo.
- **Colunas constantes**: `Termo Aditivo Alteração` (único valor: "Não pode sofrer alteração") e
  `Quantidade Termo Aditivo` (único valor: "1") — sem poder discriminante, candidatas a remoção.
- `Termo Aditivo Justificativa`: texto livre com quebras de linha internas possíveis (campo longo,
  5.018 valores distintos).

### 2.7 `dcgce_prorrogacao_oficio`
- `data/raw/sigcon/dcgce_prorrogacao_oficio.xlsx`, Excel `header=1`. Schema: `dcgce_prorrogacao_oficio.yaml`.
- 660 × 8. `PRORROGAÇÃO OFÍCIO Código` é chave perfeita. `PRORROGAÇÃO OFÍCIO Código Convênio` —
  conforme já documentado em `sources.py` — equivale a `convenio_codigo_sequencial`, **não** a SIAFI;
  448 distintos para 660 linhas (≈1,5 prorrogação por convênio em média).
- Todas as colunas de data 100% preenchidas, exceto `Data Publicação` (70,8%).

### 2.8 `dcgce_declaracao_contrapartida`
- `data/raw/sigcon/dcgce_declaracao_contrapartida.xlsx`, Excel `header=1`. Schema: `dcgce_declaracao_contrapartida.yaml`.
- 3.957 × 14. `Declaração Contrapartida Código` é chave perfeita.
- Bloco de colunas de aprovação (`Código Parecer Aprovação`, `Data Parecer Aprovação`, `Observação
  Aprovação`, `Matrícula Aprovação`) preenchido só em ~73% das linhas — plausível (só declarações já
  avaliadas têm parecer).
- **LGPD**: `Declaração Contrapartida Matrícula Aprovação` traz matrícula de servidor (`m***462` etc.).

### 2.9 `dcgce_unidades_executoras`
- `data/raw/sigcon/dcgce_unidades.executoras.xlsx`, Excel **`header=0`** (única fonte SIGCON com header
  diferente — confirmado, consistente com o comentário em `sources.py`). Schema: `dcgce_unidades.executoras.yaml`.
- 28.316 × 4, 100% preenchido em todas as colunas, sem coluna `Unnamed`.
- **Grão real: (UO, SIAFI, Unidade Executora)** — essa tripla é 100% única (28.316/28.316). Isolado,
  (UO, SIAFI) tem só 2.355 combinações distintas para 28.316 linhas (~12 unidades executoras por
  convênio em média) — ou seja, **não** é "chave composta SIAFI+UO direta" como descrito no comentário
  de `sources.py`/CLAUDE.md; é 1:N. Ver DÚVIDA em §5.
- `Convênio Código` aqui traz valores textuais de portaria/ato administrativo ("Portaria nº 2/2018"),
  **não** o mesmo domínio de `Convênio Código` nas demais fontes SIGCON (que é numérico/sentinela) —
  mesmo nome de coluna, semântica diferente entre fontes. Risco de confusão em joins futuros.

### 2.10 `dcgce_sigcon_nt_emenda`
- `data/raw/sigcon/dcgce_sigcon_nt_emenda.xlsx`, Excel `header=1`. Schema: `dcgce_sigcon_nt_emenda.yaml`.
- 14.520 × 5, sem coluna `Unnamed: 0` no bruto (diferente das demais fontes SIGCON — vale conferir se
  o export desta consulta já vem sem a linha fantasma).
- `NT emenda nº` e `NT emenda Nome` só 9,5% preenchidos — a maioria das linhas de plano de trabalho não
  tem emenda parlamentar associada (esperado).
- **DÚVIDA de grão**: não há coluna de sequência própria; `Plano Trabalho Código` tem 14.305 distintos
  para 14.520 linhas (quase único, mas não perfeitamente) — pode ser 1 linha por plano de trabalho com
  raríssimas duplicatas, ou pode haver múltiplas emendas por plano em casos raros. Não testado a fundo
  por restrição de tempo — marcar como DÚVIDA.
- **LGPD**: `NT emenda Nome` traz nome de parlamentar (pessoa física, figura pública — ainda que sejam
  agentes públicos no exercício do mandato, nomes próprios individuais; mascarados nos exemplos acima:
  "Nikolas Ferreira" → tratado como dado sensível por cautela, já que a instrução pede mascarar "nomes
  de pessoas físicas" sem exceção para figuras públicas).

### 2.11 `dcgce_esfera`
- `data/raw/sigcon/dcgce_esfera.xlsx`, Excel `header=1`. Schema: `dcgce_esfera.yaml`.
- 1.283 × 3. `Concedente CNPJ` é chave perfeita (conforme a descrição em `sources.py`).
- `Concedente Esfera` tem 5 valores distintos para uma coluna que logicamente deveria ter poucos
  (Federal/Estadual/Municipal/...) — inclui variante com espaço à direita (`"Federal "` vs. possível
  `"Federal"` sem espaço) — **candidato a problema de dado sujo** (duas grafias da mesma esfera).

### 2.12 `chaves_convenio`
- `data/raw/sigcon/Chaves_convenio.csv`, CSV `sep=";"`, `encoding=latin-1`. Schema: `chaves_convenio.yaml`
  (bem documentado: explica a troca de "." por nomes finais).
- 6.086 × 6, grão = 1 linha por `siafi_uo` (chave perfeita).
- `Código.SICONV` preenchido 100% das linhas (920 distintos) — valor sentinela aparente é `"0"` para
  convênios que não têm par SICONV (não confirmado isoladamente, mas plausível dado o comentário do
  schema). `SICONV..` (→ `siconv`) tem 5 valores distintos incluindo literal `"?"` como resposta — outro
  sentinela de incerteza não tratado pelos `SENTINELAS` padrão.
- Ver §3 para a análise de chave/grão cruzada com `dcgce_convenio` e `siconv_convenio`.

### 2.13 `dcgce_Codigo_plano_de_trabalho`
- `data/raw/sigcon/dcgce_Codigo_plano_de_trabalho.xlsx`, Excel `header=1`. Schema:
  `dcgce_Codigo_plano_de_trabalho.yaml`.
- 5.353 × 4. `Convêno Código Plano Trabalho` tem 5.315 distintos para 5.353 linhas — mesmas 38
  colisões observadas em `dcgce_geral` (§2.2), reforçando que não é chave perfeita nessa fonte-ponte.
- `Convênio Número Sequencial SIAFI` com 0,1% nulo e inclui o sentinela `"0"` nos exemplos (convênio sem
  SIAFI vinculado ainda).

### 2.14 `dcgce_codigo_ta`
- `data/raw/sigcon/dcgce_Codigo_ta.xlsx`, Excel `header=1`. Schema: `dcgce_Codigo_ta.yaml`.
- 7.105 × 5. `Termo Aditivo Código Sequencial` é chave perfeita (ponte 1:1 termo aditivo → SIAFI+UO+plano).

### 2.15 `dcgce_codigo_dec_contrap`
- `data/raw/sigcon/dcgce_Codigo_dec_contrap.xlsx`, Excel `header=1`. Schema: `dcgce_Codigo_dec_contrap.yaml`.
- 5.352 × 4 (uma linha a menos que as demais pontes de 5.353 — **DÚVIDA**: por que esta tem exatamente
  1 linha de diferença das outras pontes do mesmo lote de export?).
- `Declaração Contrapartida Código` tem só **1.520 distintos para 5.352 linhas** — muito abaixo do
  esperado se o grão fosse "1 por declaração" (a fonte `dcgce_declaracao_contrapartida` tem 3.957
  declarações reais). Isso sugere fortemente que o grão real desta ponte é **1 linha por convênio**
  (como as demais pontes, `convenio_numero_sequencial_siafi` com 4.823 distintos é compatível com esse
  padrão), com `Declaração Contrapartida Código` repetindo um valor sentinela (provavelmente `"0"` =
  "sem declaração") na maioria das linhas. **Marcado como DÚVIDA** por não ter sido confirmado via
  contagem do sentinela isoladamente.

### 2.16 `dcgce_codigo_convenio`
- `data/raw/sigcon/dcgce_Codigo_convenio.xlsx`, Excel `header=1`. Schema: `dcgce_Codigo_convenio.yaml`.
- 5.353 × 5. `Convênio Código Sequencial` é chave perfeita — esta é a ponte central usada por quase
  todos os loaders para carimbar SIAFI+UO em `dcgce_geral`, `dcgce_cronograma_desembolso` e
  `dcgce_plano_aplicacao` (ver §4).

### 2.17 `qv_despesa_ano_2019` / `qv_despesa_ano_2020`
- `data/raw/execucao/qv_despesa_ano_2019.csv` e `..._2020.csv` — **pasta `data/raw/execucao/` não
  existe neste ambiente**. Sem Bronze (`data/bronze/qv_despesa_ano_2019/` não existe) nem Silver.
- Confirmado morto por comentário explícito em `core/pipeline.py` linha 32-33: *"Não inclui
  qv_despesa_* e parlamentares - nenhum loader atual as consome."* Nenhum YAML de schema existe para
  essas duas chaves em `core/transform/schemas/`.
- Não foi possível inventariar colunas (arquivo inexistente); recomenda-se remoção do registro em
  `sources.py` ou arquivamento explícito, já que o próprio `TODO` no cabeçalho do arquivo já planeja
  substituí-las por uma fonte única `qv_despesa`.

### 2.18 `siconv_convenio`
- `data/raw/uniao/siconv_convenio.csv`, CSV `sep=";"`, `encoding=latin-1`. Schema: `siconv_convenio.yaml`
  (schema marca **27 das ~30 colunas não-tipadas como `duvidoso: true`** — heurística do gerador não
  conseguiu classificar a maioria).
- 282.968 × 40. `NR_CONVENIO` é chave perfeita (282.968 distintos).
- **Bug de encoding confirmado**: o arquivo começa com um BOM UTF-8 (`EF BB BF`) antes de
  `NR_CONVENIO` (confirmado lendo os bytes brutos do arquivo). `sources.py` configura
  `encoding="latin-1"` para esta fonte — ao decodificar esse BOM como Latin-1, o nome da primeira
  coluna se corrompe para `"ï»¿NR_CONVENIO"`, e **todo texto acentuado do arquivo vira mojibake**
  (ex.: `"Análise"` → `"AnÃ¡lise"`, `"execução"` → `"execuÃ§Ã£o"`, `"não"` → `"nÃ£o"`). Isso é visível
  em `SIT_CONVENIO`, `SUBSITUACAO_CONV`, `SITUACAO_CONTRATACAO`, `MOTIVO_SUSPENSAO` etc.
  Após `normalizar_coluna()` (que decompõe NFKD e remove apenas combinantes), o nome da coluna vira
  literalmente **`i»¿nr_convenio`** — e é exatamente esse nome esquisito que aparece registrado em
  `core/transform/schemas/siconv_convenio.yaml` linha 10, confirmando que o schema foi gerado a partir
  de uma leitura já corrompida.
  **Impacto**: `core/gold/relacionamento.py::_preparar_siconv()` e `aplicar_campos_g()` procuram a
  coluna pelo nome `"nr_convenio"` (`if "nr_convenio" in df.columns`) — que **nunca vai existir** depois
  dessa corrupção, então o join SIGCON↔SICONV falharia silenciosamente (sem erro, apenas sem efeito;
  o pipeline cairia sempre no fallback "só SIGCON"). **Correção recomendada**: trocar
  `encoding="latin-1"` por `encoding="utf-8-sig"` em `sources.py` para esta fonte, e regerar o schema.
  Isso não pôde ser confirmado ponta-a-ponta porque não há Bronze/Silver desta fonte gravado neste
  ambiente — é uma inferência forte a partir dos bytes do arquivo + do nome corrompido já no YAML, não
  uma reprodução completa do pipeline Django.
- Valores monetários em formato brasileiro (`"448745,57"`) — tratado por `_para_numero()` no Silver.
- `QTDE_CONVENIOS`: coluna constante (valor único "1") — sem poder discriminante.

### 2.19 `controle_sei`
- `data/raw/Controle SEI.xlsx` (arquivo avulso, direto em `data/raw/`), Excel `header=0`,
  `sheet_name="Página1"`, `usecols=range(27)`. Schema: `controle_sei.yaml`.
- 2.834 × 27. `Nº_SEI` quase-chave (2.812 distintos — 22 números de SEI repetidos).
- `Nº SIAFI_(SIGCON)`: 88,5% preenchido, 2.500 distintos entre os preenchidos, **8 SIAFIs com 2 SEIs**
  (confirmado — bate com o comentário já existente em `apps/sigcon/loader.py::carregar_controle_sei`,
  que deduplica mantendo o primeiro).
- Cruzamento com `dcgce_convenio`: **10 de 2.500 SIAFIs do Controle SEI (0,4%) não existem em
  `dcgce_convenio`** — órfãos (SIAFI incorreto, SIGCON mudou o número, ou convênio fora do SIGCON).
- **Colunas quase totalmente vazias (<1%)**: `TA 13`, `TA 16`, `TA 17`, `TA 20`, `TA 21` (0,0%, só 1
  valor em toda a planilha), `TA 22` (idem), `Prorrogação de Ofício` (idem), `Monitorar?` (idem) —
  claramente controles manuais pontuais, praticamente constantes/vazios. `TA 21`, `TA 22`,
  `Prorrogação de Ofício` e `Monitorar?` têm exatamente 1 valor preenchido em 2.834 linhas —
  **candidatas fortes a remoção/consolidação** (ruído herdado de planilha de controle manual).
- `usecols=range(27)` já documentado em `sources.py` como propositalmente excluindo colunas duplicadas
  nas posições 29-31 — não foi possível conferir essas colunas excluídas (não lidas pelo script).

### 2.20 `siafi2`
- `data/raw/SIAFI2.csv` (avulso), CSV `sep=";"`, `encoding=latin-1`. Schema: `siafi2.yaml`.
- 12.009 × 6, todas 100% preenchidas.
- **Achado relevante**: a chave de join documentada no próprio `sources.py`
  (`SIAFI_UO = SIAFI2 & UO2`) **não é única** — `(SIAFI2, UO2)` tem só 6.205 combinações distintas
  para 12.009 linhas, ou seja **5.804 linhas duplicadas na chave de join**. Se os pares duplicados
  apontarem para `SIAFIATUAL`/`UOATUAL` diferentes entre si, `resolver_siafi_atual()` (que faz um
  `merge`/lookup simples) pode estar resolvendo para um valor arbitrário/primeiro-encontrado sem que
  isso seja logado como ambiguidade. **Não foi possível confirmar, dentro do tempo disponível, se os
  valores de destino divergem entre as duplicatas** (poderiam ser apenas registros redundantes com o
  mesmo destino) — **marcado como DÚVIDA de alto risco** porque afeta a resolução do "SIAFI atual" em
  toda a tabela integrada (`ConvenioIntegrado`).

### 2.21 `parlamentares`
- `data/raw/De para nomes parlamentares.xlsx` (avulso), Excel `header=0`. Schema: `parlamentares.yaml`
  (ambas colunas `de`/`para` marcadas `duvidoso: true`).
- 289 × 2. Coluna "De" traz `"<código> - <Nome parlamentar>"` (ex.: `"1349 - Aécio Neves"`); coluna
  "Para" traz o nome padronizado em caixa alta (104 valores distintos para 287 variantes de grafia —
  exatamente o papel de "de-para" descrito).
- **Confirmado código-morto**: grep em todo o código-fonte (exceto GRP) não encontra nenhum uso de
  `parlamentares` fora do próprio registro em `sources.py` — nenhuma função em `core/transform/`,
  `core/gold/` ou `apps/sigcon/` lê essa fonte. Confirmado também pelo comentário explícito em
  `core/pipeline.py` (linha 32-33). **Candidata a remoção** (ou a uma futura integração com
  `dcgce_sigcon_nt_emenda.NT emenda Nome`, que tem a mesma necessidade de normalização de nomes de
  parlamentares mas hoje não usa este de-para).
- **LGPD**: nomes de parlamentares (pessoas físicas) nas duas colunas — mascarados nos exemplos acima.

---

## 3. Matriz de ligação entre fontes

| De → Para | Chave | Cobertura medida |
|---|---|---|
| `dcgce_convenio` ↔ `chaves_convenio` | `siafi_uo` = SIAFI+UO (concatenado sem separador) | 739/6.086 (12,1%) dos `siafi_uo` de `chaves_convenio` **não** existem em `dcgce_convenio` (órfãos do lado SICONV-ponte); só 5/5.352 (0,1%) dos `siafi_uo` de `dcgce_convenio` não existem em `chaves_convenio` — cobertura quase total nesse sentido. |
| `chaves_convenio.Código.SICONV` ↔ `siconv_convenio.NR_CONVENIO` | código SICONV | 27/920 (2,9%) dos códigos SICONV referenciados em `chaves_convenio` não são encontrados em `siconv_convenio.NR_CONVENIO` — **porém esse teste comparou valores já corrompidos por charset** nas colunas de texto do lado SICONV (o `NR_CONVENIO` em si é numérico e não afetado pelo bug de encoding do §2.18, então o número em si deveria ser confiável; a baixa taxa de órfãos sustenta isso). |
| `dcgce_convenio` ↔ `dcgce_geral` ↔ `dcgce_codigo_convenio` | `convenio_numero_sequencial_siafi` + `unidade_orcamentaria_codigo` (via ponte `dcgce_codigo_convenio.convenio_codigo_sequencial`) | `dcgce_codigo_convenio` e `dcgce_geral` são ambas 1:1 por `convenio_codigo_sequencial` (5.353/5.353) — join sem fan-out esperado. |
| `dcgce_geral` ↔ `dcgce_plano_trabalho` | `conveno_codigo_plano_trabalho` ↔ `plano_trabalho_codigo` | `dcgce_geral` tem 38 colisões em `codigo_plano_trabalho` (5.315 distintos / 5.353 linhas) — potencial fan-out pequeno nesse join, mitigado no loader por `drop_duplicates`. |
| `dcgce_plano_trabalho` ↔ `dcgce_esfera` | `plano_trabalho_cnpj_concedente` ↔ `concedente_cnpj` | Não testado quantitativamente (fora do tempo disponível); `dcgce_esfera` é 1:1 por CNPJ (1.283/1.283), então o lado de destino não gera fan-out. |
| `dcgce_cronograma_desembolso` / `dcgce_plano_aplicacao` ↔ `dcgce_geral` | `plano_trabalho_codigo` ↔ `conveno_codigo_plano_trabalho` | ~38% das linhas de `dcgce_cronograma_desembolso` têm `plano_trabalho_codigo` vazio — ficam sem religação a convênio (ver §2.4). |
| `dcgce_termo_aditivo` ↔ `dcgce_codigo_ta` | `termo_aditivo_codigo_sequencial` | Ambas 1:1 por essa chave (7.113 vs. 7.105 linhas — **8 termos aditivos sem ponte**, não cruzado isoladamente). |
| `dcgce_declaracao_contrapartida` ↔ `dcgce_codigo_dec_contrap` | `declaracao_contrapartida_codigo` | DÚVIDA — ver §2.15; grãos aparentemente incompatíveis (3.957 declarações reais vs. 1.520 códigos distintos na ponte de 5.352 linhas). |
| `controle_sei` ↔ `dcgce_convenio` | SIAFI | 10/2.500 (0,4%) dos SIAFIs do Controle SEI não existem em `dcgce_convenio` — cobertura alta. |
| `siafi2` ↔ `chaves_convenio`/`dcgce_convenio` | `(SIAFI2,UO2)` → `siafi_uo` | Chave de origem **não é única** (ver §2.20) — risco de ambiguidade na resolução do SIAFI atual, não quantificado em termos de impacto real sobre o resultado. |
| `dcgce_unidades_executoras` ↔ `dcgce_convenio` | `unidade_orcamentaria_codigo` + `convenio_numero_sequencial_siafi` | Não testado quantitativamente; grão é 1:N (12 execuções por convênio em média, ver §2.9), compatível com um LEFT JOIN 1:N explícito (nunca usado como chave única). |
| `siconv_convenio` ↔ `qv_despesa_*` / `parlamentares` | — | Sem ligação: as duas últimas fontes não são consumidas por nenhum código (mortas). |

---

## 4. Mapa de uso e candidatos a remoção

### 4.1 Quem lê cada fonte (grep em `*.py`, fora de `apps/grp` e `core/pipeline.py`'s GRP branch)

| Fonte | Consumida por |
|---|---|
| `dcgce_convenio` | `apps/sigcon/loader.py::carregar_convenios`, `core/gold/relacionamento.py::_preparar_sigcon_completo`/`preparar_sigcon_convenio`, `apps/sigcon/management/commands/carregar_convenios.py`, testes `tests/test_r2.py`/`test_r3.py` |
| `dcgce_geral` | `carregar_convenios`, `carregar_cronograma_desembolso`, `carregar_plano_aplicacao` (todas em `apps/sigcon/loader.py`), `carregar_fonte` (chave `dcgce_geral` → `carregar_convenio_geral`), `relacionamento.py::_preparar_sigcon_completo`/`carimbar_convenio_codigo` |
| `dcgce_plano_trabalho` | `carregar_convenios`, `relacionamento.py::_preparar_sigcon_completo`, `carregar_fonte` (chave `dcgce_plano.trabalho` → `carregar_plano_trabalho`) |
| `dcgce_cronograma_desembolso` | `carregar_cronograma_desembolso` (via `carregar_fonte dcgce_Cronograma_desembolso` e via `carregar_cronograma` dedicado) |
| `dcgce_plano_aplicacao` | `carregar_plano_aplicacao` (via `carregar_fonte dcgce_plano_aplicacao`) |
| `dcgce_termo_aditivo` | `carregar_termo_aditivo` (via `carregar_fonte dcgce_termo.aditivo`) — **mas `termo_aditivo_tipo` nunca tem dado real** (coluna sempre vazia na origem, ver §2.6) |
| `dcgce_prorrogacao_oficio` | `carregar_prorrogacao_oficio` |
| `dcgce_declaracao_contrapartida` | `carregar_declaracao_contrapartida` |
| `dcgce_unidades_executoras` | `carregar_unidades_executoras` (comando dedicado, não via `carregar_fonte`) |
| `dcgce_sigcon_nt_emenda` | `carregar_nt_emenda` |
| `dcgce_esfera` | `carregar_convenios`, `relacionamento.py::_preparar_sigcon_completo`, `carregar_esfera` |
| `chaves_convenio` | `relacionamento.py::montar_sigcon_chaves`/`construir_tabela_integrada`, `carregar_relacionamento` |
| `dcgce_Codigo_plano_de_trabalho` | `carregar_codigo_plano_trabalho` (model `CodigoPlanoTrabalho` — descrito no próprio código como legado) |
| `dcgce_codigo_ta` | `carregar_codigo_termo_aditivo` |
| `dcgce_codigo_dec_contrap` | `carregar_codigo_declaracao_contrapartida` |
| `dcgce_codigo_convenio` | `carregar_convenios`, `carregar_cronograma_desembolso`, `carregar_plano_aplicacao`, `relacionamento.py`, `carregar_tabela_integrada` |
| `siafi2` | `relacionamento.py::montar_sigcon_chaves`/`resolver_siafi_atual` (em `core/transform/chaves.py`), `carregar_relacionamento` |
| `siconv_convenio` | `relacionamento.py::_preparar_siconv`, `carregar_tabela_integrada` (opcional — só se o Silver existir) |
| `controle_sei` | `carregar_controle_sei` (comando dedicado) — **não aparece em `relacionamento.py` nem em nenhum join Gold**; é carregado isoladamente no model `ControleSEI`, aparentemente só para consulta direta no painel SIGCON |
| `qv_despesa_ano_2019`/`2020` | **nenhum código** (confirmado morto, ver §2.17) |
| `parlamentares` | **nenhum código** (confirmado morto, ver §2.21) |

### 4.2 Candidatos a remoção / limpeza

1. **`qv_despesa_ano_2019` e `qv_despesa_ano_2020`** — registradas em `sources.py` mas sem arquivo, sem
   Bronze, sem Silver, sem loader, e o próprio código documenta que não são usadas. Remoção seria segura
   do ponto de vista de código; a decisão de produto cabe à equipe (podem estar reservadas para o `TODO`
   de unificação `qv_despesa` mencionado no cabeçalho de `sources.py`).
2. **`parlamentares`** — registrada, lida com sucesso, mas sem nenhum consumidor. Candidata a remoção
   ou, alternativamente, a ser finalmente conectada a `dcgce_sigcon_nt_emenda.NT emenda Nome` (mesmo
   domínio: nomes de parlamentares com grafias inconsistentes).
3. **Colunas constantes/quase vazias dentro de fontes ativas** (não a fonte inteira, mas peso morto
   dentro dela):
   - `dcgce_termo_aditivo`: `Termo Aditivo Alteração` (constante), `Quantidade Termo Aditivo` (constante),
     `Termo Aditivo Tipo` (100% vazia e nunca populada no model).
   - `controle_sei`: `TA 21`, `TA 22`, `Prorrogação de Ofício`, `Monitorar?` (cada uma com exatamente 1
     valor preenchido em 2.834 linhas).
   - `siconv_convenio`: `QTDE_CONVENIOS` (constante).
4. **`dcgce_Codigo_plano_de_trabalho`** é descrita no próprio `loader.py` como alimentando o model
   `CodigoPlanoTrabalho`, classificado como **"legado"** no docstring de `carregar_codigo_plano_trabalho`
   — mas ainda está na cadeia ativa do `rodar_pipeline` (`CARGAS_ORM` em `core/pipeline.py`). Não é
   código morto, mas é um sinal de dívida técnica a confirmar com o time se ainda é necessária.

---

## 5. Lista consolidada de DÚVIDAS

1. **Divergência estrutural CLAUDE.md vs. código real**: o CLAUDE.md descreve `apps/convenios/loader.py`
   e `apps/convenios/management/commands/carregar_*.py` como donos da carga SIGCON→DB. No código atual
   (branch `feat/validacao-grp`), esses arquivos vivem em `apps/sigcon/loader.py` e
   `apps/sigcon/management/commands/`; `apps/convenios/` só tem `models/` e `migrations/`. Não investiguei
   se isso é uma refatoração recente não documentada no CLAUDE.md ou se há duplicação ativa em algum
   outro ponto — **recomendo confirmar com o time qual é a estrutura "fonte da verdade"** antes de usar
   este inventário para qualquer decisão de remoção de arquivo.
2. **Nomenclatura inconsistente entre `sources.py`, YAMLs de schema e `_LOADERS` de `carregar_fonte`**:
   a chave em `sources.py` é `dcgce_plano_trabalho`, mas o YAML gerado é `dcgce_plano.trabalho.yaml` e a
   chave aceita por `carregar_fonte` é `dcgce_plano.trabalho` (com ponto). O mesmo padrão se repete em
   `dcgce_termo_aditivo`/`dcgce_termo.aditivo` e em `dcgce_Codigo_convenio` (`C` maiúsculo) vs.
   `dcgce_codigo_convenio` (`c` minúsculo) em `sources.py`. Não ficou claro se isso é intencional
   (nomes de arquivo herdados do Excel original) ou uma inconsistência a corrigir — sinalizo como DÚVIDA
   porque pode confundir quem for operar o pipeline manualmente.
3. **Bug de encoding em `siconv_convenio`** (detalhado no §2.18): a leitura com `encoding="latin-1"`
   sobre um arquivo com BOM UTF-8 corrompe o nome da coluna-chave `NR_CONVENIO` para `i»¿nr_convenio`
   (confirmado no YAML gerado) e todo o texto acentuado do arquivo. Isso provavelmente quebra
   silenciosamente o enriquecimento SICONV em `core/gold/relacionamento.py`. **Não pude confirmar em
   execução real** (não há Bronze/Silver desta fonte no ambiente local) — é uma inferência forte a
   partir dos bytes do arquivo e do YAML já existente, não uma reprodução ponta-a-ponta do pipeline.
4. **`siafi2` não é único em `(SIAFI2, UO2)`** (5.804 linhas duplicadas na chave de join documentada em
   `sources.py`). Não verifiquei se os valores de `SIAFIATUAL`/`UOATUAL` divergem entre duplicatas da
   mesma chave — se divergirem, a resolução do "SIAFI atual" em `core/transform/chaves.py::resolver_siafi_atual`
   pode estar silenciosamente escolhendo um valor arbitrário. Risco potencialmente alto porque afeta a
   tabela Gold `ConvenioIntegrado` inteira; recomendo validação dedicada.
5. **Grão de `dcgce_codigo_dec_contrap`** (§2.15): os números sugerem fortemente "1 linha por convênio"
   em vez de "1 linha por declaração", mas não confirmei isolando o valor sentinela (provável `"0"`) na
   coluna `Declaração Contrapartida Código`.
6. **Grão de `dcgce_sigcon_nt_emenda`** (§2.10): `Plano Trabalho Código` é quase, mas não perfeitamente,
   único (14.305/14.520) — não investiguei os casos de duplicidade.
7. **`dcgce_unidades_executoras` não é "chave composta SIAFI+UO direta"** como o comentário de
   `sources.py`/CLAUDE.md sugere — é 1:N (12 execuções por convênio em média). Não é bug, mas a
   documentação do código induz a um entendimento de grão errado; sinalizo para correção da
   documentação, não do código.
8. **Diferença de 1 linha entre pontes do mesmo lote** (`dcgce_codigo_dec_contrap` com 5.352 linhas vs.
   `dcgce_convenio`/`dcgce_geral`/`dcgce_codigo_convenio` com 5.353) — não investigado qual convênio
   falta nessa ponte especificamente.
9. **Sentinelas textuais não cobertos por `SENTINELAS = {"N/A", "-3", ""}`** em `core/transform/utils.py`:
   observei pelo menos `"null"` (string literal) em `dcgce_geral.Convênio Matrícula Gestor` e
   `dcgce_plano_trabalho.Plano Trabalho Justificativa`, e `"?"` em `chaves_convenio.SICONV..`. Não
   verifiquei o impacto real desses valores chegando ao banco como texto "null"/"?" em vez de nulo —
   sinalizo como possível problema de qualidade de dados a confirmar com o time de produto.
10. **`controle_sei` colunas excluídas por `usecols=range(27)`** (posições 29-31, documentadas em
    `sources.py` como duplicadas) não foram inspecionadas — não consegui confirmar se são de fato
    idênticas às equivalentes dentro do intervalo lido, por não ter lido essas colunas no script.
11. **Taxa de órfãos de 12,1% entre `chaves_convenio` e `dcgce_convenio`** (§3): não investiguei se são
    convênios cancelados/expurgados de `dcgce_convenio` mas ainda presentes na ponte, ou se é uma
    defasagem normal entre exports tirados em momentos diferentes.
