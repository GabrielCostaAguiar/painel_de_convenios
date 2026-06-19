# Fase 6 — Costurar extração → Bronze

> Nota de nomenclatura: este "Fase 6" é o rótulo desta tarefa (extração→bronze),
> não o mesmo "Fase 6" do roadmap em `README.md` (que já é ✅, sobre frontend).

## FASE A — Diagnóstico (sem alterar nada)

### 1. De onde o Bronze lê hoje

`core/ingestion/sources.py` (`FONTES: dict[str, FonteDados]`) registra, para cada
fonte, um **caminho fixo e sem data** relativo a `data/raw/`:

```python
"dcgce_convenio": FonteDados(arquivo="sigcon/dcgce_convenio.xlsx", formato="excel", ...)
"siconv_convenio": FonteDados(arquivo="uniao/siconv_convenio.csv", formato="csv", ...)
```

`core/ingestion/readers.py::_resolver_caminho()` resolve isso para
`DATA_DIR/raw/<fonte.arquivo>` quando nenhum `arquivo` explícito é passado.
Formatos suportados: `"csv"` e `"excel"` (lidos com `dtype=str,
keep_default_na=False` — Bronze nunca interpreta tipo).

`core/ingestion/bronze.py::ingerir(nome_fonte, arquivo=None)` já aceita um
**caminho explícito** como override do caminho fixo — é o gancho que a ponte
nova vai usar, sem precisar mudar a assinatura.

### 2. Como decide qual arquivo processar

- **Camada raw → bronze (`ingerir`)**: não tem noção de "mais recente" — lê
  exatamente `DATA_DIR/raw/<fonte.arquivo>` (nome fixo) ou o `arquivo`
  explícito passado. Quem coloca o arquivo certo nesse caminho fixo hoje é um
  processo manual (copiar o export do BO/QlikView para `data/raw/sigcon/...`).
- **Camada bronze → silver (`core/transform/silver.py::_bronze_mais_recente`)**:
  aqui sim existe a noção de "mais recente" — `sorted(bronze_dir.glob(f"{nome}_*.csv"))[-1]`.
  Esse é o padrão que a ponte nova replica para `data/raw/`.

### 3. Descompactação de zip

Existe **hoje**, mas no lugar errado: `core/ingestion/baixar_siconv.py` (script
legado, **não chamado por nenhum management command** — só roda via
`python -m core.ingestion.baixar_siconv` manual) baixa o zip do Transferegov
**direto em `data/raw/uniao/`**, extrai todo o conteúdo ali mesmo, e **apaga o
zip original** (`zip_path.unlink()`). Isso quebra a premissa "raw é imutável":
o zip original não fica preservado, só o que foi extraído. É esse script que
explica por que `FONTES["siconv_convenio"].arquivo == "uniao/siconv_convenio.csv"`
— a extração historicamente deixava esse nome lá.

`core/extract/transferegov.py` (a extração nova) **não descompacta** — pousa o
`.zip` intacto e datado em `data/raw/transferegov/siconv_<data>.zip`, conforme
o contrato pedido ("raw guarda o original imutável, sem descompactar").

### 4. Contrato atual entre `data/raw/` e o Bronze — e o descompasso com a extração nova

| | Bronze espera (`sources.py`) | Extração produz (`core/extract/`) |
|---|---|---|
| Caminho | fixo, sem data: `data/raw/sigcon/dcgce_convenio.xlsx` | datado: `data/raw/gmail/dcgce_convenio_2026-06-19` |
| Transferegov | `data/raw/uniao/siconv_convenio.csv` (já extraído) | `data/raw/transferegov/siconv_2026-06-19.zip` (zipado) |
| Extensão (gmail) | exige `.xlsx`/`.csv` p/ inferir formato (indireto, via `fonte.formato`) | **sem extensão** (decisão da Fase 5: `ja_existe?` precisa rodar antes de saber o nome real do anexo) |

