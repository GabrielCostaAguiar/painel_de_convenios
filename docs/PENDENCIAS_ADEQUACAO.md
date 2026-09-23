# Relatório — Pendências da adequação Django

## Resumo executivo

As nove pendências que a rodada anterior deixou registradas foram corrigidas. As de maior
efeito estão no deploy: o driver do PostgreSQL entrou nos requirements (sem ele o
ambiente de produção nem subia), o cache passou a ser compartilhado entre workers (sem
isso a invalidação automática não chegava a nenhum deles) e o WhiteNoise passou a servir
os arquivos estáticos. No painel, as cinco telas que paginavam sem ordenação passaram a
ter ordem determinística — antes o usuário podia ver o mesmo convênio em duas páginas e
nunca ver outro. O GRP ganhou comando de carga próprio, mas continua fora do pipeline
diário por padrão. A suíte foi de 177 para 247 testes, todos passando, inclusive com o
aviso de paginação tratado como erro. Nada mais bloqueia o deploy; o que resta são três
perguntas para a Prodemge, todas sem impacto operacional.

## Linha de base vs. resultado final

| Verificação | Antes | Depois |
|---|---|---|
| Testes (total / passando / falhando) | 177 / 177 / 0 | 247 / 247 / 0 |
| Testes com UnorderedObjectListWarning como erro | 172 passando / 5 falhando | 247 passando / 0 falhando |
| `manage.py check` | no issues (0 silenced) | no issues (0 silenced) |
| `makemigrations --check` | No changes detected | No changes detected |
| `check --deploy` (nº de avisos) | 2 (W005, W021) — e o comando **abortava** antes dos checks, por falta do psycopg | 2 (W005, W021) — agora roda de verdade |

## Decisões aplicadas (D1–D6)

| # | Decisão | Como foi aplicada | Evidência |
|---|---|---|---|
| D1 | `inspecionar.py`: não tocar | Nunca foi adicionado, movido, apagado nem incluído no `.gitignore`. Cada `git add` nomeou caminhos explícitos. | `git status` ainda mostra `?? inspecionar.py`; a varredura dos commits da branch não encontra o arquivo |
| D2 | `.claude/settings.local.json`: delegado | Saiu do índice com `git rm --cached`, entrou no `.gitignore`, e a cópia local foi limpa de 40 para 20 entradas | Tarefa 1 |
| D3 | "Secretaria Geral · MG" é intencional | Preservado ao fechar a tag `<nav>`; há teste fixando o texto e recusando "Casa Civil" | `test_sidebar_traz_a_identificacao_institucional` |
| D4 | Cache compartilhado autorizado | `prod.py` usa Redis com `REDIS_URL`, senão `DatabaseCache` | Tarefa 4 |
| D5 | WhiteNoise em prod | Middleware logo após o `SecurityMiddleware`, com `CompressedManifestStaticFilesStorage` | Tarefa 5 |
| D6 | HSTS de subdomínios desligado, mas configurável | `env.bool(..., default=False)` para as duas variáveis | Tarefa 9 |

## Tarefas

### Tarefa 0 — Linha de base e branch
- **Status:** ✅ concluída
- **O que foi feito:** `git fetch`, verificação de que `refactor/adequacao-django` **não** foi mergeada em `main`, e criação de `fix/pendencias-adequacao` empilhada sobre ela. Medidas as quatro referências da linha de base.
- **Por quê:** Sem número de referência não há como provar que nada regrediu.
- **Arquivos alterados:** nenhum (sem commit).
- **Testes adicionados:** nenhum.
- **Commit:** — (tarefa sem commit)
- **Observações:** **`origin/main` avançou 4 commits durante o intervalo**, com um deploy para PythonAnywhere que rebaixa Django para 5.2.17, pandas para 2.2.3 e numpy para 1.26.4, e regrava `requirements.txt` em **UTF-16** (é por isso que o git o trata como binário). Essa divergência não foi mergeada nem resolvida — está fora do escopo — mas afeta diretamente o resultado da Tarefa 3 e o checklist de deploy. Ver "Pontos que precisam de decisão humana".

