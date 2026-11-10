# Relatório final — refatoração da ingestão legada (SIGCON e apoio)

Branch `refactor/ingestao-legado`. Resultado das Fases 0–6: as 21 tabelas
da especificação ("Modelo de Extração das Bases Legadas v1.0") saindo da
camada Silver com o mesmo motor declarativo do GRP, nomes/tipos
normalizados pela seção 9 do prompt, e a Silver do GRP bit a bit idêntica
à linha de base do início do trabalho.

## 1. Resumo do que mudou

- **Motor único.** `core/transform/silver.py` ganhou 9 capacidades novas
  (generalização de `anular:` → `sentinelas:` por coluna, `booleanos:` por
  coluna, `descartar:`, `descartar_linhas_se_nulo:`, `grao:` com ALERTA,
  `derivadas:` com registro de função, `desdobrar:`, `quarentena:`, e o
  `dropna(how="all")` desacoplado de ter ou não `renomear:`) — as mesmas
  usadas pelo GRP, sem segundo motor. Duas capacidades foram corrigidas
  depois de rodar contra dado real (Fase 4): `colunas.data_hora` (não
  existia; `data` agora trunca a hora) e `descartar_linhas_se_nulo` passou
  a rodar nos nomes BRUTOS, antes da tipagem (não depois do `renomear:`
  como na primeira versão) — um bloco desalinhado do relatório do BO em
  `sigcon_cronograma_desembolso` só para de quebrar a tipagem com essa
  ordem.
- **20 fontes renomeadas** em `core/ingestion/sources.py` (ver tabela da
  seção 3) + `core/ingestion/ponte_extracao.py` (mapa Gmail→fonte) +
  `core/pipeline.py::FONTES_SILVER`/`FONTES_SILVER_GRP` (só a lista
  bronze/silver, como o escopo pede).
- **20 YAMLs reescritos** com `git mv` (preserva histórico) em
  `core/transform/schemas/`, um por tabela, cobrindo `sentinelas`,
  `booleanos`, `derivadas`, `descartar`, `descartar_linhas_se_nulo`,
  `grao`, e (só nas tabelas 16 e 20) `quarentena`/`desdobrar`.
- **Limpeza GRP** (autorizada fora do escopo original, a pedido): 8 fontes
  GRP "antigas" (pré-`grp_*`) removidas de ponta a ponta — 7 models, 7
  loaders, 5 funções de `services.py`, import morto que quebrava a
  coleta de 3 módulos de teste, comando `carregar_grp` e seu teste
  reescrito contra as fontes reais.
- **Limpeza da ingestão legada** (Fase 5): 5 YAMLs órfãos e 2 módulos
  Python mortos excluídos (ver seção 2).
- **Validação com dado real** (Fase 6): `docs/validacao_ingestao_legado.md`
  — volumes batendo com a especificação em 17/20 tabelas, V1–V16
  executados, 7 divergências registradas (nenhuma corrigida inventando
  regra nova).
- **Dicionário de dados gerado** (Fase 7, não escrito à mão):
  `docs/dicionario_dados_legado.md`, a partir dos 20 YAMLs + o bloco
  `desdobrar:` de `controle_sei.yaml` (tabela 21).

## 2. Tudo o que foi excluído (arquivo/função + evidência)

**Fase 5 — ingestão legada:**
| Item | Evidência de não-uso |
|---|---|
| `core/transform/schemas/dcgce_chave.yaml` | Nenhuma `FonteDados` (ativa ou comentada) aponta para ela; nenhum teste a referencia |
| `core/transform/schemas/dcgce_convenios.yaml` | idem |
| `core/transform/schemas/dcgce_plano.trabalho.yaml` | idem — nome com ponto, órfão; a chave real tem YAML próprio sem ponto |
| `core/transform/schemas/dcgce_termo.aditivo.yaml` | idem |
| `core/transform/schemas/dcgce_unidades.executoras.yaml` | idem |
| `core/transform/convenios.py` | `NOME_FONTE="dcgce_convenios"` não existe em `FONTES`; único "uso" era `apps/sigcon/management/commands/rodar_transformacao.py` (comando já legado, "do not use" no CLAUDE.md) |
| `core/transform/mapa_grp_instrumento.py` | Duplicava 1:1 o `renomear:` de `grp_instrumento.yaml`; nenhum chamador no repo |

