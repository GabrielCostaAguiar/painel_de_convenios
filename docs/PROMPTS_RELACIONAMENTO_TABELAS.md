# Painel de Convênios — Bloco de Relacionamento de Tabelas
### Série de prompts para o Claude Code (VS Code)

Este bloco entra **entre a camada Silver (que você já tem) e a visualização**. O objetivo é reproduzir,
em Python, o "miolo" do script QlikView atual: a resolução de chaves, o de-para de SIAFI antigo→atual,
os campos coalescidos (`G_`/`A_`) e os joins SICONV↔SIGCON — **otimizando o que está certo e consertando
os erros do QlikView, sem replicá-los.** A série **para na conexão das tabelas relacionadas ao Django**;
telas, KPIs e gráficos ficam para depois.

---

## Como usar

- Cole **um prompt por vez** no Claude Code, dentro do VS Code.
- Ao fim de cada um, **confira o que foi feito, rode o que precisar e faça o commit** antes do próximo.
- Todos os prompts são **flexíveis por design**: cada um começa mandando o Claude *auditar o que já existe*
  e **só acrescentar o que falta** — não refazer o que já está correto.

> **Regra de ouro (vale para todos):**
> 1. Caminhos sempre dinâmicos (`pathlib` + `DATA_DIR`/settings), nunca fixos.
> 2. Ao terminar, o Claude deve **PARAR**, listar **o que já estava certo / o que acrescentou / o que devo conferir** — sem avançar de fase sozinho.
> 3. Avanço em camadas controladas, com commit ao fim de cada etapa.

---

## Visão geral das etapas

| Etapa | Objetivo | O que sai pronto |
|-------|----------|------------------|
| R0 | **Auditoria**: o Python cobre o QlikView? Onde otimizar? Quais erros do QlikView NÃO replicar? | Relatório de cobertura + lista de correções |
| R1 | **Mudanças estruturais**: preparar o terreno para o relacionamento (sem ainda relacionar) | Pastas/módulos de chaves e de-paras, dimensões de referência |
| R2 | **Resolução de chaves e de-paras** na Silver | `SIAFI_UO`, `SIAFI_UOATUAL`, mapas e correções como tabelas versionadas |
| R3 | **Relacionamento das tabelas** (coalesce `G_`/`A_`, joins SICONV↔SIGCON) | Tabela integrada de convênios, sem fan-out |
| R4 | **Conectar ao Django** (models + carga) e **PARAR** | Tabela relacionada disponível ao back-end Django |

---

## PROMPT R0 — Auditoria de cobertura, otimização e erros

**O que ele faz:** antes de mudar qualquer coisa, confere se o que já foi construído cobre o que o QlikView
faz de certo, aponta onde dá para otimizar e mapeia os erros do QlikView que **não** devem ser reproduzidos.

