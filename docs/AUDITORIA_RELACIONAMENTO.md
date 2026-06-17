# Auditoria R0 — Relacionamento de Tabelas

**Data:** 2026-06-10  
**Escopo:** diagnóstico pré-implementação da etapa R1–R4 do bloco de relacionamento  
**Método:** leitura de `core/`, `apps/convenios/`, `docs/` + leitura direta de `docs/bases qlikview.txt`

> Esta versão foi gerada **após a leitura do script QlikView real** (`docs/bases qlikview.txt`).
> As seções 1 e 3 foram atualizadas com referências a linhas específicas do script.

---

## 1. COBERTURA

Legenda: ✅ já coberto · ⚠️ parcial · ❌ ausente

### 1.1 Chaves e Relacionamento

| Item QlikView | Status | Detalhe Python |
|---|:---:|---|
| Chave `SIAFI_UO` (concat SIAFI + UO, sem separador) | ⚠️ Parcial | Campos existem separados; join usa tupla (SIAFI, UO); concatenação `SIAFI & UO` como string única **não implementada** — ver nota abaixo |
| De-para SIAFI antigo→atual (`SIAFI2.csv`) | ❌ Ausente | Arquivo existe no QlikView (`Dados\SIAFI2.csv`); **não registrado** em `sources.py`; campo `SIAFI_UOATUAL` inexistente |
| Tabela `sigcon_chaves` (ponte SICONV↔SIGCON) | ❌ Ausente | Conceito não implementado; a estrutura do QlikView usa `Chaves_convenio.csv` como base e acumula dados de múltiplas fontes via left join |
| Integração SICONV (join por `NR_CONVENIO`) | ❌ Ausente | `siconv_convenio` registrado como fonte, sem schema YAML, sem join com SIGCON |
| Chave SICONV: `ID_PROPOSTA` | ❌ Ausente | Campo não existe nos models nem na Silver |
| Campos `G_` (coalesce SICONV→SIGCON) | ❌ Ausente | 21 campos G_ no QlikView; nenhum no Python |
| Campos `A_` (visão sobre `SIAFI_atual`/`UOATUAL`) | ❌ Ausente | Depende de SIAFI_UOATUAL, que também está ausente |

> **Nota sobre `SIAFI_UO`:** no QlikView, a chave é construída como `[Convênio Número Sequencial SIAFI] & [Unidade Orçamentária  Código]` — **sem separador**, concatenação direta de strings. O nome original do campo UO tem **dois espaços** entre `Orçamentária` e `Código` (artefato do BO/PRODEMGE). Isso significa que `"9309074" & "1261"` gera `"93090741261"` — e qualquer diferença de padding numérico ou espaço vai quebrar o join silenciosamente. Documentar a regra exata de formatação antes de implementar.

### 1.2 ApplyMap / De-paras

| Mapa QlikView | Arquivo fonte | Status | Detalhe Python |
|---|---|:---:|---|
| `MapaG_UO` — UO código → nome completo | inline (script, linhas 1922–2075) | ❌ Ausente | Tabela completa está no script; pode ser extraída diretamente |
| `Mapa5` — nome → sigla | inline (linhas 2077–2173) | ❌ Ausente | Idem |
| `Mapa4` — nome → "nome + sigla" | inline (linhas 2177–2273) | ❌ Ausente | Idem |
| `Mapa3` — concedente padronizado | inline (linhas 2275–2746) | ❌ Ausente | Mapa muito grande (>400 entradas) — candidato a CSV versionado |
| `Mapa2` — situação padronizada (18 entradas) | inline (linhas 2747–2769) | ❌ Ausente | 18 regras de agrupamento de situação; ver lista exata abaixo |
| `Map_Tipo_SIAFI` ("Mapa1") — tipo de instrumento (2 entradas) | inline (linhas 2787–2793) | ❌ Ausente | Apenas: `11 → Acordo / Ajuste`, `15 → Transferências Especiais` |
| `Mapa_Nomes_Parlamentares` — nome bruto → nome oficial | Excel `Dados\De para nomes parlamentares.xlsx` | ❌ Ausente | Arquivo externo não registrado em `sources.py` |
| Esfera do concedente (CNPJ → esfera) | `Dados\dcgce_esfera.XLSX` | ✅ Coberto | `Esfera` model, schema, fonte e loader completos |