Efeito colateral documentado (não corrigido, `apps/` fora de escopo):
`rodar_transformacao convenios` agora falha com `ImportError` em vez de
erro em tempo de execução — já era inutilizável antes (fonte `"convenios"`
não existe em `FONTES` desde a Fase 3), só muda onde quebra.

**GRP "antigo" (autorizado fora do escopo original, a pedido explícito):**
7 models (`DadosGrp`, `RecursosContrapartidaGrp`, `RecursosConcedenteGrp`,
`PlanoAplicacaoGrp`, `PlanoAplicacaoGrpDetalhes`,
`CronogramaDesembolsoGrp`, `TabelaUoGrp`) + 7 loaders +
5 funções de `apps/grp/services.py` + 8 YAMLs comentados/órfãos em
`sources.py` + import morto em `apps/sigcon/loader.py` (que quebrava a
coleta de 3 módulos de teste). `apps/grp/views/_filtros.py` migrado para
`GrpTabelaUo`/`GrpInstrumento` (a pedido, após confirmação via pergunta).

## 3. Mapa de chaves (nome novo ← nome antigo)

| # | Chave nova | Chave antiga |
|---|---|---|
| 01 | `sigcon_convenio` | `dcgce_convenio` |
| 02 | `sigcon_convenio_geral` | `dcgce_geral` |
| 03 | `sigcon_plano_trabalho` | `dcgce_plano_trabalho` |
| 04 | `sigcon_termo_aditivo` | `dcgce_termo_aditivo` |
| 05 | `sigcon_prorrogacao_oficio` | `dcgce_prorrogacao_oficio` |
| 06 | `sigcon_declaracao_contrapartida` | `dcgce_declaracao_contrapartida` |
| 07 | `sigcon_cronograma_desembolso` | `dcgce_cronograma_desembolso` |
| 08 | `sigcon_plano_aplicacao` | `dcgce_plano_aplicacao` |
| 09 | `sigcon_unidade_executora` | `dcgce_unidades_executoras` |
| 10 | `sigcon_nt_emenda` | `dcgce_sigcon_nt_emenda` |
| 11 | `sigcon_chave_convenio` | `dcgce_codigo_convenio` |
| 12 | `sigcon_chave_termo_aditivo` | `dcgce_codigo_ta` |
| 13 | `sigcon_chave_plano_trabalho` | `dcgce_Codigo_plano_de_trabalho` |
| 14 | `sigcon_chave_declaracao` | `dcgce_codigo_dec_contrap` |
| 15 | `sigcon_chave_siconv` | `chaves_convenio` |
| 16 | `depara_siafi` | `siafi2` |
| 17 | `sigcon_concedente` | `dcgce_esfera` |
| 18 | `depara_parlamentar` | `parlamentares` |
| 19 | `siconv_convenio` | `siconv_convenio` (sem mudança) |
| 20 | `controle_sei` | `controle_sei` (sem mudança) |
| 21 | `controle_sei_documento` | _(nova — derivada de `controle_sei` via `desdobrar:`)_ |

Nomes de coluna: ver `docs/dicionario_dados_legado.md` (tabela completa
bruto→final por fonte, gerada dos YAMLs).

