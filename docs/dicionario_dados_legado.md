# Dicionário de dados — ingestão SIGCON (15 tabelas)

Modelo de Extração SIGCON v1.0 (`docs/modelo_extracao_sigcon.pdf`). Fontes fora do modelo (`siconv_convenio`, `sigcon_chave_siconv`, `depara_siafi`, `controle_sei`, `controle_sei_documento`, `depara_parlamentar`) não constam aqui; ver "Fontes adiadas" em `docs/relatorio_ingestao_legado.md`.

Gerado automaticamente a partir de `core/transform/schemas/*.yaml` (Fase 7 — não escrito à mão; qualquer mudança deve ser feita no YAML da fonte e este arquivo regenerado).

**Convenções:** `nr_` número, `cd_` código, `nm_` nome, `ds_` descrição, `tp_` tipo, `dt_` data, `dh_` data-hora, `vl_` valor, `qt_` quantidade, `fl_` flag, `tx_` texto longo. `siafi_uo` é a única exceção (chave derivada, concatenação de `nr_siafi` + `cd_uo` via `montar_siafi_uo`).

### 01 · `sigcon_convenio`

Convênios do SIGCON-MG. Grão: 1 linha por convênio (siafi_uo).

**Grão:** `siafi_uo`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `convenio_codigo` | `nr_convenio` | identificador | '-', '00', '000' |  |  |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | '0' |  |  |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |  |  |
| `situacao` | `ds_situacao_convenio` | texto |  |  |  |
| `data_inicio_vigencia` | `dt_vigencia_inicio` | data |  |  |  |
| `data_termino_vigencia` | `dt_vigencia_termino_inicial` | data |  |  |  |
| `data_real_convenio` | `dt_vigencia_termino` | data |  |  |  |
| `valor_inicial_concedente_contratado` | `vl_convenio_concedente_inicial` | valor |  |  |  |
| `valor_total_aditado_concedente_contratado` | `vl_convenio_concedente_aditado` | valor |  |  |  |
| `valor_concedente` | `vl_convenio_concedente` | valor |  |  |  |
| `valor_inicial_proponente_contratado` | `vl_convenio_proponente_inicial` | valor |  |  |  |
| `valor_total_aditado_proponente_contratado` | `vl_convenio_proponente_aditado` | valor |  |  |  |
| `valor_proponente` | `vl_convenio_proponente` | valor |  |  |  |
| `valor_total_convenio` | `vl_convenio_total` | valor |  |  |  |

**Colunas derivadas:**
- `siafi_uo` = `montar_siafi_uo(nr_siafi, cd_uo)`

### 02 · `sigcon_convenio_geral`

Dados gerais do SIGCON-MG. Grão: 1 linha por convênio (cd_convenio_sequencial).

**Grão:** `cd_convenio_sequencial`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `convenio_codigo` | `nr_convenio` | identificador | '-', '00', '000' |  |  |
| `convenio_codigo_sequencial` | `cd_convenio_sequencial` | identificador |  |  |  |
| `convenio_codigo_declaracao` | `cd_declaracao_contrapartida` | identificador | '0' |  |  |
| `convenio_data_de_publicacao` | `dt_publicacao` | data |  |  |  |
| `convenio_ano` | `nr_ano_convenio` | inteiro |  |  |  |
| `convenio_alteracao` | `fl_permite_alteracao` | texto |  | Pode sofrer alteração→True; Não pode sofrer alteração→False |  |
| `conveno_codigo_plano_trabalho` | `cd_plano_trabalho` | identificador | '0' |  |  |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | '0' |  |  |
| `convenio_matricula_tecnico_sccg` | `cd_matricula_tecnico_sccg` | identificador |  |  | ⚠️ |
| `convenio_data_alteracao_sccg` | `dh_alteracao_sccg` | data_hora |  |  |  |
| `convenio_justificativa_da_alteracao` | `tx_justificativa_alteracao` | texto |  |  |  |
| `convenio_data_controle_sccg_convenio` | `dt_controle_sccg` | data |  |  |  |
| `convenio_data_assinatura_convenio` | `dt_assinatura` | data |  |  |  |
| `convenio_matricula_gestor` | `cd_matricula_gestor` | identificador | 'null' |  | ⚠️ |
| `convenio_data_de_cadastramento` | `dh_cadastramento` | data_hora |  |  |  |

### 03 · `sigcon_plano_trabalho`

Planos de trabalho do SIGCON-MG. Grão: 1 linha por plano de trabalho (cd_plano_trabalho).

