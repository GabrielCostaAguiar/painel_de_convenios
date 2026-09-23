# Relatório — Adequação Django do Painel de Convênios

## Resumo executivo

Sete correções estruturais foram aplicadas ao painel, todas sem mudança de comportamento
para quem usa o sistema: nenhuma rota, nome de comando ou nome de tabela mudou. As duas
de maior efeito prático são a carga de dados, que agora é atômica — uma falha no meio
não deixa mais a tabela vazia —, e a invalidação de cache, que passou a ser automática
ao fim de qualquer carga em vez de depender de alguém lembrar de chamá-la. O resto é
organização: os comandos de lakehouse ganharam app próprio, e os dois maiores arquivos
do projeto (1360 e 968 linhas) viraram pacotes por domínio, sem gerar migração. A suíte
saiu de 119 para 177 testes, todos passando. Duas pendências de infraestrutura ficaram
registradas em `docs/CHECKLIST_DEPLOY.md` e precisam de decisão da Prodemge — em
particular, sem um cache compartilhado em produção a correção de invalidação não tem
efeito prático lá.

## Linha de base vs. resultado final

| Verificação | Antes | Depois |
|---|---|---|
| Testes (total / passando / falhando) | 119 / 119 / 0 | 177 / 177 / 0 |
| `manage.py check` | System check identified no issues (0 silenced) | System check identified no issues (0 silenced) |
| `makemigrations --check` | No changes detected | No changes detected |
| Nº de models no app convenios | 24 | 24 |
| Nº de URLs nomeadas no dashboard | 33 | 33 |

## Tarefas

### Tarefa 0 — Linha de base
- **Status:** ✅ concluída
- **O que foi feito:** Registrado o estado do repositório, classificados os 23 arquivos modificados/não rastreados e criada a branch `refactor/adequacao-django`. A suíte na linha de base estava verde.
- **Por quê:** Sem número de referência não há como provar que a refatoração não quebrou nada.
- **Arquivos alterados:** nenhum (sem commit).
- **Testes adicionados:** nenhum.
- **Commit:** — (tarefa sem commit)
- **Observações:** `pytest` não estava instalado no `.venv` — foi preciso rodar `pip install -r requirements-dev.txt` antes de medir a linha de base. Dos 23 arquivos pendentes, 21 eram do trabalho GRP (tipo a); 2 ficaram de fora e estão listados em "Pontos que precisam de decisão humana". Nada foi descartado.

### Tarefa 1 — Versionar o trabalho GRP e as migrações 0009–0011
- **Status:** ✅ concluída
- **O que foi feito:** Confirmado que os models GRP batem com as migrações (`makemigrations --check` limpo) e que o histórico completo aplica do zero num SQLite limpo (0001 → 0011). Commitados apenas os arquivos do trabalho GRP.
- **Por quê:** Migrações são código-fonte; fora do Git, outro ambiente gera numeração concorrente e cria dois históricos divergentes.
- **Arquivos alterados:** `apps/convenios/models.py`, `apps/convenios/loader.py`, `apps/dashboard/{services,views,urls}.py`, `apps/dashboard/templatetags/painel_filters.py`, `core/ingestion/sources.py`, migrações `0008`–`0011`, 7 schemas YAML `*_grp*`, `templates/base.html`, `templates/dashboard/{plano_aplicacao,_subtabs_grp,grp_generico}.html`.
- **Testes adicionados:** nenhum (tarefa de versionamento).
- **Commit:** `12c8f06` — `feat(grp): versiona models, migrações 0009–0011 e telas GRP em teste`
- **Observações:** `config/settings/dev.py` não lê `DATABASE_URL`, então o teste de migração do zero usou um módulo de settings temporário no diretório de scratch (fora do Git) que herda `dev.py` e troca só o `NAME` do banco. O arquivo SQLite temporário foi apagado ao final. A migração `0008` (não-GRP) entrou junto porque é elo da cadeia — sem ela, `0009` não aplica.