Ou seja: **nada se conecta hoje**. O Bronze não sabe que `core/extract/`
existe; a extração não sabe que o Bronze existe. É exatamente o buraco que
esta fase fecha.

### Achado extra (bug, corrigido nesta fase — ver FASE C)

`core/extract/armazenamento.py::caminho_destino()` usa `Path(arquivo).stem` /
`.suffix` para carimbar a data. Isso é correto para `transferegov.py`
(`"siconv.zip"` → stem `"siconv"`, suffix `".zip"`), mas **quebra** para 3 dos
17 assuntos do grupo `sigcon` do Gmail, que têm ponto **no nome**, não como
extensão:

```python
Path("dcgce_unidades.executoras").stem    # 'dcgce_unidades'   (errado: devia ser o nome completo)
Path("dcgce_unidades.executoras").suffix  # '.executoras'      (tratado como "extensao")
```

Resultado: o arquivo pousava como `dcgce_unidades_2026-06-19.executoras` em
vez de `dcgce_unidades.executoras_2026-06-19`. Sem correção, a ponte
raw→bronze não localizaria esses 3 arquivos pelo padrão de nome esperado.
Afeta: `dcgce_unidades.executoras`, `dcgce_termo.aditivo`, `dcgce_plano.trabalho`.

---

## FASE B — Plano

1. **Corrigir o bug acima** em `armazenamento.caminho_destino` antes de
   construir a ponte (senão a busca por "mais recente" erra para 3 assuntos).
   Adiciona parâmetro opcional `extensao` — `None` mantém o comportamento atual
   (infere de `Path(arquivo).suffix`, correto pro transferegov), e
   `gmail.py` passa `extensao=""` explicitamente (sem adivinhar).

2. **Mapear assunto Gmail → fonte Bronze** (`MAPA_GMAIL_PARA_FONTE`). Cruzando
   `GRUPOS_ASSUNTOS` (`core/extract/gmail.py`) com `FONTES`
   (`core/ingestion/sources.py`), só **15 dos 30 assuntos** têm uma
   `FonteDados` já cadastrada — todos no grupo `sigcon`:

   | Cobertura | Assuntos |
   |---|---|
   | ✅ Mapeado (15) | todo o grupo `sigcon` exceto os 2 abaixo |
   | ❌ Sem `FonteDados` (2, grupo sigcon) | `tabelauo2`, `dcgce_Chave` |
   | ❌ Sem `FonteDados` (8, grupo siafi) | todos |
   | ❌ Sem `FonteDados` (5, grupo siad) | todos |

   Os 15 não-mapeados **não entram nesta fase** — `README.md` já marca
   "SIAD/SEI" como 🔲 previsto, não implementado, e cadastrar uma `FonteDados`
   exige confirmar formato/separador/encoding reais (`gerar_schemas`), que não
   dá pra fazer sem uma amostra do arquivo. Vira TODO explícito no código.

3. **Resolver "arquivo mais recente"** em `data/raw/<fonte>/`, espelhando o
   padrão já usado em `core/transform/silver.py::_bronze_mais_recente`
   (`sorted(dir.glob(f"{prefixo}_*"))[-1]`).

4. **Resolver a falta de extensão dos anexos do Gmail**: como
   `pd.read_excel` precisa inferir o engine pela extensão quando ela não é
   passada explicitamente, e os anexos do Gmail **não têm extensão**
   (decisão da Fase 5), declarar `"engine": "openpyxl"` em
   `opcoes_leitura` das 15 `FonteDados` mapeadas. `openpyxl` já é dependência
   do projeto (`requirements.txt`) e é o engine que o pandas já usaria
   implicitamente para `.xlsx` — declarar explicitamente não muda
   comportamento para quem ainda usa o fluxo manual (cópia de `.xlsx` com
   extensão para `data/raw/sigcon/`).

