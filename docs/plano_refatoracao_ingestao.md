# Plano de refatoração — ingestão das bases legadas (Fase 1)

Branch `refactor/ingestao-legado`. Baseado no levantamento read-only descrito
em `docs/_baseline_fase0.md` e na investigação completa do motor/YAMLs/fontes
(resumida abaixo; evidências com arquivo:linha vieram do agente de
reconhecimento e foram conferidas contra o código antes de entrar aqui).

**Nota de divergência estrutural já registrada na Fase 0:** `apps/convenios/`
hoje é praticamente vazio — a lógica real do SIGCON está em `apps/sigcon/` e a
do GRP em `apps/grp/`, não como o `CLAUDE.md` descreve. Todas as referências
a "intocável em apps/" abaixo usam os caminhos reais (`apps/sigcon/`,
`apps/grp/`), não os do `CLAUDE.md`.

## 1. O motor hoje vs. o que a especificação pede

`core/transform/silver.py::transformar_fonte` já é o ponto de entrada único
para GRP e legado. Blocos YAML que **já existem e funcionam** hoje:

| Bloco | Linha | Observação |
|---|---|---|
| `colunas.data/valor/inteiro/identificador` | `silver.py:161-221` | `texto` é fallback automático, não lido do YAML |
| `renomear` | `silver.py:229-241` | só os 22 YAMLs `grp_*` o usam hoje |
| `anular` (coluna → lista de valores a anular) | `silver.py:142,209` | implementado, só para colunas `identificador`, **0 YAMLs usam** |

Comportamentos hoje **fixos em Python, não declarativos**:
- `SENTINELAS = {"N/A", "-3", ""}` (`utils.py:27`) — constante global única, calibrada para o GRP, sem override por fonte/coluna.
- `MAPA_BOOLEANO = {"SIM": True, "NÃO": False, "NAO": False}` (`utils.py:30`) — aplicado automaticamente a toda coluna com prefixo `fl_`, sem bloco YAML.
- `limpar_colunas_padronizadas` (sentinelas + booleanos `fl_`) só roda quando o YAML tem `renomear:` não vazio (`silver.py:239` `if mapa:`) — ou seja, hoje **nenhuma fonte legada passa por essa limpeza**, porque nenhuma tem `renomear`.
- `dropna(how="all")` (linhas 100% vazias) está amarrado à mesma condição `if mapa:` — não é uma regra geral independente.
- Não existem os blocos `sentinelas:` (por coluna), `booleanos:` (por coluna), `derivadas:`, `grao:`, `descartar:`, `descartar_linhas_se_nulo:`, `desdobrar:`, `quarentena:` pedidos pela especificação. Nenhum é gambiarra disfarçada — simplesmente não foram implementados ainda.

**Decisão de design para a Fase 2:** generalizar `anular:` para o papel de
`sentinelas:` (por coluna, qualquer tipo — hoje só cobre `identificador`),
em vez de criar um bloco redundante. `SENTINELAS` e `MAPA_BOOLEANO` globais
continuam existindo como *default* (para não quebrar o GRP, que nunca vai
declarar `sentinelas`/`booleanos` explicitamente se o comportamento atual já
for exatamente o que esses globais fazem), mas o motor passa a aceitar
override por YAML. Preciso validar com os YAMLs do GRP se declarar
explicitamente `sentinelas: {}`/`booleanos: {fl_...: {SIM:true,...}}` em cada
um deles reproduz bit a bit a saída atual antes de considerar a migração
"sem efeito colateral" — é o teste de regressão da Fase 2.

`derivadas: montar_siafi_uo(nr_siafi, cd_uo)` — a função já existe em
`core/transform/chaves.py:85-120` e é usada por `core/gold/relacionamento.py`
(intocável, fora de escopo). O motor vai importar e registrar essa função
para uso declarativo no YAML; `core/gold/` continua chamando-a direto como
hoje, sem mudança de comportamento ali.

## 2. YAMLs — classificação final

**GRP (mantém, só generaliza se necessário):** os 22 `grp_*.yaml`.

