# Fase 8 — Ligar as tabelas do SIGCON no app web (Painel de Convênios)

## 1. Papel e objetivo

Você é o engenheiro responsável por fazer o app web do Painel de Convênios
(Django, `apps/sigcon` + `apps/painel`) voltar a ler os dados do SIGCON-MG a
partir da nova camada Silver, que foi refatorada nas Fases 0–7 (branch
`refactor/ingestao-legado`).

Resultado esperado: todos os `carregar_*` e o Gold `ConvenioIntegrado`
alimentados pela Silver nova (chaves `sigcon_*`, `depara_*`, nomes de coluna
`nr_/cd_/dt_/...`), datas corretas, **nenhuma linha de dado perdida em
nenhuma camada**, e as telas do SIGCON mostrando os mesmos números de hoje,
salvo as diferenças explicadas.

## 2. REGRA INEGOCIÁVEL — preservação de linhas

**Nenhuma linha pode ser excluída, em nenhuma camada (Bronze, Silver, banco,
Gold). A única exceção é a linha que não tem NENHUM dado em NENHUMA coluna.**

Definição operacional de "linha 100% vazia", a ser usada no código e nos
testes:
- avaliada no **texto bruto** do Bronze, logo depois da leitura, **antes** de
  sentinela, tipagem, renomeação ou remoção de colunas `Unnamed`;
- **todas** as células da linha, inclusive as das colunas `Unnamed`, são
  string vazia depois de `strip()`.

Consequências, sem exceção:
- Linha só com marcadores (`N/A`, `0`, `-`, `9999`, `99999999`, `null`) **não
  é vazia** e fica. Ela pode virar uma linha toda nula depois da tipagem, e
  continua na tabela.
- Linhas 100% idênticas (duplicadas) **ficam todas**.
- Linha que repete o cabeçalho, linha com chave obrigatória vazia e linha de
  grão divergente (quarentena) **ficam** e são **marcadas**.
- Quem não quiser essas linhas numa tela ou num indicador filtra **na
  consulta** (`services.py`), nunca na carga.
- Proibido em qualquer etapa de carga: `dropna(...)` sobre a tabela que será
  gravada, `drop_duplicates(...)` sobre a tabela que será gravada,
  `df[mascara]`/`df.loc[~mascara]` que reduz a tabela, `filter`/`exclude` antes
  de `bulk_create`, `ignore_conflicts=True`.
- Permitido: `drop_duplicates` num **subconjunto de consulta** usado só para
  `merge(how="left")`, com `assert` de que o número de linhas da tabela
  principal não mudou. Se as duplicatas desse subconjunto tiverem valores
  diferentes, registre um ALERTA com a contagem; não escolha em silêncio.
- No Gold (`ConvenioIntegrado`, 1 linha por `siafi_uo`): colapsar linhas só é
  permitido quando elas forem 100% idênticas. Chave repetida com conteúdo
  diferente → `raise`, para uma pessoa decidir.

Se, durante o trabalho, alguma regra de negócio parecer exigir exclusão de
linha, **pare, não implemente, e pergunte ao usuário**.

Invariante que deve valer ao final, e ser coberta por teste automatizado:
`linhas(Silver) = linhas(Bronze) − linhas 100% vazias`, para cada fonte; e
`linhas(model no banco) = linhas(Silver de origem)`, para cada model carregado
1:1.

## 3. Leitura obrigatória antes de começar

1. `docs/auditoria_exclusao_linhas.md`: onde o código exclui linhas hoje, com
   números por fonte. É o mapa do que você vai mudar para cumprir a seção 2.
2. `docs/plano_fase8_models_sigcon.md`: conferência das Fases 0–7, os 3
   bloqueios (B1 datas, B2 banco de teste, B3 migration GRP) e o plano por
   etapa, com a tabela **campo do model ← coluna da Silver** de cada um dos 15
   models. Siga esse plano. Onde ele e este prompt divergirem, vale este
   prompt.
3. `docs/dicionario_dados_legado.md`: nomes, tipos e sentinelas finais de cada
   tabela da Silver.
4. `CLAUDE.md`: estrutura real dos apps (`apps/sigcon`, `apps/painel`; os
   diretórios `apps/convenios` e `apps/dashboard` estão mortos) e convenções do
   projeto (full refresh atômico via `core/db.py::bulk_refresh`, padrão de
   exceções dos comandos, `order_by` terminando em `"pk"`).