### Tarefa 1 — `.claude/settings.local.json` deixa de ser versionado
- **Status:** ✅ concluída
- **O que foi feito:** `git rm --cached` (o arquivo continua no disco), entrada no `.gitignore` cobrindo também o `.bak`, e expurgo das entradas obsoletas na cópia local, com backup e revalidação do JSON.
- **Por quê:** Por convenção do Claude Code, `settings.json` é a configuração compartilhada e `settings.local.json` é por máquina; versionar o local espalha permissões e caminhos de uma sessão para toda a equipe.
- **Arquivos alterados:** `.gitignore`; `.claude/settings.local.json` saiu do índice.
- **Testes adicionados:** nenhum (mudança de versionamento).
- **Commit:** `22ad04b` — `chore(claude): para de versionar settings.local.json (configuração pessoal)`
- **Observações:** 20 das 40 entradas removidas — 7 apontando para `C:\Users\M1578465\Projetos\painel_de_convenios` (local antigo do repositório, confirmado inexistente), 11 para o scratchpad da sessão `0df47ded` e 2 para `apps/convenios/models.py`, que virou pacote. Sobre as do scratchpad: a pasta **ainda existe em disco**, mas o UUID é único por sessão e a permissão nunca voltaria a casar, então foram tratadas como obsoletas. `.claude/settings.json` não foi tocado. O backup foi apagado ao final.

### Tarefa 2 — `<nav>` e newline
- **Status:** ✅ concluída
- **O que foi feito:** `</nav>` devolvido ao ponto correto (após o item GRP, antes do `.sidebar-foot`) e newline final acrescentado aos 4 arquivos `.py` versionados que estavam sem.
- **Por quê:** HTML com tag aberta depende da adivinhação do navegador, que varia entre eles e atrapalha leitor de tela.
- **Arquivos alterados:** `templates/base.html`, `apps/convenios/loader.py`, `apps/dashboard/services.py`, `core/ingestion/baixar_siconv.py`, `core/ingestion/sources.py`, `apps/dashboard/tests/test_rotas_smoke.py`.
- **Testes adicionados:** `apps/dashboard/tests/test_rotas_smoke.py` — 2 casos.
- **Commit:** `e1b0a19` — `fix(template): fecha a tag nav da sidebar e normaliza fim de arquivo`
- **Observações:** A sidebar inteira, incluindo o rodapé, estava dentro da região de navegação. O teste usa `html.parser` da stdlib para conferir o balanceamento de `nav/aside/main/body/html` na página renderizada — conferido contra o template quebrado, em que falha. A varredura de newline encontrou 3 arquivos além do previsto; `inspecionar.py` ficou de fora por não ser versionado.

### Tarefa 3 — `psycopg` e `redis`
- **Status:** ✅ concluída
- **O que foi feito:** `psycopg[binary]==3.3.6` e `redis==8.1.0` acrescentados a `requirements.txt`, que é a camada que produção instala.
- **Por quê:** `prod.py` usa o backend PostgreSQL, e sem o driver nenhum comando que toque o banco roda.
- **Arquivos alterados:** `requirements.txt`.
- **Testes adicionados:** nenhum diretamente; os testes da Tarefa 4 dependem de ambos.
- **Commit:** `492cc4d` — `fix(deps): adiciona psycopg e redis aos requirements de produção`
- **Observações:** A versão mínima foi conferida no código do Django 6.0 (`django/db/backends/postgresql/base.py` exige psycopg >= 3.1.12); 3.3.6 atende. A variante `[binary]` traz a libpq no wheel, dispensando `libpq-dev` e compilador na máquina de deploy. `django-redis` não foi adicionado — o backend nativo basta. Validação end-to-end: depois da instalação, `createcachetable` com settings de prod chega até a **autenticação** do PostgreSQL, em vez de morrer no import — prova de que o driver carrega.