**Mapa2 — situações completas (para `data/referencia/`):**

| Situação original | Situação padronizada |
|---|---|
| Aguardando Prestação de Contas | Aguardando Prestação de Contas |
| BLOQUEADO | Bloqueado |
| Cancelado | Cancelado |
| Convênio Anulado | Anulado |
| Convênio Rescindido | Rescindido |
| Em execução | Em execução |
| Prestação de Contas Aprovada | Finalizado |
| Prestação de Contas Aprovada com Ressalvas | Finalizado |
| Prestação de Contas Comprovada em Análise | Prestação de Contas em Análise |
| Prestação de Contas Concluída | Prestação de Contas Concluída |
| Prestação de Contas em Análise | Prestação de Contas em Análise |
| Prestação de Contas em Complementação | Prestação de Contas em Análise |
| Prestação de Contas enviada para Análise | Prestação de Contas em Análise |
| Prestação de Contas Rejeitada | Finalizado |
| Proposta/Plano de Trabalho Aprovado | Proposta/Plano de Trabalho Aprovado |
| Proposta/Plano de Trabalho Complementado em Análise | Proposta/Plano de Trabalho em Análise |
| Proposta/Plano de Trabalho Complementado Enviado para Análise | Proposta/Plano de Trabalho em Análise |
| VENCIDO | Vencido |
| VIGENTE | Vigente |

### 1.3 Campos G_ definidos no QlikView (sigcon_chaves3 + sigcon_chaves2)

| Campo G_ | Regra de coalesce |
|---|---|
| `G_dia_assinatura` | SICONV → SIGCON (`dia_assinatura_siconv1` / `dia_assinatura_sigcon1`) |
| `G_ano_assinatura` | derivado de G_dia_assinatura |
| `G_inicio_vigencia` | SICONV → SIGCON |
| `G_ano_inicio_vigencia` | derivado |
| `G_fim_vigencia` | SICONV → SIGCON |
| `G_fim_vigencia_inicial` | SICONV → SIGCON (valor original antes de aditivos) |
| `G_situacao_convenio` | SICONV → SIGCON |
| `G_situacao_convenio_categorizado` | ApplyMap(Mapa2, G_situacao_convenio) |
| `G_objeto_convenio` | SICONV → SIGCON |
| `G_proponente` | SICONV → SIGCON |
| `G_proponente_pad` | ApplyMap(Mapa4, G_proponente) |
| `G_proponente_pad_siglas` | ApplyMap(Mapa5, G_proponente) |
| `G_concedente` | SICONV → SIGCON |
| `G_concedente_pad` | ApplyMap(Mapa3, G_concedente) |
| `G_valor_concedente` | SICONV → SIGCON |
| `G_valor_proponente` | SICONV → SIGCON |
| `G_valor_global` | SICONV → SIGCON |
| `G_instrumento` | ApplyMap(Map_Tipo_SIAFI, ...) → fallback `'Convênio de Entrada'` |
| `G_esfera` | SICONV → SIGCON → fallback `'Federal'` |
| `G_UO` | SICONV → SIGCON |
| `G_UO_descricao` | ApplyMap(MapaG_UO, G_UO) |
| `G_vigencia` | `if(G_fim_vigencia > today(), 'Vigente', 'Vencido')` |
| `G_ano_convenio` | G_ano_assinatura → G_ano_inicio_vigencia |
| `G_responsaveis` | divisão equipe SICONV → SIGCON |
| `G_valor_não_aditado` | flag combinado SICONV+SIGCON |
| `G_período_não_aditado` | `G_fim_vigencia = G_fim_vigencia_inicial` |
| `limpeza_g` | flag que remove registros onde TODAS as datas e ano são nulos |

### 1.4 Fontes / Ingestão SIGCON

