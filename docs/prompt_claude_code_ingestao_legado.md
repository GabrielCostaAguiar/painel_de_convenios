# Refatoração da ingestão das bases legadas (SIGCON e apoio) — Painel de Convênios

## 1. Papel e objetivo

Você é o engenheiro de dados responsável por refatorar a **camada de ingestão (bronze → silver)** das bases legadas do Painel de Convênios, aplicando o "Modelo de Extração das Bases Legadas v1.0" (o PDF está em `docs/modelo_extracao_bases_legadas.pdf`; a especificação completa e suficiente está na seção 9 deste prompt).

**Resultado esperado ao final:** as 21 tabelas da especificação saindo da silver com nomes normalizados, tipos corretos, sentinelas tratados e grão validado; `sources.py` e YAMLs reescritos; motor de transformação único (o mesmo do GRP, generalizado); todo o código e todos os schemas que não são mais usados removidos; e um relatório que mostre exatamente o que precisa mudar em models, loaders e gold na próxima fase.

O GRP já passou por esse processo e é a **referência de padrão**: siga o jeito que ele faz, reaproveite as funções dele e não crie um segundo motor.

## 2. Escopo

**Dentro do escopo (pode criar, alterar, mover e excluir):**
- `core/ingestion/` (inclui `sources.py` e `readers.py`)
- `core/transform/` (motor da silver, utilitários de normalização, `schemas/*.yaml`)
- Testes de ingestão e transformação (`tests/` relativos a esses módulos)
- `core/pipeline.py`: **apenas** a lista de fontes da etapa bronze/silver
- Documentação: `CLAUDE.md` e `docs/`
- Diretórios gerados `data/bronze/` e `data/silver/` das chaves antigas (só depois que as novas rodarem)

**Fora do escopo (NÃO alterar nada):**
- `apps/` inteiro (models, loaders, management commands, views, templates) — inclui `apps/sigcon/`
- `core/gold/` e qualquer view ou consulta da gold
- Migrations e o banco de dados
- `data/raw/` (arquivos brutos nunca são tocados)
- O comportamento do pipeline do GRP: as saídas silver do GRP têm de continuar **idênticas**

A renomeação vai quebrar loaders e a gold que leem os nomes antigos. **Isso é esperado.** Não conserte esses pontos: registre cada um no relatório de impacto (Fase 7).

## 3. Regras de trabalho

1. Trabalhe na branch `refactor/ingestao-legado`, criada a partir da branch atual com a árvore limpa. Commits pequenos, um por fase, com mensagens no padrão `refactor(ingestao): ...`. Não faça push.
2. **Antes de excluir qualquer coisa, prove que não é usada**: grep do nome em todo o repositório (incluindo `apps/`, `core/gold/`, testes, templates e strings). Se algo for usado por `apps/` ou `core/gold/`, **não exclua**: liste no relatório de impacto.
3. Use `git mv` ao renomear YAMLs e módulos, para preservar o histórico.
4. Nada de lógica específica por fonte em Python quando um bloco declarativo no YAML resolve. Se precisar de uma capacidade nova, implemente-a **genericamente no motor** e declare no YAML.
5. Não instale dependências novas sem me perguntar.
6. Se a realidade contradisser a especificação (um nome atual que não bate, um volume muito diferente do esperado, um grão que não fecha), **pare a parte afetada, registre como DIVERGÊNCIA** no relatório e siga com o resto. Não invente nome nem regra.
7. Fale comigo em português. Dados pessoais (matrículas, nomes) nunca aparecem em logs ou relatórios.

## 4. Fase 0 — Linha de base

1. Crie a branch e confirme a árvore limpa.
2. Rode a silver do GRP e salve um **hash por arquivo parquet** gerado (conteúdo, não data de modificação) em `docs/_baseline_grp_silver.json`. Esse é o teste de regressão do GRP.
3. Rode a suíte de testes e registre o resultado (quantos passam e quais falham) como linha de base.

## 5. Fase 1 — Reconhecimento e plano (somente leitura) · CHECKPOINT

1. **Mapeie o motor do GRP:** leitura (`readers.py`), normalização de cabeçalho (`normalizar_coluna` ou equivalente), carregamento do YAML, `renomear:`, tipagem, sentinelas, descarte de linhas vazias, verificação de grão, log de ALERTA e escrita do parquet. Anote o que é genérico e o que está fixo para o GRP.
2. **Confira os nomes atuais:** leia só o cabeçalho de cada arquivo bruto das 20 fontes, aplique a normalização real do projeto e compare com a coluna "nome atual" da seção 9. Todos precisam bater (no `siconv_convenio`, depois de ler com `utf-8-sig`).
3. **Classifique todos os YAMLs** de `core/transform/schemas/` em: (a) usado pelo GRP — mantém; (b) fonte legada — vira um dos 21 da especificação; (c) sem uso — será excluído.
4. **Classifique as funções** de `core/ingestion/` e `core/transform/` em: motor genérico (mantém/generaliza); específica de fonte legada substituível pelo YAML (será excluída); usada por `apps/` ou `core/gold/` (intocável, vai para o relatório de impacto); sem uso (será excluída).
5. Escreva `docs/plano_refatoracao_ingestao.md` com: as divergências do passo 2, as capacidades que faltam no motor (veja a Fase 2), as listas de exclusão (arquivo/função + evidência de que não é usada) e a lista de intocáveis.

