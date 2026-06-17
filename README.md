# Painel de Convênios — DCGCE / SEPLAG-MG

Sistema web interno para substituição gradual do painel QlikView da **Diretoria Central de Gestão de Convênios e Contratos Externos (DCGCE/SEPLAG-MG)**. Construído em Python + Django sobre uma pipeline de dados no padrão **Lakehouse** (Bronze → Silver → Gold).

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Stack Tecnológica](#2-stack-tecnológica)
3. [Arquitetura de Dados](#3-arquitetura-de-dados)
4. [Estrutura de Pastas](#4-estrutura-de-pastas)
5. [Configuração e Instalação](#5-configuração-e-instalação)
6. [Fontes de Dados](#6-fontes-de-dados)
7. [Comandos de Gerência](#7-comandos-de-gerência)
8. [Pipeline de Dados — Passo a Passo](#8-pipeline-de-dados--passo-a-passo)
9. [Camada de Relacionamento (migração do QlikView)](#9-camada-de-relacionamento-migração-do-qlikview)
10. [Modelos Django](#10-modelos-django)
11. [Dados de Referência Versionados](#11-dados-de-referência-versionados)
12. [Testes](#12-testes)
13. [Painel Web](#13-painel-web)
14. [Roadmap](#14-roadmap)

---

## 1. Visão Geral

O painel consolida dados de convênios estaduais provenientes de múltiplos sistemas:

| Sistema | Papel |
|---|---|
| **SIGCON-MG** | Sistema de Gestão de Convênios de MG — fonte principal (exportações BO/PRODEMGE) |
| **Transferegov / SICONV** | Portal federal de dados abertos — enriquece campos com dados da União |
| **SIAFI / SIAFI2** | Sistema de administração financeira — resolve o número SIAFI atual de cada UO |
| **SIAD / SEI** | Execução orçamentária e processos administrativos (previsto) |

O objetivo técnico é migrar o "miolo" do script QlikView legado para Python puro, permitindo versionamento, testes e evolução independente de licença proprietária.

---

## 2. Stack Tecnológica

| Componente | Versão |
|---|---|
| Python | 3.13+ |
| Django | 6.0.6 |
| pandas | 3.0.3 |
| pyarrow | 24.0.0 |
| django-environ | 0.13.0 |
| openpyxl | 3.1.5 |
| pytest + pytest-django | 9.0.3 / 4.12.0 |

Banco de dados: **SQLite** (dev) · **PostgreSQL** (produção, via `DATABASE_URL`)  
Cache: memória local (dev) · **Redis** (produção, via `CACHE_URL`)

---

## 3. Arquitetura de Dados

```
Fontes externas
(SIGCON-MG · Transferegov · SIAFI · SIAD · SEI · Planilhas)
        │
        ▼  python manage.py rodar_ingestao <fonte>
┌─────────────────────────────────────────────────────┐
│  BRONZE  —  data/bronze/<fonte>/<fonte>_<ts>.csv    │
│  Cópia fiel dos dados originais. Append-only.       │
│  Preserva erros, duplicatas, colunas mal nomeadas.  │
└──────────────────────┬──────────────────────────────┘
                       │  python manage.py rodar_silver <fonte>
                       ▼
┌─────────────────────────────────────────────────────┐
│  SILVER  —  data/silver/<fonte>.parquet             │
│  Dados limpos, tipados (datas, floats, strings).    │
│  Nomes de colunas em snake_case. Sobrescrito.       │
└──────────────────────┬──────────────────────────────┘
                       │  core/gold/relacionamento.py
                       │  (R1–R4: migração do QlikView)
                       ▼
┌─────────────────────────────────────────────────────┐
│  GOLD  —  data/gold/convenios_integrado.parquet     │
│  Tabela integrada: SIGCON ↔ SICONV ↔ SIAFI.        │
│  Campos G_ (coalesce) e A_ (projeção SIAFI atual).  │
└──────────────────────┬──────────────────────────────┘
                       │  python manage.py carregar_relacionamento
                       ▼
┌─────────────────────────────────────────────────────┐
│  BANCO DE DADOS  —  SQLite / PostgreSQL             │
│  Model ConvenioIntegrado (todos os campos G_/A_)    │
│  Models auxiliares: Convenio, PlanoTrabalho, etc.   │
└──────────────────────┬──────────────────────────────┘
                       │  apps/dashboard/services.py (cache)
                       ▼
               Django Views + Templates
```

O diretório `data/` é inteiramente **gitignored** — apenas código e documentação são versionados.

---

## 4. Estrutura de Pastas

```
painel_de_convenios/
│
├── config/                        # Projeto Django
│   └── settings/
│       ├── base.py                # Configurações compartilhadas
│       ├── dev.py                 # SQLite, DEBUG=True
│       └── prod.py                # PostgreSQL, Redis
│
├── apps/
│   ├── convenios/                 # App de dados de convênios
│   │   ├── models.py              # Todos os models ORM
│   │   ├── loader.py              # Funções de full-refresh por model
│   │   ├── admin.py               # Registro no Django Admin
│   │   ├── migrations/            # Histórico de migrations
│   │   └── management/commands/
│   │       ├── carregar_convenios.py       # Carrega Convenio (Silver)
│   │       ├── carregar_cronograma.py      # Carrega CronogramaDesembolso
│   │       ├── carregar_fonte.py           # Carrega qualquer fonte avulsa
│   │       ├── carregar_relacionamento.py  # Carrega ConvenioIntegrado (Gold)
│   │       ├── carregar_silver.py          # Carga Silver legada
│   │       └── rodar_transformacao.py      # Transforma Silver legada
│   │
│   └── dashboard/                 # App do painel web
│       ├── views.py               # Views principais
│       ├── services.py            # Camada de serviços com cache
│       ├── urls.py
│       ├── templatetags/
│       │   └── painel_filters.py  # Filtros de template customizados
│       └── management/commands/
│           ├── gerar_schemas.py   # Gera YAML de schema para nova fonte
│           ├── rodar_ingestao.py  # Bronze: ingestão de qualquer fonte
│           └── rodar_silver.py    # Silver: transformação de qualquer fonte
│
├── core/
│   ├── ingestion/
│   │   ├── sources.py             # Registro declarativo de fontes (FONTES dict)
│   │   ├── readers.py             # Leitores CSV/Excel → DataFrame (tudo como str)
│   │   ├── bronze.py              # Grava Bronze com timestamp
│   │   └── baixar_siconv.py       # Download automático dos dados Transferegov
│   │
│   ├── transform/
│   │   ├── silver.py              # Pipeline Silver genérico (YAML-driven)
│   │   ├── chaves.py              # Chaves SIAFI_UO, filtro UO, de-paras, correções
│   │   ├── referencias.py         # Carrega core/referencia/*.csv como dicts
│   │   ├── gerar_schemas.py       # Classificador heurístico de colunas
│   │   ├── convenios.py           # Transformação Silver legada (dcgce_convenios)
│   │   ├── utils.py               # normalizar_coluna() snake_case
│   │   └── schemas/               # YAMLs de schema por fonte (gerados + revisados)
│   │       ├── dcgce_convenio.yaml
│   │       ├── chaves_convenio.yaml
│   │       ├── siafi2.yaml
│   │       └── ...
│   │
│   ├── gold/
│   │   ├── convenios.py           # Agregações KPI para o dashboard
│   │   └── relacionamento.py      # Pipeline G_/A_: migração do miolo QlikView
│   │
│   └── referencia/                # Tabelas de de-para versionadas no Git
│       ├── situacoes_padronizadas.csv
│       ├── tipos_siafi.csv
│       ├── uo_nomes.csv
│       ├── uo_siglas.csv
│       ├── uo_descricoes.csv
│       ├── concedentes_padronizados.csv
│       └── correcoes.csv
│
├── data/                          # GITIGNORED — dados locais
│   ├── raw/
│   │   ├── sigcon/                # Exportações SIGCON-MG (xlsx/csv)
│   │   ├── execucao/              # Exportações QlikView de despesas
│   │   └── uniao/                 # Dados abertos Transferegov
│   ├── bronze/                    # CSVs com timestamp (append-only)
│   ├── silver/                    # Parquets tipados (sobrescritos)
│   └── gold/                      # Parquets analíticos
│
├── static/                        # CSS, JS, imagens
├── templates/                     # Templates HTML Django
├── tests/                         # Testes automatizados
│   ├── test_r2.py                 # 28 testes: SIAFI_UO, de-paras, correções
│   ├── test_r3.py                 # 31 testes: G_, A_, coalesce, fan-out
│   └── test_r4.py                 # 2 testes: carga idempotente, leitura ORM
│
├── docs/
│   ├── ARQUITETURA.md             # Documentação técnica detalhada
│   ├── AUDITORIA_RELACIONAMENTO.md
│   └── CONFERENCIA_R3.md
│
├── .env.example
├── pytest.ini
├── requirements.txt
└── CLAUDE.md                      # Instruções para o assistente de IA
```

---

## 5. Configuração e Instalação

### Pré-requisitos

- Python 3.13+
- Git

### Passos

```powershell
# 1. Clone e entre na pasta
git clone <url-do-repositorio>
cd painel_de_convenios

# 2. Crie e ative o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate          # Linux/Mac

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o ambiente
copy .env.example .env
# Edite .env e defina DJANGO_SECRET_KEY

# 5. Aplique as migrations
python manage.py migrate

# 6. (Opcional) Crie superusuário para o Admin
python manage.py createsuperuser

# 7. Suba o servidor de desenvolvimento
python manage.py runserver
```

Acesse `http://127.0.0.1:8000` no navegador.

### Variável obrigatória em todos os terminais

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.dev"
```

> O arquivo `pytest.ini` já define isso para os testes.

---

## 6. Fontes de Dados

### SIGCON-MG (`data/raw/sigcon/`)

Exportações Business Objects / PRODEMGE. Todas em formato Excel (`.xlsx`, `header=1`).

| Fonte | Arquivo | Conteúdo |
|---|---|---|
| `dcgce_convenio` | `dcgce_convenio.xlsx` | Chave SIAFI+UO, situação, datas, valores |
| `dcgce_geral` | `dcgce_Geral.xlsx` | Data publicação/assinatura, código plano de trabalho |
| `dcgce_plano_trabalho` | `dcgce_plano.trabalho.xlsx` | Título, objeto, CNPJ concedente/proponente |
| `dcgce_cronograma_desembolso` | `dcgce_Cronograma_desembolso.xlsx` | Cronograma mensal de desembolso |
| `dcgce_plano_aplicacao` | `dcgce_plano_aplicacao.xlsx` | Classificação orçamentária |
| `dcgce_termo_aditivo` | `dcgce_termo.aditivo.xlsx` | Termos aditivos com datas e valores |
| `dcgce_prorrogacao_oficio` | `dcgce_prorrogacao_oficio.xlsx` | Prorrogações de ofício |
| `dcgce_declaracao_contrapartida` | `dcgce_declaracao_contrapartida.xlsx` | Declarações de contrapartida |
| `dcgce_esfera` | `dcgce_esfera.xlsx` | CNPJ concedente → esfera (Federal/Estadual) |
| `dcgce_sigcon_nt_emenda` | `dcgce_sigcon_nt_emenda.xlsx` | Notas técnicas de emendas parlamentares |
| `chaves_convenio` | `Chaves_convenio.csv` | **Ponte SIGCON↔SICONV**: SIAFI_UO + código SICONV |

#### Pontes ETL (carimbo de chaves)

| Fonte | Conteúdo |
|---|---|
| `dcgce_codigo_convenio` | `convenio_codigo_sequencial` → SIAFI + UO |
| `dcgce_codigo_ta` | `termo_aditivo_codigo_sequencial` → SIAFI + UO |
| `dcgce_codigo_dec_contrap` | `declaracao_contrapartida_codigo` → SIAFI + UO |

### Transferegov / SICONV (`data/raw/uniao/`)

| Fonte | Arquivo | Conteúdo |
|---|---|---|
| `siconv_convenio` | `siconv_convenio.csv` | Dados abertos de convênios federais |

### De-paras e Dimensões

| Fonte | Arquivo | Conteúdo |
|---|---|---|
| `siafi2` | `SIAFI2.csv` | De-para: (SIAFI2, UO2) → SIAFI atual + UO atual |
| `parlamentares` | `De para nomes parlamentares.xlsx` | Normalização de nomes de parlamentares |

---

## 7. Comandos de Gerência

### Ingestão e Transformação

```powershell
# Ingestão Bronze: lê data/raw/<fonte> → grava data/bronze/<fonte>/<fonte>_<ts>.csv
python manage.py rodar_ingestao <nome_fonte>
# Exemplos:
python manage.py rodar_ingestao dcgce_convenio
python manage.py rodar_ingestao chaves_convenio
python manage.py rodar_ingestao siafi2
python manage.py rodar_ingestao siconv_convenio

# Transformação Silver: lê Bronze mais recente → grava data/silver/<fonte>.parquet
python manage.py rodar_silver <nome_fonte>
python manage.py rodar_silver dcgce_convenio
python manage.py rodar_silver chaves_convenio
python manage.py rodar_silver siafi2

# Geração de schema YAML para nova fonte (revisar antes de usar)
python manage.py gerar_schemas <nome_fonte>
python manage.py gerar_schemas --sobrescrever   # força regeneração
```

### Carga no Banco de Dados

```powershell
# Convênio consolidado (Silver → DB)
python manage.py carregar_convenios

# Tabela integrada Gold G_/A_ (Silver → Gold Parquet → DB)
python manage.py carregar_relacionamento
python manage.py carregar_relacionamento --construir      # força rebuild do Gold
python manage.py carregar_relacionamento --gold <caminho> # Parquet customizado

# Cronograma de desembolso com SIAFI+UO carimbados
python manage.py carregar_cronograma
```

### Referência Completa de Fontes Registradas

```powershell
# Ver todas as fontes disponíveis para rodar_ingestao e rodar_silver:
# dcgce_convenio, dcgce_geral, dcgce_plano_trabalho, dcgce_cronograma_desembolso
# dcgce_plano_aplicacao, dcgce_termo_aditivo, dcgce_prorrogacao_oficio
# dcgce_declaracao_contrapartida, dcgce_esfera, dcgce_sigcon_nt_emenda
# dcgce_codigo_convenio, dcgce_codigo_ta, dcgce_codigo_dec_contrap
# chaves_convenio, siafi2, siconv_convenio, parlamentares
# qv_despesa_ano_2019, qv_despesa_ano_2020
```

---

## 8. Pipeline de Dados — Passo a Passo

### Pipeline principal (convênio integrado)

```powershell
# --- Silver: todas as fontes necessárias ---
python manage.py rodar_silver chaves_convenio
python manage.py rodar_silver siafi2
python manage.py rodar_silver dcgce_convenio
python manage.py rodar_silver dcgce_codigo_convenio
python manage.py rodar_silver dcgce_geral
python manage.py rodar_silver dcgce_plano_trabalho
python manage.py rodar_silver dcgce_esfera

# (opcional) SICONV
python manage.py rodar_silver siconv_convenio

# --- Gold + carga no banco ---
python manage.py carregar_relacionamento
```

### Pipeline auxiliar (Convênio consolidado do painel legado)

```powershell
python manage.py rodar_silver dcgce_convenio
python manage.py rodar_silver dcgce_codigo_convenio
python manage.py rodar_silver dcgce_geral
python manage.py rodar_silver dcgce_plano_trabalho
python manage.py rodar_silver dcgce_esfera
python manage.py carregar_convenios
```

---

## 9. Camada de Relacionamento (migração do QlikView)

A camada de relacionamento equivale ao "miolo" do script QlikView legado — blocos `sigcon_chaves1`, campos `G_`, campos `A_` e filtros de UO. Implementada em `core/gold/relacionamento.py`.

### Chave SIAFI_UO

```python
SIAFI_UO = str(convenio_numero_sequencial_siafi) + str(unidade_orcamentaria_codigo)
# Sem separador. Zeros à esquerda preservados. Nunca converter para int.
# Exemplo: "9309074" + "1261" = "93090741261"
```

### Filtro de UOs não-operacionais

```python
# 11 UOs excluídas (equivalente ao Where not match(UO, ...) do QlikView):
UOS_EXCLUIR = frozenset({"5131","9801","4611","4441","4451","2361","4121","1041","1031","1051","4031"})
```

### Campos G_ — coalesce(SICONV, SIGCON)

21 campos onde SICONV tem precedência sobre SIGCON, com fallback gracioso quando SICONV não está disponível:

| Campo | Descrição |
|---|---|
| `g_situacao_convenio` | Situação atual |
| `g_objeto_convenio` | Descrição do objeto |
| `g_proponente` / `g_concedente` | Partes do convênio |
| `g_valor_concedente` / `g_valor_proponente` / `g_valor_global` | Valores em R$ |
| `g_dia_assinatura` / `g_inicio_vigencia` / `g_fim_vigencia` | Datas |
| `g_instrumento` | Tipo (padrão: `"Convênio de Entrada"`) |
| `g_esfera` | Esfera do concedente (padrão: `"Federal"`) |
| `g_vigencia` | `"Vigente"` ou `"Vencido"` (calculado) |
| `g_situacao_convenio_categorizado` | Situação após de-para padronizado |
| `g_ano_convenio` | Ano para agrupamentos |
| + derivados de período, valor aditado, UO, concedente padronizado | |

### Campos A_ — projeção sobre SIAFI atual

Mirror dos campos G_ projetados via auto-join: `siafi_uo_atual = siafi_uo`. Útil para dashboards que não devem duplicar convênios que mudaram de número SIAFI.

### API Python

```python
from pathlib import Path
import pandas as pd
from core.gold.relacionamento import construir_tabela_integrada, gravar_tabela_integrada

DATA = Path("data")  # ou settings.DATA_DIR

tabela = construir_tabela_integrada(
    df_chaves   = pd.read_parquet(DATA / "silver/chaves_convenio.parquet"),
    df_siafi2   = pd.read_parquet(DATA / "silver/siafi2.parquet"),
    df_sigcon_convenio       = pd.read_parquet(DATA / "silver/dcgce_convenio.parquet"),
    df_sigcon_codigo_convenio= pd.read_parquet(DATA / "silver/dcgce_codigo_convenio.parquet"),
    df_sigcon_geral          = pd.read_parquet(DATA / "silver/dcgce_geral.parquet"),
    df_sigcon_plano          = pd.read_parquet(DATA / "silver/dcgce_plano_trabalho.parquet"),
    df_sigcon_esfera         = pd.read_parquet(DATA / "silver/dcgce_esfera.parquet"),
    # df_siconv = pd.read_parquet(DATA / "silver/siconv_convenio.parquet"),  # opcional
)

gravar_tabela_integrada(tabela)   # → data/gold/convenios_integrado.parquet
print(tabela.shape)               # (n_convenios, n_colunas)
```

### Etapas de implementação (R1–R4)

| Etapa | Status | O que foi feito |
|---|---|---|
| **R1** | ✅ | Estrutura, `UOS_EXCLUIR`, de-paras, filtro UO, `correcoes.csv` |
| **R2** | ✅ | `montar_siafi_uo()`, `resolver_siafi_atual()` via SIAFI2, `aplicar_correcoes()`, 28 testes |
| **R3** | ✅ | `aplicar_campos_g()` (21 coalesces + derivados), `aplicar_campos_a()`, `construir_tabela_integrada()`, 31 testes |
| **R4** | ✅ | Model `ConvenioIntegrado`, migration, `carregar_tabela_integrada()`, command `carregar_relacionamento`, admin Django, 2 testes DB |

---

## 10. Modelos Django

Todos em `apps/convenios/models.py`.

### `ConvenioIntegrado` — tabela Gold integrada (principal)

Chave natural: `siafi_uo` (unique). Campos G_/A_ completos.

| Grupo | Campos |
|---|---|
| Chaves | `siafi_uo`, `siafi_uo_atual`, `convenio_numero_sequencial_siafi`, `unidade_orcamentaria_codigo`, `siafiatual`, `uo_atual`, `codigo_siconv` |
| De-paras | `instrumento_chaves`, `situacao`, `situacao_std`, `uo_nome_std`, `uo_sigla_std`, `uo_descricao_std` |
| G_ datas | `g_dia_assinatura`, `g_inicio_vigencia`, `g_fim_vigencia`, `g_fim_vigencia_inicial` |
| G_ anos | `g_ano_assinatura`, `g_ano_inicio_vigencia`, `g_ano_convenio` |
| G_ texto | `g_situacao_convenio`, `g_situacao_convenio_categorizado`, `g_vigencia`, `g_instrumento`, `g_esfera`, `g_proponente`, `g_concedente`, `g_objeto_convenio`, e padronizados (`_pad`, `_pad_siglas`) |
| G_ valores | `g_valor_concedente`, `g_valor_proponente`, `g_valor_global` |
| G_ flags | `g_periodo_nao_aditado`, `g_valor_nao_aditado`, `limpeza_g` |
| A_ | Todos os campos acima espelhados com prefixo `a_` |

Carga: `python manage.py carregar_relacionamento`

### `Convenio` — convênio consolidado (piloto Silver)

Chave: `convenio_codigo`. Campos de situação, datas, valores e dados do plano de trabalho.

Carga: `python manage.py carregar_convenios`

### Modelos auxiliares

| Model | Fonte Silver | Conteúdo |
|---|---|---|
| `ConvenioGeral` | `dcgce_geral` | Dados gerais e datas do SIGCON |
| `PlanoTrabalho` | `dcgce_plano_trabalho` | Título, objeto, CNPJ, instrumento |
| `CronogramaDesembolso` | `dcgce_cronograma_desembolso` | Desembolsos mensais com SIAFI+UO |
| `PlanoAplicacao` | `dcgce_plano_aplicacao` | Classificação orçamentária |
| `TermoAditivo` | `dcgce_termo_aditivo` | Termos aditivos |
| `ProrrogacaoOficio` | `dcgce_prorrogacao_oficio` | Prorrogações |
| `DeclaracaoContrapartida` | `dcgce_declaracao_contrapartida` | Declarações de contrapartida |
| `NtEmenda` | `dcgce_sigcon_nt_emenda` | Notas técnicas de emendas |
| `Esfera` | `dcgce_esfera` | CNPJ → esfera (dimensão) |
| `CodigoConvenio` | `dcgce_codigo_convenio` | Ponte código sequencial ↔ SIAFI+UO |
| `CodigoPlanoTrabalho` | `dcgce_codigo_plano_de_trabalho` | Ponte plano ↔ SIAFI+UO |
| `CodigoTermoAditivo` | `dcgce_codigo_ta` | Ponte TA ↔ SIAFI+UO |
| `CodigoDeclaracaoContrapartida` | `dcgce_codigo_dec_contrap` | Ponte declaração ↔ SIAFI+UO |

---

## 11. Dados de Referência Versionados

Arquivos em `core/referencia/` — **fazem parte do repositório** (regras de negócio).

| Arquivo | Conteúdo | Equivalente QlikView |
|---|---|---|
| `situacoes_padronizadas.csv` | 19 mapeamentos situação → rótulo padronizado | `Mapa2` |
| `tipos_siafi.csv` | `11 → Acordo/Ajuste`, `15 → Transferências Especiais` | `Map_Tipo_SIAFI` |
| `uo_nomes.csv` | ~120 entradas: código UO → `"código - NOME"` | `MapaG_UO` |
| `uo_siglas.csv` | ~90 entradas: nome UO → sigla | `Mapa5` |
| `uo_descricoes.csv` | ~90 entradas: nome UO → `"nome - sigla"` | `Mapa4` |
| `concedentes_padronizados.csv` | ~470 entradas: normalização de nomes de concedentes | `Mapa3` |
| `correcoes.csv` | 14 correções hard-coded de dados incorretos no SIGCON | linhas 1601–1318 do QlikView |

---

## 12. Testes

```powershell
# Rodar todos os testes do projeto (exceto test_gold_convenios.py com import legado)
python -m pytest tests/test_r2.py tests/test_r3.py tests/test_r4.py -v
```

| Arquivo | Testes | Cobertura |
|---|---|---|
| `test_r2.py` | 28 | `montar_siafi_uo`, `resolver_siafi_atual`, `aplicar_correcoes`, `filtrar_uo`, `aplicar_deparas` |
| `test_r3.py` | 31 | `_coalesce`, campos G_ (situação, valor, instrumento, esfera, vigência, proponente, limpeza_g), anti-fan-out, campos A_ |
| `test_r4.py` | 2 | Carga idempotente (2× sem duplicatas), leitura básica do ORM |

**Total: 61 testes, todos passando.** Nenhum teste toca arquivos em disco — usam DataFrames em memória (R2/R3) ou Parquet temporário (R4).

---

## 13. Painel Web

| Rota | Descrição |
|---|---|
| `/` | Home — visão geral e navegação |
| `/painel/` | Painel principal com KPIs, gráficos e tabela de convênios |
| `/admin/` | Django Admin — navegação direta nos dados de todos os models |

O painel usa tema escuro, Chart.js para gráficos e filtro por ano na URL (`?ano=2024`).

---

## 14. Roadmap

| Fase | Status | O que faz |
|---|---|---|
| Fase 1 — Estrutura | ✅ | Repositório, `.gitignore`, `.env.example` |
| Fase 2 — Setup Django | ✅ | `config/settings/`, `django-environ`, app `dashboard` |
| Fase 3 — Bronze | ✅ | `sources.py`, `readers.py`, `bronze.py`, `rodar_ingestao` |
| Fase 4 — Silver e Models | ✅ | `silver.py` genérico, schemas YAML, `Convenio` model, migrations |
| Fase 5 — Gold e Serviços | ✅ | `core/gold/convenios.py`, `services.py` com cache, KPIs |
| Fase 6 — Frontend | ✅ | Painel com tema dark, Chart.js, filtro por ano |
| Fase 6b — Relacionamento R1–R4 | ✅ | Migração do miolo QlikView: SIAFI_UO, G_/A_, `ConvenioIntegrado` no Django |
| Fase 6c — Demais fontes | 🔲 | Transferegov completo, SIAFI execução, SIAD, SEI |
| Fase 7 — Auth e deploy | 🔲 | Login LDAP/SSO SEPLAG, PostgreSQL, Redis, CI/CD |

---

## Contato

DCGCE / SEPLAG-MG — Diretoria Central de Gestão de Convênios e Contratos Externos.
