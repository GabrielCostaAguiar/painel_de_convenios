# Checklist de deploy

Como colocar o Painel de Convênios em produção, e o que o `manage.py check --deploy`
ainda aponta.

A primeira versão deste documento era só diagnóstico — apontava três bloqueadores sem
corrigi-los. **Os três foram resolvidos** (driver do PostgreSQL, cache compartilhado e
arquivos estáticos). O que sobra aqui é o passo a passo e os pontos que continuam
dependendo de informação da Prodemge.

Última revisão: 2026-09-23 · Django 6.0.6 · Python 3.14

---

## Passo a passo de deploy

### 1. Variáveis de ambiente

Obrigatórias — sem elas `config/settings/prod.py` nem importa:

| Variável | Para quê |
|---|---|
| `DJANGO_SECRET_KEY` | chave de assinatura do Django. Longa e aleatória; nunca reaproveitar a de dev. |
| `DJANGO_ALLOWED_HOSTS` | lista separada por vírgula com os hosts que respondem pelo painel. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | conexão com o PostgreSQL. |

> `prod.py` lê host e porta **separados** (`DB_HOST`, `DB_PORT`), não uma `DATABASE_URL`
> única. `DB_HOST` assume `localhost` e `DB_PORT` assume `5432` quando omitidos.

Opcionais, todas com default seguro:

| Variável | Default | Efeito |
|---|---|---|
| `REDIS_URL` | *(vazio)* | Definida → cache em Redis. Vazia → cache na tabela `painel_cache` do próprio PostgreSQL. |
| `GOLD_CACHE_SECONDS` | `3600` | Tempo de vida do cache de indicadores. |
| `PIPELINE_INCLUIR_GRP` | `False` | `True` inclui as tabelas do GRP no `rodar_pipeline`. Ver [a seção do GRP](#o-grp-fica-fora-do-pipeline-por-padrão). |
| `STATIC_ROOT` | `BASE_DIR/staticfiles` | Destino do `collectstatic`, se o diretório servido ficar fora do projeto. |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | Ver [HSTS](#hsts-em-subdomínios-decisão-pendente). **Não ligue sem ler.** |
| `SECURE_HSTS_PRELOAD` | `False` | Idem. |

Nada disso vai para o `.env` versionado — `.env` é gitignored, e as variáveis devem vir
do mecanismo de configuração do ambiente.

### 2. Comandos, na ordem

```bash
# 1. Dependências (requirements.txt é a camada de produção;
#    requirements-dev.txt só acrescenta pytest e black por cima)
pip install -r requirements.txt

# 2. Schema do banco
python manage.py migrate --settings=config.settings.prod

# 3. Tabela de cache — SOMENTE quando não há Redis.
#    Com REDIS_URL definida, pule este passo.
python manage.py createcachetable --settings=config.settings.prod

# 4. Arquivos estáticos
python manage.py collectstatic --noinput --settings=config.settings.prod

# 5. Conferência final
python manage.py check --deploy --settings=config.settings.prod
```

`createcachetable` é idempotente: rodar de novo não recria a tabela nem apaga o cache.

> `createcachetable --dry-run` **exige conexão real com o PostgreSQL** — o comando
> inspeciona as tabelas existentes antes de decidir o que criar. Não dá para validá-lo
> fora do ambiente de destino.

### 3. Carga de dados

Depois que a aplicação sobe, o painel ainda precisa de dados:

```bash
python manage.py rodar_pipeline          # extração → Bronze → Silver → carga
```

Cada comando de carga invalida o cache de indicadores ao terminar, então o painel
reflete a nova carga imediatamente — desde que o cache seja compartilhado (item
seguinte).

---

## Cache: por que não pode ser o LocMemCache

`LocMemCache` — o default implícito do Django — guarda tudo na memória **de cada
processo**. Em produção, com vários workers de gunicorn/uWSGI, cada um fica com a sua
cópia. Pior: os comandos de carga rodam num processo à parte, então a invalidação que
eles disparam limpa apenas a memória daquele processo, e todos os workers que atendem o
painel continuam servindo indicadores velhos até o TTL expirar.

`prod.py` resolve escolhendo o backend pela `REDIS_URL`:

- **com `REDIS_URL`** → `RedisCache`, `KEY_PREFIX="painel"`;
- **sem `REDIS_URL`** → `DatabaseCache` na tabela `painel_cache`.

Os dois são compartilhados entre processos, que é o que importa. O `DatabaseCache` não
exige infraestrutura nova — para o volume de chaves deste painel (um agregado geral mais
uma entrada por ano consultado), ele dá conta com folga.

> **Detalhe que custou um bug:** a invalidação de `core/cache.py` mantém um contador de
> versão que não pode expirar. `cache.incr()` parecia o caminho óbvio para incrementá-lo,
> mas a semântica dele muda com o backend — o `DatabaseCache` não sobrescreve `incr()` e
> cai no `BaseCache.incr`, que regrava a chave **sem timeout**, trocando o "nunca expira"
> pelo padrão de 300 s. O contador morreria antes das entradas que ele invalida. Por isso
> a versão é lida e regravada com `timeout=None` explícito. Não troque por `incr()`.

---

## Arquivos estáticos

Com `DEBUG=False` o Django **para de servir** `/static/` por conta própria. `prod.py`
agora inclui o WhiteNoise logo após o `SecurityMiddleware`, e o storage é
`CompressedManifestStaticFilesStorage`:

- **Compressed** — serve `.gz`/`.br` pré-comprimidos, gerados no `collectstatic`;
- **Manifest** — renomeia cada arquivo com o hash do conteúdo, para o navegador não
  reaproveitar um CSS antigo depois de um deploy.

`collectstatic` com as settings de produção roda limpo: 133 arquivos copiados, 399
pós-processados, nenhuma referência quebrada.

### Se a Prodemge servir `/static/` na frente

Nada muda e nada precisa ser desligado. O servidor web atende a requisição antes de ela
chegar ao Python, e o WhiteNoise simplesmente não é acionado. Nesse cenário basta:

- apontar o alias de `/static/` para o `STATIC_ROOT` (ou definir `STATIC_ROOT` para o
  diretório que o servidor já serve);
- garantir que `collectstatic` rode a cada deploy, **antes** de recarregar os workers.

Deixar o WhiteNoise ligado nos dois casos é deliberado: é a configuração que funciona
sem depender de uma confirmação que ainda não veio.

---

## O GRP fica fora do pipeline por padrão

As telas do GRP estão **em teste**. Os dados delas são carregados por um comando próprio:

```bash
python manage.py carregar_grp                         # as 7 tabelas
python manage.py carregar_grp --fonte dcgce_esfera_grp  # só uma
```

`PIPELINE_INCLUIR_GRP` continua `False` de propósito: uma falha ou a ausência de um
arquivo do GRP não pode derrubar a atualização diária do painel SIGCON. Ligue só quando
o GRP sair de teste.

---

## Avisos do `check --deploy`

Rodando com as variáveis de produção, sobram **2 avisos**, ambos sobre HSTS em
subdomínios — e ambos são decisão pendente, não defeito. `prod.py` já cobre
`DEBUG=False`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` e
`SECURE_HSTS_SECONDS = 31536000`.

| Código | O que significa | O que fazer |
|---|---|---|
| `security.W005` | `SECURE_HSTS_INCLUDE_SUBDOMAINS` não está `True`. | Ver abaixo. |
| `security.W021` | `SECURE_HSTS_PRELOAD` não está `True`. | Só depois do anterior. |

### HSTS em subdomínios: decisão pendente

`SECURE_HSTS_INCLUDE_SUBDOMAINS=True` instrui o navegador a **recusar HTTP em todos os
subdomínios** do domínio, por até um ano. Se algum subdomínio da Prodemge ainda responder
só em HTTP, ele fica inacessível para quem visitou o painel — e **isso não se desfaz do
lado do servidor**, porque a instrução já está guardada no navegador de cada visitante.

`SECURE_HSTS_PRELOAD` é ainda mais difícil de reverter: uma vez na lista de preload dos
navegadores, o domínio fica marcado por meses.

Os dois são lidos do ambiente. Quando alguém confirmar que **todos** os subdomínios são
exclusivamente HTTPS, basta definir as variáveis — sem alterar código:

```bash
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

Conferido: com as duas em `True`, os avisos W005 e W021 desaparecem.

> Se o comando exigir conexão com o banco no seu ambiente, note que nenhum check do
> `--deploy` inspeciona o PostgreSQL — eles olham só a configuração.

---

## O que ainda depende da Prodemge

| # | Pergunta | Impacto se ficar sem resposta |
|---|---|---|
| 1 | Há um Redis disponível? | Nenhum imediato: sem `REDIS_URL` o cache vai para o banco e funciona. O Redis só é mais rápido. |
| 2 | O servidor web serve `/static/`? | Nenhum: o WhiteNoise cobre os dois cenários. Saber a resposta permite simplificar depois. |
| 3 | Todos os subdomínios são HTTPS? | Os 2 avisos do `check --deploy` continuam. Sem risco operacional. |

Nenhum dos três bloqueia o deploy.
