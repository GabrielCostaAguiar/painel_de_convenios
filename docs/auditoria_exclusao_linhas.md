# Auditoria de exclusão de linhas — Raw → Bronze → Silver → Banco → Gold

**Regra do dono dos dados:** nenhuma linha pode ser excluída, a não ser uma
linha sem **nenhum** dado em **nenhuma** coluna.

Medido em 2026-11-10 com os arquivos atuais de `data/raw/` e o código da branch
`refactor/ingestao-legado` (commit `1fd53fd`). Escopo: as 20 fontes legadas, as
22 do GRP, os loaders de `apps/sigcon` e `apps/grp`, e o Gold
`ConvenioIntegrado`. Script usado:
`auditar_linhas.py` (avulso, fora do repositório); os números abaixo são a
saída dele.

## Resultado

**A regra hoje não é cumprida.** Raw → Bronze está correto. A Silver, a carga
do Controle SEI e o Gold excluem linhas com dado.

| Camada | Linhas com dado excluídas | Onde |
|---|---|---|
| Raw → Bronze | 0 | — |
| Bronze → Silver (legado) | 18.423 | cronograma 18.400 (18.399 códigos de plano + 1 cabeçalho repetido), depara_siafi 20, depara_parlamentar 2, nt_emenda 1 |
| Bronze → Silver (GRP) | 1 | grp_tabela_uo |
| Silver → Banco | 334 | `carregar_controle_sei` |
| Silver → Gold | 740 convênios | `filtrar_uo` (1) + `limpeza_g` (739) |

## 1. Raw → Bronze — sem perda

Lido cada arquivo bruto sem cabeçalho (`header=None`) e comparado com o Bronze:
- As fontes Excel com `header=1` pulam a 1ª linha do arquivo; ela está vazia em
  todas (0 linhas com dado acima do cabeçalho).
- Os 21 CSVs do GRP têm 1 linha em branco no fim do arquivo; o `read_csv` a
  ignora. É 100% vazia, então pode ser descartada.
- Em todas as outras fontes, o número de linhas do Raw é igual ao do Bronze.
- `core/ingestion/readers.py` e `bronze.py` não têm nenhum filtro de linha.

Correção do relatório da Fase 6: a coluna "Bronze" de
`docs/validacao_ingestao_legado.md` contou linhas **físicas** do CSV. Isso
superestima as fontes com texto de várias linhas numa célula: plano de
trabalho 18.529 → o certo é 18.291; declaração 3.970 → 3.957; controle SEI
2.857 → 2.834. Nessas três fontes não há perda de linha.

## 2. Bronze → Silver (`core/transform/silver.py`)

Pontos de exclusão no motor e o que cada um fez com os dados atuais:

| Regra (linha do código) | Exclui linha com dado? | Efeito medido |
|---|---|---|
| `_descartar_linhas_vazias`, estágio "bruto" (l.409) | não | 0 linhas. Com `keep_default_na=False` não existe NaN nesse ponto, então essa chamada não remove nada |
| `_descartar_linhas_repetem_cabecalho` (l.410) | **sim** | 0 linhas hoje; a única linha de cabeçalho repetido (cronograma) caiu antes pela regra abaixo |
| `descartar_linhas_se_nulo` (l.412; só no `sigcon_cronograma_desembolso.yaml`) | **sim** | **18.402** linhas: 2 vazias, 1 cabeçalho repetido e **18.399 com dado**, um código de plano de trabalho (ex.: 684, 816) caído na coluna `mes_cronograma_desembolso` |
| `_descartar_linhas_vazias`, estágio "pós-tipagem" (l.513) | **sim** | Exclui linhas que ficaram 100% nulas **depois** da sentinela/tipagem: `sigcon_nt_emenda` (1 linha: `9999` / `99999999`) e `grp_tabela_uo` (1 linha: `N/A` / `N/A`). `grp_instrumento_financiado` (1 linha realmente vazia) está correta |
| `drop_duplicates()` (l.516) | **sim** | `depara_siafi` 12 e `depara_parlamentar` 2 (linhas 100% idênticas). GRP: 0 |
| `_aplicar_quarentena` (l.521; só `depara_siafi`) | **sim**, tira da tabela principal | 8 linhas (2 chaves com destino divergente) |