> **ATUALIZAÇÃO (Fase 8, 2026-11-10):** o mapa de impacto abaixo foi **executado**: loaders, `carregar_fonte`, `CARGAS_ORM`, Gold e CLI leem a Silver nova (ver `docs/validacao_models_sigcon.md`). Duas afirmações desta seção estavam erradas: (1) os models **não** usavam os nomes novos — usam os nomes históricos, e cada loader faz o de-para; (2) os `carregar_*` **não** falhavam todos com `FileNotFoundError`: como os Parquets antigos ainda existiam, vários carregavam dado velho sem erro. Os dados antigos de `data/bronze|silver` foram removidos.

## 4. Mapa de impacto para a próxima fase (histórico — já executado)

A renomeação de fontes e colunas quebra tudo que lê Silver pelos nomes
antigos. Agrupado por arquivo — cada um precisa ser adaptado para ler as
20 chaves novas (seção 3) e as colunas finais do dicionário de dados.

### `apps/sigcon/loader.py`
Ponto de maior impacto — 18 chamadas a `_silver_path("dcgce_...")` (ou
`"chaves_convenio"`/`"siafi2"`), cada uma lendo um arquivo que **não é
mais gerado** por `rodar_silver` (a Silver agora só existe sob a chave
nova). Também lê colunas pelo nome **bruto antigo** (ex.: `convenio_codigo`,
`unidade_orcamentaria_codigo`), que os YAMLs novos renomeiam para o
padrão `nr_/cd_/...` — então mesmo apontando para o arquivo certo, os
`df["coluna_antiga"]` quebrariam.
| Linha | Usado hoje | Passa a ser |
|---|---|---|
| 144 | `_silver_path("dcgce_convenio")` | `_silver_path("sigcon_convenio")` |
| 145 | `_silver_path("dcgce_codigo_convenio")` | `_silver_path("sigcon_chave_convenio")` |
| 146, 277, 345, 424 | `_silver_path("dcgce_geral")` | `_silver_path("sigcon_convenio_geral")` |
| 147, 373, 375 | `_silver_path("dcgce_plano_trabalho")`/`dcgce_plano.trabalho` | `_silver_path("sigcon_plano_trabalho")` |
| 148, 581 | `_silver_path("dcgce_esfera")` | `_silver_path("sigcon_concedente")` |
| 276 | `_silver_path("dcgce_cronograma_desembolso")` | `_silver_path("sigcon_cronograma_desembolso")` |
| 422 | `_silver_path("dcgce_plano_aplicacao")` | `_silver_path("sigcon_plano_aplicacao")` |
| 488, 490 | `_silver_path("dcgce_termo_aditivo")`/`dcgce_termo.aditivo` | `_silver_path("sigcon_termo_aditivo")` |
| 517 | `_silver_path("dcgce_declaracao_contrapartida")` | `_silver_path("sigcon_declaracao_contrapartida")` |
| 543 | `_silver_path("dcgce_prorrogacao_oficio")` | `_silver_path("sigcon_prorrogacao_oficio")` |
| 563 | `_silver_path("dcgce_sigcon_nt_emenda")` | `_silver_path("sigcon_nt_emenda")` |
| 596, 598 | `_silver_path("dcgce_codigo_convenio")`/`dcgce_Codigo_convenio` | `_silver_path("sigcon_chave_convenio")` |
| 615 | `_silver_path("dcgce_Codigo_plano_de_trabalho")` | `_silver_path("sigcon_chave_plano_trabalho")` |
| 631, 633 | `_silver_path("dcgce_codigo_ta")`/`dcgce_Codigo_ta` | `_silver_path("sigcon_chave_termo_aditivo")` |
| 650, 652 | `_silver_path("dcgce_codigo_dec_contrap")`/`dcgce_Codigo_dec_contrap` | `_silver_path("sigcon_chave_declaracao")` |
| 717 | `_silver_path("chaves_convenio")` | `_silver_path("sigcon_chave_siconv")` |
| 718 | `_silver_path("siafi2")` | `_silver_path("depara_siafi")` |

