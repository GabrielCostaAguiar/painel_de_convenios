# Arquitetura · Painel de Convênios (DCGCE)

Documento de referência. Cada seção é autossuficiente: leia só a que a tarefa pede (índice no
`CLAUDE.md`, seção 9). Itens marcados **(alvo)** ainda não existem; **(proposta)** aguarda decisão.

Versão do documento: 13/11/2026.

---

## §1. Visão geral

| | |
|---|---|
| Objetivo | Substituir o QlikView da DCGCE por um painel web próprio e unir SIGCON (legado) e GRP (novo, a partir de 2027) numa visão única do convênio. |
| Usuários | Setorialistas da DCGCE (consultam e cobram execução) e órgãos executores (conferem instrumentos e dados orçamentários). Depois, a administração direta do Estado. |
| Stack | Python, Django (views + templates), PostgreSQL, pandas, pyarrow, PyYAML, openpyxl. |
| Fora do escopo | DRF para as telas, React, Celery, Docker e Redis. |
| Produção | Uma VM Windows Server do setor (v1.1): Django, Postgres, ETL e robôs. |
| Princípios | Fonte nunca alterada; carga sem perda de histórico; ligações na gold em SQL; um padrão replicado em todos os apps (o GRP é a referência). |

---

## §2. Fluxo de dados

```
FONTES                      DISCO (lakehouse)                    POSTGRESQL                 DJANGO
BusinessObjects (e-mail) ─┐                                       
OneDrive (Graph API)     ─┼─► raw/      ─► bronze/   ─► silver/  ─► tabelas <app>_*  ─► gold.vw_*  ─► telas
TransfereGov (CSV/API)   ─┤   (como       (CSV        (parquet,     (carga do parquet)  (views SQL     e
Emendas federais         ─┘    chegou)     legível)    tipado)                          de cruzamento) exportação
```

| Camada | Onde | Quem produz | Regra |
|---|---|---|---|
| raw | `data/raw/<sistema>/` | coleta (Gmail, Graph, TransfereGov) ou cópia manual | Imutável. Nunca apagar nem editar. |
| bronze | `data/bronze/` | `rodar_ingestao` | Leitura fiel do raw (cabeçalho, encoding). Sem regra de negócio. |
| silver (disco) | `data/silver/<fonte>.parquet` | `rodar_silver` + YAML | Renomeia, tipa, limpa sentinelas, descarta linhas 100% vazias. |
| silver (banco) | tabelas `<app>_<tabela>` | `carregar_<app>` | Espelho do parquet: mesmos nomes de coluna. |
| ref | app `referencia` **(alvo v1.1)** | admin do Django | De-paras editáveis (SIAFI2, parlamentares, SIGCON × GRP). |
| gold | schema `gold`, views `vw_*` | arquivos `.sql` versionados | Cruzamentos para as telas. Única camada com junções. |
| ctrl / hist / app | schemas próprios **(alvo v1.1)** | ETL e Django | Controle de cargas, histórico de mudanças, dados da aplicação. |

---

## §3. Estrutura do repositório

```
painel_de_convenios/
├─ config/                         settings, urls, wsgi
├─ apps/
│  ├─ dashboard/                   casca: layout base, menu lateral, início
│  ├─ grp/                         ⭐ referência
│  │  ├─ apps.py                   name="apps.grp", label="grp"
│  │  ├─ models.py                 Grp* (tabelas) + Gold* (managed=False)
│  │  ├─ loader.py                 partials por fonte + _LOADERS_GRP + FONTES_GRP
│  │  ├─ views/                    uma view por sub-aba
│  │  │  └─ _filtros.py            _grp_render, _ler_filtros_grp
│  │  ├─ templatetags/             grp_filters.py (querystring_grp)
│  │  ├─ validacao/                catalogo.py (testes do app, ligados ao core)
│  │  ├─ sql/gold/                 NNN_vw_<nome>.sql
│  │  ├─ management/commands/      carregar_grp.py, validar_grp.py (finos)
│  │  └─ templates/grp/
│  ├─ sigcon/                      mesmo esqueleto do grp
│  ├─ execucao/                    (alvo S3)
│  ├─ uniao/                       (alvo S9)
│  ├─ referencia/                  (alvo S6) só models + admin, sem telas
│  └─ monitoramento/               (alvo S11)
├─ core/                           app Django SEM models: tudo que é global
│  ├─ management/commands/         rodar_ingestao, rodar_silver, rodar_pipeline, gerar_schemas
│  ├─ ingestion/sources.py         FonteDados: uma entrada por fonte
│  ├─ transform/schemas/           <fonte>.yaml
│  ├─ carga/                       loader.py (carregar_tabela_generica), refresh.py
│  │                               (bulk_refresh), comando.py (ComandoCarga)
│  ├─ validacao/                   sql.py, volumetria.py, arquivos.py, texto.py,
│  │                               limites.py, executor.py (ComandoValidacao)
│  ├─ web/                         paginacao, formatacao (formatar_celula),
│  │                               exportacao (CSV/XLSX), stubs
│  ├─ templatetags/                painel_filters.py
│  └─ gold/relacionamento.py       legado em pandas (R1–R4), só usado por testes
├─ etl/                            (alvo S5) orquestrador fora do Django
├─ data/                           raw/ bronze/ silver/ (fora do Git)
├─ docs/
├─ templates/  static/  tests/
└─ secrets/  .env                  (fora do Git)
```

