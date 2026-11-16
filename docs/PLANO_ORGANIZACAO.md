# Plano de organização · `core` como app + apps no molde do GRP

Plano de execução para um modelo (Claude) executar fase a fase. Escrito em 16/11/2026, a partir do
estado da branch `fix/testes-pos-refatoracao-sigcon` (HEAD `ebaec2d`).

**Antes de tudo:** leia o `CLAUDE.md`. Este plano roda no modo `executar`: em cada fase,
**descobrir → implementar → ⛔ parar com `git diff --stat`** e esperar o Gabriel. Não emende duas
fases sem aprovação. As regras de economia de contexto (CLAUDE.md §1) e a lista do que pode ser
executado (CLAUDE.md §6) continuam valendo.

---

## 0. Antes da fase 1

### 0.1 Decisões pendentes (perguntar ao Gabriel antes de começar)

| # | Pergunta | Recomendação |
|---|---|---|
| D1 | Criar a branch `refactor/organizacao-core` a partir da atual, com um commit por fase? (criar branch e commitar exigem ordem dele) | Sim |
| D2 | `_LOADERS_<APP>` sai do comando `carregar_<app>` e vai para `apps/<app>/loader.py`? | Sim (permite comando fino) |
| D3 | Fase 6 (label `convenios` → `sigcon`) agora ou depois da v1.0? | Depois das fases 1–5, em commit próprio |
| D4 | O componente de consulta compartilhado (S1-10) nasce em `core/web/`, não em `apps/dashboard/` como diz a ARQUITETURA §8? | Sim (é função global) |

Se a resposta divergir da recomendação, ajuste a fase correspondente e anote aqui.

### 0.2 Linha de base

Rodar e anotar antes de mexer em qualquer coisa:

```powershell
.venv\Scripts\activate
python manage.py check
python -m pytest -q -p no:cacheprovider 2>&1 | Select-Object -Last 3
```

Esperado em 16/11/2026: **1082 passed, 4 skipped, 1 xfailed**. Toda fase termina com o mesmo
número de testes passando, ou com a diferença explicada (teste movido ou renomeado, nunca removido
para "passar").

### 0.3 Arquivos não commitados que já existem

`CLAUDE.md` e `docs/ARQUITETURA.md` estão modificados e não commitados: são as versões-alvo,
escritas pelo Gabriel. Não reverter. Os arquivos soltos na raiz (`inspecionar.py`, `teste.py`,
`gerar_schemas_grp.ps1`, `divergencias_crono_fisico.xlsx`) são dele: não tocar, não commitar.

---

## 1. Diagnóstico

O GRP (`apps/grp/`) tem a estrutura aprovada. O SIGCON foi construído **copiando** o GRP em vez de
reaproveitar, e o código comum ficou espalhado:

| Duplicação | GRP | SIGCON |
|---|---|---|
| Loader genérico (`_silver_path`, `_para_date`, `_para_decimal`, `_para_str`, `_ler_parquet`, `carregar_tabela_generica`) | `apps/grp/loader.py:51-153` | `apps/sigcon/loader.py:48-149` (idêntico; só imports e docstrings mudam) |
| Comando de carga | `carregar_grp.py` | `carregar_sigcon.py` (5 linhas diferentes no `Command`, trocando o nome do app) |
| Geradores de SQL de validação | `apps/grp/validacao/generico.py` | `apps/sigcon/validacao/generico.py` (versão mais nova: parâmetro `filtro=`, sem `sql_sem_chave`) |
| Volumetria | `apps/grp/validacao/volumetria.py` | `apps/sigcon/validacao/volumetria.py` (mais completa: prefixo, variação %) |
| Formatação de célula | `apps/grp/views/_filtros.py` (`_fmt_data`, `_fmt_valor`, `_formatar_celula`) | `apps/sigcon/views/_filtros.py` (`_fmt_data`, `_fmt_valor`, `formatar_celula`) |
| Render de tabela paginada | `_grp_render` | `sigcon_render` |

Além disso:
- Os comandos de orquestração estão num app sem domínio (`apps/pipeline`), que não existe na
  ARQUITETURA.
- A casca do painel se chama `apps/painel`, mas a ARQUITETURA chama de `apps/dashboard`.
- `core/gold/contrapartida.py:158` importa `apps.sigcon.models`, ou seja, o core depende de um app.
- O label do SIGCON ainda é `convenios` (`apps/sigcon/apps.py:18`), contra a ARQUITETURA §16
  (12/11/2026).