**Legado candidato aos 20 (vira um dos 21 da especificação, via `git mv` +
reescrita):** `dcgce_convenio`, `dcgce_geral`, `dcgce_plano_trabalho`,
`dcgce_termo.aditivo`→renomeia para `sigcon_termo_aditivo`,
`dcgce_prorrogacao_oficio`, `dcgce_declaracao_contrapartida`,
`dcgce_Cronograma_desembolso`→`sigcon_cronograma_desembolso`,
`dcgce_plano_aplicacao`, `dcgce_unidades.executoras`→`sigcon_unidade_executora`,
`dcgce_sigcon_nt_emenda`, `dcgce_Codigo_convenio`→`sigcon_chave_convenio`,
`dcgce_Codigo_ta`→`sigcon_chave_termo_aditivo`,
`dcgce_Codigo_plano_de_trabalho`→`sigcon_chave_plano_trabalho`,
`dcgce_Codigo_dec_contrap`→`sigcon_chave_declaracao`, `chaves_convenio`→`sigcon_chave_siconv`,
`siafi2`→`depara_siafi`, `dcgce_esfera`→`sigcon_concedente`,
`parlamentares`→`depara_parlamentar`, `siconv_convenio` (mesmo nome),
`controle_sei` (mesmo nome, + novo `controle_sei_documento` derivado).

As 4 que hoje só funcionam por o filesystem do Windows ser case-insensitive
(`dcgce_Codigo_convenio.yaml`, `dcgce_Codigo_dec_contrap.yaml`,
`dcgce_Codigo_ta.yaml`, `dcgce_Cronograma_desembolso.yaml` vs. chaves reais
em minúsculas) resolvem-se naturalmente no `git mv` da Fase 4 — não precisam
de correção isolada.

**Excluir na Fase 5 (sem uso comprovado — nenhuma `FonteDados` ativa ou
comentada referencia, nenhum `apps/` importa):**
- `core/transform/schemas/dcgce_chave.yaml`
- `core/transform/schemas/dcgce_convenios.yaml` (plural)
- `core/transform/schemas/dcgce_plano.trabalho.yaml` (nome com ponto, órfão — a chave real usa underscore e tem seu próprio YAML sem ponto)
- `core/transform/schemas/dcgce_termo.aditivo.yaml` (idem, nome com ponto)
- `core/transform/schemas/dcgce_unidades.executoras.yaml` (idem)
- `core/transform/convenios.py` (módulo todo — `NOME_FONTE="dcgce_convenios"` não existe em `FONTES`; único "uso" é uma menção em comentário de migration, não import)
- `core/transform/mapa_grp_instrumento.py` (módulo todo — duplica 1:1 o `renomear:` de `grp_instrumento.yaml`, nenhum chamador no repo)

**NÃO EXCLUIR, apesar de hoje não terem `FonteDados` ativa em `FONTES`
(estão comentadas em `sources.py`) — são usadas por `apps/grp/loader.py` e
`apps/grp/management/commands/carregar_grp.py`, fora do escopo desta tarefa:**
`dcgce_dados_grp.yaml`, `dcgce_cronograma_desembolso_grp.yaml`,
`dcgce_recursos_contrapartida_grp.yaml`, `dcgce_recursos_concedente_grp.yaml`,
`dcgce_plano_aplicacao_grp.yaml`, `dcgce_plano_aplicacao_grp_detalhes.yaml`,
`dcgce_tabela_uo_grp.yaml`. **DIVERGÊNCIA pré-existente, não corrigida
aqui:** essas 7 fontes estão com a `FonteDados` comentada em `sources.py`
(linhas 288-360) — ou seja, `rodar_silver` não roda para nenhuma delas hoje,
e `core/pipeline.py::FONTES_SILVER_GRP`/`carregar_grp.py::_LOADERS_GRP`
apontam para um pipeline que não funciona enquanto isso não for descomentado.
Isso é problema do GRP "antigo" (distinto do GRP novo em `grp_*`), não da
migração legada — vai só para o mapa de impacto da Fase 7, sem tocar.
`dcgce_esfera_grp.yaml` fica na mesma lista por segurança (referenciada em
teste de `apps/sigcon/tests/test_carregar_grp.py`), mesmo sem loader
correspondente em `_LOADERS_GRP`.

