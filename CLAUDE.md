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

`rodar_ingestao`, `rodar_silver`, `rodar_pipeline` and `gerar_schemas` live under `apps/pipeline/management/commands/`; the `carregar_*` loaders and `carregar_relacionamento` live under `apps/convenios/management/commands/`.

`rodar_transformacao` and `carregar_silver` (both in `apps/convenios/management/commands/`) are **legacy, do not use** — superseded by `rodar_silver` and `carregar_convenios` respectively. `rodar_transformacao` references a `"convenios"` source key that no longer exists in `FONTES`.

### Tests

```bash
python -m pytest -q            # whole suite
python -m pytest -q tests/     # cross-cutting suites only
```

`pytest.ini` already points `DJANGO_SETTINGS_MODULE` at `config.settings.dev`, so no env
var is needed to run them. Dev dependencies (pytest, pytest-django, black) come from
`requirements-dev.txt`, not `requirements.txt`.

**177 tests, all passing.** Split across two locations — `tests/` at the repo root for
cross-cutting suites, and `<app>/tests/` for what belongs to one app:

| File | Tests | Covers |
|---|---|---|
| `apps/dashboard/tests/test_rotas_smoke.py` | 34 | route inventory vs. fixture; GET on every dashboard screen with an empty DB; export Content-Type |
| `tests/test_r3.py` | 31 | `_coalesce`, `G_` fields, anti-fan-out, `A_` fields |
| `tests/test_r2.py` | 28 | `montar_siafi_uo`, `resolver_siafi_atual`, `aplicar_correcoes`, de-paras |
| `apps/dashboard/tests/test_sigcon_services.py` | 22 | the SIGCON tab services |
| `tests/test_gold_convenios.py` | 13 | Gold aggregations (`kpis`, `por_situacao`, `por_ano`, `recentes`) |
| `tests/test_comandos_registrados.py` | 11 | which app owns each management command |
| `tests/test_cache_invalidacao.py` | 9 | indicator cache invalidation and when `atualizar_painel` triggers it |
| `tests/test_contrapartida.py` | 8 | contrapartida type derivation |
| `apps/dashboard/tests/test_filtros_globais.py` | 7 | global filter propagation |
| `tests/test_referencias.py` | 5 | reference tables |
| `apps/convenios/tests/test_bulk_refresh.py` | 4 | atomicity of the full refresh |
| `tests/test_sei_service.py` | 3 | SEI service |
| `tests/test_r4.py` | 2 | idempotent load, ORM read |

No test touches real data — they use in-memory DataFrames, temporary Parquet files or
small synthetic fixtures.

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

`core/` must never import from `apps/dashboard/` — the core can't depend on the
presentation layer. That's why cache keys live in `core/cache.py` and not in
`services.py`; `core/pipeline.py` used to import from `services.py` and no longer does.

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

**`core/cache.py`** — cache keys for the Gold indicators and
`invalidar_cache_indicadores()`. Imported by the loaders' management commands and by
`core/pipeline.py`; `apps/dashboard/services.py` consumes the same keys.

**`core/gold/`** — Gold  
- `convenios.py`: pure Django ORM aggregations (`kpis`, `por_situacao`, `por_ano`, `recentes`). Returns plain Python dicts/lists with JSON-safe values (no DataFrames, no `Decimal`, no `date` objects) — safe for templates and `json_script`.  
- `relacionamento.py`: builds the integrated `ConvenioIntegrado` table (SIGCON↔SICONV join, `G_`/`A_` coalesced fields) from multiple Silver Parquets — pandas, not ORM. Read by `carregar_relacionamento`.  
- `contrapartida.py`: derives contrapartida type (financeira/não financeira/sem) per SIAFI+UO.

**`apps/convenios/`**  
- `models/`: package, one file per domain — `sigcon.py` (`Convenio` main table + SIGCON-MG auxiliaries), `codigos.py` (code-mapping tables), `gold.py` (`ConvenioIntegrado`), `externos.py` (`ControleSEI`), `grp.py` (the 7 GRP models). `__init__.py` re-exports all 24 classes, so `from apps.convenios.models import X` works regardless of the file. Splitting the package does **not** generate a migration — the ORM keys models by `app_label` + class name, never by file.  
- `loader.py`: one `carregar_*` function per model — all **full refresh**: `Model.objects.all().delete()` then `bulk_create`. Chosen because SIGCON-MG has no reliable delta; running N times yields the same DB state. Every delete/insert pair goes through `_bulk_refresh`, which wraps both in `transaction.atomic()` — **keep it that way**: without the transaction, a failure mid-load leaves the table empty. Never add a delete/insert path that bypasses the helper.  
- Management commands: `carregar_convenios` (main table), `carregar_fonte <fonte>` (13 auxiliary tables, see `_LOADERS` dict), `carregar_cronograma`, `carregar_unidades_executoras`, `carregar_controle_sei`, `carregar_relacionamento` (Gold `ConvenioIntegrado`). `rodar_transformacao` and `carregar_silver` are **legacy/dead** — do not use (see Common Commands).

**`apps/dashboard/`**  
- `services.py`: the only layer views should call. Wraps Gold functions with Django cache (key `gold:indicadores:convenios`, TTL from `GOLD_CACHE_SECONDS` in settings, default 3600 s). Cache keys and invalidation live in **`core/cache.py`**, not here — every `carregar_*` command and `atualizar_painel()` already call `invalidar_cache_indicadores()` when data changes, so you don't need to remember to. Keys carry a version number (`...:convenios:v3:ano:2024`); bumping it invalidates the base key and every per-year variant at once, which works on LocMemCache and Redis alike. `invalidar_cache()` stays exported here as a façade.  
- `views/`: package, one file per screen — `sigcon.py` (the 6 SIGCON tabs), `exports.py` (their CSV/XLSX exports), `painel.py` (`indicadores`, `graficos`), `grp.py` (the 7 GRP tabs), `stubs.py` (`uniao`, `execucao`, `monitoramento`, … rendering `em_construcao.html`) and `_helpers.py`. `__init__.py` re-exports everything `urls.py` references.  
- `templatetags/painel_filters.py`: custom template filters.  

**`apps/pipeline/`** — no models; exists only to host the lakehouse orchestration commands: `rodar_ingestao`, `rodar_silver`, `rodar_pipeline` (extraction + Bronze maestro) and `gerar_schemas`. They operate on the whole Bronze/Silver layer, so they don't belong in the presentation app. `apps/dashboard/` registers **no** management commands — two apps exposing the same command name resolve ambiguously by `INSTALLED_APPS` order.

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
