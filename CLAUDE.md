# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Internal web dashboard for DCGCE/SEPLAG-MG to replace a legacy QlikView panel. Built on a Python/Django Lakehouse pipeline (Bronze → Silver → Gold) that reads SIGCON-MG exports and other government data sources.

## Environment Setup

Copy `.env.example` to `.env` and fill in `DJANGO_SECRET_KEY`. The settings module for development is `config.settings.dev` (SQLite, DEBUG=True). Always set this environment variable:

```
DJANGO_SETTINGS_MODULE=config.settings.dev
```

Activate the virtual environment before running any command:
```
.venv\Scripts\activate   # Windows
```

## Common Commands

```bash
# Run dev server
python manage.py runserver

# Apply DB migrations
python manage.py migrate

# Raw -> Bronze, automated: extracts from Gmail + Transferegov (core/extract/)
# and ingests the Bronze of every mapped source in one shot.
python manage.py rodar_pipeline

# Raw -> Bronze, manual (sources with no extraction wired up yet — place the
# file in data/raw/<...> per sources.py first): chaves_convenio, siafi2,
# parlamentares, controle_sei, qv_despesa_ano_2019, qv_despesa_ano_2020
python manage.py rodar_ingestao <nome_fonte>

# Bronze -> Silver, per source (run for every source you need downstream)
python manage.py rodar_silver <nome_fonte>

# Silver -> DB (full refresh each)
python manage.py carregar_convenios              # main Convenio table (needs dcgce_convenio/geral/plano_trabalho/esfera/codigo_convenio silver)
python manage.py carregar_fonte <nome_fonte>      # auxiliary tables — see _LOADERS in carregar_fonte.py for the 13 valid keys
python manage.py carregar_cronograma
python manage.py carregar_unidades_executoras
python manage.py carregar_controle_sei
python manage.py carregar_relacionamento --construir   # Gold ConvenioIntegrado (needs chaves_convenio, siafi2, dcgce_convenio/codigo_convenio/geral/plano_trabalho/esfera silver)

# Generate YAML schema for a new source (then manually review the YAML before running rodar_silver)
python manage.py gerar_schemas <nome_fonte>
python manage.py gerar_schemas --sobrescrever       # force regeneration of existing YAMLs
```

`rodar_ingestao`, `rodar_silver`, `rodar_pipeline` and `gerar_schemas` live under `apps/dashboard/management/commands/`; the `carregar_*` loaders and `carregar_relacionamento` live under `apps/convenios/management/commands/`.

`rodar_transformacao` and `carregar_silver` (both in `apps/convenios/management/commands/`) are **legacy, do not use** — superseded by `rodar_silver` and `carregar_convenios` respectively. `rodar_transformacao` references a `"convenios"` source key that no longer exists in `FONTES`.

There are no automated tests at this time.

## Architecture

### Data Flow (Lakehouse)

```
Gmail / Transferegov (core/extract/)
        │  python manage.py rodar_pipeline (extraction half)
        ▼
data/raw/<fonte>/<fonte>_<date>...   (not in git; datado, imutável)
data/raw/<arquivo-fixo>               (sources placed there manually)
        │  core/ingestion/ponte_extracao.py locates "most recent" per source,
        │  hands it to bronze.ingerir() — same entrypoint as manual rodar_ingestao
        ▼  python manage.py rodar_ingestao <fonte>  (or via rodar_pipeline)
data/bronze/<fonte>/<fonte>_<timestamp>.csv   ← append-only, never modified
        │
        ▼  python manage.py rodar_silver <fonte>
data/silver/<fonte>.parquet                   ← overwritten each run
        │
        ▼  python manage.py carregar_convenios / carregar_fonte / carregar_cronograma / carregar_unidades_executoras / carregar_controle_sei
SQLite / PostgreSQL (apps.convenios models)
        │
        ▼  python manage.py carregar_relacionamento --construir  (joins multiple Silver files)
data/gold/convenios_integrado.parquet  →  apps.convenios.ConvenioIntegrado
        │
        ▼  Django ORM (core/gold/)
Aggregated dicts/lists
        │
        ▼  apps/dashboard/services.py  (with cache)
Django views → templates
```

The entire `data/` directory is gitignored. Raw is meant to be immutable — `core/extract/` never unzips into it; zip extraction for Transferegov happens in-memory inside `ponte_extracao.py`, scoped to the Bronze step.

### Layer Responsibilities

**`core/extract/`** — pre-raw extraction  
- `gmail.py`: downloads mapped SIGCON-MG attachment groups (`GRUPOS_ASSUNTOS`) via Gmail API OAuth (`secrets/credentials.json` + `secrets/token.json`, gitignored).  
- `transferegov.py`: downloads the Transferegov/SICONV open-data zip.  
- `armazenamento.py`: shared helper that timestamps/dates extractor output into `data/raw/<fonte_extracao>/`.