5. **Descompactar o zip do Transferegov dentro do Bronze**, nunca em `raw/`:
   abrir o `.zip` mais recente de `data/raw/transferegov/`, extrair **apenas**
   o membro esperado (`Path(FONTES["siconv_convenio"].arquivo).name`, hoje
   `"siconv_convenio.csv"`) para um `tempfile.TemporaryDirectory()` efêmero, e
   chamar `bronze.ingerir("siconv_convenio", arquivo=<caminho temporário>)`.
   Nada é escrito de volta em `data/raw/`.

   **Risco assumido, sem amostra real para confirmar**: não há nenhum `.zip`
   real disponível neste ambiente (`data/raw/` está vazio e gitignorado) para
   confirmar o nome exato do membro dentro do zip. A suposição é que ele segue
   o que `baixar_siconv.py` (legado) já produzia. Ver TODO no código.

6. **Arquivos a tocar**:
   - `core/extract/armazenamento.py` — fix do bug (item 1).
   - `core/extract/gmail.py` — 1 linha (passa `extensao=""`).
   - `core/ingestion/sources.py` — adiciona `engine: openpyxl` nas 15 fontes mapeadas.
   - `core/ingestion/ponte_extracao.py` — **novo**: mapeamento, localizador de
     "mais recente", `ingerir_gmail_mapeados()`, `ingerir_transferegov()`.
   - `apps/dashboard/management/commands/rodar_extracao.py` → renomeado para
     `rodar_pipeline.py` — passa a encadear extração → bronze.
   - Nada em `core/transform/` (silver) ou `apps/convenios/` (gold/loader) é
     tocado — o pedido é só raw→bronze, na frente do pipeline existente.

7. **Comportamento explícito quando uma fonte falha na extração** (decisão
   documentada, não um TODO): o Bronze sempre tenta processar o **arquivo mais
   recente disponível** em `data/raw/<fonte>/`, independente de a extração de
   hoje ter rodado com sucesso. Se o grupo do Gmail foi pulado hoje (uma das
   travas de atomicidade da Fase 5), mas existe um arquivo de um dia anterior,
   o Bronze processa esse arquivo antigo — loga isso como Bronze "rodou", não
   "pulado". Só pula de fato quando **não existe nenhum arquivo**, de nenhuma
   data. Isso preserva o comportamento já usado em `_bronze_mais_recente` (que
   também ignora "frescor" e só olha existência), mas é uma decisão que merece
   sua revisão — ver seção final.

---

## FASE C — Implementado

1. **Bugfix** `core/extract/armazenamento.py::caminho_destino()` — ganhou o
   parâmetro opcional `extensao` (`None` = comportamento atual, inferido de
   `Path(arquivo).suffix`; `""` = usa o nome completo sem separar nada).
   `core/extract/gmail.py` passa `extensao=""` explicitamente. Sem isso, 3 dos
   17 assuntos do grupo `sigcon` pousavam com o nome corrompido (ver Fase A).

2. **`core/ingestion/sources.py`** — as 15 `FonteDados` do grupo `sigcon` com
   `FonteDados` cadastrada ganharam `"engine": "openpyxl"` explícito em
   `opcoes_leitura`. Necessário porque o anexo do Gmail pousa sem extensão e
   `pd.read_excel` não consegue inferir o engine sozinho nesse caso. Não muda
   nada para quem ainda copia o `.xlsx` manualmente — é o mesmo engine que o
   pandas já escolheria implicitamente para esse formato.