### `apps/sigcon/management/commands/carregar_fonte.py`
`_LOADERS` (linhas 27–40) é um dict chave→função usando os 13 nomes
antigos como argumento de CLI (`dcgce_geral`, `dcgce_plano.trabalho`,
etc.). Precisa trocar as 13 chaves para as novas (sigcon_convenio_geral,
sigcon_plano_trabalho, …) — e os `help`/docstrings (linhas 12–14) também
citam os nomes antigos.

### `core/pipeline.py`
`CARGAS_ORM` (linhas 61–78): as 13 chamadas `("carregar_fonte",
["dcgce_..."], {})` precisam das chaves novas — hoje `rodar_pipeline`
roda a Silver certa (seção bronze/silver já renomeada nesta refatoração)
mas falha na etapa seguinte porque `carregar_fonte` procura o arquivo
Silver pelo nome antigo, que não existe mais. Comentário já deixado no
código (linhas 31-35) apontando para este relatório.

### `apps/sigcon/management/commands/carregar_relacionamento.py`
Docstring (linhas 11-17) cita `chaves_convenio`, `siafi2`,
`dcgce_convenio`, `dcgce_codigo_convenio`, `dcgce_geral`,
`dcgce_plano_trabalho`, `dcgce_esfera` como pré-requisito via
`rodar_silver` — atualizar para os 7 nomes novos correspondentes (seção
3). A leitura de fato acontece em `apps/sigcon/loader.py` (ver acima).

### `apps/sigcon/management/commands/carregar_convenios.py` e `carregar_unidades_executoras.py`
Docstrings/help (linhas 4-17, 35-36, 47) citam `dcgce_convenio`,
`dcgce_geral`, `dcgce_plano_trabalho`, `dcgce_esfera`,
`dcgce_codigo_convenio`, `dcgce_unidade_executora` — só texto de ajuda,
atualizar para os nomes novos; a leitura real é via `apps/sigcon/loader.py`.

### `apps/sigcon/management/commands/carregar_cronograma.py`
Docstring (linhas 8-14) cita a cadeia `dcgce_cronograma_desembolso.
plano_trabalho_codigo → dcgce_geral.conveno_codigo_plano_trabalho →
convenio_codigo_sequencial → dcgce_codigo_convenio.
convenio_codigo_sequencial` — essa cadeia de nomes de coluna BRUTOS
também mudou (os YAMLs novos renomeiam para `cd_plano_trabalho`,
`cd_convenio_sequencial`). Atualizar texto e qualquer acesso a coluna por
esse nome bruto dentro do loader correspondente.

### `core/gold/relacionamento.py`
Só docstrings/comentários (linhas 140, 168, 189, 220, 791, 813-819, 830)
citando `dcgce_convenio`, `dcgce_geral`, `dcgce_plano_trabalho`,
`dcgce_esfera`, `dcgce_codigo_convenio`, `chaves_convenio`, `siafi2` como
nome das fontes Silver que os parâmetros `df_siafi2`, `df_chaves`, etc.
recebem. A função em si recebe DataFrames já carregados (não lê arquivo
diretamente) — quem monta esses DataFrames é `carregar_relacionamento`
(via `apps/sigcon/loader.py`), então o impacto real está lá; aqui é só
documentação a atualizar.

### `apps/pipeline/management/commands/rodar_silver.py` e `gerar_schemas.py`
Exemplos de uso no docstring (`rodar_silver dcgce_convenios`, etc.) —
só texto de ajuda desatualizado, sem efeito funcional (o comando em si
já lê de `FONTES`, que tem as chaves novas).

### Models (`apps/sigcon/models/`)
Os models mantêm os nomes de campo históricos (`convenio_codigo`, `unidade_orcamentaria_codigo`...), **não** os do dicionário novo; o acoplamento é via loader. Mudanças de schema da Fase 8: `CronogramaDesembolso.ds_alerta_linha`, `ConvenioIntegrado.fl_uo_excluida` e `siafi_uo` nulo (migrations 0013/0014 do app `convenios`).