**CHECKPOINT: pare aqui, mostre no chat um resumo do plano (divergências, capacidades novas, o que será excluído) e espere meu "ok" antes de alterar qualquer arquivo de código, schema ou configuração.**

## 6. Fase 2 — Motor genérico

Generalize o motor da silver usado pelo GRP para suportar, **de forma declarativa no YAML**, tudo o que as 21 tabelas precisam. Implemente só o que faltar:

| Bloco/regra no YAML | Comportamento |
|---|---|
| `renomear:` | já existe no GRP (nome normalizado → nome final) |
| `descartar:` | remove colunas depois de renomear (marca D) |
| `tipos:` | `identificador`/`texto`/`texto_longo` (string, preserva zeros à esquerda), `inteiro` (Int64), `valor` (decimal, ver abaixo), `data`, `data_hora`, `booleano` |
| `sentinelas:` | por coluna: lista de valores que viram nulo. Substitui o conjunto global `SENTINELAS`; se o GRP depende dele, o GRP passa a declarar os seus no próprio YAML (sem mudar a saída) |
| `booleanos:` | por coluna: mapa valor → True/False; valor fora do mapa vira nulo e gera ALERTA |
| `derivadas:` | colunas calculadas por função registrada; nesta fase só `montar_siafi_uo(nr_siafi, cd_uo)` |
| `descartar_linhas_se_nulo:` | lista de colunas; linhas com nulo nelas saem, com contagem no log |
| `grao:` | lista de colunas; ao final, testar unicidade e registrar exceções em ALERTA, sem interromper a carga |
| `desdobrar:` | gera uma segunda saída em formato longo a partir de colunas da mesma fonte (para a tabela 21) |
| `quarentena:` | regra que separa linhas para `quarentena.parquet` no diretório silver da fonte (para a tabela 16) |

Regras gerais que valem para todas as fontes (aplique na ordem): descartar `Unnamed:*` → descartar linhas 100% vazias → descartar linhas que repetem o cabeçalho → trim em todo texto (string vazia vira nulo) → renomear → **desdobrar** (gera a saída longa a partir das colunas ainda presentes; a saída longa passa pelas mesmas regras de tipo e descarta células vazias) → descartar colunas → sentinelas → tipos → booleanos → derivadas → descartar linhas → remover linhas 100% idênticas (com log) → quarentena → verificar grão.

**Valores:** o conversor precisa aceitar `179371.54`, `448745,57`, `1.234.567,89` e números já numéricos do Excel, decidindo por valor, sem perder casas e sem multiplicar por 100. Escreva testes unitários para esses casos.

**Datas:** datetime vindo do Excel passa direto; texto `dd/mm/aaaa` com `dayfirst=True`; `data` guarda só a data, `data_hora` mantém a hora.

Ao terminar a fase: testes unitários do motor passando e **regressão do GRP sem diferença** contra a linha de base.

## 7. Fases 3 a 5 — Fontes, schemas e limpeza

**Fase 3 — `sources.py`:**
- Renomeie as chaves conforme a tabela da seção 9. Caminhos dos arquivos brutos e parâmetros de leitura continuam os mesmos, exceto o encoding do `siconv_convenio`, que passa a `utf-8-sig`.
- Remova `qv_despesa_ano_2019` e `qv_despesa_ano_2020`.
- Atualize os comentários: `sigcon_unidade_executora` é 1:N (≈12 unidades por convênio); "Código Convênio" da prorrogação é o código sequencial; `chaves_convenio` → `sigcon_chave_siconv`.
- Remova aliases e mapeamentos de chaves antigas que existam dentro do escopo.

**Fase 4 — YAMLs:**
- Um YAML por tabela, com **o mesmo nome da chave** (`sigcon_convenio.yaml` etc.). Use `git mv` quando já existir um YAML da fonte.
- Cada YAML contém: `fonte`, `descricao`, `grao`, `renomear`, `descartar`, `tipos`, `sentinelas`, `booleanos`, `derivadas` e as regras específicas da seção 9. Comente as linhas não óbvias.
- As colunas marcadas **R** (redundantes) **permanecem** nesta fase; a decisão sai do relatório de validação.
- Colunas LGPD (matrículas) permanecem, com comentário `# LGPD` no YAML.

**Fase 5 — Limpeza completa (dentro do escopo):**
- Exclua os YAMLs classificados como "sem uso" na Fase 1 e os YAMLs antigos que não viraram nenhum dos 21.
- Exclua funções, módulos, constantes e helpers específicos das fontes legadas que o motor declarativo substituiu, e qualquer código morto encontrado (imports sem uso, funções sem chamador, constantes órfãs como o `SENTINELAS` global, se não for mais usado).
- Exclua ou reescreva os testes que cobriam código removido; os testes novos ficam no lugar.
- Depois que a silver nova rodar (Fase 6), apague `data/bronze/` e `data/silver/` das chaves antigas.
- **Nunca exclua** o que é usado por `apps/` ou `core/gold/`, nem nada do GRP que continue em uso.

## 8. Fases 6 e 7 — Execução, validação e relatório

**Fase 6 — Rodar e validar:**
Rode bronze e silver das 21 tabelas e gere `docs/validacao_ingestao_legado.md` com, para cada tabela: linhas no bronze, linhas na silver, linhas descartadas por regra, resultado do grão e ALERTAS. Inclua os testes abaixo, com números e uma conclusão de uma linha cada:

- **V1** `COUNT(*)` vs `COUNT(DISTINCT grão)` em todas as tabelas.
- **V2** `cd_uo` com 4 caracteres em todas as fontes (senão a concatenação do `siafi_uo` pode colidir).
- **V4** para o mesmo `siafi_uo`, `nr_convenio` da 09 igual ao da 01.
- **V5** `cd_plano_trabalho` da 13 igual ao obtido por 02 + 11; `cd_declaracao_contrapartida` da 14 igual ao de 02 + 11 (por `siafi_uo`).
- **V6** quantos `nr_siafi` da 20 casam com mais de um `siafi_uo` da 01.
- **V7** na 16, `nr_siafi_1 = nr_siafi_origem` e `cd_uo_1 = cd_uo_origem` em todas as linhas?
- **V8** órfãos de 15 em 01 depois de resolver `siafi_uo` antigo pela 16; `nr_convenio_siconv` repetido depois disso.
- **V9** cronograma: 29.992 linhas, grão único, mês entre 1 e 12.
- **V10** declaração: data de `dh_emissao` = `dt_emissao` e data de `dh_parecer_aprovacao` = `dt_parecer_aprovacao`.
- **V12** siconv: sem BOM, acentos corretos, DIA/MES/ANO iguais às partes de `dt_assinatura`.
- **V13** soma de `vl_desembolso_concedente` vs `vl_aplicacao_concedente` por plano (resumo das diferenças).
- **V14** nenhuma coluna de texto da silver com 'null', 'NULL', '?', '-' ou ' '.
- **V15** `ds_esfera` com 4 valores distintos.
- **V16** grão do plano de aplicação com `nr_ano_exercicio`.

Confirme de novo a **regressão do GRP** contra a linha de base.

**Fase 7 — Documentação e relatório final:**
1. `docs/dicionario_dados_legado.md`, gerado a partir dos YAMLs (não escrito à mão): por tabela, grão, colunas, tipo, descrição, sentinelas.
2. `docs/relatorio_ingestao_legado.md` com:
   - resumo do que mudou e lista de tudo o que foi excluído (arquivo/função + evidência);
   - **mapa de impacto para a próxima fase**: cada ponto de `apps/` e `core/gold/` que usa uma chave de fonte ou um nome de coluna antigo — `arquivo:linha`, o que é usado hoje, o que passa a ser (chave nova / nome novo). Agrupe por arquivo. É o guia para adaptar models, loaders e a carga no banco;
   - divergências encontradas e o que ficou pendente.
3. Atualize o `CLAUDE.md`: novas chaves de fonte, contrato do YAML, regras do motor e a correção da estrutura real dos apps (loaders SIGCON em `apps/sigcon/`).

**Definição de pronto:**
- [ ] 21 tabelas geradas na silver, com os nomes e tipos da seção 9
- [ ] Silver do GRP idêntica à linha de base
- [ ] Testes do motor e da ingestão passando; falhas restantes só em `apps/`/`core/gold/`, listadas no relatório
- [ ] Nenhum YAML, função ou módulo sem uso dentro do escopo
- [ ] `validacao_ingestao_legado.md`, `dicionario_dados_legado.md` e `relatorio_ingestao_legado.md` gerados
- [ ] Commits por fase na branch `refactor/ingestao-legado`

Ao final, mostre no chat: a lista de verificação acima marcada, as divergências e os 5 pontos mais importantes do mapa de impacto.

## 9. Especificação das 21 tabelas

**Mapa de chaves de fonte (`sources.py`):**

| # | Chave nova | Chave atual |
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
| 19 | `siconv_convenio` | `siconv_convenio` |
| 20 | `controle_sei` | `controle_sei` |
| 21 | `controle_sei_documento` | `(nova, derivada de controle_sei)` |

**Convenções:** `nr_` número, `cd_` código, `nm_` nome, `ds_` descrição, `tp_` tipo, `dt_` data, `dh_` data-hora, `vl_` valor, `qt_` quantidade, `fl_` flag, `tx_` texto longo. `siafi_uo` é a única exceção (chave derivada). Marcas: PK chave, G parte do grão, FK ligação, LGPD dado pessoal, R redundante (mantém nesta fase).

A coluna "nome atual" é o nome que a normalização do projeto gera a partir do cabeçalho bruto (lado esquerdo do `renomear:`). Colunas `Unnamed: 0` não aparecem: a regra geral as descarta.

### 01 · `sigcon_convenio`  ← `dcgce_convenio`
- **Arquivo:** sigcon/dcgce_convenio.xlsx (Excel, header=1) · **Linhas:** 5.353 · **Prioridade:** Must
- **Grão:** 1 linha por convênio (siafi_uo)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `convenio_codigo` | `nr_convenio` | identificador |  |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | G |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador | G |
| `situacao` | `ds_situacao_convenio` | texto |  |
| `data_inicio_vigencia` | `dt_vigencia_inicio` | data |  |
| `data_termino_vigencia` | `dt_vigencia_termino_inicial` | data |  |
| `data_real_convenio` | `dt_vigencia_termino` | data |  |
| `valor_inicial_concedente_contratado` | `vl_convenio_concedente_inicial` | valor |  |
| `valor_total_aditado_concedente_contratado` | `vl_convenio_concedente_aditado` | valor |  |
| `valor_concedente` | `vl_convenio_concedente` | valor |  |
| `valor_inicial_proponente_contratado` | `vl_convenio_proponente_inicial` | valor |  |
| `valor_total_aditado_proponente_contratado` | `vl_convenio_proponente_aditado` | valor |  |
| `valor_proponente` | `vl_convenio_proponente` | valor |  |
| `valor_total_convenio` | `vl_convenio_total` | valor |  |

