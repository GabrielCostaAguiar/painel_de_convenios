# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Internal web dashboard for DCGCE/SEPLAG-MG to replace a legacy QlikView panel. Built on a Python/Django Lakehouse pipeline (Bronze → Silver → Gold) that reads SIGCON-MG exports and other government data sources.

## Environment Setup

Copy `.env.example` to `.env` and fill in `DJANGO_SECRET_KEY`. The settings module for development is `config.settings.dev` (PostgreSQL local `painel_convenios`, DEBUG=True). Always set this environment variable:

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
# file in data/raw/<...> per sources.py first): sigcon_chave_siconv, depara_siafi,
# depara_parlamentar, controle_sei, qv_despesa_ano_2019, qv_despesa_ano_2020
python manage.py rodar_ingestao <nome_fonte>

# Bronze -> Silver, per source (run for every source you need downstream)
python manage.py rodar_silver <nome_fonte>

# Silver -> DB (full refresh each)
python manage.py carregar_convenios              # main Convenio table (needs sigcon_convenio/convenio_geral/plano_trabalho/concedente/chave_convenio silver)
python manage.py carregar_fonte <nome_fonte>      # auxiliary tables — see _LOADERS in carregar_fonte.py for the 13 valid keys
python manage.py carregar_cronograma
python manage.py carregar_unidades_executoras
python manage.py carregar_controle_sei
python manage.py carregar_relacionamento --construir   # Gold ConvenioIntegrado (needs sigcon_chave_siconv, depara_siafi, sigcon_convenio/chave_convenio/convenio_geral/plano_trabalho/concedente silver)

# GRP — as tabelas de uma vez, ou fontes escolhidas.
# Fora do rodar_pipeline por padrão: ver PIPELINE_INCLUIR_GRP abaixo.
python manage.py carregar_grp
python manage.py carregar_grp --fonte grp_instrumento --fonte grp_concedente