**Regra de dependência:** `core` nunca importa `apps.*`; um app nunca importa outro app; o que dois
apps usam sobe para o `core`. `apps/dashboard` é a casca e pode ler dos demais. Só o `core` tem
`carregar_tabela_generica`; cada app guarda apenas seus `partial` e o `_LOADERS_<APP>` em
`apps/<app>/loader.py`.

---

## §4. Apps e módulos

Um app Django por aba do menu lateral. Sub-abas são módulos dentro do app.

| App | Aba do painel | Fontes | Chave principal | Versão |
|---|---|---|---|---|
| `dashboard` | Início, layout | — | — | v1.0 |
| `grp` | GRP | 22 consultas `grp_*` do BO | `nr_grp` | v1.0 |
| `sigcon` | Consultas SIGCON (6 sub-abas) | 15 consultas `dcgce_*` do BO + `sigcon_tabela_uo` | `siafi_uo` | v1.0 |
| `execucao` (nome a confirmar) | Execução Estadual (9 sub-abas) | SIAFI, PCASP, SIAD, controle de contrapartida | `siafi_uo` + exercício | v1.0 |
| `referencia` | — (sem telas; admin) | de-paras `siafi2`, parlamentares, SIGCON × GRP | — | v1.1 |
| `uniao` | Consultas União | TransfereGov (`siconv_*`, dados abertos e API) | número do convênio federal | v1.3 |
| `emendas` ou dentro de `uniao` **(proposta)** | Painel de Emendas | SIGA Brasil, SIOP ou TransfereGov | ano + número da emenda | v1.3 |
| `monitoramento` | Monitoramento, Alertas, Relatório Individual | planilhas do OneDrive, `controle_sei` | `siafi_uo` | v1.4 |
| ferramentas **(proposta)** | Painel do diretor, suplementação, decreto, orientações | gold + dados próprios (schema `app`) | — | v1.5–v1.6 |

Sub-abas da Execução Estadual: Arrecadação, Execução SIAFI, Execução PCASP, Crédito e Cota,
Controle Contrapartida, Conta Bancária, Saldo Conta Bancária, Estimativa Receita, Portal de Compras.

---

## §5. Padrão de app de dados

### Identidade
- Pasta `apps/<app>/`; `AppConfig.name = "apps.<app>"`; `AppConfig.label = "<app>"`, igual à pasta.
- Nunca alterar o label de app com migrations aplicadas sem plano aprovado.
- Comandos usam o label: `makemigrations <app>`, `showmigrations <app>`, `sqlmigrate <app> NNNN`.

### Models de tabela
- Um model por tabela silver, `db_table = "<app>_<tabela>"` explícito.
- Nomes de campo iguais às colunas do parquet (o loader genérico depende disso). Sem campos extras,
  exceto o `id` automático.
- Tipos pelo prefixo:

| Prefixo | Campo Django |
|---|---|
| `nr_`, `cd_`, `sg_`, `tp_` | `CharField` (preserva zeros) |
| `nm_`, `ds_` curtos | `CharField`; descrições longas (ex.: `ds_item`) em `TextField` |
| `tx_` | `TextField` |
| `vl_` | `DecimalField(max_digits=15, decimal_places=2)` |
| `qt_` com fração | `DecimalField` (ex.: `qt_item`) |
| `qt_` inteiro, `nr_ano_`, mês, parcela, prazo, duração | `IntegerField` |
| `dt_` / `dh_` | `DateField` / `DateTimeField` |
| `fl_` | `BooleanField(null=True)` |