- **derivadas:** `siafi_uo` = nr_siafi || cd_uo (usar `montar_siafi_uo`)
- **sentinelas → nulo:** `nr_convenio`: ['-', '00', '000']; `nr_siafi`: ['0']
- Grão `siafi_uo`: 4 linhas sem SIAFI ficam com `siafi_uo` nulo → registrar em ALERTA, não descartar.

### 02 · `sigcon_convenio_geral`  ← `dcgce_geral`
- **Arquivo:** sigcon/dcgce_Geral.xlsx (Excel, header=1) · **Linhas:** 5.353 · **Prioridade:** Must
- **Grão:** 1 linha por convênio (cd_convenio_sequencial)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `convenio_codigo` | `nr_convenio` | identificador | R |
| `convenio_codigo_sequencial` | `cd_convenio_sequencial` | identificador | PK |
| `convenio_codigo_declaracao` | `cd_declaracao_contrapartida` | identificador | FK |
| `convenio_data_de_publicacao` | `dt_publicacao` | data |  |
| `convenio_ano` | `nr_ano_convenio` | inteiro |  |
| `convenio_alteracao` | `fl_permite_alteracao` | booleano |  |
| `conveno_codigo_plano_trabalho` | `cd_plano_trabalho` | identificador | FK |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | R |
| `convenio_matricula_tecnico_sccg` | `cd_matricula_tecnico_sccg` | identificador | LGPD |
| `convenio_data_alteracao_sccg` | `dh_alteracao_sccg` | data_hora |  |
| `convenio_justificativa_da_alteracao` | `tx_justificativa_alteracao` | texto_longo |  |
| `convenio_data_controle_sccg_convenio` | `dt_controle_sccg` | data |  |
| `convenio_data_assinatura_convenio` | `dt_assinatura` | data |  |
| `convenio_matricula_gestor` | `cd_matricula_gestor` | identificador | LGPD |
| `convenio_data_de_cadastramento` | `dh_cadastramento` | data_hora |  |

- **sentinelas → nulo:** `nr_convenio`: ['-', '00', '000']; `nr_siafi`: ['0']; `cd_plano_trabalho`: ['0']; `cd_declaracao_contrapartida`: ['0']; `cd_matricula_gestor`: ['null']
- **mapa de booleanos:** `fl_permite_alteracao`: {'Pode sofrer alteração': True, 'Não pode sofrer alteração': False}

### 03 · `sigcon_plano_trabalho`  ← `dcgce_plano_trabalho`
- **Arquivo:** sigcon/dcgce_plano.trabalho.xlsx (Excel, header=1) · **Linhas:** 18.291 · **Prioridade:** Must
- **Grão:** 1 linha por plano de trabalho (cd_plano_trabalho)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador | PK |
| `plano_trabalho_titulo` | `nm_plano_trabalho` | texto |  |
| `plano_trabalho_objeto` | `tx_objeto` | texto_longo |  |
| `plano_trabalho_justificativa` | `tx_justificativa` | texto_longo |  |
| `plano_trabalho_codigo_execucao_no_exercicio` | `cd_execucao_exercicio` | identificador |  |
| `plano_trabalho_status` | `ds_status_plano_trabalho` | texto |  |
| `plano_trabalho_caracteristica` | `ds_caracteristica_contrapartida` | texto |  |
| `plano_trabalho_tipo` | `tp_plano_trabalho` | texto |  |
| `plano_trabalho_tipo_siafi` | `tp_instrumento_siafi` | texto |  |
| `plano_trabalho_migrado_ou_novo` | `ds_origem_cadastro` | texto |  |
| `plano_trabalho_matricula_sccg_cancelamento` | `cd_matricula_cancelamento_sccg` | identificador | LGPD |
| `plano_trabalho_data_cancelamento_sccg` | `dh_cancelamento_sccg` | data_hora |  |
| `plano_trabalho_justificativa_sccg_cancelamento` | `tx_justificativa_cancelamento` | texto_longo |  |
| `plano_trabalho_cancelamento_sccg` | `ds_cancelamento_sccg` | texto |  |
| `plano_trabalho_data_cadastro` | `dh_cadastro` | data_hora |  |
| `plano_trabalho_ano` | `nr_ano_plano_trabalho` | inteiro |  |
| `plano_trabalho_data_envio_sccg` | `dh_envio_sccg` | data_hora |  |
| `plano_trabalho_altera_termo_aditivo` | `ds_alteracao_termo_aditivo` | texto |  |
| `plano_trabalho_cnpj_concedente` | `nr_cnpj_concedente` | identificador | FK |
| `plano_trabalho_razao_social_concedente` | `nm_concedente` | texto |  |
| `plano_trabalho_cnpj_proponente` | `nr_cnpj_proponente` | identificador |  |

- **sentinelas → nulo:** `tx_objeto`: ['null']; `tx_justificativa`: ['null']; `nr_cnpj_concedente`: ['0']; `nr_cnpj_proponente`: ['0']
- `tp_instrumento_siafi` mistura códigos e textos ('11', 'Convênio de Entrada', 'Portaria'): manter como veio, sem padronizar.