## 3. Capacidades que faltam no motor (Fase 2)

Implementar, nessa ordem de dependência:
1. Generalizar `anular:` → `sentinelas:` (qualquer tipo de coluna, não só identificador).
2. `booleanos:` por coluna (mapa valor→bool explícito no YAML; hoje é só `fl_` + `MAPA_BOOLEANO` global).
3. `descartar:` (remove coluna após renomear).
4. `descartar_linhas_se_nulo:` (lista de colunas).
5. `grao:` (checagem de unicidade + log de ALERTA, não interrompe).
6. `derivadas:` com registro de função (`montar_siafi_uo` primeiro e único caso).
7. Desacoplar `dropna(how="all")` da condição `if mapa:` — passa a ser regra geral incondicional.
8. `desdobrar:` (saída longa — só a tabela 21, `controle_sei_documento`).
9. `quarentena:` (saída separada — só a tabela 16, `depara_siafi`).

Testes unitários novos cobrem: conversor de valor (formatos `179371.54`,
`448745,57`, `1.234.567,89`, numérico do Excel), datas (datetime direto do
Excel vs. texto `dd/mm/aaaa` dayfirst vs. `data` sem hora vs. `data_hora` com
hora), e cada bloco novo isoladamente. Regressão do GRP = hashes de
`docs/_baseline_grp_silver.json` idênticos depois de todo YAML do GRP passar
a declarar `sentinelas`/`booleanos` explicitamente (ver decisão de design
acima).

## 4. Divergências encontradas contra a especificação (seção 9 do prompt)

- **`siconv_convenio`**: BOM real confirmado (`i»¿nr_convenio`) — a troca de
  encoding para `utf-8-sig` na Fase 3 resolve, como a especificação já
  previa.
- **`siconv_convenio.yaml` tem classificação desatualizada**: vários campos
  de data (`dia_assin_conv`, `dia_publ_conv`, `dia_inic_vigenc_conv`, etc.)
  estão como `identificador` no YAML atual por limitação da heurística do
  gerador (tokens não reconhecidos), mas a especificação já os corrige
  corretamente para `data` na tabela 19. A reescrita manual da Fase 4 segue
  a especificação, não o YAML atual — sem impacto no plano, só registro.
- **`controle_sei`**: nomes com parênteses/`?` (`no_siafi_(sigcon)`,
  `monitorar?`) confirmados batendo exatamente com a coluna "nome atual" da
  especificação — `normalizar_coluna` não trata esses caracteres, e a
  especificação já havia antecipado isso.
- Nenhuma outra divergência estrutural de cabeçalho encontrada nas 20
  fontes — todos os arquivos existem em `data/raw/` e os nomes normalizados
  batem com a coluna "nome atual" da especificação nas fontes verificadas
  em detalhe (01, 02, 03, 09, 17, 19, 20). As demais (04-08, 10-16, 18) não
  mostraram nomes inesperados no levantamento, mas recomendo confirmação
  coluna-a-coluna durante a escrita de cada YAML na Fase 4 (comparação
  linha a linha com a seção 9), não só nesta amostragem.

## 5. Mapa de intocáveis (apps/ e core/gold/) — prévia do mapa de impacto da Fase 7

Pontos que **vão quebrar** com a renomeação de chaves/colunas e que não
são tocados agora, só documentados:

- `apps/sigcon/loader.py` — todo `carregar_*` resolve o Parquet Silver por
  nome literal via `_silver_path("dcgce_...")` (ocorrências nas linhas
  151-154, 283-285, 351-352, 379-380, 416-432, 494-495, 523-524, 549-550,
  569-570, 587-588, 602-603, 621-622, 637-638, 656-657, 724-737, 830-831,
  848-859). Precisa de 1:1 para a chave nova por tabela.