## 5. Divergências pendentes

Ver detalhamento completo em `docs/validacao_ingestao_legado.md`, seção 4
(D1–D7). Resumo:
- **D1/D2** `depara_siafi`: volume de chaves repetidas e redundância das
  colunas "R" não batem com a referência original da especificação —
  base real mais "suja"/maior.
- **D3** 1 linha-sentinela sem regra em `sigcon_plano_aplicacao`.
- **D4** `ds_esfera` tem 5 valores, não 4 (`'Não Informado'`, 1 linha).
- **D5** string vazia residual em colunas de texto longo com
  `sentinelas:` customizado (achado de design, comportamento testado
  desde a Fase 2 — não alterado sem pedido explícito).
- **D6** 63 planos com soma divergente entre `sigcon_cronograma_desembolso`
  e `sigcon_plano_aplicacao`, padrão de fator ~100 em boa parte (cara de
  separador decimal trocado na origem).
- **D7** "4 linhas sem SIAFI" da especificação (tabela 01) são 8 na base
  real.
- **Gap de persistência** (não é divergência de dados): `rodar_silver`
  nunca grava `quarentena:`/`desdobrar:` em disco — só a tabela
  principal. Os artefatos da tabela 21 e da quarentena da 16 foram
  gerados por um script avulso para esta validação; estender o comando é
  mudança em `apps/`, fora do escopo desta tarefa.
- **GRP "antigo" pré-existente, não corrigido** (fora do escopo desta
  tarefa, distinto do GRP novo `grp_*`): 7 YAMLs GRP antigos continuam
  com `FonteDados` comentada em `sources.py`; `rodar_silver` não roda
  para eles hoje.

## 6. Definição de pronto

- [x] 21 tabelas geradas na silver, com os nomes e tipos da seção 9 do prompt
- [x] Silver do GRP idêntica à linha de base (22/22 hashes SHA-256)
- [x] Testes do motor e da ingestão passando; falhas restantes só em `apps/`/`core/gold/` (pré-existentes, listadas na seção 5)
- [x] Nenhum YAML, função ou módulo sem uso dentro do escopo (Fase 5)
- [x] `validacao_ingestao_legado.md`, `dicionario_dados_legado.md` e `relatorio_ingestao_legado.md` gerados
- [x] Commits por fase na branch `refactor/ingestao-legado`, sem push

## 7. Os 5 pontos mais importantes do mapa de impacto

1. **`apps/sigcon/loader.py`** precisa de 18 pontos de ajuste (nome do
   arquivo Silver + nome de coluna) antes de qualquer `carregar_*` voltar
   a funcionar — é o maior e mais crítico.
2. **`core/pipeline.py::CARGAS_ORM`** (13 chamadas `carregar_fonte`) e
   **`apps/sigcon/management/commands/carregar_fonte.py::_LOADERS`** (13
   chaves) precisam das chaves novas em conjunto — um sem o outro não
   resolve.
3. **`sigcon_chave_siconv`/`depara_siafi`** (ex-`chaves_convenio`/`siafi2`)
   alimentam `carregar_relacionamento` → Gold `ConvenioIntegrado`: sem
   ajustar essas duas, a carga Gold inteira para.
4. **D1/D2 (`depara_siafi`)** merecem decisão de produto antes de ligar
   o Gold de novo: a tabela tem muito mais duplicidade de chave do que a
   especificação original previa, e a coluna "R" não é mais redundante —
   quem for montar o de-para precisa saber disso.
5. **O gap de persistência de `rodar_silver`** (não grava
   `quarentena:`/`desdobrar:`) precisa ser resolvido antes de qualquer
   rotina automatizada depender da tabela 21 ou da quarentena da 16 em
   produção — hoje só existem porque foram geradas manualmente para esta
   validação.
