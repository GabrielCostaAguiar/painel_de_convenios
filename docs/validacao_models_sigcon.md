# Validação — models do SIGCON ligados à Silver nova (Fase 8)

Medido em 2026-11-10, carregando as 17 tabelas do app `sigcon` no banco de
desenvolvimento (PostgreSQL) pelos comandos oficiais, a partir da Silver nova.
Regra do dono dos dados: **nenhuma linha com dado é excluída em nenhuma camada**;
só a linha sem dado nenhum (todas as células `""` ou `N/A`).

Invariantes, todas verdadeiras e cobertas por teste
(`tests/test_preservacao_linhas.py`, `tests/test_loaders_preservam_linhas.py`,
`tests/test_gold_preservacao.py`):
- `linhas(Silver) = linhas(Bronze) − linhas vazias`, nas 42 fontes;
- `linhas(model) = linhas(Silver de origem)`, nos 16 models carregados 1:1;
- `ConvenioIntegrado` = 1 linha por linha de `sigcon_chave_siconv` (6.086).

## 1. Linhas por fonte e model

| Fonte | Bronze | Vazias removidas | Silver | Marcadas | Model | Linhas no banco |
|---|---:|---:|---:|---:|---|---:|
| `sigcon_convenio` | 5.353 | 0 | 5.353 | — | Convenio | 5.353 |
| `sigcon_convenio_geral` | 5.353 | 0 | 5.353 | — | ConvenioGeral | 5.353 |
| `sigcon_plano_trabalho` | 18.291 | 0 | 18.291 | — | PlanoTrabalho | 18.291 |
| `sigcon_termo_aditivo` | 7.113 | 0 | 7.113 | — | TermoAditivo | 7.113 |
| `sigcon_prorrogacao_oficio` | 660 | 0 | 660 | — | ProrrogacaoOficio | 660 |
| `sigcon_declaracao_contrapartida` | 3.957 | 0 | 3.957 | — | DeclaracaoContrapartida | 3.957 |
| `sigcon_cronograma_desembolso` | 48.394 | 2 | 48.392 | 18.400 | CronogramaDesembolso | 48.392 |
| `sigcon_plano_aplicacao` | 24.969 | 0 | 24.969 | — | PlanoAplicacao | 24.969 |
| `sigcon_unidade_executora` | 28.316 | 0 | 28.316 | — | UnidadesExecutoras | 28.316 |
| `sigcon_nt_emenda` | 14.520 | 0 | 14.520 | — | NtEmenda | 14.520 |
| `sigcon_chave_convenio` | 5.353 | 0 | 5.353 | — | CodigoConvenio | 5.353 |
| `sigcon_chave_termo_aditivo` | 7.105 | 0 | 7.105 | — | CodigoTermoAditivo | 7.105 |
| `sigcon_chave_plano_trabalho` | 5.353 | 0 | 5.353 | — | CodigoPlanoTrabalho | 5.353 |
| `sigcon_chave_declaracao` | 5.352 | 0 | 5.352 | — | CodigoDeclaracaoContrapartida | 5.352 |
| `sigcon_chave_siconv` + 7 satélites | 6.086 | 0 | 6.086 | — | ConvenioIntegrado | 6.086 |
| `sigcon_concedente` | 1.283 | 0 | 1.283 | — | Esfera | 1.283 |
| `controle_sei` | 2.834 | 0 | 2.834 | — | ControleSEI | 2.834 |
| `depara_siafi` | 12.009 | 0 | 12.009 | 8 | (sem model) | — |
| `depara_parlamentar` | 289 | 0 | 289 | — | (sem model) | — |
| `siconv_convenio` | 282.968 | 0 | 282.968 | — | (sem model) | — |

"Marcadas" = linhas com `ds_alerta_linha` preenchido. Os 8 do `depara_siafi` são
as linhas das 2 chaves de origem com destino divergente.

## 2. O que mudou em relação ao comportamento anterior