### 04 · `sigcon_termo_aditivo`  ← `dcgce_termo_aditivo`
- **Arquivo:** sigcon/dcgce_termo.aditivo.xlsx (Excel, header=1) · **Linhas:** 7.113 · **Prioridade:** Must
- **Grão:** 1 linha por termo aditivo (cd_termo_aditivo)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `termo_aditivo_codigo_sequencial` | `cd_termo_aditivo` | identificador | PK |
| `termo_aditivo_numero_termo_aditivo` | `nr_termo_aditivo` | identificador |  |
| `termo_aditivo_ano` | `nr_ano_termo_aditivo` | inteiro |  |
| `termo_aditivo_data_assinatura` | `dt_assinatura` | data |  |
| `termo_aditivo_data_inicio_vigencia` | `dt_vigencia_inicio` | data |  |
| `termo_aditivo_data_termino_vigencia` | `dt_vigencia_termino` | data |  |
| `termo_aditivo_justificativa` | `tx_justificativa` | texto_longo |  |
| `tipo_termo_aditivo` | `tp_termo_aditivo` | texto |  |
| `data_termo_aditivo` | `dh_registro` | data_hora |  |
| `valor_aditado_concedente_contratado` | `vl_aditivo_concedente` | valor |  |
| `valor_aditado_proponente_contratado` | `vl_aditivo_proponente` | valor |  |

- **descartar:** `termo_aditivo_alteracao`, `termo_aditivo_tipo`, `quantidade_termo_aditivo`
- **sentinelas → nulo:** `tx_justificativa`: ['null']

### 05 · `sigcon_prorrogacao_oficio`  ← `dcgce_prorrogacao_oficio`
- **Arquivo:** sigcon/dcgce_prorrogacao_oficio.xlsx (Excel, header=1) · **Linhas:** 660 · **Prioridade:** Should
- **Grão:** 1 linha por prorrogação (cd_prorrogacao_oficio)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `prorrogacao_oficio_codigo` | `cd_prorrogacao_oficio` | identificador | PK |
| `prorrogacao_oficio_codigo_convenio` | `cd_convenio_sequencial` | identificador | FK |
| `prorrogacao_oficio_data_inicio_vigencia` | `dt_vigencia_inicio` | data |  |
| `prorrogacao_oficio_data_termino_vigencia` | `dt_vigencia_termino` | data |  |
| `prorrogacao_oficio_data_envio` | `dt_envio` | data |  |
| `prorrogacao_oficio_data_parecer` | `dt_parecer` | data |  |
| `prorrogacao_oficio_data_publicacao` | `dt_publicacao` | data |  |

- `cd_convenio_sequencial` é o código sequencial do convênio (não o número legível).

### 06 · `sigcon_declaracao_contrapartida`  ← `dcgce_declaracao_contrapartida`
- **Arquivo:** sigcon/dcgce_declaracao_contrapartida.xlsx (Excel, header=1) · **Linhas:** 3.957 · **Prioridade:** Should
- **Grão:** 1 linha por declaração (cd_declaracao_contrapartida)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `declaracao_contrapartida_codigo` | `cd_declaracao_contrapartida` | identificador | PK |
| `declaracao_contrapartida_data_completa_emissao` | `dh_emissao` | data_hora |  |
| `declaracao_contrapartida_data_emissao` | `dt_emissao` | data | R |
| `declaracao_contrapartida_ano` | `nr_ano_declaracao` | inteiro |  |
| `declaracao_contrapartida_status` | `ds_status_declaracao` | texto |  |
| `declaracao_contrapartida_codigo_nota_tecnica` | `cd_nota_tecnica` | identificador |  |
| `declaracao_contrapartida_observacao` | `tx_observacao` | texto_longo |  |
| `declaracao_contrapartida_codigo_parecer_aprovacao` | `ds_parecer_aprovacao` | texto |  |
| `declaracao_contrapartida_data_completa_parecer_aprovacao` | `dh_parecer_aprovacao` | data_hora |  |
| `declaracao_contrapartida_data_parecer_aprovacao` | `dt_parecer_aprovacao` | data | R |
| `declaracao_contrapartida_observacao_aprovacao` | `tx_observacao_aprovacao` | texto_longo |  |
| `declaracao_contrapartida_matricula_aprovacao` | `cd_matricula_aprovacao` | identificador | LGPD |
| `declaracao_contrapartida_momento` | `ds_momento` | texto |  |

- **sentinelas → nulo:** `tx_observacao`: ['null', 'NULL']

### 07 · `sigcon_cronograma_desembolso`  ← `dcgce_cronograma_desembolso`
- **Arquivo:** sigcon/dcgce_Cronograma_desembolso.xlsx (Excel, header=1) · **Linhas:** 48.394 (29.992 válidas) · **Prioridade:** Must
- **Grão:** plano de trabalho x ano x mês

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `mes_cronograma_desembolso` | `nr_mes_desembolso` | inteiro | G |
| `ano_cronograma_desembolso` | `nr_ano_desembolso` | inteiro | G |
| `valor_concedente_cronograma_desembolso` | `vl_desembolso_concedente` | valor |  |
| `valor_proponente_cronograma_desembolso` | `vl_desembolso_proponente` | valor |  |
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador | G / FK |

- Descartar linhas com `cd_plano_trabalho` nulo (bloco desalinhado do relatório do BO; esperado ≈18.402) e qualquer linha que repita o texto do cabeçalho como dado. Registrar as contagens no log.
- Depois da limpeza: esperado 29.992 linhas, grão único e `nr_mes_desembolso` entre 1 e 12 (fora disso → ALERTA).

