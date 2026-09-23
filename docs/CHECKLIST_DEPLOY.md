# Checklist de deploy — diagnóstico

Levantamento do que o `manage.py check --deploy` aponta em `config/settings/prod.py`,
mais o estado da entrega de arquivos estáticos e do cache.

**Este documento é diagnóstico, não mudança.** Nada em `prod.py` foi alterado: o
ambiente é da Prodemge e várias das decisões abaixo (TLS, proxy reverso, quem serve
estático) podem já estar resolvidas na infraestrutura, fora deste repositório.

Data do levantamento: 2026-09-23 · Django 6.0.6 · Python 3.14

---

## Como reproduzir

O `--deploy` precisa de settings de produção válidas. As variáveis abaixo são
fictícias e vão **só na linha de comando** — nada disso entra no `.env`:

```bash
DJANGO_SECRET_KEY="dummy-$(python -c 'import secrets;print(secrets.token_urlsafe(50))')" \
DB_NAME=dummy DB_USER=u DB_PASSWORD=p \
DJANGO_ALLOWED_HOSTS="painel.exemplo.mg.gov.br" \
python manage.py check --deploy --settings=config.settings.prod
```

> Note que `prod.py` lê `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`
> separadamente — **não** uma `DATABASE_URL` única.

Rodando assim neste ambiente, o comando **aborta antes de chegar aos checks**:

```
django.core.exceptions.ImproperlyConfigured: Error loading psycopg2 or psycopg module
```

