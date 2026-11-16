# Decisões e andamento · reorganização `core` + apps no molde do GRP

Registro vivo da execução de `docs/PLANO_ORGANIZACAO.md`. Serve para retomar o trabalho em outra
sessão sem reler a conversa. Atualizar ao fim de cada fase.

Branch de trabalho: `refactor/organizacao-core` (criada a partir de `fix/testes-pos-refatoracao-sigcon`).
Linha de base dos testes: **1082 passed, 4 skipped, 1 xfailed**. Todas as fases fechadas mantêm esse número.

## Onde parei (16/11/2026)

**Fases 1, 2 e 3 concluídas. Próxima: Fase 4** (`apps/painel` → `apps/dashboard`, filtros e
formatação no `core`). Fases 5, 6 e 7 pendentes.

| Fase | Estado | Commit |
|---|---|---|
| 1. `core` vira app; comandos de pipeline movidos de `apps/pipeline` | feita | `b96370e` |
| 2. Carga genérica (`core/carga/`) e `ComandoCarga` | feita | `5fb30e0` |
| 3. Validação genérica (`core/validacao/`) e `ComandoValidacao` | feita | `dbd406d` |
| 4. `painel` → `dashboard`; filtros e formatação no core | **próxima** | — |
| 5. Gold legado em pandas sai do `core` (core ↛ apps) | pendente | — |
| 6. Label `convenios` → `sigcon` (exige SQL que o Gabriel roda) | pendente (D3: depois das fases 1–5) | — |
| 7. Documentação (ARQUITETURA §3/§5/§6/§8/§16, CLAUDE.md §3/§4/§5) | pendente | — |

## Decisões tomadas (D1–D4, resposta do Gabriel em 16/11/2026)

| # | Decisão | Resposta |
|---|---|---|
| D1 | Branch `refactor/organizacao-core`, um commit por fase, só após aprovação do diff | Sim |
| D2 | `_LOADERS_<APP>` sai do comando e vai para `apps/<app>/loader.py` | Sim |
| D3 | Fase 6 (label) | Depois das fases 1–5, em commit próprio |
| D4 | Componente de consulta compartilhado (S1-10) nasce em `core/web/`, não em `apps/dashboard/` | Sim |

## Decisões e desvios durante a execução

| Fase | Decisão ou desvio | Motivo |
|---|---|---|
| 1 | Removidas as pastas `apps/convenios`, `apps/dashboard` e `apps/__pycache__` | Só continham `.pyc`; nenhum arquivo versionado |
| 2 | `_para_date`, `_para_decimal` e `_para_str` **não** foram levados ao core | Código morto: nenhum uso no projeto |
| 2 | `core/db.py` virou `core/carga/refresh.py` (`bulk_refresh`) | Mesma lógica, agora junto da carga |
| 2 | Testes de carga fazem patch em `Command.loaders` e em `core.carga.comando.invalidar_cache_indicadores` | Os nomes `_LOADERS_*` e o cache saíram do módulo do comando |
| 2 | `tests/test_bulk_refresh.py` movido de `apps/sigcon/tests/` para `tests/` | Passou a testar código do core |
| 3 | `volumetria`, `arquivos` e `texto` recebem o prefixo do app (`"sigcon_"`, `"grp_"`); catálogos ligam com `partial(..., PREFIXO)` | Mesma lógica servia aos dois apps |
| 3 | `LIMITES_CONHECIDOS` ficou em `apps/sigcon/validacao/limites.py`; `severidade_efetiva` foi para `core/validacao/limites.py` | Dados são do app; a regra é genérica |
| 3 | Volumetria do GRP passou a seguir a do SIGCON: Parquet ausente vira divergência (antes, exceção) e a pasta vem de `settings.DATA_DIR` (antes, `BASE_DIR/data`) | Unificação no módulo mais completo |
| 3 | O SQL do catálogo do GRP mudou só na forma (56 testes: parênteses e `IS NOT NULL` redundante); o do SIGCON não mudou (0 de 55) | Verificado comparando o SQL de `HEAD` contra o novo, sem tocar no banco |
| 3 | `validar_grp`/`validar_sigcon` **não** foram rodados contra o banco | Eles gravam em `ResultadoValidacao`; o plano dizia "só fazem SELECT", o que está errado |

## Pendências e pontos de atenção para quem continuar

- **`CLAUDE.md` e `docs/ARQUITETURA.md`** são as versões novas escritas pelo Gabriel e não foram
  incluídas nos commits das fases (estavam modificados no disco). Não reverter.
- **Arquivos soltos do Gabriel na raiz** (`inspecionar.py`, `teste.py`, `gerar_schemas_grp.ps1`,
  `divergencias_crono_fisico.xlsx`, `docs/painel_convenios_resumo_projeto.pdf`): não tocar nem commitar.
- **Fase 4:** conferir se `formatar_celula` do GRP e do SIGCON fazem a mesma coisa antes de unificar
  (o plano manda parar e mostrar a diferença ao Gabriel se divergirem). Manter o nome da biblioteca de
  template tags `painel_filters`. O módulo de exportação **não pode importar pandas/numpy** (erro de
  OpenBLAS; ver `apps/sigcon/views/exports.py`).
- **Fase 5:** `core/gold/relacionamento.py` (1048 linhas) deve ser investigado antes de qualquer
  movimentação; não apagar sem ordem do Gabriel. `core/pipeline.py` ainda referencia comandos de carga
  antigos que não existem mais (há um teste `xfail` registrando isso em `tests/test_comandos_registrados.py`).
- **Fase 6:** o executor só prepara o código e o script `docs/sql/renomear_label_sigcon.sql`; o Gabriel
  roda o SQL (`UPDATE` em `django_migrations` e `django_content_type`), com `pg_dump` antes.
- Fora do escopo, só apontar: unificar `_grp_render`/`sigcon_render` (S1-10), gold em SQL, `etl/`,
  Redis em `prod.py`, `apps/grp/sql/teste.sql`, `apps/grp/serializers.py` vazio.