### Tarefa 2 — Full refresh atômico no `_bulk_refresh`
- **Status:** ✅ concluída
- **O que foi feito:** `_bulk_refresh` passou a envolver o `delete()` + `bulk_create()` em `transaction.atomic()`. Assinatura, dict de retorno e `batch_size=500` preservados (o batch size virou parâmetro com o mesmo default).
- **Por quê:** Sem transação, uma falha entre o delete e o insert deixava a tabela vazia e só um novo run bem-sucedido recuperava.
- **Arquivos alterados:** `apps/convenios/loader.py`.
- **Testes adicionados:** `apps/convenios/tests/test_bulk_refresh.py` — 4 casos.
- **Commit:** `1deb3ec` — `fix(loader): torna o full refresh atômico com transaction.atomic`
- **Observações:** Os 24 loaders passam todos pelo helper — a varredura por `.delete()` e `bulk_create` em `apps/` e `core/` só acerta `_bulk_refresh`, não há caminho paralelo. **Achado da investigação pedida:** os models da app não têm **nenhuma** FK nem sinal `pre_delete`/`post_delete`, então o `delete()` já cai no fast path do Django (um único `DELETE FROM`, sem carregar PKs) — por isso `TRUNCATE`/`_raw_delete` não traria ganho e não foi adotado. O caso de rollback foi conferido contra a versão antiga do helper: sem o `atomic` ele falha com a tabela zerada (0 registros em vez de 3), confirmando que o teste mede o que deveria.

### Tarefa 3 — Invalidação de cache centralizada
- **Status:** ✅ concluída
- **O que foi feito:** Novo `core/cache.py` com as chaves e `invalidar_cache_indicadores()`. Os 6 comandos de carga e `atualizar_painel()` passaram a invalidar automaticamente. `invalidar_cache()` continua exportado em `services.py`, delegando.
- **Por quê:** A invalidação antiga apagava só a chave base e deixava as variantes por ano servindo dado velho por até uma hora; e quase nenhum loader a chamava.
- **Arquivos alterados:** `core/cache.py` (novo), `apps/dashboard/services.py`, `core/pipeline.py`, os 6 `apps/convenios/management/commands/carregar_*.py`.
- **Testes adicionados:** `tests/test_cache_invalidacao.py` — 9 casos.
- **Commit:** `d44f29b` — `fix(cache): invalida indicadores automaticamente ao fim de toda carga`
- **Observações:** `core/pipeline.py` de fato importava `apps.dashboard.services` — a direção de dependência estava invertida e foi corrigida; `core/` não referencia mais `apps.dashboard` em lugar nenhum. O critério de invalidação do `atualizar_painel()` mudou de "o pipeline inteiro deu certo" para "pelo menos um loader ORM gravou": se `carregar_convenios` falha mas outros passam, o banco mudou e o cache precisa cair igual.

### Tarefa 4 — Mover os comandos de pipeline para um app próprio
- **Status:** ✅ concluída
- **O que foi feito:** Criado `apps/pipeline/` sem models; os 4 comandos movidos com `git mv` (rename puro, 0 linhas alteradas); `apps.pipeline` registrado no `INSTALLED_APPS`; `apps/dashboard/management/` removido por inteiro.
- **Por quê:** Comandos que operam o lakehouse inteiro não pertencem à camada de apresentação, e duas apps expondo o mesmo nome de comando resolvem ambiguamente pela ordem do `INSTALLED_APPS`.
- **Arquivos alterados:** `apps/dashboard/management/commands/{rodar_pipeline,rodar_ingestao,rodar_silver,gerar_schemas}.py → apps/pipeline/management/commands/`; `apps/pipeline/{__init__,apps.py}` (novos); `config/settings/base.py`; `core/pipeline.py` e `docs/ARQUITETURA.md` (referências de caminho).
- **Testes adicionados:** `tests/test_comandos_registrados.py` — 11 casos.
- **Commit:** `f0c9381` — `refactor(pipeline): move comandos de orquestração para o app apps.pipeline`
- **Observações:** `manage.py help` lista os 4 sob `[pipeline]` e o dashboard não registra nenhum comando. Os caminhos antigos em `docs/fase6_bronze.md` foram **mantidos de propósito**: aquele arquivo é o relato datado de uma fase concluída, e reescrevê-lo falsificaria o registro.