### Tarefa 4 — Cache compartilhado + `GOLD_CACHE_SECONDS`
- **Status:** ✅ concluída
- **O que foi feito:** `prod.py` escolhe `RedisCache` (com `REDIS_URL`) ou `DatabaseCache` na tabela `painel_cache`; `dev.py` declara `LocMemCache` explicitamente; `GOLD_CACHE_SECONDS` virou setting em `base.py`.
- **Por quê:** `LocMemCache` é por processo — com vários workers, a invalidação disparada pelo comando de carga não chega a nenhum deles.
- **Arquivos alterados:** `config/settings/{base,dev,prod}.py`, `core/cache.py`, `apps/dashboard/services.py`, `tests/test_cache_invalidacao.py`, `tests/test_settings_prod.py`.
- **Testes adicionados:** `tests/test_settings_prod.py` — 8 casos; `tests/test_cache_invalidacao.py` — 3 casos novos.
- **Commit:** `4da7992` — `fix(cache): usa cache compartilhado em produção (Redis ou banco)`
- **Observações:** **A verificação de compatibilidade entre backends encontrou um bug real.** A invalidação usava `cache.incr()`, cuja semântica muda com o backend: `LocMemCache` sobrescreve `incr()` e preserva a expiração; `RedisCache` usa o `INCR` nativo, que também preserva o TTL; mas `DatabaseCache` **não** sobrescreve `incr()` e cai no `BaseCache.incr`, que faz `self.set(chave, valor)` sem timeout — trocando o "nunca expira" do contador de versão pelo padrão de 300 s. Como o `DatabaseCache` é justamente o backend de produção sem Redis, o contador morreria em 5 minutos enquanto as entradas de indicador vivem 1 hora, a versão voltaria ao valor inicial e o painel serviria de novo dado antigo. Corrigido: a versão é lida e regravada com `timeout=None` explícito, e o relógio entra como piso do novo valor para duas cargas simultâneas nunca chegarem ao mesmo número. Há teste que grava no `DatabaseCache` e confere a coluna `expires`; ele falha contra a versão com `incr()`. **Ressalva:** `createcachetable --dry-run` exige conexão real com o PostgreSQL (o comando introspecciona as tabelas), então não pôde ser validado aqui — registrado no checklist.

### Tarefa 5 — Estáticos com WhiteNoise
- **Status:** ✅ concluída
- **O que foi feito:** WhiteNoise inserido em `prod.py` logo após o `SecurityMiddleware`, com `CompressedManifestStaticFilesStorage`; `STATIC_ROOT` ficou sobrescrevível por variável.
- **Por quê:** Com `DEBUG=False` o Django não serve `/static/`; se nada na frente servir, o painel sobe sem CSS.
- **Arquivos alterados:** `config/settings/{base,prod}.py`, `tests/test_settings_prod.py`.
- **Testes adicionados:** `tests/test_settings_prod.py` — 5 casos novos.
- **Commit:** `c463eb3` — `fix(static): serve estáticos em produção com WhiteNoise`
- **Observações:** A inserção é por índice e condicional, para não duplicar caso o middleware um dia entre no `base.py`. O `Manifest` falha no `collectstatic` se algum CSS referenciar arquivo inexistente — rodado com settings de prod, **passou**: 133 arquivos copiados, 399 pós-processados, nenhuma referência quebrada. Por isso não foi preciso rebaixar para `CompressedStaticFilesStorage`. O `staticfiles/` gerado no teste foi apagado.

### Tarefa 6 — Ordenação determinística
- **Status:** ✅ concluída
- **O que foi feito:** `order_by` aplicado nas 5 funções de serviço que alimentam telas paginadas, cada um terminando em `"pk"`; `pytest.ini` passou a tratar `UnorderedObjectListWarning` como erro.
- **Por quê:** Paginar sem ordem faz o banco devolver ordens diferentes a cada consulta — o usuário vê um registro em duas páginas e nunca vê outro.
- **Arquivos alterados:** `apps/dashboard/services.py`, `pytest.ini`.
- **Testes adicionados:** `apps/dashboard/tests/test_ordenacao.py` — 20 casos.
- **Commit:** `2c68d66` — `fix(services): ordena querysets paginados de forma determinística`
- **Observações:** **Achado durante os testes:** três serviços tinham retorno antecipado (`Model.objects.none(), context`) para o caso "convênio não encontrado", e esse caminho escapava do `order_by`. O contrato passou a ser "sempre devolve queryset ordenado", inclusive vazio. Nenhum índice novo foi criado — geraria migração. Tabela de ordenações na seção própria, abaixo.

