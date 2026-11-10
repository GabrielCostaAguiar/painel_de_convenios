# Fase 8 — Conferência da refatoração e plano para ligar o SIGCON no app web

> **Status: executada em 2026-11-10 (branch `feat/models-sigcon`).** Etapas 0.1–0.5, 1, 2, 3, 4 e 5 concluídas; a Etapa 6 (renomear campos dos models) não foi feita, por decisão do plano. Resultado em `docs/validacao_models_sigcon.md`.

Documento de execução para um agente/desenvolvedor que **não participou** das
Fases 0–7 (`docs/plano_refatoracao_ingestao.md`). Parte 1 é a conferência do que
foi feito, com evidência. Parte 2 é o plano, em etapas pequenas, cada uma com
critério de aceite verificável. Leia a Parte 1 inteira antes de começar — ela
contém 3 bloqueios que invalidam qualquer carga feita antes de resolvê-los.

**Resposta curta à pergunta "já posso montar os models e ligar as tabelas do
SIGCON no app?": ainda não.** Há um bug de datas na Silver legada (B1) que
gravaria ~29% das datas como nulas e ~17% com dia/mês trocados, e o banco de
teste não sobe (B2), então nada do que for feito pode ser testado. Resolvidos
B1–B3 (Etapa 0, pequena), sim — pelo caminho da Etapa 1 (loaders lendo a Silver
nova, models intactos), que religa as telas sem mexer em views/templates.

---

## Parte 1 — Conferência

### 1.1 Status por fase

| Fase | Status | Evidência / observação |
|---|---|---|
| 0 Linha de base | ✅ | `docs/_baseline_fase0.md`, `docs/_baseline_grp_silver.json` |
| 1 Reconhecimento | ✅ | `docs/plano_refatoracao_ingestao.md` §1–5 |
| Limpeza GRP antigo | ⚠️ | Código removido, mas **a migration de remoção não foi gerada**: `makemigrations --check` acusa `apps/grp` com 8 `DeleteModel` pendentes (`DadosGrp`, `EsferaGrp`, `TabelaUoGrp`, …). Ver B3. |
| 2 Motor genérico | ⚠️ | Capacidades novas OK e testadas. **Bug de datas ISO não detectado** (B1) — não foi introduzido pelo refactor (a linha `pd.to_datetime(..., dayfirst=True)` é a mesma desde antes da Fase 2), é do pandas 3.0.3 do ambiente, mas o motor é o lugar de corrigir. |
| 3 Renomear chaves | ✅ | `sources.py`, `ponte_extracao.py`, `core/pipeline.py::FONTES_SILVER` |
| 4 YAMLs | ✅ | 20 YAMLs; contrato em `docs/dicionario_dados_legado.md` |
| 5 Limpeza | ⚠️ parcial (proposital) | 5 YAMLs + 2 módulos removidos. **Bronze/Silver das chaves antigas não foram apagados** (item da própria Fase 5). Correto mantê-los por enquanto: são a base de comparação de paridade desta Fase 8 (ver Etapa 5). |
| 6 Validação | ⚠️ | Volumes e grão corretos, mas a validação **não comparou valores contra a Silver antiga** — por isso B1 passou. O V10 ("100% de `dh_emissao` = `dt_emissao`") é falso-positivo: as duas colunas estão erradas do mesmo jeito. |
| 7 Documentação | ⚠️ | Duas afirmações erradas a corrigir (ver 1.3). |

Regressões verificadas nesta conferência: GRP 22/22 hashes idênticos; suíte
641 passed / 1 failed / 130 errors (todos pré-existentes).

### 1.2 Bloqueios (resolver antes de qualquer carga)

**B1 — Datas ISO lidas como ano-dia-mês (Silver legada corrompida).**
O Bronze das fontes Excel traz datas em ISO (`2003-02-14 00:00:00`).
`core/transform/silver.py` linhas 421 (`data`) e 431 (`data_hora`) fazem
`pd.to_datetime(serie, errors="coerce", dayfirst=True)`. No pandas 3.0.3 o
formato é inferido pela **primeira** data não-nula da coluna: se ela tiver dia
≤ 12, a coluna inteira vira `%Y-%d-%m` → dias ≤ 12 saem com dia/mês trocados e
dias > 12 viram `NaT`. Se a primeira data tiver dia > 12, a coluna sai certa —
por isso o efeito é aleatório por coluna.
Medição (Bronze atual, colunas afetadas): 109.935 datas válidas, **32.062
anuladas (29,2%)** e **18.446 trocadas (16,8%)**. Colunas atingidas:
`sigcon_convenio_geral.dt_publicacao`/`dh_cadastramento`,
`sigcon_declaracao_contrapartida.dt_emissao`/`dh_emissao`,
`sigcon_plano_trabalho.dh_cadastro`/`dh_envio_sccg`/`dh_cancelamento_sccg`,
`sigcon_prorrogacao_oficio.dt_envio`/`dt_parecer`. As demais colunas de data
saíram certas por sorte da primeira linha — a correção tem de cobrir todas.
A Silver **antiga** (`data/silver/dcgce_*.parquet`, gerada com pandas anterior)
está correta (conferido contra o texto bruto do Bronze).
GRP não é afetado: nenhuma coluna de data do GRP vem em ISO (todas `dd/mm/aaaa`).
`siconv_convenio` também não (CSV em `dd/mm/aaaa`).