## 4. Escopo

Pode alterar:
- `core/transform/` (motor `silver.py`, `chaves.py`, `utils.py`, YAMLs),
  `core/gold/`, `core/referencia/correcoes.csv`, `core/pipeline.py`
  (`CARGAS_ORM`);
- `apps/sigcon/` (loader, comandos, models **só com AddField**, `services.py`);
- `apps/grp/migrations/0008_*.py` (só a ordem das operações) e a nova
  migration de remoção dos models antigos do GRP;
- `tests/`, `apps/*/tests/`, `docs/`, `CLAUDE.md`.

Não altere, nesta fase:
- os **nomes** de campo dos models: sem `RenameField`. A renomeação é a Etapa
  6 opcional do plano;
- views e templates, a não ser que um teste de tela quebre por causa de uma
  mudança deste escopo;
- `data/raw/`: nunca;
- o comportamento do GRP, exceto a mudança prevista em `grp_tabela_uo` (Etapa
  0.5).

## 5. Regras de trabalho

1. Crie a branch `feat/models-sigcon` a partir de `refactor/ingestao-legado`.
   Faça um commit por etapa (`fix(silver): ...`, `feat(sigcon): ...`) e **não
   faça push**.
2. Ative o venv (`source .venv/Scripts/activate`): o Python global não tem
   `psycopg` e derruba a suíte inteira.
3. **Peça confirmação ao usuário antes de:** aplicar migration que dropa
   tabela (`DeleteModel`), apagar qualquer coisa em `data/`, rodar carga no
   banco de produção, ou regravar a linha de base do GRP.
4. Regressão do GRP a cada mudança em `core/transform/`: compare os 22 hashes
   SHA-256 de `docs/_baseline_grp_silver.json` com `data/silver/grp_*.parquet`.
   Única diferença aceita nesta fase: `grp_tabela_uo` (+1 linha `N/A`/`N/A`,
   Etapa 0.5). Mostre a diferença ao usuário e regrave só essa entrada depois
   da confirmação.
5. Não apague `data/silver/dcgce_*.parquet`, `chaves_convenio.parquet`,
   `siafi2.parquet` nem `data/gold/convenios_integrado.parquet` antes da Etapa
   5: são a base de comparação de paridade.
6. Dados pessoais (matrículas, nomes de pessoas) nunca em log nem em
   relatório.
7. Se a realidade contradisser este prompt ou o plano, pare a parte afetada,
   registre como DIVERGÊNCIA e pergunte. Não invente regra.
8. Fale com o usuário em português.

## 6. Etapas

Execute na ordem do plano (`docs/plano_fase8_models_sigcon.md`, Parte 2):
**0.1 → 0.5 → 0.2 → 0.3 → 0.4 → 1 → 2 → 3 → 4 → 5**. A Etapa 6 só roda se o
usuário pedir. Abaixo está o detalhamento da Etapa 0.5, que só aparece
resumida no plano, e os ajustes que a regra da seção 2 impõe às outras etapas.

### Etapa 0.1 — Datas ISO (bug B1)

Siga o plano. Lembrete: o pandas 3.0.3 infere o formato da coluna inteira pela
**primeira** data. Decida o formato **por valor** (`^\d{4}-\d{2}-\d{2}` →
`format="ISO8601"`; o resto → `dayfirst=True`). Aceite: 0 diferença de data
contra a Silver antiga (`dcgce_*`).

### Etapa 0.5 — Motor sem exclusão de linhas (`core/transform/silver.py`)

Estado atual (números em `docs/auditoria_exclusao_linhas.md` §2):