### Tarefa 5 — Transformar `models.py` em pacote
- **Status:** ✅ concluída
- **O que foi feito:** 1360 linhas e 24 models divididos em 5 arquivos por domínio, com `__init__.py` reexportando tudo e definindo `__all__`.
- **Por quê:** Arquivo desse tamanho dificulta leitura e faz qualquer mudança aparecer no meio de um diff enorme.
- **Arquivos alterados:** `apps/convenios/models.py → apps/convenios/models/sigcon.py`; novos `models/{__init__,codigos,gold,externos,grp}.py`.
- **Testes adicionados:** nenhum novo (as verificações da tarefa são estruturais; a suíte inteira cobre a regressão).
- **Commit:** `86cb04a` — `refactor(convenios): divide models.py em pacote por domínio`
- **Observações:** `base.py` não foi criado porque não existem abstract models nem mixins; FK por string também não foi necessária porque os models não têm nenhuma FK. As classes foram movidas byte a byte, conferido programaticamente que nenhuma linha do original ficou de fora, e cada grupo manteve a ordem de declaração original. Verificado: `check` limpo, `makemigrations --check` = "No changes detected", 24 models antes e depois com os mesmos `db_table`.

### Tarefa 6 — Transformar `views.py` em pacote
- **Status:** ✅ concluída
- **O que foi feito:** 968 linhas divididas em 6 arquivos por tela, com `__init__.py` reexportando tudo que `urls.py` referencia. `urls.py` não mudou uma linha.
- **Por quê:** Mesma razão da Tarefa 5.
- **Arquivos alterados:** `apps/dashboard/views.py → apps/dashboard/views/sigcon.py`; novos `views/{__init__,_helpers,painel,exports,grp,stubs}.py`.
- **Testes adicionados:** `apps/dashboard/tests/test_rotas_smoke.py` — 34 casos.
- **Commit:** `8c49a34` — `refactor(dashboard): divide views.py em pacote por tela`
- **Observações:** O inventário de URLs foi levantado antes da divisão e comparado depois: as 33 rotas nomeadas têm exatamente os mesmos nomes e caminhos, mudando só o módulo de origem de cada função. **Nenhuma rota precisou de `xfail`** — todas as 33 respondem 200 com banco vazio. Duas alterações deliberadas e inertes: o import morto `from django.http import request` não foi propagado (em toda view o nome é o parâmetro da função, que sombreia o módulo), e o banner de comentário acima de `_ler_filtros_sigcon` foi reescrito porque o texto antigo descrevia a view `sigcon`, que foi para outro arquivo.

### Tarefa 7 — Checklist de deploy
- **Status:** ⚠️ concluída com ressalva
- **O que foi feito:** Diagnóstico registrado em `docs/CHECKLIST_DEPLOY.md`: os avisos do `check --deploy`, a resposta sobre arquivos estáticos e três achados mais graves fora do check. Nada em `prod.py` foi alterado.
- **Por quê:** `check --deploy` é a checklist oficial de segurança do Django, mas as decisões dependem do ambiente da Prodemge.
- **Arquivos alterados:** `docs/CHECKLIST_DEPLOY.md` (novo).
- **Testes adicionados:** nenhum (tarefa de diagnóstico).
- **Commit:** `05be5ec` — `docs(deploy): registra diagnóstico do check --deploy e estratégia de estáticos`
- **Ressalva:** O comando **não roda como especificado** neste ambiente: `psycopg` não está nos requirements, então ele aborta com `ImproperlyConfigured` antes de chegar aos checks. O diagnóstico foi obtido com um módulo de settings temporário (fora do Git) que herda `prod.py` inteiro e troca só o `ENGINE` para SQLite — nenhum check do `--deploy` inspeciona o banco. Também vale notar que `prod.py` lê `DB_NAME`/`DB_USER`/`DB_PASSWORD` separados, não uma `DATABASE_URL`.
- **Observações:** Resultado: 2 avisos (`security.W005` e `W021`, ambos sobre HSTS em subdomínios), nenhum bloqueador — `prod.py` já cobre `DEBUG=False`, SSL redirect, cookies seguros e HSTS. Sobre estáticos: `STATIC_ROOT` está definido e `collectstatic` roda limpo (131 arquivos), mas **WhiteNoise não está no `MIDDLEWARE` de prod** (só dentro do `MODO_COMPARTILHAR` de `dev.py`). Não foi adicionado — se o nginx da Prodemge já serve `/static/`, colocar WhiteNoise seria pôr o Python no caminho de cada arquivo estático à toa.