**B2 — Banco de teste não sobe (130 errors).**
`apps/grp/migrations/0008_grptabelauo_id_alter_grptabelauo_cd_uo.py` faz
`AddField(id, primary_key=True)` **antes** de `AlterField(cd_uo)` tirar a PK
antiga → Postgres recusa ("múltiplas chaves primárias em grp_tabela_uo") ao
criar o banco do zero. Em produção a migration já foi aplicada; o problema só
aparece em banco novo (testes). Sem isso, nenhum teste de loader/model roda.

**B3 — Migration pendente do GRP antigo.**
`python manage.py makemigrations --check --dry-run` gera
`apps/grp/migrations/0014_...` com 8 `DeleteModel`. Gerar o arquivo é seguro;
**aplicar** (`migrate`) dropa tabelas no banco — pedir confirmação ao usuário
antes de aplicar em qualquer banco que não seja o de teste.

### 1.3 Afirmações erradas nos documentos da Fase 7

1. `docs/relatorio_ingestao_legado.md` §4 "Models": diz que os models "já usam
   nomes no padrão novo (`nr_convenio`, `cd_uo`…)". **Falso.** Os models de
   `apps/sigcon/models/` usam os nomes brutos antigos (`convenio_codigo`,
   `unidade_orcamentaria_codigo`, `plano_trabalho_codigo`, …), assim como
   `services.py`, views, templates, exports, `core/gold/convenios.py` e
   `core/gold/contrapartida.py`.
2. `CLAUDE.md` e o relatório dizem que os `carregar_*` "vão falhar com
   `FileNotFoundError`". **Só metade falha.** Os Parquets antigos ainda estão em
   `data/silver/`, então `carregar_convenios`, `carregar_cronograma`,
   `carregar_unidades_executoras`, `carregar_fonte dcgce_geral|dcgce_plano.trabalho|
   dcgce_plano_aplicacao|dcgce_esfera|dcgce_Codigo_convenio|dcgce_Codigo_plano_de_trabalho`
   e `carregar_relacionamento` **carregam dado velho sem erro**. Falham de fato:
   termo aditivo, declaração, prorrogação, NT emenda, `dcgce_Codigo_ta`,
   `dcgce_Codigo_dec_contrap`. `carregar_relacionamento` sem `--construir` ainda
   lê `data/gold/convenios_integrado.parquet` antigo.
3. (Pré-existente) `CLAUDE.md` diz que `config.settings.dev` usa SQLite; o
   `dev.py` atual usa PostgreSQL.

### 1.4 Paridade Silver antiga × nova (feita nesta conferência)

Comparação posicional coluna a coluna (mesmo Bronze, mesma ordem de linhas):
- **Idênticas:** `sigcon_plano_aplicacao`, `sigcon_concedente`,
  `sigcon_unidade_executora`, `controle_sei`, `siconv_convenio` (valores).
- **Diferenças esperadas:** sentinelas que viraram nulo (`nr_siafi='0'`,
  `nr_convenio` em `-`/`00`/`000`, `cd_declaracao_contrapartida='0'`,
  `nr_cnpj_*='0'`, `cd_matricula_gestor='null'`, `codigo_siconv='0'`), flags
  texto → bool (`fl_permite_alteracao`, `fl_siconv`), `tx_*` com `'null'` → nulo.
- **Diferença errada:** todas as de data listadas em B1.
- **D6 (fator ~100 entre cronograma e plano de aplicação) não é regressão:**
  os valores na Silver nova são idênticos aos da antiga, centavo a centavo
  (somas totais iguais: R$ 67.667.444.462,10 e R$ 67.586.420.254,18). É dado de
  origem.
- `sigcon_cronograma_desembolso`: a antiga tinha 48.394 linhas e a nova tem
  29.992; as somas são idênticas. As 18.402 linhas a menos **não são lixo
  vazio**: 18.399 trazem um código de plano de trabalho caído na coluna `mês`
  (bloco desalinhado do relatório do BO), 1 é cabeçalho repetido e 2 são
  vazias. Pela regra de preservação, elas voltam marcadas (Etapa 0.5).

### 1.5 Outros pontos que afetam a próxima fase

- **Falhas silenciosas no Gold.** `core/gold/relacionamento.py::_preparar_siconv`
  renomeia colunas só `if k in df.columns`, e `core/transform/chaves.py::aplicar_deparas`
  só cria `situacao_std`/`instrumento_chaves`/`uo_*_std` se a coluna antiga
  existir. Com os nomes novos, **nada quebra — os campos SICONV e os de-paras
  simplesmente somem do `ConvenioIntegrado`**. `resolver_siafi_atual` exige
  `siafi2/uo2/siafiatual/uoatual` e quebra alto (bom). `aplicar_correcoes` usa
  `core/referencia/correcoes.csv`, cujos `campo_chave`/`campo_corrigido` estão
  nos nomes antigos (e `convenio_codigo_sigcon` não existe nem na Silver antiga —
  essas correções já eram ignoradas com WARNING; pré-existente).