| Ponto | Linha atual | Mudança |
|---|---|---|
| Leitura do Bronze | l.395–399 | **Antes** de remover `Unnamed`, calcule `vazia` (todas as células `""` após `strip()`), remova só essas linhas e registre a contagem no log. Esta é a única remoção de linha do motor |
| `_descartar_linhas_vazias(..., "bruto")` | l.409 | Remover (é substituída pelo item acima; hoje não faz nada, porque não existe NaN nesse ponto) |
| `_descartar_linhas_repetem_cabecalho` | l.410 | Não remove mais. Marca `cabecalho_repetido` quando a tabela tem marcação (ver abaixo); senão, só registra ALERTA com a contagem |
| `descartar_linhas_se_nulo` | l.412 | Renomear o bloco do YAML para `marcar_linhas_se_nulo`. Marca `chave_obrigatoria_vazia:<coluna>`. Se um YAML ainda usar a chave antiga, o motor deve levantar erro explícito, para a regra não voltar em silêncio. Atualizar `sigcon_cronograma_desembolso.yaml` |
| `_descartar_linhas_vazias(..., "pós-tipagem")` | l.513 | **Remover.** Hoje exclui linhas só com sentinela (`sigcon_nt_emenda` 1, `grp_tabela_uo` 1) |
| `df.drop_duplicates()` | l.516 | **Remover.** Trocar por um ALERTA "linhas 100% idênticas mantidas: N" (`depara_siafi` 12, `depara_parlamentar` 2) |
| `_aplicar_quarentena` | l.521 / l.303 | As linhas ficam na tabela principal, marcadas como `quarentena:grao_divergente`. `transformar_fonte_completo()["quarentena"]` continua devolvendo esse subconjunto (cópia), para relatório |

Marcação:
- Coluna `ds_alerta_linha` (string, nula quando a linha está OK; se houver mais
  de um motivo, junte com `;`). Ela existe **só** nas tabelas cujo YAML declara
  `marcar_linhas_se_nulo` ou `quarentena` (hoje: `sigcon_cronograma_desembolso`
  e `depara_siafi`). Assim o schema do GRP não muda.
- Coluna `tx_linha_bruta` (string JSON com os valores brutos da linha, chaves
  com os nomes normalizados), preenchida **só** nas linhas marcadas e
  capturada **antes** da tipagem. Nada do que estava na linha se perde, mesmo
  que uma célula não converta no tipo da coluna.
- Tipagem: numa linha **marcada**, um valor que não converte vira nulo (o
  original está em `tx_linha_bruta`) e a linha **não** quebra o
  processamento. Numa linha **não marcada**, mantenha o comportamento atual,
  para que problema real continue aparecendo.
- `grao`: continua só emitindo ALERTA.

Testes novos (`tests/test_silver_grp.py` ou um novo
`tests/test_preservacao_linhas.py`, no padrão `_criar_fonte`):
1. Linha 100% vazia é removida, inclusive quando só tem espaços.
2. Linha com dado **só** numa coluna `Unnamed` **não** é removida.
3. Linha só com sentinelas (`N/A`/`9999`) fica, toda nula.
4. Duas linhas idênticas ficam as duas.
5. Linha que repete o cabeçalho fica, marcada, com `tx_linha_bruta`.
6. `marcar_linhas_se_nulo` marca e mantém; texto em coluna `inteiro` numa linha
   marcada não quebra.
7. Quarentena mantém a linha na principal, marcada.
8. YAML com `descartar_linhas_se_nulo` (chave antiga) → erro.

Aceite da Etapa 0.5:
- Para **todas** as 42 fontes com Bronze: `linhas(Silver) = linhas(Bronze) −
  linhas 100% vazias`. Valores esperados com os arquivos atuais:
  `sigcon_cronograma_desembolso` 48.392 (18.400 marcadas), `depara_siafi`
  12.009 (marcadas: todas as linhas das 2 chaves com destino divergente, que
  hoje são 8 depois da deduplicação; confira o número sem ela),
  `depara_parlamentar` 289, `sigcon_nt_emenda` 14.520,
  `grp_tabela_uo` 161, `grp_instrumento_financiado` 0 (a única linha é vazia).
  As demais ficam iguais às de hoje.
- GRP: 21 hashes idênticos; `grp_tabela_uo` muda só pela linha `N/A`/`N/A`
  (mostrar ao usuário antes de regravar a linha de base). Confira se
  `apps/grp/views/_filtros.py::_grp_listas` precisa de `cd_uo__isnull=False`
  para o dropdown de UO não ganhar uma opção vazia.
- Rodar `rodar_silver` das 20 fontes legadas sem erro.

### Ajustes nas Etapas 1–3 impostos pela regra

Já estão refletidos no plano; confirme cada um:
- **`carregar_controle_sei`**: remover o `drop_duplicates` da carga (hoje apaga
  334 de 2.834 linhas). O banco recebe 2.834. Em `apps/sigcon/services.py`
  (l.129–132), montar `sei_map` com `order_by("pk")` e `setdefault`, para ficar
  com o **primeiro** SEI de cada SIAFI, como a tela faz hoje.