- `apps/convenios/` e `apps/dashboard/` só contêm `.pyc` velhos, sem nenhum arquivo versionado.

---

## 2. Regra de organização (alvo)

| Camada | Contém | Pode importar |
|---|---|---|
| `core` (app Django, `name="core"`, `label="core"`, **sem models, sem migrations**) | Tudo que serve a mais de um app: comandos de pipeline, carga, validação, formatação, exportação, filtros globais de template, cache | Django e bibliotecas. **Nunca `apps.*`** |
| `apps/<app>` (molde: GRP) | Só o domínio: models, registro de fontes (`partial` + `_LOADERS_<APP>`), catálogo de validação, querysets, telas, SQL gold | `core` e Django. **Nunca outro app** |
| `apps/dashboard` | Casca: layout, menu, início, indicadores, stubs "em construção" | `core` e os models gold dos apps |

**Teste para decidir onde algo vai:** se aparece em dois apps, ou recebe o model ou a fonte como
parâmetro, vai para o `core`. Se cita um model, uma fonte ou uma coluna específica, fica no app.

O `core` não tem tabela própria. Modelos de controle (`ResultadoValidacao`, `SigconHistoricoCarga`)
ficam nos apps, e as funções do core os **recebem como parâmetro**.

### Estrutura-alvo

```
core/                          app Django sem models (label "core")
├─ apps.py                     CoreConfig
├─ management/commands/        rodar_ingestao, rodar_silver, rodar_pipeline, gerar_schemas
├─ extract/  ingestion/  transform/     já existem; não mudam nesta reorganização
├─ carga/                      silver → banco
│  ├─ loader.py                carregar_tabela_generica + conversores + bulk_refresh
│  └─ comando.py               ComandoCarga: base dos carregar_<app>
├─ validacao/                  sql.py, volumetria.py, arquivos.py, texto.py, limites.py, executor.py
├─ web/                        formatacao.py, paginacao.py, exportacao.py (csv + xlsx), stubs.py
├─ templatetags/               painel_filters.py (só filtros globais)
├─ pipeline.py  cache.py  middleware/  referencia/

apps/<app>/                    molde = GRP
├─ apps.py                     name="apps.<app>", label="<app>"
├─ models.py                   <App><Tabela> + Gold* (managed=False) + ResultadoValidacao do app
├─ loader.py                   SÓ os partial(...) + _LOADERS_<APP>
├─ services.py                 get_*_qs (ordenação determinística terminando em "pk")
├─ validacao/catalogo.py       só os testes do app (+ limites do app, se houver)
├─ views/                      um arquivo por sub-aba + _filtros.py (só os filtros do app)
├─ templatetags/<app>_filters.py   só se o app tiver filtro próprio
├─ sql/gold/NNN_vw_*.sql
├─ management/commands/        carregar_<app>, validar_<app> (finos, herdam do core)
└─ templates/<app>/  tests/

apps/dashboard/                casca (ex-apps/painel); sem comandos de gerenciamento
```

---

## 3. Fases

Cada fase começa conferindo os achados da seção 1 (o código pode ter mudado) e termina com:

```powershell
python manage.py check
python -m pytest -q -p no:cacheprovider 2>&1 | Select-Object -Last 3
git diff --stat
```

Depois, **⛔ parar e esperar o Gabriel**. Commit só com ordem dele (mensagem no padrão do
repositório, `refactor(<escopo>): ...`).

Para mover arquivos, use sempre `git mv`, que preserva o histórico. Nunca use copiar e apagar.

---

### Fase 1 · `core` vira app e recebe os comandos de pipeline

**Impacto no banco:** nenhum.

1. Criar `core/apps.py`:
   ```python
   class CoreConfig(AppConfig):
       default_auto_field = "django.db.models.BigAutoField"
       name = "core"
       label = "core"
       verbose_name = "Núcleo (pipeline e utilitários compartilhados)"
   ```
   Não criar `models.py` nem `migrations/`.
2. `config/settings/base.py`: incluir `"core"` no `INSTALLED_APPS`, como primeiro dos apps locais,
   e remover `"apps.pipeline"`.
3. `git mv` de `apps/pipeline/management/commands/{rodar_ingestao,rodar_silver,rodar_pipeline,gerar_schemas}.py`
   para `core/management/commands/`, criando os `__init__.py` de `core/management/` e
   `core/management/commands/`.