```
Contexto: projeto Painel de Convênios (DCGCE/SEPLAG-MG), Django + pipeline Bronze→Silver→(integração)→front.
Estou migrando o miolo de um script QlikView legado para Python. Ainda NÃO quero que você altere código nesta
etapa — quero um diagnóstico antes de mexer.

Leia primeiro, para entender o estado atual:
- core/ingestion/sources.py e core/ingestion/readers.py
- core/transform/ (incluindo convenios.py e utils.py com normalizar_coluna)
- os schemas por fonte já gerados/revisados
- docs/ARQUITETURA.md
- e o arquivo do script QlikView que vou anexar (ou que está em docs/), prestando atenção especial em:
  - a tabela "sigcon_chaves" e os campos que começam com G_ (lógica de coalesce SICONV→SIGCON);
  - a chave SIAFI_UO = [Convênio Número Sequencial SIAFI] & [Unidade Orçamentária Código];
  - o de-para de SIAFI antigo→atual feito a partir do arquivo SIAFI2.csv (SIAFI_UO → SIAFI_UOATUAL);
  - as chaves SICONV: NR_CONVENIO e ID_PROPOSTA;
  - os mapas ApplyMap (MapaG_UO, Mapa5, Mapa4, Mapa3, Mapa2, Mapa1, Mapa_Nomes_Parlamentares).

NESTA ETAPA, NÃO altere código. Apenas produza um relatório em docs/AUDITORIA_RELACIONAMENTO.md com:

1) COBERTURA: uma tabela comparando o que o QlikView faz no relacionamento de convênios x o que já existe
   hoje no projeto Python. Marque cada item como "já coberto", "parcial" ou "ausente".
2) OTIMIZAÇÕES: onde o projeto Python já está mais limpo/eficiente que o QlikView, e onde ainda dá para
   melhorar (ex.: leitura repetida de fontes, transformações duplicadas, falta de tipagem).
3) ERROS DO QLIKVIEW A NÃO REPLICAR — confira explicitamente e relate:
   - o filtro de UO escrito como string única (ex.: not match(campo,'5131,9801,...')) em vez de argumentos
     separados — nesses pontos o filtro NÃO exclui nada; identifique se algo análogo entrou no Python;
   - o mesmo filtro de UO repetido dezenas de vezes (candidato a parametrizar em um único lugar);
   - bases anuais "explodidas" (um bloco por ano) que deveriam virar histórico estático consolidado;
   - nomes de coluna que mudam entre anos (com/sem acento) exigindo normalização de schema;
   - correções de dados hard-coded no script (ex.: ano "2919"→2019, troca de valores entre SIAFI,
     datas de TA corrigidas na unha) que deveriam virar tabelas de exceção versionadas.
4) PLANO MÍNIMO: liste, em ordem, o que falta para chegar ao relacionamento completo das tabelas
   (sem incluir KPIs nem telas — isso é fase posterior).

IMPORTANTE:
- Não escreva código de produção agora; só o relatório.
- Como professor: ao final, explique em poucas linhas POR QUE resolver chaves e de-paras ANTES de relacionar
  evita o efeito de "fan-out" (linhas multiplicadas em joins) — quero entender o conceito.
- Ao terminar, PARE e me diga o que devo decidir antes da etapa R1.
```

> **Nota (assessor):** este R0 é o seguro do projeto. Ele te diz, em uma página, o que já está pronto e o
> que do QlikView é "bug que parece feature". Não pule — é o que evita você carregar para o Python os mesmos
> defeitos que motivaram a migração.

---

## PROMPT R1 — Mudanças estruturais (preparar o terreno)

**O que ele faz:** cria a estrutura para o relacionamento (módulos de chaves, de-paras e dimensões de
referência) **sem ainda relacionar**. Flexível: se algo já existir, ele só completa.

```
Continuando o Painel de Convênios. Com base na auditoria (docs/AUDITORIA_RELACIONAMENTO.md), vamos preparar
a ESTRUTURA para o relacionamento de tabelas — ainda sem fazer os joins finais.

Antes de mexer, releia core/transform/ e o que a auditoria marcou como "já coberto". Se algo abaixo já existir
e estiver correto, NÃO refaça — apenas complete o que falta e me diga o que reaproveitou.

NESTA ETAPA R1, faça e depois PARE:
1) Defina e crie (se ainda não existir) o lugar dos módulos de relacionamento. Recomende e justifique entre:
   - core/transform/chaves.py (resolução de chaves, ainda Silver), e
   - core/gold/relacionamento.py (integração/coalesce, pré-Gold);
   ou outra organização que escale melhor dado o que já existe. Quero sua recomendação fundamentada.
2) Centralize os DE-PARAS hoje espalhados no QlikView como dados de referência versionados (CSV/Parquet em
   data/referencia/ + funções de carregamento), um por mapa:
   - UO: código → nome (MapaG_UO), código → sigla (Mapa5), código → nome padronizado (Mapa4);
   - concedente padronizado (Mapa3); situação padronizada (Mapa2); tipo SIAFI (Mapa1);
   - nomes de parlamentares (Mapa_Nomes_Parlamentares).
   NÃO precisa preencher todo o conteúdo agora — crie o esqueleto, com 1 mapa realmente populado como exemplo
   e os demais com instruções claras de como completar.
3) Crie um único ponto de verdade para o FILTRO DE UO a excluir (a lista que no QlikView aparece repetida),
   como uma constante/função reutilizável — corrigindo o erro de string única identificado na auditoria.
4) Crie um esqueleto de tabela de EXCEÇÕES/correções de dados (data/referencia/correcoes.csv + função que a
   aplica), para substituir as correções hard-coded do QlikView. Deixe 1 exemplo e o resto documentado.
5) Atualize docs/ARQUITETURA.md com a etapa de relacionamento (onde ela fica no pipeline) e faça commit:
   "R1: estrutura de relacionamento e de-paras".

IMPORTANTE:
- Caminhos dinâmicos sempre.
- Funções pequenas, testáveis, com docstring.
- Não faça os joins/coalesce ainda — isso é R3.
- Como professor: explique por que transformar de-paras e correções em dados versionados (em vez de código)
  facilita manutenção e auditoria.
- Ao terminar, liste o que já existia, o que você criou e o que devo conferir antes de R2.
```