### 08 · `sigcon_plano_aplicacao`  ← `dcgce_plano_aplicacao`
- **Arquivo:** sigcon/dcgce_plano_aplicacao.xlsx (Excel, header=1) · **Linhas:** 24.969 · **Prioridade:** Must
- **Grão:** plano de trabalho x classificação orçamentária x ano

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `codigo_plano_trabalho` | `cd_plano_trabalho` | identificador | G / FK |
| `codigo_unidade_orcamentaria` | `cd_uo` | identificador | G |
| `funcao_codigo` | `cd_funcao` | identificador | G |
| `subfuncao_codigo` | `cd_subfuncao` | identificador | G |
| `programa_codigo` | `cd_programa` | identificador | G |
| `identificador_projeto_atividade_codigo` | `cd_identificador_projeto_atividade` | identificador | G |
| `projeto_atividade_codigo` | `cd_projeto_atividade` | identificador | G |
| `subprojeto_subatividade_codigo` | `cd_subprojeto_subatividade` | identificador | G |
| `categoria_economica_despesa_codigo` | `cd_categoria_economica` | identificador | G |
| `grupo_despesa_codigo` | `cd_grupo_despesa` | identificador | G |
| `modalidade_aplicacao_codigo` | `cd_modalidade_aplicacao` | identificador | G |
| `elemento_despesa_codigo` | `cd_elemento_despesa` | identificador | G |
| `identificador_orcamento_codigo` | `cd_identificador_orcamento` | identificador | G |
| `fonte_recurso_codigo` | `cd_fonte_recurso` | identificador | G |
| `procedencia_codigo` | `cd_procedencia` | identificador | G |
| `funcional_programatica_formatado` | `cd_funcional_programatica` | identificador |  |
| `ano_exercicio_programa_trabalho` | `nr_ano_exercicio` | inteiro | G |
| `valor_concedente` | `vl_aplicacao_concedente` | valor |  |
| `valor_proponente` | `vl_aplicacao_proponente` | valor |  |

- O grão inclui `nr_ano_exercicio`. Se ainda houver duplicatas, registrar em ALERTA (não agregar).

### 09 · `sigcon_unidade_executora`  ← `dcgce_unidades_executoras`
- **Arquivo:** sigcon/dcgce_unidades.executoras.xlsx (Excel, header=0) · **Linhas:** 28.316 · **Prioridade:** Should
- **Grão:** convênio (siafi_uo) x unidade executora

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador | G |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | G |
| `convenio_codigo` | `nr_convenio` | identificador | R |
| `unidade_executora` | `cd_unidade_executora` | identificador | G |

- **derivadas:** `siafi_uo` = nr_siafi || cd_uo (usar `montar_siafi_uo`)
- Única fonte SIGCON com `header=0` (manter).

### 10 · `sigcon_nt_emenda`  ← `dcgce_sigcon_nt_emenda`
- **Arquivo:** sigcon/dcgce_sigcon_nt_emenda.xlsx (Excel, header=1) · **Linhas:** 14.520 · **Prioridade:** Should
- **Grão:** 1 linha por plano de trabalho (cd_plano_trabalho)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador | G / FK |
| `nt_emenda_no` | `nr_emenda` | identificador |  |
| `nt_emenda_nome` | `nm_parlamentar` | texto |  |
| `nota_tecnica_emenda_parlamentar_federal_situacao` | `fl_emenda_parlamentar_federal` | booleano |  |

- **sentinelas → nulo:** `cd_plano_trabalho`: ['99999999']; `cd_uo`: ['9999']
- **mapa de booleanos:** `fl_emenda_parlamentar_federal`: {'Sim': True, 'Não': False}
- Grão por `cd_plano_trabalho` vale só para valores não nulos (as ~216 linhas do sentinela ficam com plano nulo).

### 11 · `sigcon_chave_convenio`  ← `dcgce_codigo_convenio`
- **Arquivo:** sigcon/dcgce_Codigo_convenio.xlsx (Excel, header=1) · **Linhas:** 5.353 · **Prioridade:** Must
- **Grão:** 1 linha por convênio (cd_convenio_sequencial)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `convenio_codigo` | `nr_convenio` | identificador | R |
| `convenio_codigo_sequencial` | `cd_convenio_sequencial` | identificador | PK |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador |  |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |

- **derivadas:** `siafi_uo` = nr_siafi || cd_uo (usar `montar_siafi_uo`)
- **sentinelas → nulo:** `nr_convenio`: ['-', '00', '000']; `nr_siafi`: ['0']

### 12 · `sigcon_chave_termo_aditivo`  ← `dcgce_codigo_ta`
- **Arquivo:** sigcon/dcgce_Codigo_ta.xlsx (Excel, header=1) · **Linhas:** 7.105 · **Prioridade:** Must
- **Grão:** 1 linha por termo aditivo (cd_termo_aditivo)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador |  |
| `termo_aditivo_codigo_sequencial` | `cd_termo_aditivo` | identificador | PK |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador | FK |

- **derivadas:** `siafi_uo` = nr_siafi || cd_uo (usar `montar_siafi_uo`)

### 13 · `sigcon_chave_plano_trabalho`  ← `dcgce_Codigo_plano_de_trabalho`
- **Arquivo:** sigcon/dcgce_Codigo_plano_de_trabalho.xlsx (Excel, header=1) · **Linhas:** 5.353 · **Prioridade:** Could
- **Grão:** 1 linha por convênio (siafi_uo)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `conveno_codigo_plano_trabalho` | `cd_plano_trabalho` | identificador | FK |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | G |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador | G |