- Campos que podem vir vazios na fonte: `null=True, blank=True`.
- Sem `ForeignKey` entre tabelas de dados.
- `db_index=True` nas chaves de ligação; `Meta.indexes` nos campos usados como filtro de tela.
- Grão com duplicidade legítima na fonte (ALERTA registrado): sem `unique`; usar `id` automático.

### Migrations
- Dependem só do próprio app ou dos apps padrão do Django.
- Sempre revisadas com `sqlmigrate` antes do `migrate`: sem `REFERENCES`, `nr_`/`cd_` como `varchar`,
  `vl_` como `numeric(15, 2)`, índices presentes.
- `migrate` é executado pelo Gabriel.

### Models gold
- `managed = False`, `db_table = 'gold"."vw_<nome>'` (schema qualificado). Não geram migration.
- `primary_key=True` no campo do grão da view (ex.: `nr_grp` em view 1 linha por instrumento).

---

## §6. Pipeline de uma fonte

### Registro (`core/ingestion/sources.py`)
Uma entrada `FonteDados` por fonte: nome, sistema, arquivo, `header` (linha do cabeçalho), encoding,
separador e, para fontes de e-mail, o assunto. O `header` é o erro mais comum: conferir no arquivo.

### YAML de schema (`core/transform/schemas/<fonte>.yaml`)
Gerado por `gerar_schemas` (heurístico: sempre revisar) e editado à mão. Blocos:

| Bloco | Conteúdo |
|---|---|
| `renomear:` | nome normalizado → nome final (§12). Cobre **todas** as colunas. Os cabeçalhos do BO não são renomeados na origem. |
| `tipos:` | categoria por coluna: texto, decimal, data, booleano, `inteiro` (Int64). |
| `sentinelas:` | valores que viram nulo (ex.: `N/A`, `-3`). |
| `descartar:` | colunas redundantes ou fora do modelo. |
| `grao:` | colunas que identificam uma linha (usadas no teste de grão). |

### Silver (`rodar_silver`)
Ordem: ler bronze → `limpar_colunas_padronizadas` → `dropna(how="all")` com log da quantidade
descartada → renomear → descartar → sentinelas → tipos. Conversões padrão:
- valores em formato brasileiro com `_para_numero` (inclusive números sem vírgula decimal);
- datas com `dayfirst=True`;
- flags `SIM`/`NÃO` (ou `S`/`N`) → booleano;
- códigos sempre texto.

### Carga
- `carregar_tabela_generica(nome_fonte, model)` (em `core/carga/loader.py`): lê o parquet, confere colunas do parquet = campos do
  model (sem `id`), troca nulos do pandas por `None` e faz full refresh dentro de `transaction.atomic()`.
- Registro por fonte: `carregar_<fonte> = partial(carregar_tabela_generica, "<fonte>", Model)` e uma
  entrada `"<fonte>": carregar_<fonte>` em `_LOADERS_<APP>`.
- Um comando por app: `carregar_<app>` (todas as fontes ou `--fonte <nome>`), subclasse fina de
  `core.carga.comando.ComandoCarga` (define só `rotulo` e `loaders`; `apos_carga` é gancho opcional).
- Validação: `validar_<app>` é subclasse de `core.validacao.executor.ComandoValidacao`; o catálogo de
  testes do app usa os construtores genéricos de `core/validacao/` com o prefixo do app.
- A partir da v1.1 a carga muda para upsert sem apagar linhas (§13); a interface do loader se mantém.

### Receita: nova fonte do BusinessObjects
1. Consulta no BO: uma tabela por consulta, separador `;`, sem qualificador, todos os atributos de grão.
2. Envio agendado por e-mail com assunto padronizado.
3. Entrada no `sources.py` (atenção ao `header`).
4. Arquivo em `data/raw/<sistema>/`; `rodar_ingestao <fonte>`; conferir `.shape` e cabeçalhos.
5. `gerar_schemas <fonte>`; escrever `renomear`, `tipos`, `sentinelas`, `descartar`, `grao`.
6. `rodar_silver <fonte>`; conferir `list(df.columns)`, `df.dtypes` e o teste de grão.
7. Model com `db_table` explícito; `makemigrations <app>`; `sqlmigrate`; `migrate` (Gabriel).
8. `partial` + entrada em `_LOADERS_<APP>`; `carregar_<app> --fonte <fonte>`.
9. Validação (§10) e registro em `docs/qualidade_dados.md`.