| Onde | Antes | Agora |
|---|---|---|
| Silver `sigcon_cronograma_desembolso` | 29.992 (apagava 18.402) | 48.392; as 18.400 do bloco desalinhado do BO ficam marcadas |
| Silver `depara_siafi` | 11.989 + 8 em quarentena à parte (apagava 12 idênticas) | 12.009, tudo na mesma tabela, 8 marcadas |
| Silver `depara_parlamentar`, `sigcon_nt_emenda` | 287 e 14.519 | 289 e 14.520 |
| `CronogramaDesembolso` (banco) | 48.394 na Silver antiga | 48.392; telas e exports mostram 29.992 (`ds_alerta_linha IS NULL`), igual ao que o usuário via |
| `ControleSEI` (banco) | 2.500 (apagava 334 por SIAFI) | 2.834; a aba Convênios continua mostrando 1 SEI por SIAFI (o primeiro), escolhido na consulta |
| `ConvenioIntegrado` (banco) | 5.346 (apagava 1 por UO e 739 sem datas) | 6.086: 1 com `fl_uo_excluida`, 605 com `limpeza_g=1`, 4 sem SIAFI (`siafi_uo` nulo); as telas filtram e usam 5.480 |
| Datas das fontes Excel | 29% nulas e 17% com dia/mês trocados (bug do pandas) | corretas (24 colunas conferidas com o Bronze) |

## 3. Achados

**3.1 O Gold antigo nunca incluiu dados do SICONV.** O Silver de
`siconv_convenio` tinha BOM no cabeçalho (`i»¿nr_convenio`), e
`_preparar_siconv` só fazia o join `if "nr_convenio" in df.columns`: o join era
pulado em silêncio. O Gold antigo não tem nenhuma coluna `siconv_*`. Com a Silver
nova, 1.153 convênios trazem situação, datas e valores do SICONV (o design
original: coalesce SICONV → SIGCON). Efeito visível: ~1.000 situações, ~250
valores globais e ~390 datas de fim de vigência diferentes do Gold antigo, e 138
convênios a mais com dados suficientes para as telas (5.346 → 5.480).
Os `if col in df.columns` silenciosos agora são `KeyError`.

**3.2 `codigo_siconv`: de 5.346 para 1.179 preenchidos.** O `'0'` que significava
"sem SICONV" virou nulo (sentinela da especificação).

**3.3 Convênios sem SIAFI.** 4 da `sigcon_chave_siconv` (SIAFI `'0'` → nulo).
O Gold antigo os guardava com chaves inventadas (`'0'`+UO). Decisão do dono dos
dados: ficam no Gold com `siafi_uo` nulo (o model aceita nulo; UNIQUE vale para as
preenchidas). Não aparecem nas telas, que ligam por SIAFI.

**3.4 Joins por chave nula.** O pandas casa nulo com nulo. Com a Silver antiga,
convênios com SIAFI `'0'` herdavam dados uns dos outros. Os joins de consulta
agora descartam chave nula antes (e há teste para isso).

**3.5 V13/D6 (fator ~100 entre desembolso e aplicação em 63 planos):** dado de
origem, idêntico na Silver antiga. Sem relação com esta fase.

## 4. Parity Silver antiga × nova (campo a campo)

- 150 de-paras campo-do-model → coluna-da-Silver conferidos mecanicamente contra
  o loader antigo e os `renomear:` dos YAMLs: 150 batem, 0 divergem.
- 3 campos do `TermoAditivo` (`termo_aditivo_alteracao`, `termo_aditivo_tipo`,
  `quantidade_termo_aditivo`) ficam nulos: eram constantes ou vazios nas 7.113
  linhas e a tela já usa `tipo_termo_aditivo`.
- Diferenças de valor esperadas (sentinelas → nulo): `nr_siafi='0'`,
  `nr_convenio` em `-`/`00`/`000`, `cd_declaracao_contrapartida='0'`,
  `nr_cnpj_*='0'`, `cd_matricula_gestor='null'`, `codigo_siconv='0'`, `tx_*` com
  `'null'`; flags de texto → booleano reconstruído no loader.

## 5. Smoke no app

Feito com o cliente HTTP do Django (não houve navegador), contra o banco carregado:
- 6 telas (convênios, plano de aplicação, cronograma, prorrogação, termo
  aditivo, unidades executoras): 200; totais 5.353 / 24.969 / 29.992 / 660 /
  7.113 / 28.316.
- 12 exports (CSV e XLSX): 200; CSV com as mesmas linhas das telas.
- Filtros: cronograma por plano, filtro sem resultado (0), convênios por
  proponente. 1ª página de convênios: 25 com SEI, 5 com SICONV.

## 6. Pendente fora do escopo desta fase

- `apps/painel/tests/test_rotas_smoke.py`: 7 falhas de rotas do **GRP** (o
  gabarito tem as URLs antigas `grp/dados/` etc., e as telas novas leem views do
  Postgres `gold.vw_*` ausentes no banco de teste). Anteriores a este trabalho.
- `rodar_silver` ainda não grava `quarentena`/`desdobrar` em disco (tabela 21).
- Migration `grp/0014` (remove os 8 models antigos do GRP) está no repositório,
  **não aplicada** em nenhum banco.