4. Remover `apps/pipeline/` (com `git rm` no que é versionado).
5. Apagar as pastas só com `.pyc`: `apps/convenios/`, `apps/dashboard/` e `apps/__pycache__/`.
   Antes, conferir que não há nenhum arquivo que não seja `.pyc`:
   `Get-ChildItem <pasta> -Recurse -File | Where-Object Extension -ne '.pyc'` deve sair vazio.
6. `tests/test_comandos_registrados.py`: trocar `"apps.pipeline"` por `"core"` (linhas 43 e 59) e
   revisar o comentário da linha 21.
7. Confirmar com `python manage.py help` que os 4 comandos aparecem uma única vez, sob `[core]`.

**Critério de pronto:** `check` limpo, suíte igual à linha de base e `apps/pipeline` inexistente.

---

### Fase 2 · Carga genérica no `core`

**Impacto no banco:** nenhum (mesma lógica, outro endereço).

1. Criar `core/carga/__init__.py` e `core/carga/loader.py` com o conteúdo comum de
   `apps/grp/loader.py:51-153`: `_silver_path`, `_para_date`, `_para_decimal`, `_para_str`,
   `_ler_parquet` e `carregar_tabela_generica`.
   - **`pandas` importado dentro das funções**, nunca no topo (CLAUDE.md §4). Hoje os loaders
     importam no topo; corrigir na mudança.
   - Mover `core/db.py` (`bulk_refresh`) para `core/carga/loader.py`, ou deixá-lo como
     `core/carga/refresh.py`. Apagar `core/db.py` depois de atualizar todos os imports.
   - Manter o comportamento: full refresh dentro de `transaction.atomic()`, confere colunas do
     parquet contra os campos do model e devolve o mesmo `dict` de hoje.
2. `apps/grp/loader.py` e `apps/sigcon/loader.py` ficam só com:
   ```python
   from functools import partial
   from core.carga.loader import carregar_tabela_generica
   from apps.grp.models import GrpInstrumento, ...

   carregar_grp_instrumento = partial(carregar_tabela_generica, "grp_instrumento", GrpInstrumento)
   ...
   _LOADERS_GRP = {"grp_instrumento": carregar_grp_instrumento, ...}   # se D2 = sim
   ```
3. Criar `core/carga/comando.py` com `ComandoCarga(BaseCommand)`, extraindo o corpo comum de
   `carregar_grp.py` e `carregar_sigcon.py`: argumento `--fonte` (repetível), laço sobre os
   loaders, `invalidar_cache_indicadores()` e o padrão de exceções do projeto (`FileNotFoundError` →
   `CommandError` curto; qualquer outra → `logger.exception` + `raise CommandError(...) from exc`).
   A subclasse só declara `loaders = _LOADERS_GRP` e `help`. Conferir o diff dos dois comandos
   antes: as 5 linhas diferentes têm que virar atributo da subclasse, não `if app == ...`.
   **Não mudar** o comportamento visível: mesmas mensagens e mesmos códigos de saída. Os testes
   `apps/grp/tests/test_carregar_grp.py`, `apps/sigcon/tests/test_carregar_sigcon.py` e
   `apps/sigcon/tests/test_excecoes_comandos.py` são a rede de segurança.
4. Atualizar imports:
   - `apps/sigcon/tests/test_bulk_refresh.py:15` (`from apps.sigcon.loader import _bulk_refresh`)
     → importar de `core.carga`. Como o teste agora cobre código do core, avaliar movê-lo para
     `tests/test_bulk_refresh.py`.
   - Qualquer `from core.db import` restante.
5. `core/pipeline.py`: conferir se referencia os comandos ou loaders pelo nome antigo
   (`_cargas_orm`, linha ~127) e ajustar.

**Critério de pronto:** nenhum `def carregar_tabela_generica` fora de `core/carga/`
(`git grep -n "def carregar_tabela_generica"` com um resultado só), comandos `carregar_grp` e
`carregar_sigcon` com menos de ~30 linhas, e suíte igual.

---

### Fase 3 · Validação genérica no `core`

**Impacto no banco:** nenhum (os testes de validação só fazem `SELECT`; o resultado continua indo
para o `ResultadoValidacao` de cada app).

