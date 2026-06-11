# Arquitetura do Painel de Convênios

## 1. Visão Geral

O Painel de Convênios é uma aplicação web interna da DCGCE/SEPLAG-MG construída sobre uma pipeline de dados Python + Django, seguindo o padrão **Lakehouse** com três camadas de maturidade dos dados: **Bronze**, **Silver** e **Gold**.

A motivação principal é substituir o painel QlikView legado por uma solução que a equipe possa manter, versionar e evoluir sem dependência de licença proprietária.

---

## 2. Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│                        FONTES DE DADOS                          │
│                                                                 │
│  SIGCON-MG (BO/PRODEMGE)  ·  Transferegov (portal dados abertos)│
│  SIAFI / SIAFI2 (e-mail)  ·  SIAD / SEI (arquivos de controle) │
│  Planilhas de dimensão (SharePoint / OneDrive)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │  scripts em core/ingestion/
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRONZE  —  data/bronze/                                        │
│  • Cópia fiel dos dados originais em CSV                        │
│  • Sem transformação; preserva erros, duplicatas e nulos        │
│  • Particionado em histórico (2002+) e ano corrente             │
│  • Imutável após ingestão (append-only por janela de tempo)     │
└────────────────────────────┬────────────────────────────────────┘
                             │  scripts em core/transform/
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  SILVER  —  data/silver/                                        │
│  • Dados limpos, tipados e padronizados                         │
│  • Deduplicação, normalização de CNPJ/CPF, datas ISO-8601, UF  │
│  • Join com tabelas de dimensão (município, órgão, programa)    │
│  • Regras de negócio básicas validadas                          │
└────────────────────────────┬────────────────────────────────────┘
                             │  core/transform/chaves.py
                             │  core/referencia/*.csv
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  RELACIONAMENTO  —  em memória (sem arquivo intermediário)      │
│  • sigcon_chaves: ponte SIGCON ↔ SICONV via chave SIAFI_UO      │
│  • Filtro de UOs: UOS_EXCLUIR (11 UOs não-operacionais)         │
│  • Campos G_: coalesce SICONV+SIGCON (21 campos padronizados)   │
│  • Campos A_: projeção G_ sobre UO atual via SIAFI2 de-para     │
│  • De-paras: situações, tipos SIAFI, UOs, concedentes           │
│  • Correções hard-coded: core/referencia/correcoes.csv (14)     │
└────────────────────────────┬────────────────────────────────────┘
                             │  scripts em core/gold/
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  GOLD  —  data/gold/                                            │
│  • Agregações e indicadores prontos para consumo                │
│  • Séries históricas, totais por UF/órgão/programa/status       │
│  • Tabelas desnormalizadas otimizadas para leitura              │
└────────────────────────────┬────────────────────────────────────┘
                             │  leitura via pandas/ORM
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  DJANGO  —  apps/dashboard/                                     │
│  • Views que leem CSVs Gold ou tabelas do banco                 │
│  • Filtros interativos, gráficos, tabelas paginadas             │
│  • Exportação para Excel/CSV                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Decisões de Projeto

| Decisão | Escolha | Justificativa |
|---|---|---|
| Linguagem ETL | Python | Ecosistema rico (pandas, openpyxl), conhecimento da equipe |
| Framework web | Django | ORM, admin, autenticação prontos; bom para dados tabulares |
| Formato Bronze | CSV | Fidelidade máxima ao dado original; legível sem biblioteca especializada; sem coerção de tipo |
| Formato Silver/Gold | Parquet | Preserva tipos nativos (datetime, float, string nullable); compressão colunar; leitura analítica eficiente |
| Separação histórico / corrente | Dois diretórios por fonte | Evita reprocessamento do histórico a cada carga incremental |
| Caminhos dinâmicos | `pathlib.Path` + `BASE_DIR` | Portabilidade entre Windows e Linux; sem hardcode |
| Controle de versão de dados | `.gitignore` em `data/` | Dados não vão para o Git; apenas código e documentação |

---

## 4. Convenções de Nomenclatura de Arquivos

```
data/
├── raw/
│   ├── dcgce_convenio.xlsx           # planilha SIGCON-MG (Excel, input da Bronze)
│   └── ...
├── bronze/
│   └── dcgce_convenios/
│       └── dcgce_convenios_<timestamp>.csv   # histórico de cargas (append-only)
├── silver/
│   └── dcgce_convenios.parquet       # última Silver processada (sobrescrito)
└── gold/
    └── ...                           # agregações prontas para consumo
```

---

## 5. Camada Bronze — Implementação

### Módulos em `core/ingestion/`

| Arquivo | Responsabilidade |
|---|---|
| `sources.py` | Registro declarativo de fontes (`FonteDados` + dicionário `FONTES`) |
| `readers.py` | Leitura do CSV → `pd.DataFrame` (tudo como `str`, sem coerção de tipo) |
| `bronze.py` | Orquestra leitura + gravação em `data/bronze/<fonte>/` com timestamp |

### Como adicionar uma nova fonte

1. **Abra `core/ingestion/sources.py`** e adicione uma entrada ao dicionário `FONTES`:

```python
"transferegov": FonteDados(
    nome="transferegov",
    arquivo="transferegov.csv",
    separador=";",
    encoding="utf-8",
    descricao="Dados abertos do Transferegov (portal da transparência)",
),
```

2. **Coloque o arquivo CSV** em `data/raw/transferegov.csv`.

3. **Rode a ingestão**:
```bash
python manage.py rodar_ingestao transferegov
```

O arquivo Bronze será salvo em `data/bronze/transferegov/transferegov_<timestamp>.csv`.

### Regra de ouro da camada Bronze

> O dado entra como chegou. Nada é corrigido, filtrado ou convertido.
> Erros de digitação, duplicatas, colunas mal nomeadas — tudo preservado.
> O Bronze é o seu "desfazimento": se a Silver estragar algo, você reprocessa a partir daqui.

### Por que CSV no Bronze e não Parquet?

O Bronze usa **CSV** porque o objetivo é fidelidade máxima ao dado original:
- Sem coerção de tipos (`"01/01/2024"` fica string, não `datetime`)
- Legível por qualquer ferramenta (Excel, Bloco de Notas, `cat`)
- Sem dependência de biblioteca de leitura especializada

**Parquet** será usado nas camadas **Silver e Gold**, onde os tipos já estão validados e precisamos de performance de leitura analítica (compressão, leitura colunar).

---

## 6. Camada Silver — Implementação

### Módulos em `core/transform/`

| Arquivo | Responsabilidade |
|---|---|
| `utils.py` | `normalizar_coluna(nome)` — snake_case sem acentos; reutilizável por qualquer fonte |
| `convenios.py` | Pipeline completo para `dcgce_convenios`: limpeza, conversão, validação e gravação |

### Pipeline de `transformar_convenios` (fonte: `dcgce_convenios`)

| Passo | O que faz |
|---|---|
| Lê Bronze | `pd.read_csv(..., dtype=str, keep_default_na=False)` — tudo como texto |
| Remove fantasmas | Colunas `Unnamed: N` (artefato do Excel) são descartadas |
| Normaliza nomes | `normalizar_coluna` → snake_case sem acentos (ex: `Situação` → `situacao`) |
| Converte datas | `pd.to_datetime(errors="coerce")` → `datetime64[us]`; inválidos → NaT |
| Converte valores | `pd.to_numeric(errors="coerce")` → `float64`; inválidos → NaN |
| Limpa IDs | strip + remove artefato `".0"`; vazio → `<NA>`; dtype `string` (nullable) |
| Limpa categórico | `situacao` → strip + dtype `string` |
| Valida | Relatório de nulos por coluna, alertas de negativos e duplicatas (apenas log) |

### Schema Silver — `dcgce_convenios`

| Coluna | Dtype pandas | Observação |
|---|---|---|
| `convenio_codigo` | `string` | Identificador textual; pode conter `-` |
| `convenio_numero_sequencial_siafi` | `string` | 4 registros sem SIAFI (`<NA>`) |
| `unidade_orcamentaria_codigo` | `string` | Código numérico como texto |
| `situacao` | `string` | Ex: `VENCIDO`, `EM EXECUÇÃO` |
| `data_inicio_vigencia` | `datetime64[us]` | Início da vigência |
| `data_termino_vigencia` | `datetime64[us]` | Término da vigência |
| `data_real_convenio` | `datetime64[us]` | Data de assinatura |
| `valor_inicial_concedente_contratado` | `float64` | 18 linhas com NaN (sem valor informado) |
| `valor_total_aditado_concedente_contratado` | `float64` | |
| `valor_concedente` | `float64` | |
| `valor_inicial_proponente_contratado` | `float64` | |
| `valor_total_aditado_proponente_contratado` | `float64` | |
| `valor_proponente` | `float64` | |
| `valor_total_convenio` | `float64` | |

### Arquivo de saída

```
data/silver/dcgce_convenios.parquet
```

Formato Parquet (via `pyarrow`): preserva `datetime64`, `float64` e `StringDtype` sem
reinterpretação. Sobrescrito a cada execução (Silver não mantém histórico — o histórico fica no Bronze).

### Command

```bash
python manage.py rodar_silver dcgce_convenios
```

### Como adicionar transformação para nova fonte

1. Crie `core/transform/<nome_fonte>.py` com `transformar_<fonte>` e `gravar_silver`.
2. Registre em `_TRANSFORMADORES` dentro de `apps/dashboard/management/commands/rodar_silver.py`.
3. Rode: `python manage.py rodar_silver <nome_fonte>`

---

## 7. Modelo de Dados — `apps/convenios`

### Model: `Convenio`

| Campo | Tipo Django | Descrição |
|---|---|---|
| `nr_convenio` | `CharField(30, unique=True)` | Chave natural do domínio (ex: `123456/2024`) |
| `nr_processo` | `CharField(50, blank=True)` | Número do processo administrativo |
| `objeto` | `TextField` | Descrição do objeto do convênio |
| `concedente` | `CharField(255)` | Órgão federal concedente |
| `convenente` | `CharField(255)` | Entidade convenente (prefeitura, ONG etc.) |
| `situacao` | `CharField(100)` | Status atual (Ex Execução, Encerrado...) |
| `valor_global` | `DecimalField(16,2)` | Valor total em reais |
| `data_inicio` | `DateField(null=True)` | Data de início da vigência |
| `data_termino` | `DateField(null=True)` | Data de término da vigência |
| `atualizado_em` | `DateTimeField(auto_now=True)` | Timestamp da última carga |

Índices criados: `situacao`, `concedente`, `data_inicio`.

### Idempotência da carga (`carregar_silver`)

O comando usa `update_or_create(nr_convenio=..., defaults={...})`:
- Registro inexistente → cria.
- Registro existente → atualiza todos os campos.
- Rodar N vezes → mesmo estado final no banco.

---

## 8. Roadmap

### Fase 1 — Estrutura inicial ✅
- Criação do repositório e estrutura de pastas
- `.gitignore`, `.env.example`, documentação base

### Fase 2 — Setup Django ✅
- Projeto Django em `config/`, settings base/dev/prod
- `django-environ` para variáveis sensíveis
- App `dashboard` com URL raiz funcionando

### Fase 3 — Pipeline Bronze ✅
- Registro declarativo de fontes (`sources.py`)
- Leitor genérico (`readers.py`), ingestão com timestamp (`bronze.py`)
- Management command `rodar_ingestao`

### Fase 4 — Pipeline Silver e Models ✅
- Transformações puras e testáveis em `core/transform/convenios.py`
- App `apps/convenios` com model `Convenio`, migrations e admin
- Management commands `rodar_transformacao` e `carregar_silver` (idempotente)

### Fase 5 — Camada Gold e Servicos ✅
- Funções de agregação puras em `core/gold/convenios.py`
- Camada de serviços com cache em `apps/dashboard/services.py`
- 12 testes unitários (sem banco) cobrindo todos os indicadores

### Fase 6 — Frontend do Dashboard
- View Django com tabela paginada e filtros básicos
- Gráfico de barras (convênios por situação)

### Fase 6b — Relacionamento SIGCON↔SICONV (migração do QlikView) — em andamento
- R1 ✅ estrutura, de-paras, filtro UO, correções
- R2 ✅ chaves resolvidas, de-para SIAFI→atual, correções data-driven, 28 testes
- R3 ✅ G_ (coalesce SICONV→SIGCON), A_ (projeção siafi_atual), tabela integrada Gold, 31 testes
- R4 ✅ model `ConvenioIntegrado` + loader + command + admin + 2 testes

### Fase 6c — Demais fontes (Transferegov, SIAFI, SIAD, SEI)
- Módulos de ingestão e transformação por fonte
- Consolidação Silver com todas as fontes
- Indicadores Gold completos

### Fase 7 — Autenticação, deploy e CI/CD
- Login LDAP/SSO SEPLAG
- Deploy em servidor interno
- Pipeline de atualização automática dos dados

---

## 9. Camada de Relacionamento — Implementação (R1–R4)

### Visão geral

A camada de relacionamento fica entre Silver e Gold. Equivale ao "miolo" do script QlikView legado
(`sigcon_chaves1`, campos `G_`, campos `A_`, filtros de UO e de-paras).

### Módulos

| Arquivo | Responsabilidade |
|---|---|
| `core/transform/chaves.py` | `UOS_EXCLUIR` (frozenset), `filtrar_uo()`, `montar_siafi_uo()` |
| `core/transform/referencias.py` | Carrega CSVs de `core/referencia/` como dicts/DataFrames |
| `core/gold/relacionamento.py` | `montar_sigcon_chaves()`, `aplicar_campos_g()`, `aplicar_campos_a()` |

### Dados de referência versionados — `core/referencia/`

> Estes CSVs **fazem parte do repositório** (não estão em `data/`, que é gitignored).
> Representam regras de negócio estáveis extraídas do QlikView.

| Arquivo | Conteúdo | Fonte QlikView |
|---|---|---|
| `situacoes_padronizadas.csv` | 19 mapeamentos situação original → padronizada | `Mapa2` |
| `tipos_siafi.csv` | 2 tipos: `11 → Acordo/Ajuste`, `15 → Transferências Especiais` | `Map_Tipo_SIAFI` |
| `uo_nomes.csv` | ~120 entradas `código → "código - NOME"` | `MapaG_UO` |
| `uo_siglas.csv` | ~90 entradas `nome → sigla` | `Mapa5` |
| `uo_descricoes.csv` | ~90 entradas `nome → "nome - sigla"` | `Mapa4` |
| `concedentes_padronizados.csv` | ~470 entradas normalização concedentes (**parcial** — completar)| `Mapa3` |
| `correcoes.csv` | 14 correções hard-coded de dados incorretos no SIGCON | linhas 1601–1318 |

### Chave de relacionamento SIAFI_UO

```
SIAFI_UO = str(convenio_numero_sequencial_siafi) + str(unidade_orcamentaria_codigo)
```

Concatenação **direta, sem separador**. Exemplo: `"9309074"` + `"1261"` = ``"93090741261"`.
Qualquer espaço nos valores de origem corrompe a chave — sempre aplicar `.strip()` antes.

### Filtro de UOs

```python
from core.transform.chaves import UOS_EXCLUIR, filtrar_uo

df_filtrado = filtrar_uo(df, coluna_uo="unidade_orcamentaria_codigo")
```

Equivalente ao `Where not match(UO, '5131', '9801', ...)` do QlikView (11 UOs).

### Join SIGCON ↔ SICONV

- **Cardinalidade**: LEFT JOIN de SIGCON → SICONV (0 ou 1 SICONV por convênio SIGCON)
- **Fan-out**: sempre deduplicar a dimensão SICONV antes do join para evitar multiplicação de linhas
- **Chave**: `nr_convenio` (campo `Código.SICONV` da Chaves_convenio.csv)

### Roadmap de implementação

| Etapa | O que faz |
|---|---|
| **R1** ✅ | Estrutura, de-paras, filtro UO, correções |
| **R2** ✅ | Chaves resolvidas, de-para SIAFI→atual, correções data-driven, 28 testes |
| **R3** ✅ | `aplicar_campos_g` (21 coalesces) + `aplicar_campos_a` + `construir_tabela_integrada` + `gravar_tabela_integrada` + `deduplicar_por_siafi_atual`, 31 testes |
| **R4** ✅ | `ConvenioIntegrado` (model + migration), `carregar_tabela_integrada()`, command `carregar_relacionamento`, admin com fieldsets G_/A_, 2 testes Django |

---

## 10. Camada Gold — Implementação

### Módulos em `core/gold/`

| Arquivo | Responsabilidade |
|---|---|
| `convenios.py` | Funções puras de agregação (resumo_geral, total_por_situacao, total_por_ano, total_por_concedente) |

### Indicadores disponíveis

| Função | Retorno | Descrição |
|---|---|---|
| `resumo_geral(df)` | `dict` | Total de convênios, valor total, nº de situações e concedentes |
| `total_por_situacao(df)` | `DataFrame` | Quantidade e valor por status |
| `total_por_ano(df)` | `DataFrame` | Quantidade e valor por ano (série temporal) |
| `total_por_concedente(df)` | `DataFrame` | Quantidade e valor por órgão federal |

### Serviços e cache (`apps/dashboard/services.py`)

- `get_indicadores(usar_cache=True)` — retorna todos os indicadores, opcionalmente cacheados.
- `invalidar_cache()` — limpa o cache; chamado automaticamente por `carregar_silver`.
- TTL configurável via `GOLD_CACHE_SECONDS` em `settings.py` (padrão: 3600 s).

**Estratégia de cache por tipo de dado:**

| Dado | Frequência de mudança | TTL recomendado |
|---|---|---|
| Indicadores históricos (anos anteriores) | Nunca após carga inicial | Longo (24 h+) ou permanente |
| Indicadores do ano corrente | A cada nova carga Silver | Curto (1 h) ou invalidar no `carregar_silver` |

Em produção, configure Redis no `settings.py` para cache que sobreviva reinicializações do servidor.

---

## 11. Consultas SIGCON — Abas de Detalhe

### Visão geral

A seção **Consultas SIGCON** do painel expõe 6 abas navegáveis. A aba **Convênios** é a lista
mestre; as demais são abas de detalhe que mostram registros de um único convênio selecionado.

A seleção é feita clicando no botão `›` de qualquer linha da lista — ele abre a aba
**Plano de Aplicação** com o parâmetro `?cod_sigcon=<código_SIGCON>`. Os demais links de subtab
carregam o mesmo `cod_sigcon` para manter o contexto ao navegar entre abas.

### URLs e views

| Aba | URL | View | Modo standalone |
|---|---|---|---|
| Convênios | `/` | `sigcon` | lista com filtros |
| Plano de Aplicação | `/plano_aplicacao/` | `plano_aplicacao` | todos os registros |
| Cronograma de Desembolso | `/cronograma/` | `cronograma` | filtros cod_siafi + plano |
| Prorrogação de Ofício | `/prorrogacao/` | `prorrogacao` | todos os registros |
| Termo Aditivo | `/termo_aditivo/` | `termo_aditivo` | todos os registros |
| Unidades Executoras | `/unidades_executoras/` | `unidades_executoras` | sem dados (sem fonte) |

### Camada de serviços (`apps/dashboard/services.py`)

Toda a lógica de query/join vive nos serviços. As views são roteadores finos.
Isso torna os serviços testáveis independentemente do ciclo request/response.

| Função | Retorno | Descrição |
|---|---|---|
| `enrich_convenios_page(page_items)` | `dict[pk → extra]` | Enriquece página de `Convenio` com campos de `ConvenioIntegrado` |
| `get_plano_aplicacao_qs(cod_sigcon)` | `(QuerySet, ctx)` | Filtra `PlanoAplicacao` por `plano_trabalho_codigo` |
| `get_cronograma_qs(cod_sigcon, ...)` | `(QuerySet, ctx)` | Filtra `CronogramaDesembolso` por `siafi + uo` |
| `get_prorrogacao_qs(cod_sigcon)` | `(QuerySet, ctx)` | Filtra `ProrrogacaoOficio` diretamente por `convenio_codigo` |
| `get_termos_aditivos_qs(cod_sigcon)` | `(QuerySet, ctx)` | Filtra `TermoAditivo` via `CodigoTermoAditivo` (ponte siafi+uo) |

### Chaves de ligação mestre → detalhe

| Aba | Chave URL | Lógica de join |
|---|---|---|
| Plano de Aplicação | `cod_sigcon` | `Convenio.plano_trabalho_codigo` → `PlanoAplicacao.codigo_plano_trabalho` |
| Cronograma | `cod_sigcon` | `Convenio.(siafi, uo)` → `CronogramaDesembolso.(siafi, uo)` |
| Prorrogação | `cod_sigcon` | `Convenio.convenio_codigo` = `ProrrogacaoOficio.prorrogacao_oficio_codigo_convenio` (direto) |
| Termo Aditivo | `cod_sigcon` | `Convenio.(siafi, uo)` → `CodigoTermoAditivo.(siafi, uo)` → `TermoAditivo.termo_aditivo_codigo_sequencial` |

### Enriquecimento da aba Convênios

O model `Convenio` já contém a maioria dos campos (consolidado pelo `loader.py` a partir de
`dcgce_convenio + dcgce_geral + dcgce_plano_trabalho + dcgce_esfera`). Dois campos extras
são preenchidos via Python com dados de `ConvenioIntegrado` (join por `siafi + uo`):

| Campo | Fonte |
|---|---|
| Código União | `ConvenioIntegrado.codigo_siconv` |
| Proponente | `ConvenioIntegrado.g_proponente_pad` |
| Fim Vigência Inicial | `ConvenioIntegrado.g_fim_vigencia_inicial` |

### Lacunas de fonte (pendências)

Os campos abaixo não têm fonte disponível no estado atual do projeto e são exibidos com o
marcador `— sem fonte —` no template:

| Campo / Aba | Motivo |
|---|---|
| **SEI** (aba Convênios) | Nenhum model atual possui campo SEI |
| **Tipo de Contrapartida** (aba Convênios) | Não encontrado em nenhum model |
| **Fonte nova** (aba Plano de Aplicação) | `PlanoAplicacao` tem apenas `fonte_recurso_codigo`; de-para `fontes_2023` não foi carregado |
| **Aba Unidades Executoras inteira** | `dcgce_unidades.executoras` tem erro de geração de schema (header não detectado); model não criado — ver comentário em `models.py:803` |

### Testes

`apps/dashboard/tests/test_sigcon_services.py` — 11 testes cobrindo todas as abas com fonte:
- `EnrichConveniosPageTest` (2) — enriquecimento com `ConvenioIntegrado`
- `PlanoAplicacaoQsTest` (3) — filtragem por `plano_trabalho_codigo`
- `CronogramaQsTest` (2) — filtragem por `siafi + uo`
- `ProrrogacaoQsTest` (2) — join direto por `convenio_codigo`
- `TermoAditivoQsTest` (2) — bridge `CodigoTermoAditivo`

---

## 12. Referências

- [Transferegov — Portal de Dados Abertos](https://portaldatransparencia.gov.br/download-de-dados/convenios)
- [Documentação Django](https://docs.djangoproject.com/)
- [Medallion Architecture (Databricks)](https://www.databricks.com/glossary/medallion-architecture)