- **A aba Convênios depende do Gold.** `apps/sigcon/services.py` e
  `apps/sigcon/views/convenios.py` usam `ConvenioIntegrado`. Religar só os
  loaders ORM não basta: o Gold (Etapa 3) é obrigatório para a aba principal.
- `D5` (string vazia residual) **não chega ao banco**: `_para_str` do loader já
  converte `''` em `None`.
- Colunas descartadas na Silver de termo aditivo (`termo_aditivo_tipo`,
  `termo_aditivo_alteracao`, `quantidade_termo_aditivo`) eram constantes/vazias
  em 100% das 7.113 linhas; a tela já faz fallback para `tipo_termo_aditivo`
  (`templates/sigcon/termo_aditivo.html:73`, `views/exports.py:331,358`).
- `rodar_silver` só persiste a tabela principal (tabela 21 e quarentena da 16
  não são gravadas pelo CLI). Não bloqueia esta fase — nenhuma tela usa as duas.

---

## Parte 2 — Plano de execução

### Regras para quem executar

- Branch nova a partir de `refactor/ingestao-legado`: `feat/models-sigcon`.
  Um commit por etapa, prefixo `feat(sigcon): ...` ou `fix(silver): ...`.
  **Não fazer push.**
- Ativar o venv antes de tudo (`source .venv/Scripts/activate`; o Python global
  3.14 não tem psycopg e quebra a suíte inteira).
- Regressão do GRP a cada etapa que tocar `core/transform/`: 22/22 hashes de
  `docs/_baseline_grp_silver.json` (script de conferência na Etapa 0.1).
- **Pedir confirmação ao usuário antes de:** aplicar migration que dropa
  tabela (B3), apagar qualquer coisa em `data/`, rodar carga no banco de
  produção.
- Dados pessoais (matrículas) nunca em log nem em relatório.
- Decisão de arquitetura desta fase: **Opção A** — manter os nomes de campo
  atuais dos models e adaptar só os loaders/Gold para ler a Silver nova. Motivo:
  views, templates, exports, `services.py`, `core/gold/convenios.py`,
  `core/gold/contrapartida.py` e ~45 testes usam os nomes atuais dos campos;
  renomear tudo junto multiplica o risco sem ganho para o usuário final. A
  renomeação para o padrão `nr_/cd_/dt_` fica como Etapa 6 opcional.

### Regra de preservação de linhas (inegociável, vale para todas as etapas)

Nenhuma linha pode ser excluída em nenhuma camada (Bronze, Silver, banco,
Gold). A única exceção é a linha **100% vazia**: todas as células do Bronze,
inclusive as colunas `Unnamed`, vazias depois de `strip()`, avaliadas no texto
bruto **antes** de sentinela e tipagem. Linhas só com marcadores (`N/A`,
`9999`, `99999999`, `0`) têm texto e **ficam**. Toda regra que hoje exclui
linha passa a **marcar** a linha (`ds_alerta_linha`), e quem não quiser a
linha na tela filtra na **consulta**. Diagnóstico completo, com números, em
`docs/auditoria_exclusao_linhas.md`.

### Etapa 0 — Desbloqueio

**0.1 Corrigir datas ISO no motor (`core/transform/silver.py`, B1).**
Criar uma função única usada pelos dois laços (linhas ~421 e ~431):
valores que casam `^\d{4}-\d{2}-\d{2}` → `pd.to_datetime(..., format="ISO8601", errors="coerce")`;
os demais → `pd.to_datetime(..., dayfirst=True, errors="coerce")` (comportamento
atual, que o GRP usa). Em `data`, manter o `.dt.normalize()`. Decidir por valor,
não pela coluna — há colunas com formatos misturados.
Testes novos em `tests/test_silver_grp.py` (padrão `_criar_fonte`): coluna ISO
cuja primeira data tem dia ≤ 12; coluna ISO com dia > 12; coluna BR; coluna
mista ISO+BR; `data_hora` ISO preserva a hora.
Aceite:
- GRP 22/22 hashes idênticos.
- `rodar_silver` das 20 fontes legadas sem erro.
- Paridade de **todas** as colunas `data`/`data_hora` contra a Silver antiga
  (ver script da Parte 1.4 — comparar `dcgce_*` × `sigcon_*` pelo `renomear` do
  YAML): 0 diferenças além de nulos esperados por sentinela.
- Atualizar `docs/validacao_ingestao_legado.md`: registrar o bug, refazer V10.