**Grão:** `cd_plano_trabalho`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador |  |  |  |
| `plano_trabalho_titulo` | `nm_plano_trabalho` | texto |  |  |  |
| `plano_trabalho_objeto` | `tx_objeto` | texto | 'null' |  |  |
| `plano_trabalho_justificativa` | `tx_justificativa` | texto | 'null' |  |  |
| `plano_trabalho_codigo_execucao_no_exercicio` | `cd_execucao_exercicio` | identificador |  |  |  |
| `plano_trabalho_status` | `ds_status_plano_trabalho` | texto |  |  |  |
| `plano_trabalho_caracteristica` | `ds_caracteristica_contrapartida` | texto |  |  |  |
| `plano_trabalho_tipo` | `tp_plano_trabalho` | texto |  |  |  |
| `plano_trabalho_tipo_siafi` | `tp_instrumento_siafi` | texto |  |  |  |
| `plano_trabalho_migrado_ou_novo` | `ds_origem_cadastro` | texto |  |  |  |
| `plano_trabalho_matricula_sccg_cancelamento` | `cd_matricula_cancelamento_sccg` | identificador |  |  | ⚠️ |
| `plano_trabalho_data_cancelamento_sccg` | `dh_cancelamento_sccg` | data_hora |  |  |  |
| `plano_trabalho_justificativa_sccg_cancelamento` | `tx_justificativa_cancelamento` | texto |  |  |  |
| `plano_trabalho_cancelamento_sccg` | `ds_cancelamento_sccg` | texto |  |  |  |
| `plano_trabalho_data_cadastro` | `dh_cadastro` | data_hora |  |  |  |
| `plano_trabalho_ano` | `nr_ano_plano_trabalho` | inteiro |  |  |  |
| `plano_trabalho_data_envio_sccg` | `dh_envio_sccg` | data_hora |  |  |  |
| `plano_trabalho_altera_termo_aditivo` | `ds_alteracao_termo_aditivo` | texto |  |  |  |
| `plano_trabalho_cnpj_concedente` | `nr_cnpj_concedente` | identificador | '0' |  |  |
| `plano_trabalho_razao_social_concedente` | `nm_concedente` | texto |  |  |  |
| `plano_trabalho_cnpj_proponente` | `nr_cnpj_proponente` | identificador | '0' |  |  |

### 04 · `sigcon_termo_aditivo`

Termos aditivos do SIGCON-MG. Grão: 1 linha por termo aditivo (cd_termo_aditivo).

**Grão:** `cd_termo_aditivo`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `termo_aditivo_codigo_sequencial` | `cd_termo_aditivo` | identificador |  |  |  |
| `termo_aditivo_numero_termo_aditivo` | `nr_termo_aditivo` | texto |  |  |  |
| `termo_aditivo_ano` | `nr_ano_termo_aditivo` | inteiro |  |  |  |
| `termo_aditivo_data_assinatura` | `dt_assinatura` | data |  |  |  |
| `termo_aditivo_data_inicio_vigencia` | `dt_vigencia_inicio` | data |  |  |  |
| `termo_aditivo_data_termino_vigencia` | `dt_vigencia_termino` | data |  |  |  |
| `termo_aditivo_justificativa` | `tx_justificativa` | texto | 'null' |  |  |
| `tipo_termo_aditivo` | `tp_termo_aditivo` | texto |  |  |  |
| `data_termo_aditivo` | `dh_registro` | data_hora |  |  |  |
| `valor_aditado_concedente_contratado` | `vl_aditivo_concedente` | valor |  |  |  |
| `valor_aditado_proponente_contratado` | `vl_aditivo_proponente` | valor |  |  |  |

**Descartadas (não vão para a silver):** `quantidade_termo_aditivo`, `termo_aditivo_alteracao`, `termo_aditivo_tipo`

### 05 · `sigcon_prorrogacao_oficio`

Prorrogações de ofício do SIGCON-MG. Grão: 1 linha por prorrogação (cd_prorrogacao_oficio).

**Grão:** `cd_prorrogacao_oficio`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `prorrogacao_oficio_codigo` | `cd_prorrogacao_oficio` | identificador |  |  |  |
| `prorrogacao_oficio_codigo_convenio` | `cd_convenio_sequencial` | identificador |  |  |  |
| `prorrogacao_oficio_data_inicio_vigencia` | `dt_vigencia_inicio` | data |  |  |  |
| `prorrogacao_oficio_data_termino_vigencia` | `dt_vigencia_termino` | data |  |  |  |
| `prorrogacao_oficio_data_envio` | `dt_envio` | data |  |  |  |
| `prorrogacao_oficio_data_parecer` | `dt_parecer` | data |  |  |  |
| `prorrogacao_oficio_data_publicacao` | `dt_publicacao` | data |  |  |  |

### 06 · `sigcon_declaracao_contrapartida`

Declarações de contrapartida do SIGCON-MG. Grão: 1 linha por declaração (cd_declaracao_contrapartida).