1. `core/validacao/sql.py`: partir de `apps/sigcon/validacao/generico.py`, que é a versão mais
   completa (`_onde`, `_literal` e `filtro=` opcional em todos os geradores), e acrescentar
   `sql_sem_chave` do GRP (`apps/grp/validacao/generico.py:44`). O parâmetro `filtro` tem default
   `None`, então as chamadas do GRP continuam válidas. Conferir que o SQL gerado para o GRP é
   **idêntico** ao de hoje, com `filtro=None` (há testes em `tests/test_generico.py`).
2. `core/validacao/volumetria.py`: partir da versão do SIGCON e parametrizar o que hoje é fixo:
   `PREFIXO = "sigcon_"` e `tabelas_sigcon()` viram parâmetros (`prefixo`, `tabelas`). A pasta da
   silver deve vir de `settings.DATA_DIR`, e não de `settings.BASE_DIR / "data"` como no GRP.
3. `arquivos.py`, `texto.py` e `limites.py` (hoje só no SIGCON): ver o que é genérico. Exemplo:
   `teste_mojibake` e `severidade_efetiva` vão para `core/validacao/`; `LIMITES_CONHECIDOS` e a
   lista de arquivos esperados ficam em `apps/sigcon/validacao/`, porque são dados do app.
4. `core/validacao/executor.py`: extrair o laço comum de `validar_grp.py` e `validar_sigcon.py`
   (rodar o catálogo, gravar no model de resultado, amostra e severidade) para uma função ou classe
   base que recebe `testes`, `model_resultado` e as opções. `validar_<app>` passa a ser fino.
5. Em cada app sobra só `validacao/catalogo.py` (e os dados do app), importando de
   `core.validacao`.
6. Atualizar imports em: `apps/grp/validacao/catalogo.py`, `apps/sigcon/validacao/catalogo.py`,
   `apps/sigcon/validacao/arquivos.py`, os dois `validar_*.py`, `tests/test_generico.py`,
   `tests/test_catalogo_validacao.py`, `apps/sigcon/tests/test_validacao_sigcon.py`,
   `apps/sigcon/tests/test_validacao_sigcon_regras_novas.py` e
   `apps/sigcon/tests/test_carregar_sigcon.py:251`.

**Critério de pronto:** `apps/*/validacao/` sem `generico.py` nem `volumetria.py`; `validar_grp` e
`validar_sigcon` produzindo os mesmos resultados de antes (rodar os dois e comparar, já que só
fazem `SELECT`); suíte igual.

---

### Fase 4 · Apresentação: `painel` → `dashboard`, filtros e formatação no `core`

**Impacto no banco:** nenhum. `apps/painel` não tem models nem migrations; confirmar com
`python manage.py showmigrations painel` antes.

1. `git mv apps/painel apps/dashboard`. Em `apps/dashboard/apps.py`: `name="apps.dashboard"`,
   `label="dashboard"`, classe `DashboardConfig`. Atualizar `INSTALLED_APPS` e `config/urls.py:19`.
2. URL namespace: `app_name = "dashboard"` em `apps/dashboard/urls.py` e trocar `'painel:` por
   `'dashboard:` em `templates/base.html` (linhas 31, 37, 71, 77, 83, 89) e em
   `templates/painel/convenios.html`. Depois, `git grep -n "painel:"` não pode retornar nada em
   `.html` nem em `.py`.
3. `git mv templates/painel templates/dashboard` e atualizar os `render(..., "painel/...")` em
   `apps/dashboard/views/painel.py` (linhas 22, 29, 50, 55) e o `TEMPLATE_EM_CONSTRUCAO` em
   `core/web/stubs.py:5`. Conferir com `git grep -nE "[\"']painel/"`, que deve sair vazio.
4. Template tags: `git mv apps/painel/templatetags/painel_filters.py core/templatetags/painel_filters.py`
   (criar `core/templatetags/__init__.py`). O nome da biblioteca **continua `painel_filters`**,
   para não tocar nos `{% load %}` de 6 templates.
   - Mover `GRP_PARAMS` e `querystring_grp` (linhas 38–52) para
     `apps/grp/templatetags/grp_filters.py`. Em `apps/grp/templates/grp/_subtabs_grp.html`,
     acrescentar `{% load grp_filters %}`. Atualizar `apps/grp/tests/test_filtro_cd_uo.py:17`.
   - Atualizar `apps/dashboard/tests/test_filtros_globais.py:14`.
