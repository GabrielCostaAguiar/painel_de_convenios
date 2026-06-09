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
| Formato de armazenamento | CSV | Simplicidade operacional; sem dependência de banco externo nas camadas de dados |
| Separação histórico / corrente | Dois diretórios por fonte | Evita reprocessamento do histórico a cada carga incremental |
| Caminhos dinâmicos | `pathlib.Path` + `BASE_DIR` | Portabilidade entre Windows e Linux; sem hardcode |
| Controle de versão de dados | `.gitignore` em `data/` | Dados não vão para o Git; apenas código e documentação |

---

## 4. Convenções de Nomenclatura de Arquivos

```
data/
├── bronze/
│   ├── sigcon_historico.csv          # histórico 2002–ano anterior
│   ├── sigcon_corrente.csv           # ano corrente (sobrescrito a cada carga)
│   ├── transferegov_historico.csv
│   └── ...
├── silver/
│   ├── convenios_silver.csv          # consolidado limpo
│   └── ...
└── gold/
    ├── convenios_por_status.csv
    ├── convenios_por_uf.csv
    └── ...
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
| `convenios.py` | Funções puras de limpeza + `transformar_bronze()` para orquestração |

### Funções de transformação (puras, testáveis)

| Função | Entrada | Saída |
|---|---|---|
| `_limpar_texto` | `"  texto "` | `"texto"` |
| `_parse_data_br` | `"01/01/2024"` | `date(2024, 1, 1)` |
| `_parse_valor_br` | `"1.234,56"` | `Decimal("1234.56")` |
| `transformar_df` | DataFrame Bronze | DataFrame Silver |

### Saída Silver

- Datas: ISO 8601 como string (`"2024-01-01"`)
- Valores: ponto decimal (`"500000.00"`)
- Textos: stripped, sem leading/trailing spaces
- Campos vazios: `""` (nunca `NaN`)

### Como adicionar transformação para nova fonte

1. Crie `core/transform/<nome_fonte>.py` com as funções `transformar_df()` e `transformar_bronze()`.
2. Registre o módulo em `_TRANSFORMADORES` dentro de `apps/convenios/management/commands/rodar_transformacao.py`.
3. Rode: `python manage.py rodar_transformacao <nome_fonte>`

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

### Fase 6 — Demais fontes (Transferegov, SIAFI, SIAD, SEI)
- Módulos de ingestão e transformação por fonte
- Consolidação Silver com todas as fontes
- Indicadores Gold completos

### Fase 7 — Autenticação, deploy e CI/CD
- Login LDAP/SSO SEPLAG
- Deploy em servidor interno
- Pipeline de atualização automática dos dados

---

## 9. Camada Gold — Implementação

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

## 10. Referências

- [Transferegov — Portal de Dados Abertos](https://portaldatransparencia.gov.br/download-de-dados/convenios)
- [Documentação Django](https://docs.djangoproject.com/)
- [Medallion Architecture (Databricks)](https://www.databricks.com/glossary/medallion-architecture)