### Tarefa 7 — Tratamento de exceção nos comandos
- **Status:** ✅ concluída
- **O que foi feito:** Os 6 comandos de carga passaram a distinguir `FileNotFoundError` (esperado, mensagem curta) de qualquer outra exceção (inesperada, `logger.exception` + `raise ... from exc`). Os dois laços por item do pipeline ganharam também um `except Exception`.
- **Por quê:** `except (FileNotFoundError, Exception)` é tupla redundante e escondia o traceback: quando uma carga falhava, sobrava mensagem genérica.
- **Arquivos alterados:** os 6 `apps/convenios/management/commands/carregar_*.py`, `core/pipeline.py`.
- **Testes adicionados:** `apps/convenios/tests/test_excecoes_comandos.py` — 14 casos.
- **Commit:** `6f3ffde` — `fix(commands): distingue erro esperado de inesperado e preserva o traceback`
- **Observações:** **Semântica do pipeline — como era e como ficou:** `_etapa_silver` e `_etapa_gold_orm` chamam cada item via `call_command` dentro de um `try` e capturavam **apenas `CommandError`**. Como os comandos continuam levantando `CommandError`, o comportamento observável não mudou; mas qualquer exceção que escapasse sem virar `CommandError` derrubaria o laço inteiro, e as cargas seguintes nem seriam tentadas. Os dois laços passaram a ter também um `except Exception` por item, com `logger.exception`, como rede de segurança. Há teste em que uma carga estoura `RuntimeError` e as demais ainda rodam. Os comandos legados `rodar_transformacao` e `carregar_silver` não foram tocados.

### Tarefa 8 — Carga GRP pela CLI
- **Status:** ✅ concluída
- **O que foi feito:** Novo comando `carregar_grp` (todas as 7 fontes ou `--fonte` repetível) e etapa GRP **opcional** no pipeline, controlada por `PIPELINE_INCLUIR_GRP` (default `False`).
- **Por quê:** Os 7 loaders GRP existiam mas nenhum comando os chamava — só dava para popular as telas abrindo um shell.
- **Arquivos alterados:** `apps/convenios/management/commands/carregar_grp.py` (novo), `config/settings/base.py`, `core/pipeline.py`.
- **Testes adicionados:** `apps/convenios/tests/test_carregar_grp.py` — 14 casos.
- **Commit:** `7918962` — `feat(grp): adiciona comando carregar_grp e etapa opcional no pipeline`
- **Observações:** Os 7 loaders já passavam pelo `_bulk_refresh` atômico — nada a ajustar. Sobre a ordem de carga: os models do GRP **não têm nenhuma ForeignKey** entre si (tabelas planas ligadas por `nr_grp` na consulta), então a ordem não afeta consistência; `dcgce_dados_grp` vem primeiro por ser a tabela de onde as telas tiram a lista de instrumentos. Verificado com os dados reais: as 7 carregam, 67.226 linhas. Com `PIPELINE_INCLUIR_GRP=False`, `rodar_pipeline` fica idêntico ao anterior — conferido: 19 fontes Silver e 18 cargas ORM, sem `carregar_grp`.

### Tarefa 9 — HSTS configurável
- **Status:** ✅ concluída
- **O que foi feito:** `SECURE_HSTS_INCLUDE_SUBDOMAINS` e `SECURE_HSTS_PRELOAD` passaram a ser lidos do ambiente, com default `False`. `SECURE_HSTS_SECONDS` intocado.
- **Por quê:** Ligar sem confirmar que todos os subdomínios são HTTPS tornaria inacessível qualquer subdomínio em HTTP — e isso não se desfaz do lado do servidor.
- **Arquivos alterados:** `config/settings/prod.py`, `tests/test_settings_prod.py`.
- **Testes adicionados:** `tests/test_settings_prod.py` — 4 casos novos.
- **Commit:** `8220cf4` — `chore(security): torna HSTS de subdomínios configurável, desligado por padrão`
- **Observações:** Conferido nos dois sentidos: com o default, o `check --deploy` acusa exatamente os mesmos 2 avisos de antes; com as variáveis em `True`, W005 e W021 desaparecem.