| Fonte | Status |
|---|:---:|
| `dcgce_convenio` (chave SIAFI+UO, valores, vigência) | ✅ Coberto |
| `dcgce_geral` (publicação, assinatura, plano_trabalho_codigo) | ✅ Coberto |
| `dcgce_plano_trabalho` (título, objeto, CNPJ, instrumento) | ✅ Coberto |
| `dcgce_cronograma_desembolso` | ✅ Coberto |
| `dcgce_plano_aplicacao` | ✅ Coberto |
| `dcgce_termo_aditivo` | ✅ Coberto |
| `dcgce_prorrogacao_oficio` | ✅ Coberto |
| `dcgce_declaracao_contrapartida` | ✅ Coberto |
| `dcgce_sigcon_nt_emenda` | ✅ Coberto |
| `dcgce_esfera` | ✅ Coberto |
| `dcgce_codigo_convenio` (ponte ETL) | ✅ Coberto |
| `dcgce_codigo_ta` (ponte ETL) | ✅ Coberto |
| `dcgce_codigo_dec_contrap` (ponte ETL) | ✅ Coberto |
| `dcgce_chave` / `Chaves_convenio.csv` | ⚠️ Parcial | Schema gerado mas colunas com ponto (ver seção 3) |
| `dcgce_unidades_executoras` | ⚠️ Parcial | Schema gerado; `duvidoso` não revisados; model ausente |
| `siconv_convenio` (Transferegov) | ⚠️ Parcial | Fonte registrada; **schema YAML ausente**; sem join |
| `SIAFI2.csv` (de-para UO antigo→atual) | ❌ Ausente | Confirmado no QlikView: `Dados\SIAFI2.csv`, colunas `SIAFI2`, `UO2`, `UOATUAL` |
| `De para nomes parlamentares.xlsx` | ❌ Ausente | Fonte do `Mapa_Nomes_Parlamentares`; não registrada |
| `uo_siconv.xlsx` (proponente → UO da equipe) | ❌ Ausente | Tabela de divisão/equipe SICONV |

### 1.5 Infraestrutura de ETL

| Capacidade | Status |
|---|:---:|
| Bronze imutável / append-only | ✅ Coberto |
| Silver tipada por schema YAML | ✅ Coberto |
| Normalização de nomes de colunas (acento/case) | ✅ Coberto |
| Full refresh idempotente no banco | ✅ Coberto |
| Joins SIGCON internos (Convenio+Geral+Plano+Esfera) | ✅ Coberto |
| Drop-duplicates antes de joins (anti-fan-out) | ✅ Coberto |
| Filtro de UOs a excluir | ❌ Ausente |
| Tabela de correções versionadas | ❌ Ausente |
| `normalizar_coluna()` trata pontos | ❌ Ausente — bug confirmado |

---

## 2. OTIMIZAÇÕES

### 2.1 Onde o Python já está mais limpo que o QlikView

| Aspecto | O que o Python faz melhor |
|---|---|
| **Tipagem** | Schema YAML por fonte com contratos explícitos de tipo; QlikView não tinha contratos |
| **Rastreabilidade Bronze** | CSV com timestamp + append-only |
| **Separação de responsabilidades** | Bronze → Silver → Gold; QlikView misturava tudo |
| **Idempotência** | `delete + bulk_create`; QlikView não tinha controle transacional |
| **Anti-fan-out declarativo** | `drop_duplicates` antes de cada merge em `loader.py` |
| **Pontes ETL explícitas** | `dcgce_codigo_convenio` etc. são fontes declaradas; no QlikView eram intermediários implícitos |

### 2.2 Onde o Python ainda pode melhorar

| Problema | Localização | Impacto |
|---|---|---|
| **`iterrows()` em todos os loaders** | `loader.py`, todas as `carregar_*` | Performance: ~50× mais lento que abordagem vetorizada |
| **`_normalizar_chave()` no loader** | `loader.py:107-119` | Indicador que a Silver entrega chaves mal limpas; normalização deveria ser na Silver |
| **`normalizar_coluna()` não trata pontos** | `core/transform/utils.py:9-22` | Colunas exportadas do QlikView usam pontos como separadores (`Convênio.Número.Sequencial.SIAFI`); precisam virar underscores — **bug confirmado** |
| **Dois schemas para `dcgce_plano_trabalho`** | `dcgce_plano.trabalho.yaml` e `dcgce_plano_trabalho.yaml` | Confusão; consolidar num único nome |
| **`chaves_convenio.yaml` com nomes corrompidos** | Colunas `plano.trabalho.tipo.siafi`, `unidade.orcamentaria..codigo` | Resultado direto do bug acima: pontos não foram convertidos |
| **`siconv_convenio` sem schema** | Registrado em `sources.py`; sem `schemas/siconv_convenio.yaml` | Bloqueia etapa R2 |
| **`ano` como `texto`** | Vários schemas, campo `convenio_ano` etc. | Devia ser `int16` ou pelo menos `identificador` para facilitar filtros de ano |
| **Typo `conveno_codigo_plano_trabalho`** | `ConvenioGeral`, `CodigoPlanoTrabalho`, `loader.py` | Veio da fonte; documentado e propagado corretamente, mas precisa de comentário para não ser "corrigido" acidentalmente |