- **`CronogramaDesembolso`**: AddField `ds_alerta_linha` (nulo). A carga recebe
  48.392 linhas. As consultas e somas do cronograma em `services.py`/views
  filtram `ds_alerta_linha__isnull=True`. A tela continua com 29.992.
- **`ConvenioIntegrado`**: `filtrar_uo` (`core/transform/chaves.py:63`) passa a
  marcar em vez de remover. AddField `fl_uo_excluida` (bool). `limpeza_g`
  (`core/gold/relacionamento.py:858`) deixa de remover, porque o campo
  `limpeza_g` já existe no model. As consultas em `services.py` (l.115 e
  l.409) filtram `limpeza_g=0, fl_uo_excluida=False`. Esperado: Gold com
  **6.082** linhas com chave (hoje 5.346) e tela inalterada.
- **Ponto de decisão (pare e pergunte):** na Silver nova, 4 linhas da
  `sigcon_chave_siconv` têm `siafi_uo` nulo (`nr_siafi` era `'0'`, que virou
  nulo). Os `drop_duplicates("siafi_uo")` atuais colapsariam as 4 numa só, e o
  model exige `siafi_uo` único e não nulo, então elas não cabem no Gold do
  jeito que está. As linhas continuam preservadas na Silver. Apresente ao
  usuário duas opções: (a) aceitar que elas fiquem fora do Gold, registradas
  no log e no relatório; (b) mudar o model para aceitar chave nula (outra PK,
  sem `unique`). Não decida sozinho.
- `resolver_siafi_atual`: ignora **na consulta** as linhas de `depara_siafi`
  marcadas como quarentena.
- Os `drop_duplicates("siafi_uo")` do Gold (`relacionamento.py:223` e `:356`):
  colapsar só linhas 100% idênticas; chave repetida com conteúdo diferente →
  `raise`.

## 7. Teste permanente da regra

Crie `tests/test_preservacao_linhas.py`, que fica no repositório e protege a
regra de regressão futura:
- os testes unitários da Etapa 0.5;
- teste com dado real, marcado para pular (`pytest.mark.skipif`) quando
  `data/bronze/` não existir: para cada fonte de `FONTES` com YAML e Bronze,
  `len(transformar_fonte(nome)) == len(bronze) − vazias_brutas`;
- teste de loader no banco de teste com Parquet sintético: `ControleSEI` e
  `CronogramaDesembolso` gravam exatamente o número de linhas do Parquet
  (inclusive duplicadas e marcadas);
- teste do Gold: `construir_tabela_integrada` devolve todo `siafi_uo` da
  `sigcon_chave_siconv`, com `fl_uo_excluida`/`limpeza_g` em vez de remoção.

## 8. Definição de pronto

- [ ] B1 (datas), B2 (banco de teste) e B3 (migration GRP gerada) resolvidos
- [ ] Invariante de linhas verdadeira nas 42 fontes, coberta por teste
- [ ] Nenhum `dropna`/`drop_duplicates`/filtro que reduza tabela gravada em
      `core/transform/silver.py`, `apps/sigcon/loader.py` e
      `core/gold/relacionamento.py`, exceto a remoção de linha 100% vazia e os
      subconjuntos de consulta com `assert` anti fan-out
- [ ] Os 15 models carregados a partir da Silver nova; contagem de cada model =
      contagem da Silver de origem
- [ ] `ConvenioIntegrado` com uma linha por `siafi_uo` não-nulo (6.082), com
      flags em vez de exclusão; decisão do usuário registrada sobre as 4
      linhas sem SIAFI; telas do SIGCON com os mesmos números da linha de base
      (Etapa 0.4)
- [ ] GRP: 21 hashes idênticos e `grp_tabela_uo` com +1 linha aprovada pelo
      usuário
- [ ] Suíte completa passando, exceto
      `apps/painel/tests/test_rotas_smoke.py::test_inventario_de_rotas_bate_com_o_gabarito`
      se continuar falhando por motivo independente (relatar)
- [ ] `docs/validacao_models_sigcon.md` com contagem por fonte/model e as
      diferenças explicadas; documentação corrigida (Etapa 5)
- [ ] Um commit por etapa, sem push

Ao final, mostre no chat:
1. a lista acima marcada;
2. uma tabela por fonte: Bronze, linhas vazias removidas, Silver, linhas
   marcadas, model, linhas no banco;
3. tudo o que ficou pendente ou foi registrado como DIVERGÊNCIA.
