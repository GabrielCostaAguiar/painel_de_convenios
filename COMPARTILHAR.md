# Compartilhar o painel temporariamente (feedback de colegas)

Expõe o servidor de dev na internet via túnel HTTPS (cloudflared), protegido por
usuário/senha. **Não é deploy de produção** — é só pra ~10 pessoas testarem e
darem sugestões. Quando terminar, é só fechar os dois terminais; nada fica
exposto depois disso.

Tudo controlado pela env var `MODO_COMPARTILHAR`. Sem ela, o `runserver`
normal de desenvolvimento continua exatamente igual.

## Passo a passo (Windows / PowerShell)

1. Ative o venv e defina as variáveis de ambiente da sessão:

   ```powershell
   .venv\Scripts\activate
   $env:DJANGO_SETTINGS_MODULE = "config.settings.dev"
   $env:MODO_COMPARTILHAR = "1"
   $env:SHARE_USER = "escolha-um-usuario"
   $env:SHARE_PASSWORD = "escolha-uma-senha-forte"
   ```

   Essas variáveis valem só para esse terminal aberto — feche e abra de novo
   para voltar ao modo dev normal.

2. Gere os arquivos estáticos (precisa disso porque `DEBUG` vira `False` no
   modo compartilhar, e o Django para de servir estático sozinho):

   ```powershell
   python manage.py collectstatic --noinput
   ```

3. Suba o servidor escutando em todas as interfaces:

   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```

   Deixe esse terminal aberto.

4. Em **outro terminal**, instale o `cloudflared` (uma vez só, fica instalado):

   ```powershell
   winget install --id Cloudflare.cloudflared
   ```

5. Ainda nesse segundo terminal, abra o túnel apontando para o servidor local:

   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```

   O cloudflared imprime uma URL parecida com
   `https://palavras-aleatorias.trycloudflare.com`.

6. Copie essa URL e envie pros colegas junto com o usuário/senha do passo 1.
   Cada um vai ver um popup de login do navegador (Basic Auth) antes de
   entrar no painel.

## Encerrando

`Ctrl+C` nos dois terminais (cloudflared e runserver). A URL gerada para de
funcionar imediatamente — o cloudflared não reaproveita o mesmo endereço numa
próxima sessão.

## Limitar por IP (opcional)

Se quiser restringir ainda mais (além da senha), defina também:

```powershell
$env:SHARE_IPS = "200.1.2.3,200.4.5.6"
```

IPs fora dessa lista recebem 403, mesmo com a senha certa. Deixe `SHARE_IPS`
sem definir (ou vazia) para não filtrar por IP — só a senha já basta para o
teste com os colegas.

## O que muda tecnicamente

- `DEBUG = False`, então erros não mostram stack trace pra quem acessa.
- `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` passam a aceitar o domínio
  `*.trycloudflare.com`.
- WhiteNoise assume a entrega dos arquivos estáticos (CSS/JS) no lugar do
  servidor de dev do Django, que não serve estático com `DEBUG=False`.
- Um middleware de Basic Auth (`core/middleware/basic_auth.py`) entra no
  topo da pilha e bloqueia qualquer requisição sem usuário/senha corretos
  — inclusive os próprios arquivos estáticos.

Nada disso acontece se `MODO_COMPARTILHAR` não estiver definida (ou for
`0`/`false`) — o ambiente de dev do dia a dia não é afetado.