- **derivadas:** `siafi_uo` = nr_siafi || cd_uo (usar `montar_siafi_uo`)
- **sentinelas → nulo:** `cd_plano_trabalho`: ['0']; `nr_siafi`: ['0']

### 14 · `sigcon_chave_declaracao`  ← `dcgce_codigo_dec_contrap`
- **Arquivo:** sigcon/dcgce_Codigo_dec_contrap.xlsx (Excel, header=1) · **Linhas:** 5.352 · **Prioridade:** Could
- **Grão:** 1 linha por convênio (siafi_uo)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `declaracao_contrapartida_codigo` | `cd_declaracao_contrapartida` | identificador | FK |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | G |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador | G |

- **derivadas:** `siafi_uo` = nr_siafi || cd_uo (usar `montar_siafi_uo`)
- **sentinelas → nulo:** `cd_declaracao_contrapartida`: ['99999999']; `nr_siafi`: ['0']

### 15 · `sigcon_chave_siconv`  ← `chaves_convenio`
- **Arquivo:** sigcon/Chaves_convenio.csv (CSV ';', cp1252) · **Linhas:** 6.086 · **Prioridade:** Must
- **Grão:** 1 linha por convênio (siafi_uo)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `plano_trabalho_tipo_siafi` | `tp_instrumento_siafi` | texto |  |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador | G |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | G |
| `situacao` | `ds_situacao_convenio` | texto |  |
| `codigo_siconv` | `nr_convenio_siconv` | identificador | FK |
| `siconv` | `fl_siconv` | booleano |  |

- **derivadas:** `siafi_uo` = nr_siafi || cd_uo (usar `montar_siafi_uo`)
- **sentinelas → nulo:** `ds_situacao_convenio`: ['0']; `nr_convenio_siconv`: ['0']; `nr_siafi`: ['0']; `fl_siconv`: ['?']
- **mapa de booleanos:** `fl_siconv`: {'Sim': True, 'Nao': False, 'Não': False}
- Encoding continua cp1252/latin-1 (o arquivo não é UTF-8).

### 16 · `depara_siafi`  ← `siafi2`
- **Arquivo:** SIAFI2.csv (CSV ';') · **Linhas:** 12.009 · **Prioridade:** Must
- **Grão:** 1 linha por SIAFI de origem (siafi_uo_origem)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `siafi1` | `nr_siafi_1` | identificador | R |
| `uo1` | `cd_uo_1` | identificador | R |
| `siafi2` | `nr_siafi_origem` | identificador | G |
| `uo2` | `cd_uo_origem` | identificador | G |
| `siafiatual` | `nr_siafi_atual` | identificador |  |
| `uoatual` | `cd_uo_atual` | identificador |  |

- **derivadas:** `siafi_uo_origem` = nr_siafi_origem || cd_uo_origem; `siafi_uo_atual` = nr_siafi_atual || cd_uo_atual (usar `montar_siafi_uo`)
- Remover linhas 100% idênticas (esperado 12) com log.
- Para chaves `siafi_uo_origem` repetidas com o MESMO destino: manter uma linha (esperado ~1.878 chaves).
- Chaves com destino DIVERGENTE (esperado 2: SIAFI2 9427781 e 9428079, UO2 1451): retirar da tabela principal e gravar em `quarentena.parquet` no diretório silver da fonte, com log.

### 17 · `sigcon_concedente`  ← `dcgce_esfera`
- **Arquivo:** sigcon/dcgce_esfera.xlsx (Excel, header=1) · **Linhas:** 1.283 · **Prioridade:** Must
- **Grão:** 1 linha por concedente (nr_cnpj_concedente)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `concedente_esfera` | `ds_esfera` | texto |  |
| `concedente_cnpj` | `nr_cnpj_concedente` | identificador | PK |

- Trim em `ds_esfera` (há 'Federal ' com espaço). Esperado: 4 valores distintos.

### 18 · `depara_parlamentar`  ← `parlamentares`
- **Arquivo:** De para nomes parlamentares.xlsx (Excel, header=0) · **Linhas:** 289 · **Prioridade:** Should
- **Grão:** 1 linha por grafia de origem (ds_parlamentar_origem)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `de` | `ds_parlamentar_origem` | texto | PK |
| `para` | `nm_parlamentar` | texto |  |


