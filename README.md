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
9. [Camada de Relacionamento (legado QlikView)](#9-camada-de-relacionamento-migração-do-qlikview)
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
(SIGCON-MG · GRP · TransfereGov · Execução estadual · planilhas internas)
        │
        ▼  python manage.py rodar_ingestao <fonte>
┌─────────────────────────────────────────────────────┐
│  BRONZE  —  data/bronze/<fonte>/<fonte>_<ts>.csv    │
│  Cópia fiel dos dados originais. Append-only.       │
└──────────────────────┬──────────────────────────────┘
                       │  python manage.py rodar_silver <fonte>
                       ▼
┌─────────────────────────────────────────────────────┐
│  SILVER  —  data/silver/<fonte>.parquet             │
│  Dados tipados, colunas em snake_case. Sobrescrito. │
│  Linha problemática é marcada, nunca excluída.      │
└──────────────────────┬──────────────────────────────┘
                       │  python manage.py carregar_<app>
                       ▼
┌─────────────────────────────────────────────────────┐
│  BANCO (PostgreSQL, schema public)                  │
│  Uma tabela por fonte: grp_*, sigcon_*, ...         │
│  Sem ForeignKey entre tabelas de dados.             │
└──────────────────────┬──────────────────────────────┘
                       │  views SQL em apps/<app>/sql/gold/
                       ▼
┌─────────────────────────────────────────────────────┐
│  GOLD  —  schema gold (views, models managed=False) │
│  Ligações entre tabelas, agregação 1:N em CTE,      │
│  recorte por regra de negócio.                      │
└──────────────────────┬──────────────────────────────┘
                       ▼
               Django Views + Templates
```

Regras que não mudam: a fonte nunca é alterada (correção vai para curadoria, problema para
quarentena); códigos (`nr_`, `cd_`, CNPJ, UO) são texto; tabela 1:N é agregada antes de qualquer
junção (anti fan-out). Detalhes em `docs/ARQUITETURA.md`.

O diretório `data/` é inteiramente **gitignored** — apenas código e documentação são versionados.

---

## 4. Estrutura de Pastas

```
painel_de_convenios/
│
├── config/                        # Projeto Django (settings/base, dev, prod; urls)
│
├── apps/
│   ├── grp/                       # ⭐ App de referência (22 tabelas grp_*)
│   │   ├── models.py              # Tabelas e models gold (managed=False)
│   │   ├── loader.py              # Loaders por fonte (_LOADERS_GRP, FONTES_GRP)
│   │   ├── views/                 # Telas (_filtros.py)
│   │   ├── validacao/catalogo.py  # Testes de qualidade do app
│   │   ├── sql/gold/              # Views do schema gold
│   │   └── management/commands/   # carregar_grp, validar_grp, aplicar_gold, pipeline_grp
│   ├── sigcon/                    # 15 tabelas sigcon_* + 4 views gold
│   │   ├── models.py, loader.py, services.py, contrapartida.py
│   │   ├── validacao/             # catalogo.py + limites.py (exceções conhecidas)
│   │   ├── sql/gold/              # vw_plano_trabalho, plano_aplicacao, cronograma, termo_aditivo
│   │   └── management/commands/   # carregar_sigcon, validar_sigcon
│   ├── uniao/                     # Consultas TransfereGov
│   ├── execucao/                  # Execução estadual (inventário na S2)
│   └── dashboard/                 # Casca do painel: layout, menu lateral, início
│
├── core/                          # App Django sem models: tudo que é global
│   ├── management/commands/       # rodar_ingestao, rodar_silver, rodar_pipeline, gerar_schemas
│   ├── ingestion/sources.py       # Registro de fontes (FonteDados)
│   ├── transform/schemas/         # Um YAML por fonte
│   ├── carga/                     # carregar_tabela_generica, ComandoCarga
│   ├── validacao/                 # Construtores de teste, ComandoValidacao
│   ├── web/                       # formatar_celula, exportação CSV/XLSX, paginação
│   ├── templatetags/              # painel_filters
│   ├── sql/000_schema_gold.sql    # Cria o schema gold
│   ├── gold/relacionamento.py     # Legado do QlikView (G_/A_); ver seção 9
│   └── referencia/                # De-paras versionados (CSV)
│
├── data/                          # GITIGNORED: raw, bronze, silver
├── static/  templates/
├── tests/                         # pytest
├── docs/                          # ARQUITETURA, DECISOES, qualidade_dados, TRILHA_PAINEL
├── .env.example  pytest.ini  requirements.txt
└── CLAUDE.md                      # Instruções para o assistente de IA
```

Dependências: `core` nunca importa `apps.*`; um app nunca importa outro app; `apps/dashboard`
pode ler dos demais; o Django nunca importa nada de `etl/`.

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

### Carga, validação e gold

```powershell
# Carga (apaga e recarrega as tabelas do app). Um comando por app, nunca por tabela
python manage.py carregar_grp
python manage.py carregar_sigcon

# Validação de qualidade (grava em dq_resultado_validacao*); ERRO bloqueia, ALERTA só registra
python manage.py validar_grp
python manage.py validar_sigcon

# Pipeline do GRP: carga + validação com portão de qualidade
python manage.py pipeline_grp

# Pipeline completo de uma fonte: extração/bronze -> silver -> carga
python manage.py rodar_pipeline

# Views gold do GRP (recria o schema gold a partir dos .sql)
python manage.py aplicar_gold
```

As views gold do SIGCON (`apps/sigcon/sql/gold/`) ainda não têm comando: aplique cada arquivo
com `CREATE OR REPLACE VIEW` no banco. Cada arquivo termina com um bloco de validação (só `SELECT`:
grão, fan-out, reconciliação de valores) com o resultado esperado em comentário.

### Fontes registradas

O nome da fonte é idêntico em 4 lugares: chave de `core/ingestion/sources.py`, nome do YAML em
`core/transform/schemas/`, nome do parquet e string do `partial` no loader. Confira sempre no
`sources.py`: as fontes SIGCON usam o prefixo `dcgce_`; as do GRP **não** (ex.: `grp_instrumento`).

```powershell
python manage.py rodar_ingestao grp_instrumento
python manage.py rodar_silver grp_instrumento
python manage.py rodar_ingestao dcgce_convenio
python manage.py rodar_silver dcgce_convenio
```

---

## 8. Pipeline de Dados — Passo a Passo

```powershell
# 1. Bronze e Silver, por fonte (nomes em core/ingestion/sources.py)
python manage.py rodar_ingestao <fonte>
python manage.py rodar_silver <fonte>

# 2. Carga no banco (apaga e recarrega as tabelas do app)
python manage.py carregar_sigcon        # ou carregar_grp

# 3. Validação de qualidade
python manage.py validar_sigcon         # ou validar_grp

# 4. Views gold (SIGCON: aplicar os .sql de apps/sigcon/sql/gold/; GRP: aplicar_gold)
```

Fonte nova: `gerar_schemas <fonte>` cria o YAML (revisar antes de usar), depois copie o padrão do
GRP (model, loader, comando de carga, catálogo de validação). O passo a passo está em
`docs/ARQUITETURA.md` §5 e §6.

---

## 9. Camada de Relacionamento (legado QlikView)

> **Legado.** Esta camada (`core/gold/relacionamento.py`) vem do script QlikView e não é usada
> pelas telas atuais, que leem as views do schema `gold`. Ficou no `core` porque só os testes
> `tests/test_r2.py` e `tests/test_r3.py` a usam; aposentar é decisão pendente (`docs/DECISOES.md`).

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
| **R4** | ✅ | Model `ConvenioIntegrado`, migration, `carregar_tabela_integrada()`, command `carregar_relacionamento` (removido; camada legada), admin Django, 2 testes DB |

---

## 10. Modelos Django

Cada app tem seus models; nenhuma tabela de dados tem `ForeignKey`: as ligações ficam na gold, em SQL.

| App | Models | Observação |
|---|---|---|
| `apps/grp` | `Grp*` (22 tabelas), `GrpGold*` (5 views), `ResultadoValidacao` | Referência: copie daqui. Ex.: `GrpInstrumento` (1:1), `GrpRecursoConcedente` (1:N), `GrpGoldInstrumento` |
| `apps/sigcon` | `Sigcon*` (15 tabelas), `SigconHistoricoCarga`, `ResultadoValidacao`, `GoldSigcon*` (4 views) | Tabelas das consultas `dcgce_*`; `sigcon_tabela_uo` entra na S3 |

Views gold do SIGCON (grão: convênio × ...; id = `ROW_NUMBER()`):

| View | Grão |
|---|---|
| `gold.vw_plano_trabalho_sigcon` | convênio × plano de trabalho (ponte das demais) |
| `gold.vw_plano_aplicacao_sigcon` | convênio × plano × classificação orçamentária × ano |
| `gold.vw_cronograma_desembolso_sigcon` | convênio × plano × ano × mês |
| `gold.vw_termo_aditivo_sigcon` | convênio × termo aditivo |

Plano compartilhado por vários SIAFI (erro de origem, ex.: 7964) repete a linha em cada SIAFI:
some valores sempre por `siafi_uo`, nunca por `cd_plano_trabalho`.

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
python -m pytest            # o pytest.ini já define DJANGO_SETTINGS_MODULE
python -m pytest tests/test_validar_grp.py -v
```

Os testes ficam em `tests/` (carga, preservação de linhas, validação, gold, comandos registrados)
e nos `tests/` de cada app. `test_r2.py` e `test_r3.py` cobrem a camada legada de relacionamento
(seção 9). Os testes de dados usam DataFrames em memória ou Parquet temporário.

---

## 13. Painel Web

| Rota | Descrição |
|---|---|
| `/` | Aba mestre do SIGCON, que também é a página inicial |
| `/plano_aplicacao/`, `/cronograma/`, `/prorrogacao/`, `/termo_aditivo/`, `/unidades_executoras/` | Sub-abas do SIGCON (cada uma com `export.csv` e `export.xlsx`) |
| `/indicadores/`, `/graficos/`, `/monitoramento/`, `/relatorio/`, `/alertas/`, `/emendas/` | App `dashboard` |
| `/grp/` | GRP: instrumentos, cronograma, plano de aplicação, emenda, regiões atendidas, prestação de contas |
| `/uniao/` | Consultas TransfereGov |
| `/execucao/` | Execução estadual |
| `/admin/` | Django Admin |

Telas em Django puro (views + templates), sem DRF, React ou Celery. Os filtros e a exportação
vêm de `core/web/`.

---

## 14. Roadmap

Rumo à **v1.0 em 31/12/2026** (SIGCON + Execução Estadual + GRP). Estado por sprint em `CLAUDE.md` §8
e `docs/TRILHA_PAINEL.md`.

| Etapa | Status | O que faz |
|---|---|---|
| Bronze e Silver genéricos | ✅ | `sources.py`, YAMLs de schema, `rodar_ingestao`, `rodar_silver` |
| GRP | ✅ | 22 tabelas, `gold.vw_instrumento`; golds restantes na S4-03 |
| SIGCON | 🔶 | 15 tabelas carregadas, 4 views gold; validação em andamento (S1-07) |
| Reorganização do `core` | ✅ | Carga e validação genéricas, `painel` → `dashboard` (`docs/DECISOES.md`) |
| Componente de consulta e aba Convênios | 🔲 | S1-10 e S1-11 |
| Execução Estadual | 🔲 | Inventário e modelo de extração na S2 |
| Auth e deploy | 🔲 | Login, PostgreSQL de produção, agendamento (ARQUITETURA §13–§15) |

---

## 15. Qualidade de dados

O GRP possui um portão de qualidade automatizado que valida a integridade dos dados após cada carga.

### Como rodar

```powershell
# Validação isolada (precisa de banco com dados carregados)
python manage.py validar_grp

# Pipeline completo: carga + validação com portão
python manage.py pipeline_grp

# Testes unitários (sem banco, sem data/)
python -m pytest tests/test_silver_grp.py tests/test_catalogo_validacao.py tests/test_generico.py tests/test_validar_grp.py tests/test_pipeline_grp.py -v
```

### Como ler o resultado

A saída do terminal mostra cada teste com status PASSOU/FALHOU. Para consultar a execução mais recente com falhas:

```sql
SELECT id_teste, tabela, qt_falhas, descricao
FROM dq_resultado_validacao
WHERE status = 'FALHOU'
ORDER BY execucao DESC, id_teste;
```

### Severidade

| Tipo | Comportamento |
|---|---|
| **ERRO** | Bloqueia o pipeline (`exit 1`). A gold não é atualizada. |
| **ALERTA** | Registra a divergência e segue. Não bloqueia. |

### O que fazer diante de uma falha

1. Classificar: erro da fonte (dado errado na origem), erro da nossa silver (transformação incorreta) ou regra do teste errada.
2. **Nunca alterar nem apagar dado de origem** — corrigir na transformação ou ajustar o teste.
3. Registrar a decisão em [`docs/qualidade_dados.md`](docs/qualidade_dados.md).

### Como acrescentar um teste novo

Edite `apps/grp/validacao/catalogo.py`. Adicione a entrada **no final do bloco** correspondente à família de testes. Um `id` nunca é reaproveitado para outra regra. IDs fixos são reservados para testes avulsos que não pertencem a nenhum gerador.

### Famílias de testes

| Família | Prefixo | O que valida |
|---|---|---|
| Volumetria | T-A | Contagem parquet = contagem banco |
| Schema | T-B | Tipos das colunas no banco (prefixo → tipo) |
| Grão | T-C | Unicidade da chave primária declarada |
| Completude | T-D | Campos obrigatórios preenchidos (nr_grp, cd_proposta) |
| Formato e domínio | T-E | CNPJ 14 dígitos, UF válida, mês 0–12, ano 1950–2050 |
| Integridade referencial | T-F | Chaves estrangeiras existem na tabela pai |
| Reconciliação | T-G | Somas e totais batem entre tabelas relacionadas |

Documentação detalhada: [`docs/qualidade_dados.md`](docs/qualidade_dados.md).

---

## Contato

DCGCE / SEPLAG-MG — Diretoria Central de Gestão de Convênios e Contratos Externos.