### Tarefa 8 — Documentação e fechamento
- **Status:** ✅ concluída
- **O que foi feito:** `CLAUDE.md`, `README.md` e `docs/ARQUITETURA.md` atualizados; este relatório versionado; suíte e checks rodados de novo e comparados com a linha de base.
- **Por quê:** Documentação que aponta para caminhos que não existem mais é pior que documentação nenhuma.
- **Arquivos alterados:** `CLAUDE.md`, `README.md`, `docs/ARQUITETURA.md`, `docs/ADEQUACAO_DJANGO.md` (novo).
- **Testes adicionados:** nenhum.
- **Commit:** `docs: atualiza CLAUDE.md, README e arquitetura após adequação Django`
- **Observações:** A afirmação "There are no automated tests at this time" do `CLAUDE.md` foi substituída por uma tabela com as 13 suítes e a contagem atual. Registradas as três regras novas: full refresh sempre atômico, invalidação via `core/cache.py`, e `core/` não importa de `apps/dashboard/`.

## Decisões que tomei sozinho

1. **Invalidação de cache por número de versão, não por enumeração de anos.** O prompt deixava a escolha em aberto. A enumeração falha exatamente quando mais importa — se uma carga remove um ano do conjunto de dados, a chave daquele ano não aparece mais em `get_anos_disponiveis()` e nunca seria apagada — e forçaria `core/` a consultar o ORM do painel, contrariando a direção de dependência que a própria tarefa pedia para respeitar. A versão resolve tudo numa operação e funciona igual em LocMemCache e Redis.
2. **Instalar `requirements-dev.txt` no `.venv`.** `pytest` não estava instalado; sem isso não havia como medir a linha de base. Nenhum arquivo do repositório foi alterado por isso.
3. **Settings temporários no diretório de scratch** (fora do Git) para o teste de migração do zero e para o `check --deploy`, já que `dev.py` não lê `DATABASE_URL` e o driver do PostgreSQL não está instalado.
4. **Não propagar o import morto `from django.http import request`** para os 6 novos arquivos de views. É provadamente inerte (sempre sombreado pelo parâmetro da função) e replicá-lo espalharia ruído.
5. **Manter os caminhos antigos em `docs/fase6_bronze.md`.** É relato datado de uma fase concluída, não documentação viva.
6. **`batch_size` como parâmetro com default 500** em vez do valor fixo, preservando exatamente o comportamento atual e deixando o número ajustável.
7. **Não criar `base.py` no pacote de models** nem usar FK por string: não existem abstract models, mixins ou FKs no app.

## Pendências observadas (fora de escopo — NÃO corrigidas)

1. **`templates/base.html` está com a tag `<nav>` da sidebar sem fechamento.** O bloco do GRP foi adicionado no lugar do `</nav>`. Os navegadores fecham sozinhos, então renderiza, mas é HTML inválido. Gravidade: baixa.
2. **`psycopg` não está nos requirements**, embora `prod.py` use o backend PostgreSQL. Um ambiente montado a partir dos requirements não sobe. Gravidade: **alta** — detalhado em `docs/CHECKLIST_DEPLOY.md`.
3. **`CACHES` não é configurado em lugar nenhum**, então o Django cai no LocMemCache, que é por processo. Com múltiplos workers em produção, a invalidação automática da Tarefa 3 não atinge nenhum worker do painel — a carga roda em processo à parte. Gravidade: **alta**.
4. **WhiteNoise ausente do `MIDDLEWARE` de prod.** Com `DEBUG=False` e nada na frente servindo `/static/`, o painel sobe sem CSS. Gravidade: alta, mas pode já estar resolvida pela infraestrutura.
5. **`GOLD_CACHE_SECONDS` não existe nas settings** — funciona pelo default de 3600 s em `services.py`, mas o número fica invisível para quem opera. Gravidade: baixa.
6. **`UnorderedObjectListWarning` em 5 telas** (`plano_aplicacao`, `cronograma`, `prorrogacao`, `termo_aditivo`, `unidades_executoras`): paginação sobre queryset sem `order_by`, o que pode repetir ou pular registros entre páginas. Gravidade: média.
7. **`core/ingestion/sources.py` sem newline no fim do arquivo.** Gravidade: cosmética.
8. **`except (FileNotFoundError, Exception)` nos comandos de carga** captura tudo e converte em `CommandError`, escondendo o traceback original. Gravidade: baixa.
9. **A carga GRP não é executável pela CLI** — não há comando de gerência ligando os loaders GRP. Fora de escopo por instrução explícita.