- `apps/sigcon/management/commands/carregar_fonte.py:27-41` — dict
  `_LOADERS` usa como argumento de CLI nomes que **já hoje** divergem da
  chave real em `FONTES` (`"dcgce_plano.trabalho"`, `"dcgce_Cronograma_desembolso"`,
  `"dcgce_termo.aditivo"`, `"dcgce_Codigo_convenio"`, `"dcgce_Codigo_ta"`,
  `"dcgce_Codigo_dec_contrap"`) — isso é problema duplo: já está dessincronizado
  hoje, e vai precisar de nomes totalmente novos depois.
- `core/pipeline.py:58-77` (`CARGAS_ORM`) usa essas mesmas strings antigas
  como argumento posicional de `carregar_fonte` via `call_command` — mesma
  lista, mesmo impacto.
- `apps/sigcon/models/sigcon.py`, `apps/sigcon/models/externos.py:16-17`,
  `apps/sigcon/models/codigos.py:50` — docstrings citando nomes de fonte/
  parquet antigos. Não quebram em runtime, mas ficam incorretos; listar para
  atualização na próxima fase.
- `core/gold/relacionamento.py` — `montar_siafi_uo` (linhas 176, 209, 283),
  `resolver_siafi_atual` (linha 220), e a docstring de
  `montar_sigcon_integrado`/chamada real `montar_sigcon_chaves(df_chaves,
  df_siafi2)` (linha 830) leem diretamente os Parquets Silver de
  `dcgce_convenio`, `dcgce_codigo_convenio`, `dcgce_geral`,
  `dcgce_plano_trabalho`, `dcgce_esfera`, `chaves_convenio`, `siafi2`,
  `siconv_convenio` — maior ponto único de impacto da renomeação.
- `apps/grp/loader.py` e `apps/grp/models.py` — não são afetados pela
  migração legada (usam fontes `grp_*`/`dcgce_*_grp` que são um universo
  separado), citados aqui só pelo achado da seção anterior (pipeline GRP
  antigo pré-existente quebrado).

## 6. Pendências / riscos a decidir antes da Fase 2

1. Confirmar que generalizar `anular:`→`sentinelas:` não exige mudança de
   assinatura que afete os 0 usos atuais (seguro, zero YAML usa hoje).
2. Decisão sobre declarar `sentinelas`/`booleanos` explicitamente em todos
   os 22 YAMLs do GRP (necessário para não deixar comportamento "invisível"
   dependendo de globais) — aumenta o tamanho dos YAMLs do GRP, mas é o que
   a regra 4 da especificação pede explicitamente.
3. `core/transform/chaves.py` (filtrar_uo, aplicar_deparas, aplicar_correcoes)
   fica integralmente como está — é lógica de `core/gold/`, não do motor
   Silver, mesmo estando hoje dentro de `core/transform/`. Vou manter nessa
   pasta (está no escopo "pode alterar"), mas não vou tocar no conteúdo,
   só confirmar que nada do motor Silver passa a depender dele.

## Fase 2 — executada

Implementados em `core/transform/silver.py`/`utils.py`: `sentinelas:` (generaliza
o antigo `anular:`, agora para qualquer coluna tipada, chaves = nomes BRUTOS),
`booleanos:` (chaves = nomes FINAIS, com fallback para a convenção `fl_` +
`MAPA_BOOLEANO`), `descartar:`, `descartar_linhas_se_nulo:`, `grao:` (só loga
ALERTA), `derivadas:` (registro `FUNCOES_DERIVADAS`, hoje só `montar_siafi_uo`),
`desdobrar:` (gera uma segunda saída, acessível via `transformar_fonte_completo`)
e `quarentena:` (idem). `dropna(how="all")` deixou de depender de `renomear:`
não vazio — roda sempre, nos dois pontos (bruto e pós-tipagem). Removida
também a deduplicação de linhas 100% idênticas como regra geral.

`transformar_fonte` manteve o contrato público exato (devolve só a tabela
principal) — quem precisa de quarentena/desdobramento usa a nova
`transformar_fonte_completo`, que devolve os três resultados possíveis.