**0.2 Corrigir a ordem da migration `apps/grp/migrations/0008_...` (B2).**
Trocar a ordem das duas operações: primeiro o `AlterField` de `cd_uo` (tira a
PK), depois o `AddField` de `id`. Não altera banco já migrado (a migration já
consta como aplicada). Aceite: `python -m pytest -q` sem os 130 errors de
`ProgrammingError`/`InvalidTableDefinition` (o 1 failed de
`apps/painel/tests/test_rotas_smoke.py::test_inventario_de_rotas_bate_com_o_gabarito`
é independente — anotar se continuar).

**0.3 Gerar a migration pendente do GRP antigo (B3).**
`python manage.py makemigrations grp` → revisar que só contém os 8
`DeleteModel`/`RemoveIndex` esperados. Commitar o arquivo. **Não** aplicar no
banco dev/prod sem confirmação do usuário (dropa tabelas). Aceite:
`makemigrations --check` limpo.

**0.5 Motor sem exclusão de linhas (`core/transform/silver.py`).** _Executada._
Ver o detalhamento no prompt (`docs/prompt_fase8_models_sigcon.md`, seção
"Etapa 0.5"). Resumo: a única remoção que fica é a de linha 100% vazia no
texto bruto. A remoção pós-tipagem e o `drop_duplicates()` saem. Cabeçalho
repetido, `descartar_linhas_se_nulo` (vira `marcar_linhas_se_nulo`) e
`quarentena` passam a marcar a linha em `ds_alerta_linha`, guardando o texto
original em `tx_linha_bruta`. A tipagem não pode quebrar nem descartar linha
marcada. "Vazia" = células `""` ou `N/A` em todas as colunas (decisão do dono
dos dados). GRP: os 22 hashes continuam idênticos.

**0.4 Linha de base do banco.**
Se o banco dev estiver carregado, exportar (somente leitura, via ORM) cada model
de `apps/sigcon` para `data/_baseline_db/<Model>.parquet` com contagem por
tabela num JSON. É a referência de paridade da Etapa 1/3. Se o banco estiver
vazio, a paridade da Etapa 1 será feita contra a Silver antiga.

### Etapa 1 — Loaders ORM lendo a Silver nova (`apps/sigcon/loader.py`)

Trocar o arquivo lido e os nomes de coluna, sem mudar models. Remover os
fallbacks para nomes com ponto/maiúscula (`dcgce_plano.trabalho`,
`dcgce_Codigo_*`). Conversões: `nr_ano_*`/`nr_mes_*` (int64) → `str` para os
`CharField`; `fl_*` (bool) → texto quando o campo do model é texto (ver
tabelas); `dh_*` (datetime) → `DateField` via `_para_date` (já trunca).

Atenção ao join por chave nula: `nr_siafi` agora é nulo onde antes era `'0'`.
`pandas.merge` casa nulo com nulo. Nos merges por (`nr_siafi`, `cd_uo`), fazer
`dropna(subset=chaves)` no lado direito antes do merge, para que convênios sem
SIAFI não herdem dados de outro convênio sem SIAFI. (Na Silver antiga isso
acontecia com `'0'`; é correção, registrar no commit.)

`carimbar_convenio_codigo` (`core/gold/relacionamento.py:126`) hoje fixa
`conveno_codigo_plano_trabalho`/`convenio_codigo`; passar a ler
`cd_plano_trabalho`/`nr_convenio` da `sigcon_convenio_geral` e devolver a
coluna como `convenio_codigo` (nome que os loaders gravam no model).

**Mapeamento campo do model ← coluna da Silver nova:**

`Convenio` (`carregar_convenios`; fontes `sigcon_convenio`, `sigcon_chave_convenio`,
`sigcon_convenio_geral`, `sigcon_plano_trabalho`, `sigcon_concedente`)
| campo | origem |
|---|---|
| convenio_codigo | convenio.nr_convenio (nulo → `""`, campo não aceita nulo) |
| convenio_numero_sequencial_siafi | convenio.nr_siafi |
| unidade_orcamentaria_codigo | convenio.cd_uo |
| situacao | convenio.ds_situacao_convenio |
| data_inicio_vigencia | convenio.dt_vigencia_inicio |
| data_termino_vigencia | convenio.**dt_vigencia_termino_inicial** |
| data_real_convenio | convenio.**dt_vigencia_termino** |
| valor_inicial_concedente_contratado | vl_convenio_concedente_inicial |
| valor_total_aditado_concedente_contratado | vl_convenio_concedente_aditado |
| valor_concedente | vl_convenio_concedente |
| valor_inicial_proponente_contratado | vl_convenio_proponente_inicial |
| valor_total_aditado_proponente_contratado | vl_convenio_proponente_aditado |
| valor_proponente | vl_convenio_proponente |
| valor_total_convenio | vl_convenio_total |
| plano_trabalho_codigo | geral.cd_plano_trabalho |
| data_publicacao | geral.dt_publicacao |
| data_assinatura | geral.dt_assinatura |
| convenio_ano | geral.nr_ano_convenio (str) |
| instrumento | plano.tp_instrumento_siafi |
| titulo | plano.nm_plano_trabalho |
| objeto | plano.tx_objeto |
| concedente | plano.nm_concedente |
| cnpj_concedente / cnpj_proponente | plano.nr_cnpj_concedente / nr_cnpj_proponente |
| esfera | concedente.ds_esfera (join `plano.nr_cnpj_concedente = concedente.nr_cnpj_concedente`) |