5. Formatação: criar `core/web/formatacao.py` com `fmt_data`, `fmt_valor` e
   `formatar_celula(campo, valor)` (por **prefixo** do campo, nunca `isinstance`; ARQUITETURA §8).
   Conferir que as versões GRP e SIGCON fazem a mesma coisa. Se divergirem, parar e mostrar a
   diferença ao Gabriel antes de escolher. `apps/grp/views/_filtros.py` e
   `apps/sigcon/views/_filtros.py` passam a importar daqui e mantêm só os filtros do app
   (`_ler_filtros_grp`, `_grp_listas`, `ler_filtros_sigcon`).
   **Não** unificar `_grp_render`/`sigcon_render` nesta fase: isso é o componente de consulta da
   S1-10 (decisão D4).
6. Exportação: unir `core/export/xlsx.py` e `core/web/exports.py` em `core/web/exportacao.py`.
   Atenção ao aviso em `apps/sigcon/views/exports.py:8`: **o módulo de exportação não pode importar
   pandas/numpy** (erro de OpenBLAS). Atualizar `apps/sigcon/views/_filtros.py:21-22` e o
   `__init__.py` de `core/web`. Apagar `core/export/`.
7. Atualizar `tests/test_cache_invalidacao.py:96,104` e `tests/test_comandos_registrados.py:62`
   (`"apps.painel"` → `"apps.dashboard"`).

**Critério de pronto:** `git grep -nE "apps\.painel|'painel:|\"painel:"` vazio; todas as telas
respondem (há `apps/dashboard/tests/test_rotas_smoke.py`); suíte igual. Se possível, subir o
`runserver` e abrir Início, GRP e SIGCON uma vez.

---

### Fase 5 · Gold legado em pandas sai do `core`

**Impacto no banco:** nenhum.

`core/gold/` faz cruzamentos em pandas/ORM. A ARQUITETURA (§2, §7) quer gold em SQL, e o core não
pode importar apps. Esta fase **só remove a dependência core → app**. A reescrita em SQL é trabalho
de sprint (S1-09 e seguintes), fora deste plano.

1. `core/gold/contrapartida.py` (importa `apps.sigcon.models`, linha 158) →
   `git mv` para `apps/sigcon/contrapartida.py`. Atualizar `apps/sigcon/services.py:153,466`,
   `apps/sigcon/views/convenios.py:15` e `tests/test_contrapartida.py:9`.
2. `core/gold/convenios.py` (agregações dos indicadores) → `apps/dashboard/indicadores.py`.
   Atualizar `apps/dashboard/services.py:39` e os testes que a importarem
   (`git grep -n "gold.convenios\|gold import convenios"`).
3. `core/gold/relacionamento.py` (1048 linhas; Gold SIGCON×SICONV): **investigar antes de mover**.
   O model `ConvenioIntegrado` não existe mais em `apps/sigcon/models.py`. Ver quem chama de fato:
   `core/pipeline.py`, `core/transform/chaves.py`, `core/ingestion/sources.py`,
   `tests/test_r3.py` e `tests/test_gold_preservacao.py`. Relatar ao Gabriel se está vivo ou
   morto e **não apagar sem ordem dele**. Se estiver vivo e for do SIGCON, vai para `apps/sigcon/`;
   se for da onda União (v1.3), anotar como pendência.
4. Ao final, `git grep -nE "(from|import) apps\." -- core` tem que sair **vazio**.

**Critério de pronto:** o core sem nenhum import de `apps.*`; `core/gold/` vazio ou removido;
suíte igual.

---

### Fase 6 · Label `convenios` → `sigcon` (só depois da decisão D3)

**Impacto no banco: sim.** O Claude **não executa** SQL de escrita (CLAUDE.md §6). Ele prepara o
código e o script, e o Gabriel roda.

Estado medido em 16/11/2026 (com `SELECT`): nenhuma tabela `convenios_*` existe, porque todos os
models têm `db_table = "sigcon_*"` explícito. O label só aparece em `django_migrations` (21 linhas,
`app='convenios'`) e em `django_content_type` (35 linhas, `app_label='convenios'`, várias de models
que não existem mais). O `auth_permission` acompanha o `content_type` pela FK.

1. Remedir com `SELECT` (os números podem ter mudado).
2. Código: em `apps/sigcon/apps.py`, `label = "sigcon"`, e reescrever a docstring (a justificativa
   atual, de que "renomearia 24 tabelas", não vale mais). Em todas as
   `apps/sigcon/migrations/*.py`, trocar as dependências `("convenios", "00xx_...")` por
   `("sigcon", ...)`. Conferir que nenhuma migration de outro app depende de `convenios`
   (em 16/11 nenhuma dependia). Revisar o comentário de `tests/test_comandos_registrados.py:21`.
