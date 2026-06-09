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

## 6. Roadmap

### Fase 1 — Estrutura inicial ✅
- Criação do repositório e estrutura de pastas
- `.gitignore`, `.env.example`, documentação base
- Primeiro commit

### Fase 2 — Setup Django ✅
- Projeto Django em `config/`, settings base/dev/prod
- `django-environ` para variáveis sensíveis
- App `dashboard` registrado e URL raiz funcionando

### Fase 3 — Pipeline Bronze ✅
- Registro declarativo de fontes em `sources.py`
- Leitor genérico `readers.py` (CSV → DataFrame, tudo como string)
- Ingestão Bronze com timestamp em `bronze.py`
- Management command `rodar_ingestao`
- Fixture de teste em `tests/fixtures/`

### Fase 4 — Pipeline Silver
- Limpeza e padronização (tipos, datas ISO-8601, CNPJ normalizado)
- Join com tabela de municípios (dimensão)
- Gravação em `data/silver/`

### Fase 5 — Pipeline Gold e Dashboard inicial
- Agregações por status, UF e ano
- View Django com tabela paginada e filtros básicos
- Gráfico de barras (convênios por status)

### Fase 6 — Demais fontes (SIGCON-MG, SIAFI, SIAD, SEI)
- Módulos de ingestão e transformação por fonte
- Consolidação Silver com todas as fontes
- Indicadores Gold completos

### Fase 7 — Autenticação, deploy e CI/CD
- Login LDAP/SSO SEPLAG
- Deploy em servidor interno
- Pipeline de atualização automática dos dados

### Fase 4 — Pipeline Silver
- Limpeza e padronização dos dados Transferegov
- Join com tabela de municípios (dimensão)
- Gravação em `data/silver/`

### Fase 5 — Pipeline Gold e Dashboard inicial
- Agregações por status, UF e ano
- View Django com tabela paginada e filtros básicos
- Gráfico de barras (convênios por status)

### Fase 6 — Demais fontes (SIGCON-MG, SIAFI, SIAD, SEI)
- Módulos de ingestão e transformação por fonte
- Consolidação Silver com todas as fontes
- Indicadores Gold completos

### Fase 7 — Autenticação, deploy e CI/CD
- Login LDAP/SSO SEPLAG
- Deploy em servidor interno
- Pipeline de atualização automática dos dados

---

## 7. Referências

- [Transferegov — Portal de Dados Abertos](https://portaldatransparencia.gov.br/download-de-dados/convenios)
- [Documentação Django](https://docs.djangoproject.com/)
- [Medallion Architecture (Databricks)](https://www.databricks.com/glossary/medallion-architecture)