---

## 3. ERROS DO QLIKVIEW A NÃO REPLICAR

### 3.1 Filtro de UO com argumento único (bug de sintaxe — 2 ocorrências confirmadas)

A maioria das ~55 ocorrências do filtro de UO está **correta** (argumentos separados):
```
Where not match([Unidade Orçamentária  Código], '5131','9801','4611',...)   ← correto
```

Porém existem **exatamente 2 ocorrências com o bug de string única** (filtro não exclui nada):
```
linha 1762: Where not match([Unidade Orçamentária - Código],'5131,9801,4611,4441,...')  ← BUG
linha 1793: Where not match([Código Unidade Orçamentária],'5131,9801,4611,4441,...')    ← BUG
```
Esses dois blocos carregam registros que deveriam ser excluídos. No Python, o filtro ainda não existe — a constante `UOS_EXCLUIR` (R1) deve ser implementada com `frozenset`, não uma string.

**Lista oficial de UOs a excluir (confirmada no script):**
```
5131, 9801, 4611, 4441, 4451, 2361, 4121, 1041, 1031, 1051, 4031
```
(11 códigos — copiar exatamente para `UOS_EXCLUIR`)

### 3.2 Filtro de UO repetido ~55 vezes

O mesmo conjunto de 11 UOs aparece em ~55 `WHERE` clauses distribuídas ao longo do script, com variações no nome do campo (`[Unidade Orçamentária  Código]`, `[Unidade Orçamentária - Código]`, `[Código Unidade Orçamentária]`, `UO_COD`, `UO`). Qualquer alteração na lista exige editar dezenas de lugares — e já ficou fora de sincronia nos 2 casos com bug.

**No Python:** centralizar em `UOS_EXCLUIR` em `core/transform/chaves.py`.

### 3.3 Bases anuais "explodidas" — já entrou no Python

**No QlikView:** blocos anuais separados para execução estadual.

**No Python — confirmado em `sources.py`:**
```python
"qv_despesa_ano_2019": ...
"qv_despesa_ano_2020": ...
```
Adicionar um exercício novo requer uma nova entrada no registro, um novo schema YAML e um novo parquet. A correção (fonte dinâmica + coluna `exercicio`) deve ser feita em R1.

### 3.4 Nomes de coluna com pontos (QlikView CSV export)

O arquivo `Chaves_convenio.csv` é exportado do QlikView e usa pontos como separadores de palavras nos nomes de coluna (convenção interna do QlikView):
```
Convênio.Número.Sequencial.SIAFI
Unidade.Orçamentária..Código    ← dois pontos = dois espaços originais
SICONV..                        ← campo com nome estranho "SICONV ?"
```

`normalizar_coluna()` **não converte pontos**, apenas whitespace. Resultado: o schema `chaves_convenio.yaml` tem colunas como `unidade.orcamentaria..codigo` que nunca vão bater com nenhum merge. Correção mínima em `utils.py`:

```python
# acrescentar antes do re.sub:
nome = nome.replace(".", " ")
```

### 3.5 Correções de dados hard-coded — inventário completo

O QlikView tem 3 categorias de correções hard-coded. **Nenhuma entrou no Python** (Bronze preserva dado cru), mas precisam virar `data/referencia/correcoes.csv` antes de R2.

**Categoria 1 — Erros de digitação sistêmicos (mapeamento inline)**

| Mapa | Regra | Linhas QlikView |
|---|---|---|
| `Map_2919` | `Year = 2919 → 2019` | 1304–1310 |
| `Map_Data_2919` | `'27/12/2919' → 43826` (Excel serial de 27/12/2019) | 1313–1320 |
| `Map_Data_2919` | `'12/27/2919' → 43826` (formato americano errado) | 1313–1320 |

**Categoria 2 — Correções de datas por código de plano de trabalho** (hard-coded no `IF`)