**Grão:** `cd_declaracao_contrapartida`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `declaracao_contrapartida_codigo` | `cd_declaracao_contrapartida` | identificador |  |  |  |
| `declaracao_contrapartida_data_completa_emissao` | `dh_emissao` | data_hora |  |  |  |
| `declaracao_contrapartida_data_emissao` | `dt_emissao` | data |  |  |  |
| `declaracao_contrapartida_ano` | `nr_ano_declaracao` | inteiro |  |  |  |
| `declaracao_contrapartida_status` | `ds_status_declaracao` | texto |  |  |  |
| `declaracao_contrapartida_codigo_nota_tecnica` | `cd_nota_tecnica` | identificador |  |  |  |
| `declaracao_contrapartida_observacao` | `tx_observacao` | texto | 'null', 'NULL' |  |  |
| `declaracao_contrapartida_codigo_parecer_aprovacao` | `ds_parecer_aprovacao` | texto |  |  |  |
| `declaracao_contrapartida_data_completa_parecer_aprovacao` | `dh_parecer_aprovacao` | data_hora |  |  |  |
| `declaracao_contrapartida_data_parecer_aprovacao` | `dt_parecer_aprovacao` | data |  |  |  |
| `declaracao_contrapartida_observacao_aprovacao` | `tx_observacao_aprovacao` | texto |  |  |  |
| `declaracao_contrapartida_matricula_aprovacao` | `cd_matricula_aprovacao` | identificador |  |  | ⚠️ |
| `declaracao_contrapartida_momento` | `ds_momento` | texto |  |  |  |

### 07 · `sigcon_cronograma_desembolso`

Cronograma de desembolso do SIGCON-MG. Grão: plano de trabalho x ano x mês. O export do BO traz blocos desalinhados sem cd_plano_trabalho (relatório paginado) — essas linhas são descartadas por descartar_linhas_se_nulo (esperado ≈18.402 linhas descartadas, restando ≈29.992).

**Grão:** `cd_plano_trabalho, nr_ano_desembolso, nr_mes_desembolso`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `mes_cronograma_desembolso` | `nr_mes_desembolso` | inteiro |  |  |  |
| `ano_cronograma_desembolso` | `nr_ano_desembolso` | inteiro |  |  |  |
| `valor_concedente_cronograma_desembolso` | `vl_desembolso_concedente` | valor |  |  |  |
| `valor_proponente_cronograma_desembolso` | `vl_desembolso_proponente` | valor |  |  |  |
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador |  |  |  |

**Descarte de linhas:** linhas com `plano_trabalho_codigo` vazio (nome bruto, antes da tipagem) são descartadas.

### 08 · `sigcon_plano_aplicacao`

Plano de aplicação do SIGCON-MG. Grão: plano de trabalho x classificação orçamentária x ano de exercício.

**Grão:** `cd_plano_trabalho, cd_uo, cd_funcao, cd_subfuncao, cd_programa, cd_identificador_projeto_atividade, cd_projeto_atividade, cd_subprojeto_subatividade, cd_categoria_economica, cd_grupo_despesa, cd_modalidade_aplicacao, cd_elemento_despesa, cd_identificador_orcamento, cd_fonte_recurso, cd_procedencia, nr_ano_exercicio`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `codigo_plano_trabalho` | `cd_plano_trabalho` | identificador |  |  |  |
| `codigo_unidade_orcamentaria` | `cd_uo` | identificador |  |  |  |
| `funcao_codigo` | `cd_funcao` | identificador |  |  |  |
| `subfuncao_codigo` | `cd_subfuncao` | identificador |  |  |  |
| `programa_codigo` | `cd_programa` | identificador |  |  |  |
| `identificador_projeto_atividade_codigo` | `cd_identificador_projeto_atividade` | identificador |  |  |  |
| `projeto_atividade_codigo` | `cd_projeto_atividade` | identificador |  |  |  |
| `subprojeto_subatividade_codigo` | `cd_subprojeto_subatividade` | identificador |  |  |  |
| `categoria_economica_despesa_codigo` | `cd_categoria_economica` | identificador |  |  |  |
| `grupo_despesa_codigo` | `cd_grupo_despesa` | identificador |  |  |  |
| `modalidade_aplicacao_codigo` | `cd_modalidade_aplicacao` | identificador |  |  |  |
| `elemento_despesa_codigo` | `cd_elemento_despesa` | identificador |  |  |  |
| `identificador_orcamento_codigo` | `cd_identificador_orcamento` | identificador |  |  |  |
| `fonte_recurso_codigo` | `cd_fonte_recurso` | identificador |  |  |  |
| `procedencia_codigo` | `cd_procedencia` | identificador |  |  |  |
| `funcional_programatica_formatado` | `cd_funcional_programatica` | identificador |  |  |  |
| `ano_exercicio_programa_trabalho` | `nr_ano_exercicio` | inteiro |  |  |  |
| `valor_concedente` | `vl_aplicacao_concedente` | valor |  |  |  |
| `valor_proponente` | `vl_aplicacao_proponente` | valor |  |  |  |