Joins (mesma lógica de hoje, nomes novos): geral + chave_convenio por
`cd_convenio_sequencial` (traz `cd_uo`) → convenio por (`nr_siafi`, `cd_uo`) →
plano por `cd_plano_trabalho` → concedente por CNPJ.

`ConvenioGeral` ← `sigcon_convenio_geral`: convenio_codigo←nr_convenio;
convenio_codigo_sequencial←cd_convenio_sequencial;
conveno_codigo_plano_trabalho←cd_plano_trabalho;
convenio_numero_sequencial_siafi←nr_siafi;
convenio_codigo_declaracao←cd_declaracao_contrapartida;
convenio_data_de_publicacao←dt_publicacao; convenio_data_alteracao_sccg←dh_alteracao_sccg;
convenio_data_controle_sccg_convenio←dt_controle_sccg;
convenio_data_assinatura_convenio←dt_assinatura;
convenio_data_de_cadastramento←dh_cadastramento; convenio_ano←nr_ano_convenio (str);
convenio_alteracao←fl_permite_alteracao (True→"Pode sofrer alteração",
False→"Não pode sofrer alteração", nulo→None);
convenio_matricula_tecnico_sccg←cd_matricula_tecnico_sccg;
convenio_justificativa_da_alteracao←tx_justificativa_alteracao;
convenio_matricula_gestor←cd_matricula_gestor.

`PlanoTrabalho` ← `sigcon_plano_trabalho`: plano_trabalho_codigo←cd_plano_trabalho;
_codigo_execucao_no_exercicio←cd_execucao_exercicio; _tipo_siafi←tp_instrumento_siafi;
_cnpj_concedente←nr_cnpj_concedente; _cnpj_proponente←nr_cnpj_proponente;
_data_cancelamento_sccg←dh_cancelamento_sccg; _data_cadastro←dh_cadastro;
_data_envio_sccg←dh_envio_sccg; _titulo←nm_plano_trabalho; _objeto←tx_objeto;
_justificativa←tx_justificativa; _status←ds_status_plano_trabalho;
_caracteristica←ds_caracteristica_contrapartida; _tipo←tp_plano_trabalho;
_migrado_ou_novo←ds_origem_cadastro;
_matricula_sccg_cancelamento←cd_matricula_cancelamento_sccg;
_justificativa_sccg_cancelamento←tx_justificativa_cancelamento;
_cancelamento_sccg←ds_cancelamento_sccg; _ano←nr_ano_plano_trabalho (str);
_altera_termo_aditivo←ds_alteracao_termo_aditivo;
_razao_social_concedente←nm_concedente. (Prefixo `plano_trabalho_` omitido.)

`CronogramaDesembolso` ← `sigcon_cronograma_desembolso` (+ geral + chave_convenio):
plano_trabalho_codigo←cd_plano_trabalho;
valor_concedente_cronograma_desembolso←vl_desembolso_concedente;
valor_proponente_cronograma_desembolso←vl_desembolso_proponente;
mes_cronograma_desembolso←nr_mes_desembolso (str);
ano_cronograma_desembolso←nr_ano_desembolso (str); convenio_codigo via
`carimbar_convenio_codigo`; SIAFI/UO via geral.cd_convenio_sequencial →
chave_convenio. Esperado: **48.392 linhas** (48.394 − 2 vazias). As 18.400
do bloco desalinhado vêm marcadas em `ds_alerta_linha`. O model ganha o campo
`ds_alerta_linha` (AddField, nulo), e as telas e somas do cronograma filtram
`ds_alerta_linha__isnull=True`, o que mantém os números de tela (29.992).

`PlanoAplicacao` ← `sigcon_plano_aplicacao`: codigo_plano_trabalho←cd_plano_trabalho;
codigo_unidade_orcamentaria←cd_uo; funcao_codigo←cd_funcao; subfuncao_codigo←cd_subfuncao;
programa_codigo←cd_programa;
identificador_projeto_atividade_codigo←cd_identificador_projeto_atividade;
projeto_atividade_codigo←cd_projeto_atividade;
subprojeto_subatividade_codigo←cd_subprojeto_subatividade;
categoria_economica_despesa_codigo←cd_categoria_economica;
grupo_despesa_codigo←cd_grupo_despesa; modalidade_aplicacao_codigo←cd_modalidade_aplicacao;
elemento_despesa_codigo←cd_elemento_despesa;
identificador_orcamento_codigo←cd_identificador_orcamento;
fonte_recurso_codigo←cd_fonte_recurso; procedencia_codigo←cd_procedencia;
funcional_programatica_formatado←cd_funcional_programatica;
valor_concedente←vl_aplicacao_concedente; valor_proponente←vl_aplicacao_proponente;
ano_exercicio_programa_trabalho←nr_ano_exercicio (str). Manter os dois
`assert` anti fan-out.