### Receita: fonte que mudou (coluna nova, cabeçalho novo)
Substituir o raw → conferir `header` → `rodar_ingestao` → atualizar o YAML à mão (não usar
`--sobrescrever` sem guardar as edições) → `rodar_silver` → ajustar model → `makemigrations` →
`migrate` → `carregar_<app> --fonte` → validar. O loader não muda.

---

## §7. Camada gold

### Regras
- Arquivos em `apps/<app>/sql/gold/NNN_vw_<nome>.sql`, numerados na ordem de criação, schema `gold`,
  `CREATE OR REPLACE VIEW`. (O `001_gold_instrumento.sql` do GRP é anterior a este padrão.)
- Cabeçalho obrigatório, para que a view seja entendida sem ler o corpo:
  ```sql
  -- gold.vw_<nome>
  -- grão: 1 linha por <...> | chave: <campo>
  -- fontes: <tabelas> | tela: <app> › <sub-aba>
  -- validação: SELECT COUNT(*), COUNT(DISTINCT <chave>) FROM gold.vw_<nome>;  -- esperado: <n> = <n>
  ```
- **Regra contra fan-out:** tabela 1:N é agregada por chave numa CTE antes de juntar. Duas tabelas 1:N
  nunca são juntadas diretamente.
- Tabelas com grão diferente viram views separadas (ex.: no GRP, plano de aplicação dividido em
  `vw_recurso_concedente`, `vw_recurso_contrapartida`, `vw_acao_orcamentaria` e `vw_plano_aplicacao`).
- Tabela com ALERTA de grão não entra em junção direta: deduplicar antes (ex.: emendas por
  `nr_grp` + ano + número) ou usar só para filtro/nome (ex.: `grp_tabela_uo`).
- Filtros de recorte (ex.: só MG nas bases federais) ficam na gold, não na silver.
- Campos calculados (vigente/vencido, mês descritivo) ficam na gold.
- Integração entre sistemas: views que usam um sistema e, se vazio, o outro, com uma coluna de
  origem de cada campo.
- Indicadores pesados: view materializada com `REFRESH MATERIALIZED VIEW CONCURRENTLY` no fim do
  ETL **(alvo v1.2)**.

### Receita: nova view gold
1. Definir grão, chave e fontes; escrever o cabeçalho.
2. CTEs de agregação das 1:N; junção final.
3. Gabriel aplica o SQL; Claude roda a validação do cabeçalho.
4. Model `managed=False` (§5).
5. Validar contra as tabelas silver (§10).

---

## §8. Camada de apresentação

### Padrão atual (GRP)
- Django puro: uma view por sub-aba, templates com sub-abas horizontais (`.subtabs`/`.subtab`),
  contexto com `secao_ativa`/`secao_sub`.
- `_grp_render`: monta a tabela a partir de três listas de mesmo tamanho: `colunas` (rótulos),
  `campos` (nomes no model) e `larguras`. Tamanhos diferentes = larguras descartadas com warning.
- `formatar_celula(campo, valor)` (`core/web/formatacao.py`): formata pelo **prefixo** do campo (`vl_` moeda, `dt_` data,
  `fl_` Sim/Não). Nova regra de formatação = novo prefixo, nunca `isinstance`.
- `_ler_filtros_grp`: filtros lidos da querystring, que é a fonte única de verdade. Ao trocar de
  sub-aba, os filtros comuns continuam aplicados.
- Paginação no servidor (25 linhas), helper `_visible_pages`.
- `min-width` da tabela = soma das larguras das colunas (com `table-layout:fixed`).
- Exportação para Excel com `openpyxl` direto (não pandas), com as colunas visíveis e os filtros
  (`core/web/exportacao.py`; esse módulo nunca importa pandas/numpy).

### Componente de consulta compartilhado (S1-10)
Promover as funções do GRP a um módulo comum, para que **uma aba nova = configuração + URL**.
Local: `core/web/` (decisão D4 de nov/2026) e `templates/partials/consulta_*.html`.
Configuração por aba (lista Python): model gold, colunas visíveis, rótulos, larguras, filtros,
ordenação padrão e nome do arquivo de exportação. Os nomes `_grp_*` viram genéricos e o GRP passa a
usar o componente (sem mudança visível).

### Receita: nova aba
1. View gold (§7) e model gold.
2. Configuração do componente: colunas, rótulos, larguras, filtros, exportação.
3. URL e item de menu; permissão do perfil (a partir da v1.1).
4. Conferir com o QlikView (legado) ou com a própria fonte (GRP) uma amostra e os totais.