Ver [o item 1 dos bloqueadores](#1-driver-do-postgresql-nao-esta-nos-requirements).
Para obter mesmo assim o diagnóstico de segurança, o levantamento foi refeito com um
módulo de settings temporário (fora do Git) que herda `prod.py` inteiro e troca só o
`ENGINE` do banco para SQLite. Nenhum check do `--deploy` inspeciona o banco, então o
resultado vale igual.

---

## Avisos do `check --deploy`

Saída: **2 avisos**. `prod.py` já cobre o grosso — `DEBUG=False`, `SECURE_SSL_REDIRECT`,
`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` e `SECURE_HSTS_SECONDS = 31536000`.

| Código | O que significa | Recomendação |
|---|---|---|
| `security.W005` | `SECURE_HSTS_INCLUDE_SUBDOMAINS` não está `True`: o HSTS protege só o domínio exato, e um subdomínio servido em HTTP puro continua sendo porta de entrada para interceptação. | Ligar **apenas** se todos os subdomínios do domínio do painel forem servidos exclusivamente por HTTPS. Quem responde isso é a Prodemge, não o repositório — um subdomínio legado em HTTP ficaria inacessível. |
| `security.W021` | `SECURE_HSTS_PRELOAD` não está `True`: sem ele o domínio não pode ser submetido à lista de preload dos navegadores, que dispensa a primeira visita em HTTP. | Baixa prioridade para um painel interno. Só faz sentido depois de `W005` resolvido, e o preload é **difícil de reverter** — uma vez na lista, o domínio fica marcado por meses. |

Nenhum dos dois é bloqueador. Ambos dependem de informação sobre o domínio que só a
equipe de infraestrutura tem.

---

## Bloqueadores encontrados fora do `--deploy`

### 1. Driver do PostgreSQL não está nos requirements

`prod.py` usa `django.db.backends.postgresql`, mas nem `psycopg` nem `psycopg2-binary`
aparecem em `requirements.txt` ou `requirements-dev.txt`. Um ambiente montado só a
partir desses arquivos **não sobe**: qualquer comando do Django que toque o banco morre
com `ImproperlyConfigured: Error loading psycopg2 or psycopg module`.

**Recomendação:** acrescentar `psycopg[binary]` (psycopg 3, o recomendado pelo Django 6)
a `requirements.txt`, com versão fixada como o resto do arquivo.

**Gravidade: alta.** É a diferença entre a aplicação subir e não subir.

### 2. `CACHES` não é configurado em lugar nenhum

Nem `base.py` nem `prod.py` definem `CACHES`. Sem isso o Django cai no default,
`LocMemCache` — um dicionário **por processo**.

Com mais de um worker (gunicorn/uWSGI), cada um passa a ter o seu próprio cache de
indicadores. Duas consequências:

- dois acessos seguidos ao painel podem cair em workers diferentes e mostrar números
  diferentes, até os TTLs convergirem;
- a invalidação automática de cache implementada em `core/cache.py` só atinge o
  processo que rodou a carga. Como as cargas rodam por linha de comando, num processo
  próprio, **nenhum worker do painel é invalidado** — os indicadores velhos sobrevivem
  o TTL inteiro em produção.

O docstring de `apps/dashboard/services.py` já instrui a configurar Redis em produção,
mas a configuração nunca foi escrita.

**Recomendação:** definir em `prod.py`

```python
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
}}
```

e confirmar com a Prodemge se há um Redis disponível. Enquanto não houver, a alternativa
sem infraestrutura nova é `DatabaseCache` (tabela criada por `createcachetable`), que
também é compartilhada entre workers.

**Gravidade: alta** — é o que faz a correção de invalidação de cache valer em produção.

### 3. `GOLD_CACHE_SECONDS` não existe nas settings

`apps/dashboard/services.py` lê `getattr(settings, "GOLD_CACHE_SECONDS", 3600)`, e a
variável não está definida em nenhum arquivo de settings. Funciona — cai no default de
1 hora — mas o número fica invisível para quem opera.

**Recomendação:** declarar explicitamente em `base.py`, lendo do `.env`.
**Gravidade: baixa.** Só clareza operacional.

---

## Como os arquivos estáticos são servidos em produção?

**Resposta curta: hoje, por ninguém.**

| Item | Estado |
|---|---|
| `STATIC_ROOT` | definido em `base.py` → `BASE_DIR/staticfiles` ✅ |
| `STATIC_URL` | `/static/` ✅ |
| `STATICFILES_DIRS` | `BASE_DIR/static` ✅ |
| `collectstatic` com settings de prod | roda sem erro — 131 arquivos ✅ |
| WhiteNoise no `MIDDLEWARE` de prod | **ausente** ❌ |
| `STORAGES["staticfiles"]` em prod | `StaticFilesStorage` (sem hash, sem compressão) |

`whitenoise` está em `requirements.txt` e o projeto sabe usá-lo — mas só dentro do bloco
`MODO_COMPARTILHAR` de `dev.py`, que serve o túnel temporário do cloudflared. Esse bloco
insere o middleware logo após o `SecurityMiddleware` e troca o storage para
`CompressedManifestStaticFilesStorage`. Em `prod.py` não há nada equivalente.

Com `DEBUG=False` e sem WhiteNoise, o Django **não serve** `/static/` — se nada na frente
estiver servindo, o painel sobe sem CSS nem JS.

Só há dois desfechos possíveis, e qual vale depende de informação que não está no
repositório:

1. **O servidor web da Prodemge (nginx/Apache) serve `/static/` a partir de
   `STATIC_ROOT`.** É o arranjo mais comum e o mais eficiente. Nesse caso não falta nada
   no código — falta só garantir que `collectstatic` rode no deploy e que o alias aponte
   para `staticfiles/`.
2. **Nada na frente serve estático.** Aí o WhiteNoise precisa entrar em `prod.py`, com o
   mesmo arranjo já usado no `MODO_COMPARTILHAR`.

**Nenhuma mudança foi feita.** Adicionar WhiteNoise "por garantia" no cenário 1 colocaria
o Python no caminho de cada arquivo estático sem necessidade. É **decisão pendente** para
quem conhece o ambiente da Prodemge.

---

## Resumo — o que decidir

| # | Assunto | Quem decide | Gravidade |
|---|---|---|---|
| 1 | Incluir `psycopg[binary]` nos requirements | equipe do projeto | alta |
| 2 | Backend de cache compartilhado (Redis ou DatabaseCache) | Prodemge + equipe | alta |
| 3 | Quem serve `/static/`: servidor web ou WhiteNoise | Prodemge | alta |
| 4 | `SECURE_HSTS_INCLUDE_SUBDOMAINS` (`security.W005`) | Prodemge | média |
| 5 | `SECURE_HSTS_PRELOAD` (`security.W021`) | Prodemge | baixa |
| 6 | Declarar `GOLD_CACHE_SECONDS` nas settings | equipe do projeto | baixa |