`TermoAditivo` ← `sigcon_termo_aditivo`: termo_aditivo_codigo_sequencial←cd_termo_aditivo;
termo_aditivo_numero_termo_aditivo←nr_termo_aditivo;
termo_aditivo_data_assinatura←dt_assinatura;
termo_aditivo_data_inicio_vigencia←dt_vigencia_inicio;
termo_aditivo_data_termino_vigencia←dt_vigencia_termino; data_termo_aditivo←dh_registro;
valor_aditado_concedente_contratado←vl_aditivo_concedente;
valor_aditado_proponente_contratado←vl_aditivo_proponente;
termo_aditivo_justificativa←tx_justificativa; termo_aditivo_ano←nr_ano_termo_aditivo (str);
tipo_termo_aditivo←tp_termo_aditivo; termo_aditivo_alteracao, termo_aditivo_tipo,
quantidade_termo_aditivo ← None (descartadas; eram constantes).

`DeclaracaoContrapartida` ← `sigcon_declaracao_contrapartida`:
_codigo←cd_declaracao_contrapartida; _codigo_nota_tecnica←cd_nota_tecnica;
_codigo_parecer_aprovacao←ds_parecer_aprovacao; _data_completa_emissao←dh_emissao;
_data_emissao←dt_emissao; _data_completa_parecer_aprovacao←dh_parecer_aprovacao;
_data_parecer_aprovacao←dt_parecer_aprovacao; _observacao←tx_observacao;
_observacao_aprovacao←tx_observacao_aprovacao; _ano←nr_ano_declaracao (str);
_status←ds_status_declaracao; _matricula_aprovacao←cd_matricula_aprovacao;
_momento←ds_momento. (Prefixo `declaracao_contrapartida_` omitido.)

`ProrrogacaoOficio` ← `sigcon_prorrogacao_oficio`: _codigo←cd_prorrogacao_oficio;
_codigo_convenio←cd_convenio_sequencial; _data_inicio_vigencia←dt_vigencia_inicio;
_data_termino_vigencia←dt_vigencia_termino; _data_envio←dt_envio;
_data_parecer←dt_parecer; _data_publicacao←dt_publicacao. (Valores idênticos aos
de hoje; o docstring do model diz que a ligação é com `Convenio.convenio_codigo`,
mas a especificação diz que é o código **sequencial** — conferir como
`services.py` filtra `prorrogacao_oficio_codigo_convenio__in` e anotar; não
mudar comportamento nesta etapa.)

`NtEmenda` ← `sigcon_nt_emenda`: unidade_orcamentaria_codigo←cd_uo;
plano_trabalho_codigo←cd_plano_trabalho; nt_emenda_no←nr_emenda;
nt_emenda_nome←nm_parlamentar;
nota_tecnica_emenda_parlamentar_federal_situacao←fl_emenda_parlamentar_federal
(True→"Sim", False→"Não", nulo→None). 215 linhas passam a ter plano nulo
(sentinela `99999999`).

`Esfera` ← `sigcon_concedente`: concedente_cnpj←nr_cnpj_concedente;
concedente_esfera←ds_esfera (grão único confirmado: 1.283).

`UnidadesExecutoras` ← `sigcon_unidade_executora`: unidade_orcamentaria_codigo←cd_uo;
convenio_numero_sequencial_siafi←nr_siafi; unidade_executora←cd_unidade_executora;
convenio_codigo←nr_convenio.

`CodigoConvenio` ← `sigcon_chave_convenio`: convenio_codigo←nr_convenio;
convenio_codigo_sequencial←cd_convenio_sequencial;
convenio_numero_sequencial_siafi←nr_siafi; unidade_orcamentaria_codigo←cd_uo.

`CodigoPlanoTrabalho` ← `sigcon_chave_plano_trabalho`:
conveno_codigo_plano_trabalho←cd_plano_trabalho;
convenio_numero_sequencial_siafi←nr_siafi; unidade_orcamentaria_codigo←cd_uo.

`CodigoTermoAditivo` ← `sigcon_chave_termo_aditivo`:
convenio_numero_sequencial_siafi←nr_siafi; termo_aditivo_codigo_sequencial←cd_termo_aditivo;
unidade_orcamentaria_codigo←cd_uo; plano_trabalho_codigo←cd_plano_trabalho.

`CodigoDeclaracaoContrapartida` ← `sigcon_chave_declaracao`:
declaracao_contrapartida_codigo←cd_declaracao_contrapartida;
convenio_numero_sequencial_siafi←nr_siafi; unidade_orcamentaria_codigo←cd_uo.

`ControleSEI` ← `controle_sei`: no_sei←nr_sei; no_siafi_sigcon←nr_siafi;
no_proposta_siconv←nr_proposta_siconv. **Remover a deduplicação da carga**
(hoje apaga 334 das 2.834 linhas). O banco recebe as 2.834. A escolha de "um
SEI por SIAFI" vai para a consulta em `apps/sigcon/services.py:129-132`:
`order_by("pk")` e ficar com o **primeiro** de cada SIAFI (`setdefault`), que
reproduz o comportamento atual da tela.