3. Script para o Gabriel, em `docs/sql/renomear_label_sigcon.sql`, no formato do CLAUDE.md §6:
   ```sql
   -- pg_dump -Fc -d painel_convenios -f backup_antes_label_sigcon.dump
   BEGIN;
   UPDATE django_migrations   SET app = 'sigcon'       WHERE app = 'convenios';
   UPDATE django_content_type SET app_label = 'sigcon' WHERE app_label = 'convenios';
   SELECT app, COUNT(*) FROM django_migrations WHERE app IN ('convenios','sigcon') GROUP BY app;
   SELECT app_label, COUNT(*) FROM django_content_type WHERE app_label IN ('convenios','sigcon') GROUP BY app_label;
   ROLLBACK;
   -- COMMIT;
   ```
4. Ordem para o Gabriel: aplicar o código → rodar o script com `COMMIT` → depois disso,
   `python manage.py showmigrations sigcon` com tudo `[X]` e `python manage.py migrate --plan`
   **sem nenhuma operação pendente**. Se o `migrate --plan` listar operações, parar: algo saiu
   do sincronismo.
5. Não remover content types órfãos nesta fase. Apenas listá-los para o Gabriel.

**Critério de pronto:** `showmigrations sigcon` todo aplicado, `migrate --plan` vazio, suíte igual.

---

### Fase 7 · Documentação

1. `docs/ARQUITETURA.md`:
   - §3: substituir a árvore pela estrutura-alvo da seção 2 deste plano e remover a nota
     "o caminho exato do `loader.py` deve ser confirmado".
   - §5/§6: na seção "Carga", `carregar_tabela_generica` passa a morar em `core/carga/loader.py`;
     o app só tem `partial` + `_LOADERS_<APP>`; `carregar_<app>` herda de `ComandoCarga`.
   - §8: o componente de consulta compartilhado nasce em `core/web/` (se D4 = sim).
   - §16: uma linha por decisão, com data. Por exemplo: "`core` é app Django sem models: comandos
     de pipeline e funções compartilhadas"; "core nunca importa apps; apps nunca importam outros
     apps"; "`apps/painel` → `apps/dashboard`"; "label `sigcon`" (se a fase 6 rodou).
2. `CLAUDE.md`:
   - §3 (mapa): incluir `core/` com `management/commands/`, `carga/`, `validacao/`, `web/` e
     `templatetags/`, e trocar a linha `loader.py ... ⚠ confirmar caminho` por
     `core/carga/loader.py` (genérico) + `apps/<app>/loader.py` (só `partial`).
   - §4: acrescentar a regra de dependência (core ↛ apps; app ↛ app).
   - §5: "Loader" e "Comando de carga" apontando para os novos lugares.
3. `README.md`: conferir se cita `apps/pipeline`, `apps/painel` ou `core/export`, e corrigir.

**Critério de pronto:** `git grep -nE "apps/pipeline|apps\.pipeline|apps/painel|apps\.painel|core/export|core\.db" -- docs CLAUDE.md README.md`
sem nenhuma ocorrência fora de trechos históricos (relatórios datados em `docs/`, que não devem ser
reescritos).

---

## 4. Fora do escopo deste plano

Não fazer. Se encontrar, apontar em uma linha (CLAUDE.md §2):

- Unificar `_grp_render` e `sigcon_render` no componente de consulta (S1-10).
- Reescrever gold pandas em views SQL (S1-09 e seguintes).
- Pasta `etl/`, upsert e schemas `ctrl`/`hist` (v1.1).
- Redis em `config/settings/prod.py` (a ARQUITETURA §1 o declara fora do escopo; decisão do
  Gabriel).
- `apps/grp/sql/teste.sql`, arquivo solto fora de `sql/gold/`.
- `apps/grp/serializers.py`, arquivo vazio (o projeto não usa DRF).
- `pipeline_grp` e `aplicar_gold` (GRP): candidatos a generalização no core
  (`aplicar_gold --app <app>`), mas só depois de a gold do SIGCON existir.

## 5. Registro de execução

Preencher ao concluir cada fase (data, commit, resultado da suíte, observações).

| Fase | Data | Commit | Suíte | Observações |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