### Outras regras de tela
- Gráficos com Chart.js servido localmente (sem CDN) **(alvo v1.2)**.
- Dados bancários: permissão própria (`ver_conta_bancaria`), mascarados por padrão, exportação
  respeitando a permissão **(alvo S3)**.
- Botão "Dados de carga" lendo `ctrl.execucao` **(alvo v1.1)**.

---

## §9. Checklists de revisão (modo `revisar`)

### YAML
- [ ] `renomear` cobre todas as colunas; nenhuma ficou com o nome normalizado automático.
- [ ] Nomes seguem §12 (prefixos, snake_case, sem acento).
- [ ] Códigos, CNPJ, UO, município, CATMAS como texto.
- [ ] Anos, meses, parcelas, prazos e durações como `inteiro`; identificadores (ex.: `nr_emenda`) como texto.
- [ ] `sentinelas` e `grao` declarados; `descartar` justificado.

### Model
- [ ] `db_table = "<app>_<tabela>"`; nome do model em PascalCase com prefixo do app.
- [ ] Conjunto de campos = colunas do parquet (conferir com `df.columns`).
- [ ] Tipos conforme a tabela da §5; `null=True, blank=True` onde a fonte pode vir vazia.
- [ ] Sem `ForeignKey`; índices nas chaves e nos filtros.

### Migration
- [ ] Só operações esperadas (`CreateModel`, `AddField`, `AlterField`); dependências só do próprio app.
- [ ] `sqlmigrate`: sem `REFERENCES`; `nr_`/`cd_` em `varchar`; `vl_` em `numeric(15, 2)`; índices.

### Loader e comando
- [ ] `partial(carregar_tabela_generica, "<fonte>", Model)` com o nome idêntico ao do `sources.py`.
- [ ] Entrada em `_LOADERS_<APP>`; nenhum comando novo por tabela.
- [ ] `pandas` importado dentro das funções.

### View gold
- [ ] Arquivo e cabeçalho no padrão da §7; grão declarado.
- [ ] Toda 1:N agregada antes da junção; nenhuma tabela com ALERTA de grão em junção direta.
- [ ] `COUNT(*) = COUNT(DISTINCT chave)` quando o grão é 1 linha por chave.
- [ ] Model `managed=False` com `db_table` qualificado e `primary_key` no grão.

### Aba
- [ ] Usa o componente compartilhado (ou `_grp_render` até a S1-10).
- [ ] `colunas`, `campos` e `larguras` com o mesmo tamanho; `min-width` = soma das larguras.
- [ ] Filtros pela querystring; paginação no servidor; exportação respeita filtros.
- [ ] Formatação por prefixo; nada de regra por tipo Python.
- [ ] URL, menu e permissão.

---

## §10. Validação e qualidade de dados (modo `testar`)

| # | Teste | Como | Esperado |
|---|---|---|---|
| T1 | Contagem | linhas no banco × `len(parquet)` | iguais |
| T2 | Grão | `GROUP BY <grao> HAVING COUNT(*) > 1` | nenhuma linha |
| T3 | Chave nula | `WHERE <chave> IS NULL` | zero ou explicado (ex.: propostas sem `nr_grp`) |
| T4 | Órfãos | `LEFT JOIN` filho → pai `WHERE pai IS NULL` | zero ou explicado |
| T5 | Somas | soma dos filhos × valor do pai | diferenças explicáveis |
| T6 | Zeros à esquerda | `LENGTH(cd_*)` fora do esperado (CNPJ 14, município 7, UF 2) | nenhuma |
| T7 | View gold | `COUNT(*)` × `COUNT(DISTINCT chave)` e contagem esperada no cabeçalho | iguais |
| T8 | Paridade | amostra de registros e totais × QlikView (legado) ou × BO (GRP) | diferenças explicadas |

- Resultado **ERRO**: bloqueia o avanço para a gold. **ALERTA**: problema da fonte conhecido e
  registrado; a gold contorna (deduplicação, junção evitada).
- Registro em `docs/qualidade_dados.md`, no formato já usado no arquivo.
- ALERTAs conhecidos: `grp_emenda` (emendas repetidas no mesmo `nr_grp`), `grp_cronograma_fisico`
  (sem nº de meta/etapa), `grp_tabela_uo` (um código com dois nomes), `cd_proposta` vazio nos
  instrumentos do GRP; no SIGCON, `pt_codigo` duplicado e planos órfãos de SIAFI.