---

## PROMPT R2 — Resolução de chaves e de-paras

**O que ele faz:** implementa de fato as chaves do modelo (`SIAFI_UO`, `SIAFI_UOATUAL` via `SIAFI2.csv`,
`NR_CONVENIO`, `ID_PROPOSTA`) e aplica os de-paras e correções — ainda **antes** de relacionar.

```
Continuando o Painel de Convênios. A estrutura de relacionamento e de-paras já existe (R1). Agora vamos
resolver as CHAVES e aplicar os de-paras, deixando as tabelas prontas para serem relacionadas em R3.

Antes de mexer, releia core/transform/chaves.py (ou onde decidimos em R1) e os schemas das fontes.
Se algo já estiver implementado e correto, só complete — e me diga o que aproveitou.

NESTA ETAPA R2, faça e depois PARE:
1) Implemente a construção das chaves, em funções pequenas e testáveis:
   - SIAFI_UO = concatenação de [numero_sequencial_siafi] + [codigo_unidade_orcamentaria]
     (use os nomes já normalizados em snake_case; trate espaços/nulos/zeros à esquerda de forma explícita
      e documentada, porque isso muda o resultado do join);
   - NR_CONVENIO e ID_PROPOSTA nas fontes SICONV.
2) Implemente o de-para de SIAFI antigo→atual a partir da fonte equivalente ao SIAFI2.csv:
   gere SIAFI_UOATUAL para cada SIAFI_UO. Trate o caso de um convênio com vários números SIAFI ao longo dos
   exercícios (linhagem). Documente a regra de escolha do "atual".
3) Aplique os de-paras de R1 (UO, concedente, situação, tipo, parlamentar) gerando colunas padronizadas,
   sem sobrescrever as colunas originais (mantenha rastreabilidade origem → padronizado).
4) Aplique a tabela de correções/exceções (substituindo as correções hard-coded do QlikView). Cada correção
   aplicada deve ser logada (o que mudou, em qual registro, por qual regra).
5) Garanta que cada fonte de chave seja DESDUPLICADA quando for servir de dimensão (equivalente ao
   Distinct_SIAFI_UO do QlikView), para não multiplicar linhas depois. Explique onde a desduplicação é
   necessária e onde não é.
6) Escreva testes para: construção de SIAFI_UO (incluindo casos com zero à esquerda/nulos), de-para
   antigo→atual, e aplicação de pelo menos uma correção. Use amostras pequenas.
7) Atualize docs/ARQUITETURA.md e faça commit: "R2: resolucao de chaves e de-paras".

IMPORTANTE:
- Caminhos dinâmicos sempre.
- NÃO faça os joins entre tabelas ainda (isso é R3) — aqui só preparamos as chaves e padronizações.
- Como professor: explique por que a forma de montar a chave (zeros à esquerda, tipo texto x número,
  espaços) é a causa nº 1 de joins que "perdem" linhas — quero entender o detalhe.
- Ao terminar, liste o que já estava certo, o que acrescentou e o que devo conferir antes de R3.
```

