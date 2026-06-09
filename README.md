# Painel de Convênios — DCGCE / SEPLAG-MG

## Objetivo

Substituir gradualmente o painel QlikView de convênios da Diretoria Central de Gestão de Convênios e Contratos Externos (DCGCE/SEPLAG-MG), oferecendo uma solução moderna baseada em Python (ETL) e Django (visualização web), com dados organizados na arquitetura **Lakehouse Bronze / Silver / Gold**.

---

## Arquitetura de Dados

```
Fontes externas
(SIGCON-MG · Transferegov · SIAFI · SIAD · SEI · Planilhas)
        │
        ▼
┌──────────────┐
│    BRONZE    │  Dados brutos, sem transformação. Ingestão direta das fontes.
│  data/bronze │  Preservação fiel do original (CSV histórico + ano corrente).
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    SILVER    │  Dados limpos, tipados e padronizados. Deduplicação, join de
│  data/silver │  dimensões, normalização de campos-chave (CNPJ, datas, UF…).
└──────┬───────┘
       │
       ▼
┌──────────────┐
│     GOLD     │  Agregações e indicadores prontos para consumo. Tabelas
│  data/gold   │  analíticas que alimentam diretamente as views do Django.
└──────┬───────┘
       │
       ▼
 Django (apps/dashboard)
 Visualização web, filtros e exportações
```

---

## Estrutura de Pastas

```
painel_convenios/
├── config/             # Projeto Django: settings, urls, wsgi (fase futura)
├── apps/
│   └── dashboard/      # App Django principal do painel
├── core/
│   ├── ingestion/      # Camada Bronze: scripts de ingestão por fonte
│   ├── transform/      # Camada Silver: limpeza e padronização
│   └── gold/           # Camada Gold: agregações e indicadores
├── data/               # Arquivos CSV (NÃO versionado, exceto .gitkeep)
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── static/             # CSS, JS, imagens
├── templates/          # Templates HTML Django
├── tests/              # Testes automatizados
├── docs/               # Documentação técnica
├── .env.example        # Variáveis de ambiente (modelo sem valores reais)
├── .gitignore
└── README.md
```

---

## Como Rodar

### Pré-requisitos
- Python 3.13+
- Git

### Passos

```bash
# 1. Clone o repositório e entre na pasta
git clone <url-do-repositorio>
cd painel_de_convenios

# 2. Crie e ative o ambiente virtual
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# Linux/Mac
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
# Para desenvolvimento (inclui black, pytest):
pip install -r requirements-dev.txt

# 4. Configure as variáveis de ambiente
copy .env.example .env      # Windows
# cp .env.example .env      # Linux/Mac
# Edite o .env e defina ao menos DJANGO_SECRET_KEY

# 5. Aplique as migrações
python manage.py migrate

# 6. Carregue os dados de exemplo na pipeline
python manage.py rodar_ingestao convenios
python manage.py rodar_transformacao convenios
python manage.py carregar_silver

# 7. Crie um superusuário (opcional — acesso ao /admin/)
python manage.py createsuperuser

# 8. Inicie o servidor de desenvolvimento
python manage.py runserver
```

Acesse [http://127.0.0.1:8000](http://127.0.0.1:8000) no navegador.

### Navegacao do Painel

| Rota | Descricao |
|---|---|
| `/` | Painel principal — KPIs, graficos e tabelas |
| `/?ano=2024` | Filtra todos os indicadores pelo ano selecionado |
| `/admin/` | Django Admin — gerenciamento de dados |

---

## Roadmap

Veja [docs/ARQUITETURA.md](docs/ARQUITETURA.md) para o roadmap detalhado das fases.
