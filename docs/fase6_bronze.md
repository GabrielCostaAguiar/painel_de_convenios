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

(FASE C, D e relatório final são adicionados ao final desta execução.)