Aceite da Etapa 1:
- Todos os `carregar_*` rodam contra a Silver nova num banco de teste.
- Paridade com a linha de base (0.4) ou com a Silver antiga, por model:
  **contagem de cada model = contagem da Silver de origem** (invariante da
  regra de preservação; `CronogramaDesembolso` 48.392, `ControleSEI` 2.834),
  e campos iguais exceto a lista de diferenças esperadas (sentinelas → nulo,
  flags reconstruídas, datas corrigidas). Gerar um relatório curto em
  `docs/validacao_models_sigcon.md` com a diferença por model/campo.
- `apps/sigcon/tests/` e `tests/` passando; atualizar fixtures que montam
  Parquet com nomes antigos (`apps/sigcon/tests/test_excecoes_comandos.py`,
  `test_bulk_refresh.py`, `tests/test_r4.py` — conferir com grep).

### Etapa 2 — CLI e pipeline

- `apps/sigcon/management/commands/carregar_fonte.py::_LOADERS` (linhas 27–40):
  trocar as 13 chaves antigas pelas novas (`sigcon_convenio_geral`,
  `sigcon_plano_trabalho`, `sigcon_cronograma_desembolso`,
  `sigcon_plano_aplicacao`, `sigcon_termo_aditivo`,
  `sigcon_declaracao_contrapartida`, `sigcon_prorrogacao_oficio`,
  `sigcon_nt_emenda`, `sigcon_concedente`, `sigcon_chave_convenio`,
  `sigcon_chave_plano_trabalho`, `sigcon_chave_termo_aditivo`,
  `sigcon_chave_declaracao`). Sem aliases para as antigas.
- `core/pipeline.py::CARGAS_ORM` (linhas 61–78): as mesmas 13 chaves; remover o
  comentário das linhas 31–35 que aponta para o relatório.
- Docstrings/help com nomes antigos: `carregar_convenios.py`, `carregar_cronograma.py`,
  `carregar_unidades_executoras.py`, `carregar_relacionamento.py`,
  `carregar_fonte.py`, `apps/pipeline/management/commands/rodar_silver.py`,
  `gerar_schemas.py`.
- `carregar_relacionamento`: garantir que a carga reconstrói o Gold a partir da
  Silver (hoje, sem `--construir`, lê o `convenios_integrado.parquet` antigo).
Aceite: `rodar_pipeline` (com extração desligada/mocada, ou rodando só a parte
Silver→ORM) executa todas as `CARGAS_ORM` sem erro; `tests/test_comandos_registrados.py`
e `tests/test_cache_invalidacao.py` passando.

### Etapa 3 — Gold `ConvenioIntegrado` (obrigatória para a aba Convênios)

Arquivos: `core/gold/relacionamento.py`, `core/transform/chaves.py`,
`core/referencia/correcoes.csv`, `apps/sigcon/loader.py::carregar_tabela_integrada`
(linhas 717–723), `tests/test_r2.py`, `tests/test_r3.py`.
- Leitura: `chaves_convenio`→`sigcon_chave_siconv`, `siafi2`→`depara_siafi`,
  `dcgce_convenio`→`sigcon_convenio`, `dcgce_codigo_convenio`→`sigcon_chave_convenio`,
  `dcgce_geral`→`sigcon_convenio_geral`, `dcgce_plano_trabalho`→`sigcon_plano_trabalho`,
  `dcgce_esfera`→`sigcon_concedente`.
- `resolver_siafi_atual`: usar direto `siafi_uo_origem`/`siafi_uo_atual`/
  `nr_siafi_atual`/`cd_uo_atual` da `depara_siafi` (já derivados no YAML). As
  linhas marcadas como quarentena (`ds_alerta_linha`) ficam na tabela, mas são
  ignoradas **na consulta** de resolução. As 2 chaves divergentes caem no
  fallback "atual = própria chave"; registrar.
- **Gold sem exclusão de convênio.** `filtrar_uo` passa a marcar
  (`fl_uo_excluida`) em vez de remover. `limpeza_g` deixa de remover: o campo
  `limpeza_g` já existe no model. `ConvenioIntegrado` ganha `fl_uo_excluida`
  (AddField). As consultas de `apps/sigcon/services.py` (l.115 e l.409)
  filtram `limpeza_g=0, fl_uo_excluida=False`, o que mantém a tela igual
  (hoje 5.346 convênios no Gold, 6.082 com a regra; as 4 linhas de
  `sigcon_chave_siconv` sem SIAFI são ponto de decisão do usuário, ver o
  prompt). Os `drop_duplicates("siafi_uo")`
  das linhas 223 e 356 só podem colapsar linhas **100% idênticas**; com chave
  repetida e conteúdo diferente, levantar erro (não escolher em silêncio).