> **Nota (assessor):** o ponto 2 (linhagem SIAFI antigo→atual) é o que mais costuma furar silenciosamente.
> Antes de seguir para R3, pegue 3 ou 4 convênios que você sabe que mudaram de número SIAFI e confira na mão
> se o `SIAFI_UOATUAL` ficou correto. É barato agora e caríssimo depois.

---

## PROMPT R3 — Relacionamento das tabelas (coalesce `G_`/`A_` + joins)

**O que ele faz:** o coração da migração — relaciona SICONV e SIGCON, monta os campos coalescidos
(`G_`/`A_`) e entrega uma tabela integrada de convênios sem multiplicar linhas.

```
Continuando o Painel de Convênios. Chaves e de-paras já estão resolvidos (R2). Agora vamos RELACIONAR as
tabelas, reproduzindo a lógica central do QlikView (a tabela sigcon_chaves e os campos G_/A_), de forma
limpa e testável.

Antes de mexer, releia core/gold/relacionamento.py (ou onde decidimos), o relatório de auditoria e a parte
do QlikView que monta os campos G_. Se parte já estiver feita e correta, só complete e me diga o que reusou.

NESTA ETAPA R3, faça e depois PARE:
1) Monte a tabela integrada de convênios juntando as fontes pelas chaves de R2:
   - SICONV (por NR_CONVENIO / ID_PROPOSTA) com SIGCON (por SIAFI_UO), respeitando a granularidade correta
     para NÃO multiplicar linhas (use as dimensões desduplicadas de R2; explique cada join e seu "how").
2) Reproduza a lógica de COALESCE dos campos G_ (prioridade SICONV, com fallback SIGCON), por exemplo para:
   valor_global, valor_concedente, valor_proponente, situação, objeto, proponente, concedente, datas de
   vigência/assinatura, instrumento, esfera. Em pandas isso deve ficar legível, ex.:
   resultado["valor_global"] = resultado["valor_global_siconv"].fillna(resultado["valor_global_sigcon"])
   Documente cada campo coalescido com a regra de origem.
3) Reproduza os campos A_ (a mesma informação projetada sobre o SIAFI mais atual, usando SIAFI_UOATUAL de R2).
   Explique a diferença prática entre a visão G_ e a visão A_.
4) DÊ CHECK NO QUE ESTÁ CERTO: para um conjunto pequeno de convênios conhecidos, compare os campos resultantes
   (valores, situação, vigência) com o que o QlikView produz hoje. Gere um pequeno relatório de divergências
   em docs/CONFERENCIA_R3.md (convênio, campo, valor Python, valor QlikView, status).
5) Valide a ausência de fan-out: o nº de convênios distintos na tabela integrada deve bater com a contagem
   esperada; alerte se algum join multiplicou linhas. Explique como detectou.
6) Escreva testes para: pelo menos 2 campos coalescidos (G_) e 1 campo da visão A_, usando amostras pequenas
   que cubram os três casos (só SICONV, só SIGCON, e ambos preenchidos).
7) Grave a tabela integrada em data/gold/ (ou onde fizer sentido) e atualize docs/ARQUITETURA.md.
8) Faça commit: "R3: relacionamento de tabelas e campos coalescidos".

IMPORTANTE:
- Caminhos dinâmicos sempre.
- NÃO construa KPIs, agregações de painel nem telas — isso é fase posterior. Pare no relacionamento.
- Como professor: explique por que fazer o coalesce em Python (fillna encadeado) é mais auditável que o
  IF aninhado do QlikView — e por que isso torna a regra de negócio testável.
- Ao terminar, liste o que já estava certo, o que acrescentou, o resultado da conferência (ponto 4) e o que
  devo conferir antes de R4.
```