## Pontos que precisam de decisão humana

1. **`inspecionar.py` na raiz do repositório** (não rastreado). É script exploratório ad-hoc, com caminho e nomes de coluna fixos no código, apontando para um arquivo Bronze específico. Não foi commitado nem apagado. Decidir: descartar, ou mover para uma pasta de scripts auxiliares?
2. **`.claude/settings.local.json` modificado** (arquivo rastreado). As 16 entradas novas são permissões de ferramenta apontando para um diretório de scratch de uma sessão anterior, que já não existe. Ficou modificado na árvore de trabalho, sem commit. Decidir: commitar, reverter ou limpar as entradas obsoletas?
3. **`templates/base.html` mudou "Casa Civil · MG" para "Secretaria Geral · MG".** Entrou junto no commit do GRP por estar no mesmo arquivo, mas é mudança de identidade institucional, não trabalho GRP. Confirmar se é intencional.
4. **Cache compartilhado em produção** (Redis ou `DatabaseCache`) — ver pendência 3. Sem isso a Tarefa 3 não tem efeito prático em produção.
5. **Quem serve `/static/` em produção**: servidor web da Prodemge ou WhiteNoise?
6. **`SECURE_HSTS_INCLUDE_SUBDOMAINS`** (`security.W005`): só pode ser ligado se todos os subdomínios forem exclusivamente HTTPS — informação que está com a Prodemge.

## Git

- Branch: `refactor/adequacao-django`
- Commits (em ordem):
  - `12c8f06` feat(grp): versiona models, migrações 0009–0011 e telas GRP em teste
  - `1deb3ec` fix(loader): torna o full refresh atômico com transaction.atomic
  - `d44f29b` fix(cache): invalida indicadores automaticamente ao fim de toda carga
  - `f0c9381` refactor(pipeline): move comandos de orquestração para o app apps.pipeline
  - `86cb04a` refactor(convenios): divide models.py em pacote por domínio
  - `8c49a34` refactor(dashboard): divide views.py em pacote por tela
  - `05be5ec` docs(deploy): registra diagnóstico do check --deploy e estratégia de estáticos
  - `7afc68a` docs: atualiza CLAUDE.md, README e arquitetura após adequação Django
  - `(este commit)` docs: preenche o resultado do push no relatório
- Push: **sucesso** — https://github.com/GabrielCostaAguiar/painel_de_convenios/tree/refactor/adequacao-django
- PR: **não aberto** — o `gh` CLI não está instalado neste ambiente
  (`gh: command not found`), então o PR draft não pôde ser criado por linha de
  comando. Abrir manualmente em
  https://github.com/GabrielCostaAguiar/painel_de_convenios/pull/new/refactor/adequacao-django
  (comparação: `main...refactor/adequacao-django`), com o conteúdo deste
  documento como descrição. **Não foi feito merge.**

## Como revisar / reverter

- **Para revisar o conjunto:** `git log main..refactor/adequacao-django --stat`
- **Para revisar uma tarefa só:** `git show <hash>`
- **Para conferir que as divisões preservaram o conteúdo:**
  `git show 86cb04a --stat` e `git show 8c49a34 --stat` — nas Tarefas 5 e 6 o que importa
  é que `makemigrations --check` continue limpo e que o inventário de rotas bata.
- **Para reverter uma tarefa isolada:** `git revert <hash>`
- **Dependências entre tarefas:**
  - a Tarefa 8 (docs) depende das 4, 5, 6 e 7 — reverter qualquer uma delas deixa a
    documentação descrevendo uma estrutura que não existe mais;
  - a Tarefa 3 depende da 1 apenas por ordem de commit, não logicamente;
  - as Tarefas 2, 4, 5 e 6 são independentes entre si e podem ser revertidas isoladamente.