---

## §11. Chaves e ligações

### GRP
- `nr_grp`: chave do instrumento em todas as consultas. Propostas ainda não conveniadas vêm com
  `nr_grp` vazio e só elas têm `cd_proposta` preenchido.
- `nr_instrumento_financiado` guarda o `nr_grp` do instrumento financiado.
- Ligação instrumento × UO por `nr_grp` (não por CNPJ). `grp_tabela_uo` é apoio para filtros e nomes.
- Concedente identificado por CNPJ.

### SIGCON
- `siafi_uo` (sequencial SIAFI + código da UO): espinha que liga o convênio às tabelas filhas.
- `cd_plano_trabalho` (`pt_codigo`) e `cd_convenio_sequencial` como chaves secundárias.
- Pontes (`chave_convenio`, `chave_termo_aditivo` e equivalentes) são mapeamentos de negócio legítimos,
  não candidatas a remoção.
- Plano de trabalho por convênio: plano original (via `chave_convenio`) UNION planos dos aditivos
  (via `chave_termo_aditivo`) na view `vw_plano_trabalho_sigcon`.
- Só tem vínculo com convênio o plano que chega a um `siafi_uo`. Planos de cadastro de instrumento,
  suplementação e remanejamento não têm ligação por SIAFI e ficam fora da gold (`qualidade_dados.md` S7).

### Execução Estadual
- `siafi_uo` + exercício. Anos fechados carregados uma vez; diário só exercício corrente e restos a
  pagar **(alvo v1.1)**.

### Entre sistemas
- SIGCON × GRP: de-para `siafi_uo ↔ nr_grp` no app `referencia`, com origem, data e responsável
  (chave a definir com a equipe do GRP: número do instrumento, SIAFI ou processo SEI) **(alvo S6)**.
- SIGCON × federal: `chaves_convenio` e `siafi2` no app `referencia` **(alvo S9)**. Até lá, convênios
  só com SIAFI antigo ficam sem ligação com a base federal.

---

## §12. Convenção de nomes

### Colunas (snake_case, sem acento)
`nr_` número · `cd_` código · `nm_` nome · `ds_` descrição · `sg_` sigla · `tp_` tipo · `dt_` data ·
`dh_` data e hora · `vl_` valor · `qt_` quantidade · `fl_` flag · `tx_` texto longo.
Sufixos: `_inicial` (pactuado, sem aditivos), `_fin` / `_nao_fin` (contrapartida).

### Objetos
| Objeto | Padrão | Exemplo |
|---|---|---|
| Fonte (sources.py = YAML = parquet = partial) | `<sistema>_<tabela>`, conforme registrado | `grp_concedente` |
| Tabela | `<app>_<tabela>` | `sigcon_convenio` |
| Model | `<App><Tabela>` | `GrpRecursoConcedente` |
| View gold | `gold.vw_<nome>` | `gold.vw_convenio` |
| Model gold | `Gold<Nome>` | `GoldInstrumento` |
| Arquivo gold | `NNN_vw_<nome>.sql` | `002_vw_convenio.sql` |
| Loader | `carregar_<fonte>` | `carregar_grp_emenda` |
| Registro de loaders | `_LOADERS_<APP>` | `_LOADERS_SIGCON` |
| Comando | `carregar_<app>` | `carregar_sigcon` |
| Branch | `feat/`, `fix/`, `refactor/` + assunto | `feat/gold-sigcon` |

---

## §13. ETL de produção (alvo v1.1)

Pasta `etl/` independente do Django; `python etl/run.py --fluxo diario|completo` ou `--fonte <nome>`.
Disparada pelo Agendador do Windows (~6h), com conta de serviço.

| Etapa | Funções | Registro |
|---|---|---|
| Orquestração | `executar_fluxo`, `executar_fonte`, `adquirir_trava`, `liberar_trava`, `registrar_execucao` | `ctrl.execucao` (início, fim, status, linhas) |
| Coleta | `buscar_emails_novos`, `baixar_anexo`, `calcular_hash`, `arquivo_ja_recebido`, `salvar_no_raw`, `marcar_email_processado` | `ctrl.arquivo_recebido` (fonte, data, hash, tamanho, id do e-mail) |
| Portões | `checar_colunas_esperadas`, `checar_grao`, `checar_queda_volume` (limite por fonte, ex.: 10%) | falha = fonte não carrega, motivo registrado, alerta por e-mail |
| Carga | `copiar_para_staging` (COPY), `aplicar_upsert`, `marcar_ausentes`, `gravar_historico` | tudo numa transação; falha = nada muda |