### 19 · `siconv_convenio`  ← `siconv_convenio`
- **Arquivo:** uniao/siconv_convenio.csv (CSV ';', utf-8-sig) · **Linhas:** 282.968 · **Prioridade:** Should
- **Grão:** 1 linha por convênio federal (nr_convenio_siconv)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `nr_convenio` | `nr_convenio_siconv` | identificador | PK |
| `id_proposta` | `cd_proposta_siconv` | identificador |  |
| `dia_assin_conv` | `dt_assinatura` | data |  |
| `sit_convenio` | `ds_situacao_convenio` | texto |  |
| `subsituacao_conv` | `ds_subsituacao_convenio` | texto |  |
| `situacao_publicacao` | `ds_situacao_publicacao` | texto |  |
| `instrumento_ativo` | `fl_instrumento_ativo` | booleano |  |
| `ind_opera_obtv` | `fl_obtv` | booleano |  |
| `nr_processo` | `nr_processo` | identificador |  |
| `ug_emitente` | `cd_ug_emitente` | identificador |  |
| `dia_publ_conv` | `dt_publicacao` | data |  |
| `dia_inic_vigenc_conv` | `dt_vigencia_inicio` | data |  |
| `dia_fim_vigenc_conv` | `dt_vigencia_termino` | data |  |
| `dia_fim_vigenc_original_conv` | `dt_vigencia_termino_inicial` | data |  |
| `dias_prest_contas` | `qt_dias_prestacao_contas` | inteiro |  |
| `dia_limite_prest_contas` | `dt_pc_limite` | data |  |
| `data_suspensiva` | `dt_clausula_suspensiva` | data |  |
| `data_retirada_suspensiva` | `dt_retirada_suspensiva` | data |  |
| `dias_clausula_suspensiva` | `qt_dias_clausula_suspensiva` | inteiro |  |
| `situacao_contratacao` | `ds_situacao_contratacao` | texto |  |
| `ind_assinado` | `fl_assinado` | booleano |  |
| `motivo_suspensao` | `tx_motivo_suspensao` | texto_longo |  |
| `ind_foto` | `fl_foto` | booleano |  |
| `qtd_ta` | `qt_termo_aditivo` | inteiro |  |
| `qtd_prorroga` | `qt_prorrogacao` | inteiro |  |
| `vl_global_conv` | `vl_global` | valor |  |
| `vl_repasse_conv` | `vl_repasse` | valor |  |
| `vl_contrapartida_conv` | `vl_contrapartida` | valor |  |
| `vl_empenhado_conv` | `vl_empenhado` | valor |  |
| `vl_desembolsado_conv` | `vl_desembolsado` | valor |  |
| `vl_saldo_reman_tesouro` | `vl_saldo_remanescente_tesouro` | valor |  |
| `vl_saldo_reman_convenente` | `vl_saldo_remanescente_convenente` | valor |  |
| `vl_rendimento_aplicacao` | `vl_rendimento_aplicacao` | valor |  |
| `vl_ingresso_contrapartida` | `vl_ingresso_contrapartida` | valor |  |
| `vl_saldo_conta` | `vl_saldo_conta` | valor |  |
| `valor_global_original_conv` | `vl_global_inicial` | valor |  |

- **descartar:** `dia`, `mes`, `ano`, `qtde_convenios`
- **sentinelas → nulo:** `nr_processo`: ['000']
- **mapa de booleanos:** `fl_instrumento_ativo`: {'SIM': True, 'NÃO': False}; `fl_obtv`: {'SIM': True, 'NÃO': False}; `fl_assinado`: {'SIM': True, 'NÃO': False}; `fl_foto`: {'SIM': True, 'NÃO': False}
- **Encoding `utf-8-sig`** (corrige o BOM; o cabeçalho passa a gerar `nr_convenio`, não `i»¿nr_convenio`).
- Datas em dd/mm/aaaa (dayfirst).
- Valores com formato misto: a maioria usa vírgula decimal, `vl_saldo_conta` e `vl_global_inicial` usam ponto. A conversão tem de funcionar por coluna/valor sem multiplicar por 100 nem perder casas.
- Antes de descartar DIA/MES/ANO, verificar que são iguais às partes de `dt_assinatura` (registrar o resultado no relatório de validação).

### 20 · `controle_sei`  ← `controle_sei`
- **Arquivo:** Controle SEI.xlsx (Excel, aba Página1, usecols=27) · **Linhas:** 2.834 · **Prioridade:** Should
- **Grão:** 1 linha por processo SEI (nr_sei)

| nome atual (normalizado) | nome novo | tipo | marca |
|---|---|---|---|
| `no_sei` | `nr_sei` | identificador | PK |
| `no_siafi_(sigcon)` | `nr_siafi` | identificador | FK |
| `no_proposta_(siconv)` | `nr_proposta_siconv` | identificador |  |
| `obs` | `tx_observacao` | texto_longo |  |
| `monitorar?` | `fl_monitorar` | booleano |  |

- **descartar:** `instrumento, instrumento_2, instrumento_3`, `ta_1 a ta_13, ta_16, ta_17, ta_20, ta_21, ta_22`, `prorrogacao_de_oficio`
- **mapa de booleanos:** `fl_monitorar`: {'Sim': True, 'Não': False}
- Manter `sheet_name="Página1"` e `usecols=range(27)`.
- As colunas de documentos NÃO vão para a tabela 20: alimentam a tabela 21.

### 21 · `controle_sei_documento`  ← `(nova, derivada de controle_sei)`
- **Arquivo:** Gerada na silver a partir de Controle SEI.xlsx · **Linhas:** — · **Prioridade:** Should
- **Grão:** processo SEI x tipo de documento x ordem
- **Colunas:** `nr_sei` (texto, G/FK) · `tp_documento` (texto, G) · `nr_ordem` (inteiro, G) · `nr_documento_sei` (texto)
- Gerada na silver a partir do mesmo bronze de `controle_sei` (não é nova fonte no `sources.py`, a menos que o motor exija; nesse caso, registrar como fonte derivada).
- Desdobramento: `Instrumento` → (tp_documento='Instrumento', nr_ordem=1); `Instrumento 2/3` → ordem 2/3; `TA n` → ('Termo Aditivo', n); `Prorrogação de Ofício` → ('Prorrogação de Ofício', 1).
- Uma linha por célula preenchida; `nr_documento_sei` sempre texto (há valores como 'PT 12767' e '7547409/9962530').