Todas as outras 36 fontes: Silver = Bronze − linhas 100% vazias. Ou seja, sem
perda.

Observação sobre as linhas só com marcadores. Decisão do dono dos dados em
2026-11-10: `N/A` em **todas** as colunas conta como sem dado, então a linha
`N/A`/`N/A` de `grp_tabela_uo` é vazia e continua saindo (160 linhas, hash do
GRP inalterado). `9999`/`99999999` (`sigcon_nt_emenda`) e `0` têm texto e a
linha **fica**; se o dono quiser tratá-los como sem dado, é só acrescentar o
valor a `_SEM_DADO` em `core/transform/silver.py`.

## 3. Silver → Banco (loaders)

- `core/db.py::bulk_refresh`: apaga e insere a tabela inteira. Não filtra
  linha nem usa `ignore_conflicts`. Sem perda.
- `apps/sigcon/loader.py`: os `drop_duplicates` das linhas 164, 178, 199, 204,
  289, 308, 434 e 451 atuam em **subconjuntos de consulta** de join (pegam um
  valor por chave). A tabela que é carregada mantém todas as linhas: os merges
  são `left` e há `assert` anti fan-out.
- **`carregar_controle_sei` (l.860) exclui linhas:**
  `drop_duplicates(subset=SIAFI)` remove **334 de 2.834**. Desse total, 326 são
  linhas sem SIAFI, que colapsam todas numa só; 8 são SIAFIs com 2 processos
  SEI. A intenção era evitar que a aba Convênios mostrasse dois SEIs para o
  mesmo SIAFI. Isso pode ser feito na consulta, sem apagar dado.
- `apps/grp/loader.py`: sem filtro de linha.

## 4. Silver → Gold (`core/gold/relacionamento.py`, `core/transform/chaves.py`)

`ConvenioIntegrado` tem 1 linha por `siafi_uo`. Rodando o código atual sobre a
Silver antiga: 6.086 convênios entram, **5.346 saem**.
- `filtrar_uo` (`chaves.py:63`, chamado em `relacionamento.py:173` e `:207`):
  **1** convênio excluído por UO da lista `UOS_EXCLUIR` (11 UOs
  "não-operacionais", regra herdada do QlikView).
- `limpeza_g` (`relacionamento.py:858`): **739** convênios excluídos por não
  terem nenhuma data `G_`.
- `montar_sigcon_chaves` (`relacionamento.py:223`) e `_preparar_sigcon_completo`
  (`:356`) fazem `drop_duplicates("siafi_uo")`: hoje removem 0 (6.086 chaves
  distintas em 6.086 linhas). Mas, se aparecer duplicata, ela some sem aviso.
- `resolver_siafi_atual` (`chaves.py:178`): deduplica a **dimensão** de de-para
  para fazer a consulta (5.804 linhas repetidas). Não tira linha da tabela-base.
- `deduplicar_por_siafi_atual` (`relacionamento.py:901`): nenhum chamador.
- `core/gold/convenios.py` (l.80 e l.106): `.exclude(data_inicio_vigencia=None)`
  é filtro de consulta de gráfico, não apaga dado.

Na aba Convênios, a lista vem de `Convenio` (5.353 linhas, sem perda). O Gold
só complementa as linhas (`apps/sigcon/services.py:115`, filtro de proponente
em `:409`). Os 740 convênios excluídos do Gold aparecem na tela com "—" nas
colunas do Gold.

## 5. O que não é exclusão de linha, mas perde dado

- **Datas (bug B1 em `docs/plano_fase8_models_sigcon.md`):** 32.062 datas
  viram nulo na Silver legada. A linha fica, a célula se perde. Precisa ser
  corrigido junto com esta regra.
- `errors="coerce"` na tipagem: valor que não converte vira nulo, com contagem
  no log. Nas fontes atuais, só as datas de B1 são afetadas de forma
  relevante.