| Campo | Condição | Valor errado | Valor correto | Linha |
|---|---|---|---|---|
| `[Convênio Data Assinatura Convênio]` | `plano_trabalho = '11043'` | `'13/06/2014'` | `'12/06/2014'` | 1338 |
| `[Convênio Data Assinatura Convênio]` | `plano_trabalho = '11042'` | `'28/05/2014'` | `'27/05/2014'` | 1338 |

**Categoria 3 — Correções de registros específicos por SIAFI** (hard-coded em `IF`)

| Campo | SIAFI | Valor errado | Valor correto | Linha |
|---|---|---|---|---|
| `[Data Real Convênio]` | `9309074` | `'29/01/2025'` | `'31/12/2023'` | 1606 |
| `[Situação]` | `9440702` | `'BLOQUEADO'` | `'VIGENTE'` | 1603 |
| `[Valor Concedente]` | `9051491` | `787155` | `708680` | 1609 |
| `[Valor Concedente]` | `9051488` | `708680` | `787155` | 1609 |
| `[Valor Total Convênio]` | `9051491` | `787155` | `708680` | 1615 |
| `[Valor Total Convênio]` | `9051488` | `708680` | `787155` | 1615 |

**Categoria 4 — Correções de código do convênio** (hard-coded em `IF`)

| Valor errado | Valor correto | Linha |
|---|---|---|
| `'CV s/ nº 2020'` | `'CV 559/5502'` | 1601 |
| `'CV 98/2020'` | `'CV 10954'` | 1601 |
| `'CV 89/2020'` | `'CV 10953'` | 1601 |
| `'TE - 202139600001 - PMMG'` | `'TE - 202129940004 - PMMG'` | 1601 |

### 3.6 Problema não documentado no QlikView: SIAFI_UOATUAL suspeito

O próprio desenvolvedor deixou um comentário na linha 2799 do script:
```
//parece estar errado, antigamente trazia somente siafi atualizado nessa tabela,
// hoje parece estar trazendo tudo - procurar com o rafa tabela de siafis atuais
```
Isso significa que a coluna `SIAFI_UOATUAL` em `sigcon_chaves1` **pode estar igual a `SIAFI_UO`** para todos os registros — o de-para `SIAFI2.csv` pode não estar funcionando como esperado na versão atual. **Verificar com o Rafa (ou responsável pelo dado SIAFI) antes de implementar em R2.** Não replicar o comportamento errado; reimplementar com regra de negócio clara.

---

## 4. PLANO MÍNIMO (R1 → R4)

### R1 — Estrutura (sem implementar joins)

1. **Corrigir `normalizar_coluna()`** para converter pontos em underscores — pequena mas crítica para `dcgce_chave`.
2. **Consolidar bases anuais de execução:** substituir `qv_despesa_ano_XXXX` por fonte dinâmica que varre `data/raw/execucao/` com coluna `exercicio` derivada do nome do arquivo.
3. **Criar `data/referencia/`** com os de-paras extraídos diretamente do script QlikView:
   - `uo_nomes.csv` — extrair `MapaG_UO` (linhas 1922–2075 do script)
   - `uo_siglas.csv` — extrair `Mapa5` (2077–2173)
   - `uo_descricoes.csv` — extrair `Mapa4` (2177–2273)
   - `concedentes_padronizados.csv` — extrair `Mapa3` (2275–2746)
   - `situacoes_padronizadas.csv` — extrair `Mapa2` (tabela acima, 18 entradas)
   - `tipos_siafi.csv` — `Map_Tipo_SIAFI` (2 entradas: 11, 15)
   - `parlamentares.csv` — registrar fonte `Dados\De para nomes parlamentares.xlsx`
   - `correcoes.csv` — todas as 14 correções da seção 3.5
4. **Registrar `SIAFI2.csv` em `sources.py`** (colunas: `SIAFI2`, `UO2`, `UOATUAL`).
5. **Registrar `De para nomes parlamentares.xlsx` em `sources.py`**.
6. **Centralizar `UOS_EXCLUIR`** como `frozenset` em `core/transform/chaves.py` com os 11 códigos confirmados.
7. **Gerar e revisar schema de `siconv_convenio`.**
8. **Resolver schemas problemáticos:** `chaves_convenio.yaml` e limpar `dcgce_plano.trabalho.yaml` antigo.
9. Atualizar `docs/ARQUITETURA.md`.