3. **`core/ingestion/ponte_extracao.py`** (novo módulo):
   - `MAPA_GMAIL_PARA_FONTE`: 15 assuntos → chave em `FONTES` (só os que já
     tinham `FonteDados` cadastrada).
   - `_localizar_mais_recente(diretorio, prefixo)`: mesmo padrão de
     `silver._bronze_mais_recente` (`sorted(glob(f"{prefixo}_*"))[-1]`),
     aplicado a `data/raw/<fonte>/`.
   - `ingerir_gmail_mapeados()`: para cada assunto mapeado, localiza o
     arquivo mais recente em `data/raw/gmail/` e chama `bronze.ingerir()`.
     Assunto sem nenhum arquivo no disco → log + pula, não aborta os demais.
   - `ingerir_transferegov()`: localiza o `.zip` mais recente em
     `data/raw/transferegov/`, extrai **apenas** o membro esperado
     (`Path(FONTES["siconv_convenio"].arquivo).name`) para um
     `tempfile.TemporaryDirectory()` efêmero, chama `bronze.ingerir()` sobre
     ele. Nada é escrito de volta em `data/raw/` — raw continua imutável.

   **Validação feita** (sem rede, sem credenciais — `data/raw/` está vazio
   neste ambiente): criei fixtures sintéticas (`.xlsx` sem extensão simulando
   um anexo do Gmail para `dcgce_esfera`; um `.zip` fake com
   `siconv_convenio.csv` dentro simulando o Transferegov), rodei
   `ingerir_gmail_mapeados()` e `ingerir_transferegov()` diretamente, conferi
   que os dois geraram Bronze corretamente e removi as fixtures depois. Os 14
   assuntos mapeados sem arquivo (esperado, fixture só cobria 1) logaram
   warning e foram pulados sem abortar — comportamento conforme o plano.

## FASE D — Maestro

`apps/dashboard/management/commands/rodar_extracao.py` foi **renomeado** para
`rodar_pipeline.py` (via `git mv`, histórico preservado) porque o escopo
cresceu de "só extração" para "extração + bronze". O comando:

1. Chama `transferegov.extrair()` e `gmail.extrair()` em sequência (já
   existia) — falha de um não impede o outro.
2. Em seguida chama `ingerir_gmail_mapeados()` e `ingerir_transferegov()` — a
   etapa Bronze.

**Decisão tomada sobre fonte com extração falha** (pedida explicitamente na
tarefa): o Bronze **sempre roda** sobre o arquivo mais recente disponível em
`data/raw/<fonte>/`, **independente** de a extração de hoje ter tido sucesso
para aquela fonte. Só é **pulado** quando não existe nenhum arquivo, de
nenhuma data. Não diferenciei "rodou com dado de hoje" de "rodou com dado
antigo" no log atual — ambos aparecem como `[bronze] <caminho>`. Replica
exatamente a semântica que `core/transform/silver.py::_bronze_mais_recente`
já usa entre bronze→silver; mantive consistência em vez de inventar uma regra
nova. **Avalie se isso é aceitável** — ver TODO abaixo.

Continua "magro": nenhuma lógica de download/parsing/escrita nova no comando,
só chamadas às funções de `core/extract/` e `core/ingestion/`.

### Regressão verificada (não quebrei o que já funcionava)

- `python manage.py check` — sem issues.
- `rodar_ingestao`, `rodar_silver`, `gerar_schemas` — carregam normalmente.
- `rodar_ingestao siafi2` com um CSV sintético — ingestão CSV inalterada.
- `rodar_ingestao dcgce_convenio --arquivo tests/fixtures/convenios_exemplo.csv`
  falha **igual** com o `sources.py` antigo e o novo (testei os dois) — é um
  descompasso pré-existente entre o docstring do comando (exemplo usa a fonte
  `"convenios"`, que não existe mais em `FONTES`) e o fixture CSV, não uma
  regressão desta tarefa. Não toquei nisso — fora do escopo.

---

## O que ficou pendente da sua revisão (TODOs no código)

1. **`core/ingestion/ponte_extracao.py` — `MAPA_GMAIL_PARA_FONTE` incompleto
   por falta de amostra real**: `tabelauo2`, `dcgce_Chave` (grupo `sigcon`) e
   os grupos `siafi` (8 assuntos) e `siad` (5 assuntos) não têm `FonteDados`
   cadastrada. Cadastrar uma fonte exige confirmar formato/separador/encoding
   reais (`gerar_schemas`) — não tinha um anexo real pra isso neste ambiente.
   `README.md` já marcava SIAD/SEI como previsto, não implementado, então
   isso não é regressão, é trabalho futuro explícito.

