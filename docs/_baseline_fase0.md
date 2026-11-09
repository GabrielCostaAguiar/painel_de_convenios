# Fase 0 — Linha de base

Gerado em 2026-11-09, branch `refactor/ingestao-legado` (criada a partir de
`feat/validacao-grp`, commit `47aeb6f`).

## Silver do GRP

As 21 fontes `grp_*` (registradas em `core/ingestion/sources.py`, não as 7
`dcgce_*_grp` listadas em `core/pipeline.py:FONTES_SILVER_GRP` — ver
DIVERGÊNCIA abaixo) foram rodadas com `rodar_silver` sem erro. Hash SHA-256
de cada parquet gerado (22 arquivos — uma fonte produz uma saída extra,
provavelmente desdobramento/quarentena) em `docs/_baseline_grp_silver.json`.
Esse arquivo é o teste de regressão: ao final da Fase 6, os hashes devem
bater de novo.

## DIVERGÊNCIA — `core/pipeline.py:FONTES_SILVER_GRP` está desatualizada

`FONTES_SILVER_GRP` (linhas 82-90) lista 7 chaves (`dcgce_dados_grp`,
`dcgce_cronograma_desembolso_grp`, `dcgce_recursos_contrapartida_grp`,
`dcgce_recursos_concedente_grp`, `dcgce_plano_aplicacao_grp`,
`dcgce_plano_aplicacao_grp_detalhes`, `dcgce_esfera_grp`) que **não existem**
em `FONTES` — `rodar_silver` falha com `CommandError` para todas elas. As
fontes GRP reais são as 21 chaves `grp_*`. Isso é pré-existente (não foi
introduzido por este trabalho) e está fora do escopo desta refatoração
(`core/pipeline.py` só pode ter a lista de fontes **legadas** tocada aqui) —
registrado para follow-up, não corrigido nesta tarefa.

## Testes — linha de base

Comando: `pytest -q` (ambiente `config.settings.dev`).

**3 erros de coleção, fora da suíte:**
- `apps/sigcon/tests/test_bulk_refresh.py`
- `apps/sigcon/tests/test_carregar_grp.py`
- `tests/test_r4.py`

Todos pelo mesmo motivo: `ImportError: cannot import name 'DadosGrp' from
'apps.sigcon.models'` — `apps/sigcon/loader.py` importa um model que não
existe em `apps/sigcon/models/__init__.py`. Pré-existente, não relacionado a
este trabalho (não toquei em `apps/`).

**Suíte (excluindo os 3 arquivos acima):** `1 failed, 621 passed, 1 skipped, 115 errors`.
Saída completa salva fora do repositório (scratchpad da sessão). A maioria
dos 115 `ERROR` é `django.db.utils.ProgrammingError` (tabela ausente —
aparenta ser estado de banco/migração dessincronizado, não ligado à
ingestão). 1 `FAILED`:
`apps/painel/tests/test_rotas_smoke.py::test_inventario_de_rotas_bate_com_o_gabarito`.

## DIVERGÊNCIA — estrutura de apps diferente do `CLAUDE.md`

O `CLAUDE.md` documenta `apps/dashboard/` e `apps/convenios/`; o código atual
tem `apps/painel/` e `apps/sigcon/`. A Fase 7 deste trabalho já prevê
corrigir isso no `CLAUDE.md` — registrado aqui como confirmação de que a
divergência é real e generalizada (nomes de app, não só de pastas
specific).

## Ambiente

- Python via `.venv/Scripts/python.exe` (Windows)
- `DJANGO_SETTINGS_MODULE=config.settings.dev`
- SQLite em `db.sqlite3`