### Tarefa 10 — Documentação e publicação
- **Status:** ✅ concluída
- **O que foi feito:** `docs/CHECKLIST_DEPLOY.md` reescrito (os três bloqueadores viraram passo a passo), `CLAUDE.md` e `README.md` atualizados, este relatório versionado, e verificação final comparada com a linha de base.
- **Por quê:** O checklist anterior descrevia três bloqueadores que não existem mais.
- **Arquivos alterados:** `docs/CHECKLIST_DEPLOY.md`, `docs/PENDENCIAS_ADEQUACAO.md` (novo), `CLAUDE.md`, `README.md`.
- **Testes adicionados:** nenhum.
- **Commit:** `docs: atualiza checklist de deploy, CLAUDE.md e README após pendências`
- **Observações:** O checklist ganhou seção "Passo a passo de deploy" com as variáveis de ambiente e os comandos na ordem, mais a nota de que `createcachetable` só é necessário sem Redis. `CLAUDE.md` registra as regras novas: padrão de exceção dos comandos, `order_by` terminando em `pk`, cache compartilhado obrigatório em produção e a proibição de voltar ao `cache.incr()`.

## Tabela de ordenação das telas (Tarefa 6)

| Tela | Função de serviço | `order_by` aplicado | Motivo |
|---|---|---|---|
| Plano de Aplicação | `get_plano_aplicacao_qs` | `convenio_numero_sequencial_siafi`, `convenio_codigo`, `ano_exercicio_programa_trabalho`, `funcional_programatica_formatado`, `pk` | Colunas da tela da esquerda para a direita (SIAFI, SIGCON, Ano Exercício, Dotação); a dotação desempata linhas do mesmo exercício |
| Cronograma de Desembolso | `get_cronograma_qs` | `convenio_numero_sequencial_siafi`, `convenio_codigo`, `ano_cronograma_desembolso`, `mes_cronograma_desembolso`, `pk` | Mesma leitura da tela, terminando na ordem cronológica das parcelas |
| Prorrogação de Ofício | `get_prorrogacao_qs` | `prorrogacao_oficio_codigo_convenio`, `prorrogacao_oficio_codigo`, `pk` | Chave de ligação da tela (código do convênio) e depois o identificador da própria prorrogação |
| Termo Aditivo | `get_termos_aditivos_qs` | `termo_aditivo_codigo_sequencial`, `termo_aditivo_numero_termo_aditivo`, `pk` | `TermoAditivo` não tem `convenio_codigo` (a ligação é via `CodigoTermoAditivo`); a chave natural é o código sequencial, e o nº do TA ordena os aditivos do mesmo convênio |
| Unidades Executoras | `get_unidades_executoras_qs` | `convenio_codigo`, `convenio_numero_sequencial_siafi`, `unidade_orcamentaria_codigo`, `unidade_executora`, `pk` | Exatamente as 4 colunas da tela, nessa ordem |

Nenhuma tela tinha ordenação pretendida registrada (não há parâmetro de ordenação, comentário
ou referência no `docs/bases qlikview.txt`), então o critério foi a chave de negócio mais
natural de cada uma. Como tela, export CSV e export XLSX compartilham a mesma função de
serviço, **os arquivos baixados passam a sair na mesma ordem da tela** — o que é desejado.

**Sugestão de índice (não criada, geraria migração):** as ordenações de Plano de Aplicação
e Cronograma começam por `(convenio_numero_sequencial_siafi, convenio_codigo)`; um índice
composto nesse par ajudaria as duas. Ambos os models já têm índice em
`convenio_codigo`/chave composta, então o ganho deve ser modesto — vale medir antes.

## Inventário GRP (Tarefa 8)

| Fonte | Loader | Schema YAML | `rodar_silver` ok? | Carga ok? |
|---|---|---|---|---|
| `dcgce_dados_grp` | `carregar_dados_grp` | ✅ | ✅ | ✅ 4.799 linhas |
| `dcgce_cronograma_desembolso_grp` | `carregar_cronograma_desembolso_grp` | ✅ | ✅ | ✅ 18.889 linhas |
| `dcgce_recursos_contrapartida_grp` | `carregar_recurso_contrapartida_grp` | ✅ | ✅ | ✅ 6.599 linhas |
| `dcgce_recursos_concedente_grp` | `carregar_recurso_concedente_grp` | ✅ | ✅ | ✅ 4.928 linhas |
| `dcgce_plano_aplicacao_grp` | `carregar_plano_aplicacao_grp` | ✅ | ✅ | ✅ 7.208 linhas |
| `dcgce_plano_aplicacao_grp_detalhes` | `carregar_plano_aplicacao_grp_detalhes` | ✅ | ✅ | ✅ 24.231 linhas |
| `dcgce_esfera_grp` | `carregar_esfera_grp` | ✅ | ✅ | ✅ 572 linhas |