2. **`core/ingestion/ponte_extracao.py::ingerir_transferegov()` — nome do
   membro dentro do zip é uma suposição**: assumi que é
   `Path(FONTES["siconv_convenio"].arquivo).name` (`"siconv_convenio.csv"`),
   espelhando o que o script legado `baixar_siconv.py` produzia ao extrair o
   zip inteiro. **Não havia um `.zip` real do Transferegov disponível neste
   ambiente para confirmar.** Se o nome real for diferente, a função loga
   erro com a lista completa de membros do zip — use esse log pra corrigir o
   nome esperado na primeira execução real.

3. **`core/ingestion/baixar_siconv.py` (script legado)** — não é chamado por
   nenhum management command, baixa e extrai direto em `data/raw/uniao/`, e
   **apaga o zip original** depois de extrair (`zip_path.unlink()`), o que
   viola "raw é imutável". Não removi nem toquei nele — fica candidato a
   deprecação/remoção, mas é uma decisão sua (pode haver gente rodando esse
   script manualmente).

4. **Comportamento "Bronze sempre usa o mais recente disponível, mesmo se a
   extração de hoje falhou"** (Fase D) — decisão tomada por consistência com
   o padrão já existente em Silver, não por ter certeza de que é o que você
   quer. Alternativa seria: se a extração de hoje falhou/pulou aquele grupo,
   pular o Bronze daquela fonte também (mais conservador, porém o painel
   ficaria sem nenhum dado novo até a próxima extração bem-sucedida).

5. **Nada foi testado fim-a-fim com rede/credenciais reais.**
   `secrets/credentials.json` e `secrets/token.json` existem neste ambiente
   — rodar `gmail.extrair()` de verdade dispararia autenticação OAuth real
   contra uma conta de e-mail real, e `transferegov.extrair()` faria uma
   requisição HTTP real a um site do governo. Não executei nenhum dos dois de
   verdade (autonomamente, sem você por perto, pareceu a decisão certa) — só
   testei a ponte com fixtures sintéticas. **A primeira execução real de
   `rodar_pipeline` precisa ser sua.**

---

## Comandos para você testar quando voltar

```bash
# 1. Revisar o diff completo da branch antes de tocar em qualquer coisa
git log --oneline main..feature/fase6-bronze
git diff main..feature/fase6-bronze

# 2. Conferir que nada quebrou (regressão)
python manage.py check
python manage.py rodar_ingestao siafi2          # ou outra fonte CSV que você já usa
python manage.py rodar_silver dcgce_convenio    # fluxo silver inalterado

# 3. Primeira execução REAL da extração + bronze (efeitos colaterais reais:
#    rede + OAuth Gmail) — rode isolado antes do pipeline completo se quiser
#    controlar melhor:
python manage.py shell -c "from core.extract import transferegov; print(transferegov.extrair())"
python manage.py shell -c "from core.extract import gmail; print(gmail.extrair())"

# 4. Se os dois acima rodarem limpo, o maestro completo:
python manage.py rodar_pipeline

# 5. Se ingerir_transferegov() logar erro de "membro nao encontrado", o log
#    traz a lista real de arquivos dentro do zip - ajuste
#    core/ingestion/ponte_extracao.py::ingerir_transferegov() com o nome certo.
```

## Branch e commits

Branch: `feature/fase6-bronze` (criada a partir de `main`, nada foi tocado
direto na main). Commits, em ordem:

1. `chore: protege secrets/ contra rastreamento acidental pelo git`
2. `feat(extract): camada de extracao (transferegov + gmail) com orquestrador` (trabalho de sessões anteriores, commitado agora)
3. `docs(fase6): diagnostico raw->bronze e plano de costura com a extracao`
4. `fix(extract): caminho_destino nao deve tratar ponto interno do assunto como extensao`
5. `feat(ingestion): ponte raw->bronze entre core/extract/ e bronze.ingerir()`
6. `feat(maestro): rodar_extracao -> rodar_pipeline, encadeia extracao + bronze`

Nenhum commit toca `secrets/`. Nenhum merge foi feito na `main`.