# Generate YAML schema for a new source (then manually review the YAML before running rodar_silver)
python manage.py gerar_schemas <nome_fonte>
python manage.py gerar_schemas --sobrescrever       # force regeneration of existing YAMLs
```

`rodar_ingestao`, `rodar_silver`, `rodar_pipeline` and `gerar_schemas` live under `apps/pipeline/management/commands/`; the `carregar_*` loaders and `carregar_relacionamento` live under **`apps/sigcon/management/commands/`** — not `apps/convenios/` (that directory still exists on disk for historical migration state only; it is **not** in `INSTALLED_APPS` and has no code). `INSTALLED_APPS` (`config/settings/base.py`) is `apps.painel`, `apps.sigcon`, `apps.grp`, `apps.uniao`, `apps.execucao`, `apps.pipeline` — `apps/convenios/` and `apps/dashboard/` are dead directories, not installed apps; don't add code there.

`rodar_transformacao` and `carregar_silver` (both in `apps/sigcon/management/commands/`) are **legacy, do not use** — superseded by `rodar_silver` and `carregar_convenios` respectively. `rodar_transformacao` imports `core.transform.convenios`, which was deleted in the legacy-ingestion refactor (dead module, no caller left) — the command now fails at import time instead of at the old `"convenios"` source-key lookup.

### Ingestão legada (SIGCON e apoio)

**Escopo atual: o modelo é estritamente SIGCON — 15 tabelas** (`docs/modelo_extracao_sigcon.pdf`,
consultas `dcgce_*` do BusinessObjects). `siconv_convenio`, `sigcon_chave_siconv`, `depara_siafi`
(onda TransfereGov) e `controle_sei` (+ `controle_sei_documento`), `depara_parlamentar` (onda OneDrive)
estão fora do modelo e não são validadas até essas ondas; ver "Fontes adiadas" em
`docs/relatorio_ingestao_legado.md` (o código ainda lê `sigcon_chave_siconv`, `depara_siafi` e
`siconv_convenio` pelos nomes novos, então não foram devolvidas às chaves originais). Os parágrafos
abaixo descrevem a refatoração que originou as 21 fontes.

As 20 fontes legadas do SIGCON-MG (+ 1 tabela derivada) foram renomeadas e
migradas para o mesmo motor declarativo do GRP (ver "Fase 2 — generaliza o
motor Silver" no histórico de commits `refactor/ingestao-legado`). Nomes
antigos (`dcgce_*`, `chaves_convenio`, `siafi2`, `parlamentares`) não
existem mais em `FONTES` — ver a tabela de chave nova/antiga e o contrato
completo de cada YAML (`grao`, `renomear`, `sentinelas`, `booleanos`,
`derivadas`, `descartar`, `marcar_linhas_se_nulo`, e os casos especiais
`quarentena`/`desdobrar`) em:
- `docs/dicionario_dados_legado.md` — gerado a partir dos YAMLs, uma
  tabela por fonte com nome bruto→final, tipo, sentinelas e marca LGPD.
- `docs/relatorio_ingestao_legado.md` — o que mudou, o que foi excluído, e
  o mapa de impacto completo para `apps/sigcon/loader.py` e
  `core/pipeline.py::CARGAS_ORM` (**já adaptados na Fase 8**: loaders,
  `carregar_fonte` e o Gold leem a Silver nova).
- `docs/validacao_models_sigcon.md` — contagem por fonte/model (nenhuma linha
  com dado é excluída: Silver = Bronze − linhas vazias; model = Silver) e o
  que mudou no Gold (o antigo nunca incluiu o SICONV).
- `docs/auditoria_exclusao_linhas.md` — regra de preservação de linhas e onde o
  código excluía linhas antes.
- `docs/validacao_ingestao_legado.md` — contagens reais por tabela e as
  divergências encontradas contra a base de produção.

### Tests

```bash
python -m pytest -q            # whole suite
python -m pytest -q tests/     # cross-cutting suites only
```

`pytest.ini` already points `DJANGO_SETTINGS_MODULE` at `config.settings.dev`, so no env
var is needed to run them. Dev dependencies (pytest, pytest-django, black) come from
`requirements-dev.txt`, not `requirements.txt`.

**247 tests, all passing.** Split across two locations — `tests/` at the repo root for
cross-cutting suites, and `<app>/tests/` for what belongs to one app:

| File | Tests | Covers |
|---|---|---|
| `apps/painel/tests/test_rotas_smoke.py` | 34 | route inventory vs. fixture; GET on every dashboard screen with an empty DB; export Content-Type |
| `tests/test_r3.py` | 31 | `_coalesce`, `G_` fields, anti-fan-out, `A_` fields |
| `tests/test_r2.py` | 28 | `montar_siafi_uo`, `resolver_siafi_atual`, `aplicar_correcoes`, de-paras |
| `apps/sigcon/tests/test_sigcon_services.py` | 22 | the SIGCON tab services |
| `tests/test_gold_convenios.py` | 13 | Gold aggregations (`kpis`, `por_situacao`, `por_ano`, `recentes`) |
| `tests/test_comandos_registrados.py` | 11 | which app owns each management command |
| `tests/test_cache_invalidacao.py` | 9 | indicator cache invalidation and when `atualizar_painel` triggers it |
| `tests/test_contrapartida.py` | 8 | contrapartida type derivation |
| `apps/painel/tests/test_filtros_globais.py` | 7 | global filter propagation |
| `tests/test_referencias.py` | 5 | reference tables |
| `apps/sigcon/tests/test_bulk_refresh.py` | 4 | atomicity of the full refresh |
| `tests/test_sei_service.py` | 3 | SEI service |
| `tests/test_r4.py` | 2 | idempotent load, ORM read |
| `tests/test_settings_prod.py` | 17 | production settings, loaded in a subprocess |
| `apps/sigcon/tests/test_excecoes_comandos.py` | 14 | expected vs. unexpected errors in the load commands |
| `apps/grp/tests/test_carregar_grp.py` | 14 | `carregar_grp` and the optional GRP pipeline stage |
| `apps/sigcon/tests/test_ordenacao.py` | 20 | deterministic ordering of the paginated screens |

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
PostgreSQL (apps.sigcon models)
        │
        ▼  python manage.py carregar_relacionamento --construir  (joins multiple Silver files)
data/gold/convenios_integrado.parquet  →  apps.sigcon.ConvenioIntegrado
        │
        ▼  Django ORM (core/gold/)
Aggregated dicts/lists
        │
        ▼  apps/painel/services.py  (with cache)
Django views → templates
```

