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

> **Em construção** — esta seção será preenchida nas próximas fases do projeto.

Passos previstos:
1. Criar e ativar o ambiente virtual Python
2. Instalar dependências: `pip install -r requirements.txt`
3. Configurar variáveis de ambiente a partir de `.env.example`
4. Aplicar migrações Django: `python manage.py migrate`
5. Iniciar servidor de desenvolvimento: `python manage.py runserver`

---

## Roadmap

Veja [docs/ARQUITETURA.md](docs/ARQUITETURA.md) para o roadmap detalhado das fases.