### R2 — Resolução de chaves e de-paras

1. Implementar `montar_siafi_uo(siafi, uo)` com regra explícita de formatação (sem separador, sem padding adicional — confirmar com a equipe se há zeros à esquerda relevantes).
2. Implementar de-para `SIAFI_UOATUAL` via `SIAFI2.csv` — **validar contra o comentário da seção 3.6 antes de implementar**.
3. Aplicar de-paras de R1 gerando colunas `_pad` / `_std` sem sobrescrever originais.
4. Aplicar `correcoes.csv` com log.
5. Desduplicar dimensões.
6. Testes unitários para pontos 1–4.

### R3 — Relacionamento das tabelas

1. Montar `sigcon_chaves`: join SICONV por `NR_CONVENIO`/`ID_PROPOSTA` ↔ SIGCON por `SIAFI_UO`.
2. Produzir 21 campos `G_` (coalesce SICONV→SIGCON conforme tabela da seção 1.3).
3. Produzir campos `A_` (visão sobre `SIAFI_atual`).
4. Validar ausência de fan-out.
5. Gravar `data/gold/convenios_relacionados.parquet`.

### R4 — Conectar ao Django

1. Novo model com campos G_/A_ e chaves SICONV.
2. Migration + loader idempotente.
3. Admin para inspeção.

---

## Por que resolver chaves e de-paras ANTES de relacionar — conceito de fan-out

Imagine que você tem:
- Tabela A (convênios SIGCON): **1 000 linhas**, uma por convênio
- Tabela B (SICONV): **1 200 linhas**, às vezes com mais de um registro por convênio (versões, aditivos)

Se você fizer o join sem antes garantir que B está desduplicada por convênio, o resultado pode ter
**1 000 × n linhas**, onde n é o número de ocorrências duplicadas em B para cada chave de A.
Isso é chamado de **fan-out** (espalhamento): cada linha de A "faz fã" de N linhas de B.

O efeito prático é devastador:
- Somar `valor_global` soma o mesmo convênio N vezes → totais inflados
- Contar convênios distintos dá um número correto, mas agregar por situação dá errado
- O bug é difícil de detectar porque o resultado parece plausível

A solução é garantir, **antes do join**, que o lado "dimensão" tem **no máximo uma linha por chave**.
Isso se faz com `drop_duplicates(subset=["chave"])` ou escolhendo qual versão manter por regra explícita.

O mesmo vale para de-paras: se `MapaG_UO` tiver duas entradas para o mesmo código de UO, o join duplica cada convênio daquela UO. Resolver o de-para primeiro evita o problema na raiz.

---

## O que você precisa decidir antes de iniciar R1

Com o script em mãos, 4 das 5 perguntas agora têm resposta; só a 5ª precisa de confirmação:

1. **Script no repositório?** — ✅ Resolvido: `docs/bases qlikview.txt` já está no repo.

2. **Lista de UOs a excluir?** — ✅ Confirmada:
   `5131, 9801, 4611, 4441, 4451, 2361, 4121, 1041, 1031, 1051, 4031`

3. **`SIAFI2.csv` disponível?** — ⚠️ **Parcialmente resolvido:** o arquivo existe (`Dados\SIAFI2.csv` no ambiente QlikView). Precisa ser copiado para `data/raw/` e registrado. **Mas atenção:** há um comentário de desenvolvedor no script (linha 2799) dizendo que a lógica "parece estar errada". Confirmar com quem mantém o dado (citado no comentário como "Rafa") antes de R2.

4. **De-paras: CSV estáticos ou fonte automática?** — ✅ Decidido por você: `MapaG_UO`, `Mapa5`, `Mapa4`, `Mapa2`, `Map_Tipo_SIAFI` podem ser **extraídos diretamente do script** como CSVs estáticos em `data/referencia/`. O `Mapa3` (concedentes) e `Mapa_Nomes_Parlamentares` são mais dinâmicos e podem precisar de atualização periódica — definir se são CSVs versionados no Git ou fontes externas.

5. **❓ Granularidade do join SICONV↔SIGCON:** um convênio SIGCON pode ter 0, 1 ou N registros no SICONV? Isso determina o `how=` do join e onde desduplicar. Verificar na prática com os dados antes de R3.