**Divergência deliberada da ordem da especificação:** tipagem (`colunas.*`)
continua rodando ANTES do `renomear:`, com `sentinelas:` usando nomes BRUTOS
— mudar isso exigiria reescrever as chaves de `colunas` nos 22 YAMLs do GRP.
Os blocos novos (exceto `sentinelas`) rodam DEPOIS do renomear, com nomes
FINAIS, na ordem da especificação. Documentado no docstring do módulo.

**Achado durante a regressão do GRP:** ao mover a nulagem de sentinela do
pós-renomear (`limpar_colunas_padronizadas`, um `.where()` cego sobre toda
coluna texto/string) para o pré-renomear (`sentinelas:`, já tipado), o
`.map()` de limpeza de espaços que sobrou em `limpar_colunas_padronizadas`
passou a degradar para dtype `object` em vez de `string` sempre que a coluna
ficava 100% nula ANTES de chegar lá (pandas 3 preserva `StringDtype` via
`.map()` só quando o resultado tem pelo menos um valor de string real, não
só `<NA>`). Corrigido com um `.astype("string")` explícito no final do loop.
Isso por sua vez revelou que a saída ORIGINAL do GRP já misturava, por
acidente, duas variantes de `StringDtype` (`na_value=nan` vs `na_value=<NA>`)
dependendo de qual caminho do código tocou a coluna por último — sem
diferença de valor nenhuma (confirmado coluna a coluna com `.equals()` contra
o motor antigo, incluindo nas 21 fontes GRP). A linha de base de hashes
(`docs/_baseline_grp_silver.json`) foi **regerada** para refletir a saída
agora uniforme (sempre `na_value=<NA>`); a regressão passou a vigiar a partir
daqui.

Testes novos em `tests/test_silver_grp.py` (15 casos): `sentinelas` (override
vs. padrão global), `booleanos` (override vs. erro em valor fora do mapa),
`descartar` (coluna presente/ausente), `descartar_linhas_se_nulo`, `grao`
(ALERTA sem remover), `derivadas` (`siafi_uo`), dedup de linhas idênticas,
`quarentena` (destino divergente vs. sem divergência) e `desdobrar` (uma
linha por célula preenchida, null não gera linha).

## Fase 4 — executada

`git mv` + reescrita completa dos 16 YAMLs renomeados, mais `siconv_convenio.yaml`
e `controle_sei.yaml` (mesmo nome, reescritos no lugar). Rodei `rodar_ingestao`
+ `rodar_silver` para as 20 fontes contra os arquivos reais em `data/raw/` —
todas geram Silver sem erro.

**Duas capacidades novas no motor, descobertas rodando contra dados reais
(não previstas na Fase 2):**

1. **`colunas.data_hora`** — a especificação pede a distinção "`data` guarda
   só a data, `data_hora` mantém a hora" (várias colunas `dh_*` nas tabelas
   02-07), mas a Fase 2 só implementou `data` (sem truncar a hora). Adicionado
   `data_hora` como categoria própria; `data` agora trunca para meia-noite
   (`.dt.normalize()`). Testado sem regressão no GRP (3 fontes usam `data`,
   nenhuma carrega hora real).
2. **`descartar_linhas_se_nulo:` passou a rodar ANTES da tipagem**, usando
   nomes BRUTOS — não depois do renomear como a Fase 2 original implementou.
   Achado ao rodar `sigcon_cronograma_desembolso` contra o arquivo real: o
   bloco desalinhado do relatório do BO (linha 29993) tem o texto solto
   "Plano Trabalho Código" caindo na coluna `mes_cronograma_desembolso`
   (declarada `inteiro`) — a conversão numérica (`errors="raise"`, proposital)
   quebra antes de qualquer `descartar_linhas_se_nulo` pós-renomear rodar.
   Resolvido fazendo esse bloco rodar logo depois do descarte de linhas
   vazias/cabeçalho repetido, operando em "" (ainda não há NaN nesse ponto).
   Documentado no docstring do módulo.

**DIVERGÊNCIA encontrada e corrigida (`sigcon_chave_siconv`):** o valor real
da coluna `siconv` tem `"N?o"` (não `"Não"`) — artefato de um caractere que a
exportação não conseguiu codificar, não erro de digitação. Adicionado ao
`booleanos.fl_siconv` como variante aceita de `False`, com comentário no YAML.