As 7 estão registradas em `FONTES`, têm Bronze e Silver gerados, e todas passam pelo
`_bulk_refresh` atômico. Total carregado: 67.226 linhas.

## Decisões que tomei sozinho

1. **Piso pelo relógio no número de versão do cache.** Além de trocar `cache.incr()` por
   leitura + regravação, a nova versão é `max(atual + 1, time.time())`. Sem isso, duas
   cargas simultâneas que lessem a mesma versão chegariam ao mesmo número, e entradas
   gravadas entre elas continuariam visíveis. O timestamp só cresce, então não repete.
2. **Remover também as entradas do scratchpad de `settings.local.json`**, embora a pasta
   ainda exista em disco: o UUID é por sessão e a permissão nunca voltaria a casar.
3. **Manter `CompressedManifestStaticFilesStorage`** em vez de rebaixar preventivamente —
   o `collectstatic` passou, então o hash de conteúdo (que evita CSS velho em cache no
   navegador) foi preservado.
4. **Fixture do GRP derivando as colunas do código do loader**, por regex sobre
   `row["..."]`, em vez de listá-las à mão: no GRP o nome da coluna não coincide com o do
   campo (`concedente_nome` vem de `concedente_-_nome`), e derivar mantém a fixture
   sincronizada se uma coluna mudar de nome.
5. **Reverter uma alteração de espaçamento em `apps/dashboard/urls.py`** que o editor fez
   sozinha (realinhamento de um `name=`). Não era de nenhuma tarefa e sujaria o commit.
6. **Testes de settings de produção em subprocesso**, com uma "sonda" que imprime JSON:
   importar as settings de prod no processo do pytest contaminaria o resto da suíte.
7. **Ordem de carga do GRP com `dcgce_dados_grp` primeiro**, mesmo sem FKs obrigarem —
   uma carga interrompida deixa o painel num estado mais útil.

## Pendências observadas (NÃO corrigidas)

1. **`origin/main` divergiu com um deploy para PythonAnywhere** (commits `658dd10`,
   `fd4758e`, `432c548`, `37e1862`): Django rebaixado para 5.2.17, pandas para 2.2.3,
   numpy para 1.26.4, pyarrow para 17.0.0, e dependências de dev misturadas ao
   `requirements.txt`. **Gravidade: alta** — é um segundo alvo de deploy, com versões
   incompatíveis com esta branch.
2. **O `requirements.txt` de `origin/main` está em UTF-16**, provavelmente por um
   `pip freeze > requirements.txt` no PowerShell (que usa UTF-16LE por padrão). É por
   isso que o git o trata como binário. `pip install -r` costuma lidar com o BOM, mas o
   arquivo fica ilegível em diff e review. **Gravidade: média.**
3. **`origin/main` também não tem `psycopg` nem `redis`** — a correção da Tarefa 3 vive só
   nesta branch. **Gravidade: alta**, se o deploy sair de `main`.
4. **Mês e ano do cronograma são `CharField`**, então a ordenação é lexicográfica: "10"
   vem antes de "2". A ordem fica determinística (que era o objetivo), mas não
   cronológica. Vale o mesmo para `get_grp_cronograma_qs`. Corrigir exigiria `Cast` para
   inteiro, com o risco de haver valores não numéricos. **Gravidade: média.**
5. **As ordenações das 7 telas GRP não terminam em `pk`** (`get_grp_*_qs` ordenam por
   `nr_grp` e afins). Não disparam o aviso, porque têm `order_by`, mas admitem empate —
   mesma classe de problema da Tarefa 6, fora do escopo dela. **Gravidade: média.**
6. **`Convenio.Meta.ordering = ["-data_inicio_vigencia"]`** ordena a tela mestre por um
   campo que admite empate e aceita `NULL`. `qs.ordered` é `True`, então o aviso não
   dispara, mas a paginação pode ser instável entre registros da mesma data.
   **Gravidade: média.**
7. **Schemas YAML com grafias concorrentes** (`dcgce_plano.trabalho` vs.
   `dcgce_plano_trabalho`) e a mesma mistura ponto/underscore em `_LOADERS` do
   `carregar_fonte`. Fora de escopo por instrução. **Gravidade: baixa.**