**`core/ingestion/`** — Bronze  
- `sources.py`: declarative registry of all data sources (`FONTES` dict of `FonteDados` dataclasses). Adding a new source starts here.  
- `readers.py`: reads raw CSV/Excel into a DataFrame with all columns as `str`, no type coercion.  
- `bronze.py`: wraps readers + writes timestamped CSV to `data/bronze/<fonte>/`. `ingerir(nome_fonte, arquivo=None)` accepts an explicit path override.  
- `ponte_extracao.py`: bridges `core/extract/` output to `bronze.ingerir()` — locates the most recent file per source in `data/raw/<fonte_extracao>/`, unzips the Transferegov member in a temp dir (never writes back to raw), and maps Gmail subjects to `FONTES` keys via `MAPA_GMAIL_PARA_FONTE` (currently 15 of the `sigcon` group; `siafi`/`siad` groups and 2 `sigcon` subjects have no `FonteDados` yet — TODO in code).

**`core/transform/`** — Silver  
- `silver.py`: generic pipeline — reads Bronze, removes `Unnamed` columns, normalizes column names to snake_case (via `utils.py`), then applies type conversions driven by the YAML schema for that source.  
- `schemas/<nome>.yaml`: per-source column classification (`data`, `valor`, `identificador`, `texto`). Auto-generated by `gerar_schemas`, but must be **manually reviewed** before production use — the generator marks uncertain columns as `duvidoso: true`.  
- `gerar_schemas.py`: heuristic classifier (name tokens + value sampling) that produces the YAML schemas.

**`core/gold/`** — Gold  
- `convenios.py`: pure Django ORM aggregations (`kpis`, `por_situacao`, `por_ano`, `recentes`). Returns plain Python dicts/lists with JSON-safe values (no DataFrames, no `Decimal`, no `date` objects) — safe for templates and `json_script`.  
- `relacionamento.py`: builds the integrated `ConvenioIntegrado` table (SIGCON↔SICONV join, `G_`/`A_` coalesced fields) from multiple Silver Parquets — pandas, not ORM. Read by `carregar_relacionamento`.  
- `contrapartida.py`: derives contrapartida type (financeira/não financeira/sem) per SIAFI+UO.

**`apps/convenios/`**  
- `models.py`: `Convenio` (main table) plus auxiliary models per SIGCON-MG table and `ConvenioIntegrado` (Gold).  
- `loader.py`: one `carregar_*` function per model — all **full refresh**: `Model.objects.all().delete()` then `bulk_create`. Chosen because SIGCON-MG has no reliable delta; running N times yields the same DB state.  
- Management commands: `carregar_convenios` (main table), `carregar_fonte <fonte>` (13 auxiliary tables, see `_LOADERS` dict), `carregar_cronograma`, `carregar_unidades_executoras`, `carregar_controle_sei`, `carregar_relacionamento` (Gold `ConvenioIntegrado`). `rodar_transformacao` and `carregar_silver` are **legacy/dead** — do not use (see Common Commands).

**`apps/dashboard/`**  
- `services.py`: the only layer views should call. Wraps Gold functions with Django cache (key `gold:indicadores:convenios`, TTL from `GOLD_CACHE_SECONDS` in settings, default 3600 s). Call `invalidar_cache()` after a data load to force recalculation — note most `carregar_*` loaders do **not** call this automatically; in dev (LocMemCache) restarting `runserver` clears it.  
- `views.py`: `sigcon` (paginated table with filters), `indicadores` (KPIs), `graficos` (Chart.js charts). Stub views (`uniao`, `execucao`, `monitoramento`, etc.) render `em_construcao.html`.  
- `templatetags/painel_filters.py`: custom template filters.  
- Management commands: `rodar_ingestao`, `rodar_silver`, `rodar_pipeline` (extraction + Bronze maestro), `gerar_schemas` — despite living under `dashboard`, these operate on the whole Bronze/Silver layer, not just the dashboard app.

**`config/settings/`**  
- `base.py`: shared settings; reads `.env` via `django-environ`. Exposes `DATA_DIR` (defaults to `BASE_DIR/data`).  
- `dev.py`: extends base; SQLite at `BASE_DIR/db.sqlite3`.  
- `prod.py`: extends base; configure `DATABASE_URL` and Redis cache here.

### Adding a New Data Source

1. Register in `core/ingestion/sources.py` → `FONTES`.
2. Place the raw file in `data/raw/`.
3. `python manage.py rodar_ingestao <fonte>` — creates Bronze.
4. `python manage.py gerar_schemas <fonte>` — generates `core/transform/schemas/<fonte>.yaml`.
5. Review the YAML: fix `duvidoso` columns; correct misclassifications.
6. `python manage.py rodar_silver <fonte>` — creates Silver Parquet.
7. Create a new loader (`apps/<fonte>/loader.py`) and management command if the source needs to populate a DB table.