The entire `data/` directory is gitignored. Raw is meant to be immutable — `core/extract/` never unzips into it; zip extraction for Transferegov happens in-memory inside `ponte_extracao.py`, scoped to the Bronze step.

### Layer Responsibilities

`core/` must never import from `apps/painel/` — the core can't depend on the
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
- `silver.py`: generic pipeline, shared by every source (GRP and legacy SIGCON alike — **one motor, never source-specific Python logic**). Reads Bronze, removes `Unnamed` columns, normalizes column names to snake_case (via `utils.py`), applies sentinela-nulling, type conversion, renaming, and then the declarative blocks below, all driven by the YAML schema for that source. Pipeline order (see the module docstring for the full 17-step list): normalizar → sentinelas pré-tipagem/`descartar_linhas_se_nulo` (nomes brutos) → tipagem (`data`, `data_hora`, `valor`, `inteiro`, `identificador`; qualquer coluna não listada vira texto, sentinela-limpa pelo conjunto padrão ou por override) → `renomear` → `desdobrar` → `descartar` (colunas, nomes finais) → `booleanos` → `derivadas` → linhas idênticas (só ALERTA, todas ficam) → `quarentena` (marca) → `grao` (ALERTA, não bloqueia). **The engine never drops a row with data**: the only removal is the 100%-empty row (every cell `""` or `N/A` in the raw text, `_SEM_DADO`); see `docs/auditoria_exclusao_linhas.md` and `tests/test_preservacao_linhas.py`.
- `schemas/<nome>.yaml`: per-source contract. Required/common keys: `fonte`, `descricao`, `grao` (list of final column names; duplicates log an ALERTA, never block), `colunas` (`data`, `data_hora`, `valor`, `inteiro`, `identificador` — anything else defaults to texto), `renomear` (raw→final, raw keys are the *normalized* bronze header). Optional, per-column override keys: `sentinelas` (raw names; a column's list **replaces** the global default `{"N/A", "-3", ""}` entirely, it does not add to it), `booleanos` (final names; replaces the project-wide `fl_` + `MAPA_BOOLEANO` convention for that column), `descartar` (final names, drops the column), `marcar_linhas_se_nulo` (raw names, runs **before** typing — flags, never removes, rows of malformed export blocks: `ds_alerta_linha` gets the reason and `tx_linha_bruta` the original text; typing does not break on flagged rows), `derivadas` (final name → `{funcao, args}`, function must be registered in `FUNCOES_DERIVADAS` — e.g. `montar_siafi_uo`), `quarentena` (`grao`/`destino` final columns — **flags** rows whose grão repeats with a *different* destino in `ds_alerta_linha`; they stay in the main table and `transformar_fonte_completo()["quarentena"]` returns a copy; only `depara_siafi` uses it today), `desdobrar` (`chave`/`valor`/`mapa` — generates a second, long-format DataFrame from several wide columns; only `controle_sei` → `controle_sei_documento` uses it today). Auto-generated by `gerar_schemas`, but must be **manually reviewed** before production use — the generator marks uncertain columns as `duvidoso: true`.
- `gerar_schemas.py`: heuristic classifier (name tokens + value sampling) that produces the YAML schemas.
- `transformar_fonte(nome)` returns only the main DataFrame (stable public contract, used by `rodar_silver`); `transformar_fonte_completo(nome)` returns `{"principal", "quarentena", "desdobrado"}` for sources that declare those blocks. **`rodar_silver` only persists `"principal"`** — nothing in `apps/` writes `quarentena.parquet` or a `desdobrar`-derived table to `data/silver/` yet (see `docs/relatorio_ingestao_legado.md`, "Gap de persistência").

**`core/cache.py`** — cache keys for the Gold indicators and
`invalidar_cache_indicadores()`. Imported by the loaders' management commands and by
`core/pipeline.py`; `apps/painel/services.py` consumes the same keys.

**`core/gold/`** — Gold  
- `convenios.py`: pure Django ORM aggregations (`kpis`, `por_situacao`, `por_ano`, `recentes`). Returns plain Python dicts/lists with JSON-safe values (no DataFrames, no `Decimal`, no `date` objects) — safe for templates and `json_script`.  
- `relacionamento.py`: builds the integrated `ConvenioIntegrado` table (SIGCON↔SICONV join, `G_`/`A_` coalesced fields) from multiple Silver Parquets — pandas, not ORM. Read by `carregar_relacionamento`.  
- `contrapartida.py`: derives contrapartida type (financeira/não financeira/sem) per SIAFI+UO.

**`apps/sigcon/`** — the real home of the SIGCON-MG domain (**not** `apps/convenios/`, which is a dead directory kept only for historical migration state — see Common Commands).
- `models/`: package, one file per domain — `sigcon.py` (`Convenio` main table + SIGCON-MG auxiliaries), `codigos.py` (code-mapping tables), `gold.py` (`ConvenioIntegrado`), `externos.py` (`ControleSEI`). `__init__.py` re-exports every class, so `from apps.sigcon.models import X` works regardless of the file. Splitting the package does **not** generate a migration — the ORM keys models by `app_label` + class name, never by file. The GRP models live in **`apps/grp/models.py`** (a separate Django app, own `app_label`), not here — they were moved out via `SeparateDatabaseAndState` migrations; the old `convenios_dadosgrp`-style DB table names are historical and don't reflect the current app.
- `loader.py`: one `carregar_*` function per model — all **full refresh**: `Model.objects.all().delete()` then `bulk_create`. Chosen because SIGCON-MG has no reliable delta; running N times yields the same DB state. Every delete/insert pair goes through `_bulk_refresh`, which wraps both in `transaction.atomic()` — **keep it that way**: without the transaction, a failure mid-load leaves the table empty. Never add a delete/insert path that bypasses the helper. **Reads the new Silver** (`sigcon_*`, `controle_sei`; the models keep their historical field names and each loader maps Silver column → field). **Never drops a row**: a model has exactly the rows of its Silver (`tests/test_loaders_preservam_linhas.py`); enrichment joins are LEFT, with a de-duplicated right side that has no null keys (pandas matches null with null) and an assert that the row count did not change. Rows the engine flagged go to the DB flagged (`CronogramaDesembolso.ds_alerta_linha`, `ConvenioIntegrado.fl_uo_excluida`/`limpeza_g`) and the **queries** filter them: `get_cronograma_qs` uses `ds_alerta_linha__isnull=True`, the Gold lookups use `fl_uo_excluida=False` and `exclude(limpeza_g=1)`. `ConvenioIntegrado.siafi_uo` is nullable (convênios without SIAFI).
- Management commands that load data follow one exception pattern: `FileNotFoundError` is the *expected* error (source not ingested yet) and becomes a short `CommandError`; anything else is *unexpected* and gets `logger.exception(...)` plus `raise CommandError(...) from exc`, so the traceback survives. Never go back to `except (FileNotFoundError, Exception)` — it hides the cause.  
- Management commands: `carregar_convenios` (main table), `carregar_fonte <fonte>` (13 auxiliary tables, see `_LOADERS` dict), `carregar_cronograma`, `carregar_unidades_executoras`, `carregar_controle_sei`, `carregar_relacionamento` (Gold `ConvenioIntegrado`). `rodar_transformacao` and `carregar_silver` are **legacy/dead** — do not use (see Common Commands).

**`apps/painel/`** — the dashboard app (**not** `apps/dashboard/`, which is not in `INSTALLED_APPS` and has no active code).
- `services.py`: the only layer views should call. Wraps Gold functions with Django cache (key `gold:indicadores:convenios`, TTL from `GOLD_CACHE_SECONDS` in settings, default 3600 s). Cache keys and invalidation live in **`core/cache.py`**, not here — every `carregar_*` command and `atualizar_painel()` already call `invalidar_cache_indicadores()` when data changes, so you don't need to remember to. Keys carry a version number (`...:convenios:v3:ano:2024`); bumping it invalidates the base key and every per-year variant at once, which works on LocMemCache and Redis alike. `invalidar_cache()` stays exported here as a façade. The backend is per environment: `LocMemCache` in `dev.py`; in `prod.py`, Redis when `REDIS_URL` is set, else `DatabaseCache`. Production **must** use a shared backend — with `LocMemCache` each worker keeps its own copy and the invalidation fired by the load command reaches none of them. Do not swap the version bump for `cache.incr()`: `DatabaseCache` falls back to `BaseCache.incr`, which rewrites the key without a timeout and lets the counter expire before the entries it invalidates.  
- Paginated screens **must** have a deterministic `order_by`, applied in the `get_*_qs` function of `services.py` (not in the view, not via `Meta.ordering` — that would affect every query of the model, including Gold aggregations). Each ordering follows the screen's columns and **ends in `"pk"`**, because the SIGCON-MG business keys allow ties. `pytest.ini` turns `UnorderedObjectListWarning` into an error to keep it that way.
- `views/`: package, one file per screen — `sigcon.py` (the 6 SIGCON tabs), `exports.py` (their CSV/XLSX exports), `painel.py` (`indicadores`, `graficos`), `grp.py` (the GRP tabs), `stubs.py` (`uniao`, `execucao`, `monitoramento`, … rendering `em_construcao.html`) and `_helpers.py`. `__init__.py` re-exports everything `urls.py` references.  
- `templatetags/painel_filters.py`: custom template filters.  

**`apps/pipeline/`** — no models; exists only to host the lakehouse orchestration commands: `rodar_ingestao`, `rodar_silver`, `rodar_pipeline` (extraction + Bronze maestro) and `gerar_schemas`. They operate on the whole Bronze/Silver layer, so they don't belong in the presentation app. `apps/painel/` registers **no** management commands — two apps exposing the same command name resolve ambiguously by `INSTALLED_APPS` order.

**Settings worth knowing** (`config/settings/base.py`, overridable by env): `GOLD_CACHE_SECONDS` (default 3600) and `PIPELINE_INCLUIR_GRP` (default `False` — the GRP is still in testing and must not break the daily SIGCON refresh; `rodar_pipeline` behaves exactly as before while it is off). `prod.py` adds `REDIS_URL`, `STATIC_ROOT`, `SECURE_HSTS_INCLUDE_SUBDOMAINS` and `SECURE_HSTS_PRELOAD`. Deploy steps in `docs/CHECKLIST_DEPLOY.md`.

**`config/settings/`**  
- `base.py`: shared settings; reads `.env` via `django-environ`. Exposes `DATA_DIR` (defaults to `BASE_DIR/data`).  
- `dev.py`: extends base; PostgreSQL (`painel_convenios` on localhost).  
- `prod.py`: extends base; configure `DATABASE_URL` and Redis cache here.

### Adding a New Data Source

1. Register in `core/ingestion/sources.py` → `FONTES`.
2. Place the raw file in `data/raw/`.
3. `python manage.py rodar_ingestao <fonte>` — creates Bronze.
4. `python manage.py gerar_schemas <fonte>` — generates `core/transform/schemas/<fonte>.yaml`.
5. Review the YAML: fix `duvidoso` columns; correct misclassifications.
6. `python manage.py rodar_silver <fonte>` — creates Silver Parquet.
7. Create a new loader (`apps/<fonte>/loader.py`) and management command if the source needs to populate a DB table.