- Raw datado: `raw/<sistema>/<fonte>/<aaaa>/<mm>/<dd>/<hhmm>_<arquivo>`; arquivo repetido (mesmo hash)
  não é guardado de novo.
- Colunas de controle nas tabelas: `dt_primeira_carga`, `dt_ultima_carga`, `fl_presente_fonte`,
  `dt_saida_fonte`. Linha que sai da fonte é marcada, não excluída.
- Histórico em `hist.*` para situação, valores e vigência.
- Retenção do raw: 90 dias (BO), 7 dias (federais), depois uma cópia mensal compactada.
- Robôs (e-mail de pré-qualificação, decreto) em `etl/robos/`, lendo a silver com o papel de leitura.

### Quando a carga diária falha
1. Ver em `ctrl.execucao` qual fonte falhou e o motivo.
2. Queda de volume: arquivo cortado → pedir reenvio ao BO; queda real → ajustar o limite da fonte.
3. Arquivo faltando: conferir o Gmail e o assunto.
4. Reprocessar só a fonte: `python etl/run.py --fonte <nome>`.
5. O painel segue com os dados do dia anterior até a carga passar.

---

## §14. Banco e segurança

### Schemas
Hoje: tabelas de dados em `public`, views em `gold`. Alvo (v1.1): `silver`, `ref`, `gold`, `ctrl`,
`app`, `stg`, `hist`.

### Papéis do banco (alvo v1.1)
`painel_web` (Django), `painel_etl` (cargas), `painel_leitura` (robôs, só leitura).

### Aplicação
- Acesso só pela rede do Estado ou VPN; HTTPS (IIS ou Caddy) na frente do Waitress.
- Login com o AD (`django-auth-ldap`) ou contas locais provisórias. Grupos: setorialista, órgão
  executor, diretor, administrador. Permissão por aba via mixin nas views.
- Contas bancárias: permissão própria, mascaradas por padrão, log em `ctrl.acesso_sensivel`.
- LGPD: só os dados pessoais necessários. `grp_matriz_responsabilidade` (CPF, e-mail, telefone)
  fica fora por ora.
- Segredos em variáveis de ambiente ou `secrets/`, nunca no Git.
- Backup: `pg_dump` diário + cópia do raw fora da VM; teste de restauração mensal.

---

## §15. Ambiente, deploy e release

### Local
Windows, PowerShell, `.venv`, PostgreSQL local (psycopg2-binary), VS Code + Claude Code.

### VM (alvo v1.1)
Windows Server 2022/2025, 8 vCPU, 32 GB, SSD 512 GB (C: 100 GB sistema; D: 412 GB dados).
Python 3.12, PostgreSQL 16 (dados em `D:\postgres`), Git, Waitress + NSSM, IIS ou Caddy, pgAdmin 4.
Pastas: `D:\painel` (código e venv), `D:\dados\raw`, `D:\dados\silver`, `D:\backups`.
Saída para a internet só para Gmail API, Microsoft Graph, TransfereGov e SIGA Brasil.

### Settings de produção
`DEBUG=False`, `ALLOWED_HOSTS`, segredos em variáveis de ambiente, cookies seguros, HSTS,
`collectstatic`.

### Receita: release de versão
1. Testes e validação das fontes alteradas.
2. Merge na branch principal e tag (`v1.0`, `v1.1`…).
3. Notas de versão em `docs/`.
4. Deploy: `git pull` → `migrate` → aplicar SQL da gold → `collectstatic` → reiniciar o serviço.
5. Homologação com 2 setorialistas e comunicado aos usuários.

---

## §16. Registro de decisões

Uma linha por decisão: data, decisão, motivo. Mais recentes no fim.