- `montar_sigcon_chaves`: entrada com `nr_siafi`, `cd_uo`, `nr_convenio_siconv`,
  `tp_instrumento_siafi`, `ds_situacao_convenio`, `siafi_uo` já pronto. As
  colunas de **saída** continuam com os nomes que `carregar_tabela_integrada`
  grava no model (`codigo_siconv`, `situacao`, `instrumento_chaves`,
  `convenio_numero_sequencial_siafi`, `unidade_orcamentaria_codigo`, …).
- `_preparar_sigcon_completo` e `preparar_sigcon_convenio`: nomes novos conforme
  o mapeamento da Etapa 1.
- `_preparar_siconv`: `nr_convenio_siconv` (chave), `cd_proposta_siconv`,
  `dt_assinatura`, `dt_vigencia_inicio`, `dt_vigencia_termino`,
  `dt_vigencia_termino_inicial`, `ds_situacao_convenio`, `vl_repasse`,
  `vl_contrapartida`, `vl_global`. (`nm_proponente`, `desc_orgao_sup`,
  `objeto_proposta` nunca existiram em `siconv_convenio` — continuam ausentes.)
- `chaves.py`: `filtrar_uo` default `cd_uo`; `aplicar_deparas` com
  `ds_situacao_convenio`, `tp_instrumento_siafi`, `cd_uo`.
- **Trocar os `if col in df.columns` silenciosos por erro explícito** nas
  colunas obrigatórias (`_preparar_siconv`, `aplicar_deparas`,
  `_preparar_sigcon_completo`) — é o que deixou os campos sumirem sem aviso.
- `correcoes.csv`: atualizar `campo_chave`/`campo_corrigido` para os nomes
  novos; as linhas com `convenio_codigo_sigcon` (coluna que não existe) ficam
  como estão e entram no relatório como pendência pré-existente.
Aceite: `carregar_relacionamento --construir` sem erro; comparar o novo
`data/gold/convenios_integrado.parquet` com o antigo (renomear o antigo para
`convenios_integrado_antes_fase8.parquet` **antes** de rodar) campo a campo:
mesmas `siafi_uo`, mesmos `g_*`/`a_*` exceto diferenças explicadas (datas
corrigidas, sentinelas). `tests/test_r2.py`/`test_r3.py` reescritos com os
nomes novos e passando.

### Etapa 4 — Smoke no app web

`python manage.py runserver`, abrir cada aba do SIGCON (convênios,
cronograma, plano de aplicação, prorrogação, termo aditivo, unidades
executoras), aplicar os filtros globais e baixar CSV/XLSX de cada uma. Conferir
contagens contra a linha de base 0.4. Testar estado vazio e um filtro sem
resultado. Se não puder abrir o navegador, dizer isso explicitamente no relato
em vez de declarar pronto.

### Etapa 5 — Limpeza e documentação

- Com a paridade aceita pelo usuário: **pedir confirmação** e então apagar
  `data/bronze/` e `data/silver/` das chaves antigas (`dcgce_*`,
  `chaves_convenio`, `siafi2`, `convenios`, e os `dcgce_*_grp` do GRP antigo),
  item pendente da Fase 5. Não apagar `data/raw/`.
- Corrigir as afirmações da seção 1.3 em `docs/relatorio_ingestao_legado.md` e
  `CLAUDE.md` (models, `FileNotFoundError`, dev = PostgreSQL); atualizar a
  seção do loader no `CLAUDE.md` (passa a ler a Silver nova).

### Etapa 6 (opcional, depois) — Models no padrão novo e tabelas que faltam

Só depois de as Etapas 0–5 estarem em produção.
- Renomear campos dos models para o padrão do dicionário (`convenio_codigo` →
  `nr_convenio`, …) com `migrations.RenameField` (preserva dado), atualizando
  junto `services.py`, views, templates, exports, `core/gold/convenios.py`,
  `core/gold/contrapartida.py` e testes. Um model por commit.
- Tipos: `nr_ano_*`/`nr_mes_*` como `SmallIntegerField`; `fl_*` como
  `BooleanField(null=True)`; `dh_*` como `DateTimeField` (hoje truncado em
  `DateField`).
- Models novos, se a tela precisar: `ControleSEIDocumento` (tabela 21 — exige
  antes fazer `rodar_silver` persistir `desdobrado`), `DeparaParlamentar`
  (padronizar `nm_parlamentar` da NT emenda), `SiconvConvenio`.

### Ordem e dependências

```
0.1 datas ───┐
0.5 linhas ──┤
0.2 test DB  ├─► 1 loaders ─► 2 CLI/pipeline ─► 3 Gold ─► 4 smoke ─► 5 limpeza ─► (6 opcional)
0.3 migr.    │
0.4 baseline ┘
```
0.1–0.5 são independentes entre si (0.1 e 0.5 mexem no mesmo arquivo; fazer
em commits separados). 1 depende de 0.1 e 0.5 (senão grava datas erradas e
linhas a menos) e de 0.2 (senão não testa). 3 depende de 1 por causa de
`carimbar_convenio_codigo`.