8. **Comandos legados `rodar_transformacao` e `carregar_silver`** continuam registrados e
   ainda usam o padrão antigo de exceção. Fora de escopo por instrução.
   **Gravidade: baixa.**
9. **`GOLD_CACHE_SECONDS` é lido no import de `services.py`** (`_CACHE_TTL` é módulo-level),
   então `override_settings` não o altera em teste. Não afeta produção.
   **Gravidade: baixa.**

## Pontos que precisam de decisão humana

1. **O deploy sai de `main` ou desta linha de trabalho?** `origin/main` recebeu um deploy
   para PythonAnywhere com Django 5.2.17, enquanto as duas branches de adequação estão em
   6.0.6. As correções de produção (psycopg, cache compartilhado, WhiteNoise) existem só
   nesta linha. Se o destino real é PythonAnywhere, boa parte do checklist de deploy
   precisa ser revista — lá não há Redis e o modelo de servir estáticos é outro.
2. **Há um Redis disponível na Prodemge?** Sem `REDIS_URL`, o cache vai para o
   PostgreSQL e funciona; o Redis só é mais rápido.
3. **O servidor web da Prodemge serve `/static/`?** O WhiteNoise cobre os dois cenários,
   então não bloqueia. Saber a resposta permite simplificar depois.
4. **Todos os subdomínios são exclusivamente HTTPS?** Só com essa confirmação dá para
   ligar `SECURE_HSTS_INCLUDE_SUBDOMAINS` e zerar os 2 avisos restantes.
5. **A ordenação escolhida para cada tela bate com a expectativa de quem usa o painel?**
   Foi derivada das colunas da tela, sem referência no QlikView — vale uma conferida com
   a área.

## Git

- Branch: `fix/pendencias-adequacao` (base: `refactor/adequacao-django`, que **não** foi
  mergeada em `main`)
- Commits (em ordem):
  - `22ad04b` chore(claude): para de versionar settings.local.json (configuração pessoal)
  - `e1b0a19` fix(template): fecha a tag nav da sidebar e normaliza fim de arquivo
  - `492cc4d` fix(deps): adiciona psycopg e redis aos requirements de produção
  - `4da7992` fix(cache): usa cache compartilhado em produção (Redis ou banco)
  - `c463eb3` fix(static): serve estáticos em produção com WhiteNoise
  - `2c68d66` fix(services): ordena querysets paginados de forma determinística
  - `6f3ffde` fix(commands): distingue erro esperado de inesperado e preserva o traceback
  - `7918962` feat(grp): adiciona comando carregar_grp e etapa opcional no pipeline
  - `8220cf4` chore(security): torna HSTS de subdomínios configurável, desligado por padrão
  - `2274378` docs: atualiza checklist de deploy, CLAUDE.md e README após pendências
  - `(este commit)` docs: preenche o resultado do push no relatório
- Push: **sucesso** — https://github.com/GabrielCostaAguiar/painel_de_convenios/tree/fix/pendencias-adequacao
- PR: **não aberto** — o `gh` CLI não está instalado neste ambiente
  (`gh: command not found`). Abrir manualmente em
  https://github.com/GabrielCostaAguiar/painel_de_convenios/pull/new/fix/pendencias-adequacao,
  **com base em `refactor/adequacao-django`** (não em `main`), usando este
  documento como descrição. **Não foi feito merge.**

## Como revisar / reverter

- **Revisar o conjunto:** `git log refactor/adequacao-django..fix/pendencias-adequacao --stat`
- **Revisar uma tarefa:** `git show <hash>`
- **Reverter uma tarefa:** `git revert <hash>`
- **Dependências entre tarefas:**
  - a Tarefa 4 (cache) depende da 3 (o `redis` nos requirements);
  - a Tarefa 8 (GRP) usa o padrão de exceção da 7;
  - a Tarefa 9 estende o arquivo de testes criado pela 4 e estendido pela 5, então
    revertê-la isoladamente exige atenção a `tests/test_settings_prod.py`;
  - a Tarefa 10 (docs) depende de 3, 4, 5, 6, 7, 8 e 9 — reverter qualquer uma deixa a
    documentação descrevendo um estado que não existe;
  - as Tarefas 1, 2 e 6 são independentes das demais.