**DIVERGÊNCIA encontrada e corrigida no motor (não na fonte):** a detecção
de "linha que repete o cabeçalho" (Fase 2) comparava o valor da célula contra
o nome JÁ normalizado da coluna (`plano_trabalho_codigo`), mas o texto que
vaza nas linhas desalinhadas é o cabeçalho ORIGINAL ("Plano Trabalho
Código"). Corrigido normalizando a célula com a mesma função antes de
comparar (`normalizar_coluna`).

Nenhuma outra divergência contra a seção 9 da especificação — as 20 fontes
geraram Silver com as colunas, sentinelas e de-paras exatamente como
documentado.

**Pendente para a Fase 6 (validação com números reais):** confirmar as
contagens esperadas (ex.: 29.992 linhas em sigcon_cronograma_desembolso,
~1.878 chaves em depara_siafi, 4 valores distintos em sigcon_concedente.ds_esfera)
e rodar os testes V1-V16 da especificação.

## Fase 5 — executada

Excluídos, exatamente os itens já previstos na seção 2 (nenhum achado novo):

- `core/transform/schemas/dcgce_chave.yaml`
- `core/transform/schemas/dcgce_convenios.yaml`
- `core/transform/schemas/dcgce_plano.trabalho.yaml`
- `core/transform/schemas/dcgce_termo.aditivo.yaml`
- `core/transform/schemas/dcgce_unidades.executoras.yaml`
- `core/transform/convenios.py`
- `core/transform/mapa_grp_instrumento.py`

Confirmado antes de excluir: nenhum teste em `tests/` ou `apps/*/tests/`
referenciava qualquer um dos 7 itens; nenhuma `FonteDados` ativa ou
comentada em `sources.py` apontava para eles.

**Efeito colateral documentado, não corrigido (fora de escopo — `apps/`):**
`apps/sigcon/management/commands/rodar_transformacao.py` importa
`core.transform.convenios` em nível de módulo. Esse comando já era
legado/morto na prática — `CLAUDE.md` o marca como "legacy, do not use", e
ele só aceitava a fonte `"convenios"`, que não existe em `FONTES` desde a
Fase 3 (então rodá-lo já terminava em erro antes desta fase, só que em
tempo de execução). Depois da exclusão, `python manage.py
rodar_transformacao convenios` passa a falhar com `ImportError` no
carregamento do comando, em vez de `FileNotFoundError`/erro de fonte
inexistente em tempo de execução — mesmo resultado prático (comando
inutilizável), só muda onde quebra. `apps/sigcon/management/commands/
carregar_silver.py` (também legado, lê de um layout de Silver que não
existe mais — `data/silver/<fonte>/<fonte>_silver_*.csv` em vez de
`data/silver/<fonte>.parquet`) não importa nada que foi excluído, então
continua do mesmo jeito que já estava: inutilizável, mas sem erro de
import. Vai para o mapa de impacto da Fase 7.

Regressão: suíte completa idêntica ao baseline pré-Fase-5 (641 passed, 1
failed pré-existente, 1 skipped, 130 errors pré-existentes de Postgres —
zero diferença linha a linha no conjunto de FAILED/ERROR). Hash SHA-256
das 22 Parquets do GRP: 22/22 idênticos ao baseline.

## Resumo para o checkpoint

- [x] Motor do GRP mapeado (`silver.py`, `utils.py`, `chaves.py`, `readers.py`, `bronze.py`)
- [x] 20 fontes legadas: cabeçalhos lidos e comparados com a especificação — sem divergência estrutural bloqueante
- [x] 45 YAMLs classificados (22 GRP ativos / 16 legados a migrar / 4 com nome divergente mas resolvidos pelo `git mv` da Fase 4 / 7 "GRP antigo" intocáveis fora de escopo / 5 + 2 módulos Python mortos a excluir na Fase 5)
- [x] Capacidades novas do motor listadas (8 itens, seção 3 acima)
- [x] Mapa de impacto preliminar (seção 5) para a Fase 7
