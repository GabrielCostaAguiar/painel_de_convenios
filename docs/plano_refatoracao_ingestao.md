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

## Resumo para o checkpoint

- [x] Motor do GRP mapeado (`silver.py`, `utils.py`, `chaves.py`, `readers.py`, `bronze.py`)
- [x] 20 fontes legadas: cabeçalhos lidos e comparados com a especificação — sem divergência estrutural bloqueante
- [x] 45 YAMLs classificados (22 GRP ativos / 16 legados a migrar / 4 com nome divergente mas resolvidos pelo `git mv` da Fase 4 / 7 "GRP antigo" intocáveis fora de escopo / 5 + 2 módulos Python mortos a excluir na Fase 5)
- [x] Capacidades novas do motor listadas (8 itens, seção 3 acima)
- [x] Mapa de impacto preliminar (seção 5) para a Fase 7