| Data | Decisão | Motivo |
|---|---|---|
| set/2026 | Arquitetura medallion (raw → bronze → silver → gold) com YAML por fonte | Regras escritas uma vez por fonte; auditabilidade |
| set/2026 | Fonte nunca alterada; curadoria e quarentena separadas | Exigência do Tribunal de Contas |
| out/2026 | Gold em views SQL versionadas, não em pandas; desenvolvimento direto em PostgreSQL | Cruzamentos legíveis e reproduzíveis |
| out/2026 | Um app por aba do menu; sub-abas como módulos | Escopo claro por app |
| out/2026 | Modelo de extração GRP em 22 consultas, uma por grão | Evitar fan-out e agregação automática do BO |
| out/2026 | De-para de nomes no bloco `renomear:` do YAML | Uma única fonte de verdade por coluna |
| out/2026 | Loader genérico + `functools.partial` | Fonte nova sem código novo de carga |
| out/2026 | Telas em Django puro, sem DRF | Padrão já existente; menos camadas |
| out/2026 | Colunas inteiras corrigidas na silver (categoria `inteiro`) | Tipo certo desde a origem |
| out/2026 | Linhas 100% vazias descartadas na silver, com log | Ruído da exportação do BO |
| nov/2026 | Ligação instrumento × UO no GRP por `nr_grp`; de-para por CNPJ desfeito | CNPJ × UO não é obtível no BO |
| 09/11/2026 | Cabeçalhos do BO não são renomeados na origem | Normalização só no YAML |
| 09/11/2026 | Refatoração legada restrita ao SIGCON (15 tabelas); de-paras, `siconv_*` e `controle_sei` em ondas futuras | Foco na v1.0 |
| 12/11/2026 | App `sigcon` com label `sigcon`, no padrão do `grp` | Padronização antes da produção |
| 13/11/2026 | Padrão do GRP replicado para todos os apps de dados; ajustes conforme necessidade | Previsibilidade e menos retrabalho |
| 16/11/2026 | `core` vira app Django sem models, com os comandos de pipeline, a carga e a validação genéricas | Código global em um lugar só |
| 16/11/2026 | Regra de dependência: `core` ↛ `apps.*`; app ↛ outro app | Evitar acoplamento circular |
| 17/11/2026 | `apps/painel` → `apps/dashboard` (label e namespace); `painel_filters` no core, `querystring_grp` no grp | Nome coerente com a arquitetura |
| 17/11/2026 | Label do app `sigcon` trocado de `convenios` para `sigcon`; SQL em `docs/sql/renomear_label_sigcon.sql` | Pacote, label e tabelas com o mesmo nome |
| 17/11/2026 | Schema `gold` criado uma vez, em `core/sql/000_schema_gold.sql` (`CREATE SCHEMA IF NOT EXISTS`, sem `DROP`); apps não têm `000_schema` | O `DROP SCHEMA ... CASCADE` do GRP apagaria as views de todos os apps |
| 17/11/2026 | Plano de trabalho do SIGCON em `gold.vw_plano_trabalho_sigcon`, grão convênio (`siafi_uo`) × plano, ponte = plano original (`chave_convenio` + `geral`) UNION planos dos aditivos (`chave_termo_aditivo`); substitui `vw_plano_aplicacao_convenio`, que ligava o plano ao convênio só por `cd_plano_trabalho` e duplicava linhas | O plano não identifica um convênio só (erros de origem, ver `qualidade_dados.md` S7) e os planos dos aditivos ficavam sem convênio |
| 17/11/2026 | Planos de cadastro, suplementação e remanejamento (sem `siafi_uo`) ficam no banco e fora da gold; recorte na gold, não na carga | Banco é derivado da silver; carga continua tabela a tabela; testes silver × banco mantêm a referência |
| 17/11/2026 | Views gold do SIGCON que dependem de plano de trabalho (plano de aplicação, cronograma, nt_emenda) entram pela ponte `vw_plano_trabalho_sigcon`, com join interno | Garante só planos com `siafi_uo` e 1 linha por convênio × plano; valores somam por `siafi_uo`, nunca por plano |

---

## §17. Roadmap

| Versão | Data | Entrega |
|---|---|---|
| v1.0 | 31/12/2026 | Consultas SIGCON (6 abas), Execução Estadual (9 abas) e GRP pronto |
| v1.1 | 29/01/2027 | Produção na VM, ETL automático sem apagar linhas, backup, segurança, visão única SIGCON × GRP |
| v1.2 | 26/02/2027 | Indicadores, Gráficos, testes automatizados, desempenho |
| v1.3 | 25/03/2027 | Consultas União (TransfereGov) e Painel de Emendas |
| v1.4 | 23/04/2027 | Monitoramento, Alertas, Relatório Individual; desligamento do QlikView |
| v1.5 | 21/05/2027 | Painel do diretor, robô de e-mails com histórico, relatório orçamentário (PDF e Excel) |
| v1.6 | 18/06/2027 | Calculadora de suplementação, gerador de decreto, orientações, links úteis |
| — | 30/06/2027 | Estabilização e manuais |
| v2.0 | 2º sem/2027 | Oportunidades de captação |