### 09 · `sigcon_unidade_executora`

Unidades executoras do SIGCON-MG. Grão: convênio (siafi_uo) x unidade executora — relação 1:N, ≈12 unidades por convênio em média. Única fonte SIGCON com header=0 (ver core/ingestion/sources.py).

**Grão:** `siafi_uo, cd_unidade_executora`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |  |  |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador |  |  |  |
| `convenio_codigo` | `nr_convenio` | identificador |  |  |  |
| `unidade_executora` | `cd_unidade_executora` | identificador |  |  |  |

**Colunas derivadas:**
- `siafi_uo` = `montar_siafi_uo(nr_siafi, cd_uo)`

### 10 · `sigcon_nt_emenda`

Notas técnicas de emendas parlamentares do SIGCON-MG. Grão: 1 linha por plano de trabalho (cd_plano_trabalho) — vale só para valores não nulos; as ~216 linhas do sentinela ficam com cd_plano_trabalho nulo e não entram na verificação de unicidade.

**Grão:** `cd_plano_trabalho`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador | '9999' |  |  |
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador | '99999999' |  |  |
| `nt_emenda_no` | `nr_emenda` | identificador |  |  |  |
| `nt_emenda_nome` | `nm_parlamentar` | texto |  |  |  |
| `nota_tecnica_emenda_parlamentar_federal_situacao` | `fl_emenda_parlamentar_federal` | texto |  | Sim→True; Não→False |  |

### 11 · `sigcon_chave_convenio`

Ponte ETL: mapeia cd_convenio_sequencial → SIAFI+UO. Grão: 1 linha por convênio (cd_convenio_sequencial).

**Grão:** `cd_convenio_sequencial`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `convenio_codigo` | `nr_convenio` | identificador | '-', '00', '000' |  |  |
| `convenio_codigo_sequencial` | `cd_convenio_sequencial` | identificador |  |  |  |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | '0' |  |  |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |  |  |

**Colunas derivadas:**
- `siafi_uo` = `montar_siafi_uo(nr_siafi, cd_uo)`

### 12 · `sigcon_chave_termo_aditivo`

Ponte ETL: mapeia cd_termo_aditivo → SIAFI+UO+cd_plano_trabalho. Grão: 1 linha por termo aditivo (cd_termo_aditivo).

**Grão:** `cd_termo_aditivo`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador |  |  |  |
| `termo_aditivo_codigo_sequencial` | `cd_termo_aditivo` | identificador |  |  |  |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |  |  |
| `plano_trabalho_codigo` | `cd_plano_trabalho` | identificador |  |  |  |

**Colunas derivadas:**
- `siafi_uo` = `montar_siafi_uo(nr_siafi, cd_uo)`

### 13 · `sigcon_chave_plano_trabalho`

Ponte ETL: mapeia cd_plano_trabalho → SIAFI+UO. Grão: 1 linha por convênio (siafi_uo).

**Grão:** `siafi_uo`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `conveno_codigo_plano_trabalho` | `cd_plano_trabalho` | identificador | '0' |  |  |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | '0' |  |  |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |  |  |

**Colunas derivadas:**
- `siafi_uo` = `montar_siafi_uo(nr_siafi, cd_uo)`

### 14 · `sigcon_chave_declaracao`

Ponte ETL: mapeia cd_declaracao_contrapartida → SIAFI+UO. Grão: 1 linha por convênio (siafi_uo).

**Grão:** `siafi_uo`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `declaracao_contrapartida_codigo` | `cd_declaracao_contrapartida` | identificador | '99999999' |  |  |
| `convenio_numero_sequencial_siafi` | `nr_siafi` | identificador | '0' |  |  |
| `unidade_orcamentaria_codigo` | `cd_uo` | identificador |  |  |  |

**Colunas derivadas:**
- `siafi_uo` = `montar_siafi_uo(nr_siafi, cd_uo)`

### 15 · `sigcon_concedente`

Dimensão de concedentes/esferas do SIGCON-MG. Grão: 1 linha por concedente (nr_cnpj_concedente). Esperado: 4 valores distintos de ds_esfera (o trim genérico de texto já resolve o 'Federal ' com espaço à direita do export).

**Grão:** `nr_cnpj_concedente`

| nome bruto (normalizado) | nome final | tipo | sentinelas → nulo | mapa booleano | LGPD |
|---|---|---|---|---|---|
| `concedente_esfera` | `ds_esfera` | texto |  |  |  |
| `concedente_cnpj` | `nr_cnpj_concedente` | identificador |  |  |  |