> **Nota (assessor):** o ponto 4 (conferência contra o QlikView) é a sua prova de migração. Enquanto os campos
> coalescidos de um lote de convênios conhecidos não baterem com o painel atual, **não avance** — é exatamente
> aqui que se ganha ou se perde a confiança da liderança na nova solução.

---

## PROMPT R4 — Conectar as tabelas ao Django (e PARAR)

**O que ele faz:** liga a tabela relacionada ao back-end Django (models + carga idempotente), deixando-a
disponível para a futura camada de visualização. **Aqui a série termina.**

```
Continuando o Painel de Convênios. A tabela integrada de convênios (relacionamento + campos G_/A_) já existe
e foi conferida contra o QlikView (R3). Agora vamos CONECTAR essa tabela ao Django — e PARAR aqui. Nada de
telas, gráficos ou KPIs nesta etapa.

Antes de mexer, releia os models já existentes (apps/dashboard ou apps/convenios) e o management command de
carga que já temos (ex.: carregar_silver). Se já houver model/carga reutilizável, ESTENDA em vez de criar do
zero — e me diga o que aproveitou.

NESTA ETAPA R4, faça e depois PARE:
1) Crie/ajuste o model do Django que representa o convênio relacionado, com os campos da tabela integrada
   (chaves SIAFI_UO, SIAFI_UOATUAL, NR_CONVENIO, ID_PROPOSTA + os campos coalescidos G_/A_ relevantes).
   Defina índices nas chaves usadas para consulta e justifique-os. Recomende, com base na escala, se vale um
   app próprio (apps/convenios) — e implemente sua recomendação.
2) Gere e aplique as migrations.
3) Crie/estenda um management command (ex.: carregar_relacionamento) que leia a tabela integrada de data/gold/
   e popule o banco de forma IDEMPOTENTE (rodar de novo não duplica; use update_or_create ou chave única).
   Explique como garantiu a idempotência.
4) Registre o model no Django admin (list_display, search_fields, list_filter nas chaves e na situação) só
   para eu conseguir inspecionar os dados pela interface — sem montar telas de painel.
5) Escreva 1 teste de carga (rodar duas vezes não duplica) e 1 teste de leitura básica do model.
6) Atualize docs/ARQUITETURA.md indicando que o relacionamento está conectado ao Django e PRONTO para a
   futura camada de visualização (que NÃO faremos agora).
7) Faça commit: "R4: tabela relacionada conectada ao Django".

IMPORTANTE:
- Caminhos dinâmicos sempre.
- Esta é a ÚLTIMA etapa deste bloco. Ao terminar, NÃO comece telas, KPIs nem dashboards.
- Como professor: explique por que isolar a carga (Python/Gold → banco) da apresentação (views/templates)
  deixa o sistema mais escalável e fácil de testar.
- Ao terminar, me mostre: como rodar a carga, como abrir o admin e o que conferir; depois PARE e me diga
  qual seria o ponto de partida natural da próxima fase (visualização) — sem executá-la.
```

> **Nota (assessor):** ao fim do R4 você tem o que pediu: as tabelas relacionadas, conferidas contra o
> QlikView e disponíveis ao Django. A visualização (telas, KPIs, `SITUACAO_MONITORAMENTO`, alertas) é um
> bloco à parte — e é melhor assim, porque permite validar os números antes de gastar esforço com a tela.

---

## Resumo do que esta série entrega (e onde para)

- **Cobre o que o QlikView faz de certo** (chaves, coalesce SICONV→SIGCON, linhagem SIAFI) — R0 audita, R2/R3 implementam.
- **Otimiza o existente** — de-paras e correções viram dados versionados; filtro de UO num único ponto; histórico não "explode".
- **Conserta os erros do QlikView** — filtro de UO em string única, duplicação de filtros, correções hard-coded.
- **É flexível** — todo prompt audita antes e só acrescenta o que falta.
- **Para no ponto certo** — tabelas relacionadas e conectadas ao Django; visualização fica para a próxima fase.
