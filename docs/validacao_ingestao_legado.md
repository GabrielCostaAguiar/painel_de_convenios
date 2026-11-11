# Validação da ingestão SIGCON — 15 tabelas

Modelo de referência: `docs/modelo_extracao_sigcon.pdf` (Modelo de Extração SIGCON v1.0,
estritamente SIGCON: 15 tabelas `dcgce_*` do BusinessObjects). Execução de
`rodar_ingestao` + `rodar_silver` contra os arquivos reais de `data/raw/`.

As fontes `siconv_convenio`, `sigcon_chave_siconv`, `depara_siafi`, `controle_sei`
(+ `controle_sei_documento`) e `depara_parlamentar` saíram do modelo e **não são
validadas aqui** (ver "Fontes adiadas" em `docs/relatorio_ingestao_legado.md`). Os antigos
V7 (de-para SIAFI) e V8 (ponte SICONV) saíram junto.

Regressão do GRP: 22/22 hashes SHA-256 idênticos à linha de base
(`docs/_baseline_grp_silver.json`).

## 1. Linhas por tabela

| # | Fonte | Bronze | Silver | Esperado |
|---|---|---|---|---|
| 01 | sigcon_convenio | 5.353 | 5.353 | 5.353 ✅ |
| 02 | sigcon_convenio_geral | 5.353 | 5.353 | 5.353 ✅ |
| 03 | sigcon_plano_trabalho | 18.529 | 18.291 | 18.291 ✅ |
| 04 | sigcon_termo_aditivo | 7.113 | 7.113 | 7.113 ✅ |
| 05 | sigcon_prorrogacao_oficio | 660 | 660 | 660 ✅ |
| 06 | sigcon_declaracao_contrapartida | 3.970 | 3.957 | 3.957 ✅ |
| 07 | sigcon_cronograma_desembolso | 48.394 | 48.392 (29.992 válidas) | 29.992 válidas ✅ |
| 08 | sigcon_plano_aplicacao | 24.969 | 24.969 | 24.969 ✅ |
| 09 | sigcon_unidade_executora | 28.316 | 28.316 | 28.316 ✅ |
| 10 | sigcon_nt_emenda | 14.520 | 14.520 | 14.520 ✅ |
| 11 | sigcon_chave_convenio | 5.353 | 5.353 | 5.353 ✅ |
| 12 | sigcon_chave_termo_aditivo | 7.105 | 7.105 | 7.105 ✅ |
| 13 | sigcon_chave_plano_trabalho | 5.353 | 5.353 | 5.353 ✅ |
| 14 | sigcon_chave_declaracao | 5.352 | 5.352 | 5.352 ✅ |
| 15 | sigcon_concedente | 1.283 | 1.283 | 1.283 ✅ |

A Silver só perde linhas 100% vazias (ver `docs/auditoria_exclusao_linhas.md`). A tabela 07
mantém as linhas do bloco desalinhado do BO, marcadas em `ds_alerta_linha`; as 29.992
válidas são as de `ds_alerta_linha` nulo.

## 2. Checks V1–V14 (os números, exceto V6 e V10, vêm da validação anterior)

| Check | Resultado | Conclusão |
|---|---|---|
| **V1** grão das 15 tabelas | grão limpo em todas; nulos de grão esperados em `sigcon_convenio` (8), `sigcon_unidade_executora` (1), `sigcon_nt_emenda` (215), `sigcon_chave_plano_trabalho` (8) e `sigcon_chave_declaracao` (7) | Convênios sem SIAFI/UO: ALERTA, nunca descarte. |
| **V2** `cd_uo` com 4 caracteres | 100% das fontes com `cd_uo`, exceto 1 linha de `sigcon_plano_aplicacao` (`cd_uo='9999999999'`) | Linha-sentinela sem regra na tabela 08 (D3); 1 em 24.969. |
| **V4** `sigcon_unidade_executora.nr_convenio` == `sigcon_convenio.nr_convenio` | 28.315 linhas comparadas, 0 divergentes | Perfeito. |
| **V5a** `sigcon_chave_plano_trabalho` == (geral + chave_convenio) | 5.345 chaves, 0 divergentes | Perfeito. |
| **V5b** `sigcon_chave_declaracao` == (geral + chave_convenio) | 5.345 chaves, 0 divergentes | Perfeito. |
| **V6** `nr_siafi` de `sigcon_convenio` com mais de um `siafi_uo` | 4.822 `nr_siafi` distintos; **255** aparecem em mais de um `siafi_uo` (até 9 UOs), afetando 778 das 5.353 linhas | O `nr_siafi` sozinho não identifica o convênio: qualquer ligação só por `nr_siafi` é ambígua e deve usar `siafi_uo`. |
| **V7** cronograma: 29.992 válidas, grão único, mês 1–12 | 29.992 válidas, grão único, 0 fora de 1–12 | Perfeito. |
| **V8** declaração: `dh_emissao`.date == `dt_emissao` e `dh_parecer_aprovacao`.date == `dt_parecer_aprovacao` | 3.956/3.956 e 2.894/2.894 | As colunas "R" da declaração são de fato redundantes. |
| **V9** declarações sem ponte | não reexecutado nesta revisão (premissa P5 do modelo) | Pendente. |
| **V10** nenhuma coluna `Unnamed` e nenhuma linha com o texto do cabeçalho | 15 tabelas: **0** colunas `Unnamed*` e **0** linhas com o texto do próprio cabeçalho em qualquer coluna de texto | Silver limpa de artefatos de exportação. |
| **V11** soma `vl_desembolso_concedente` (07) × `vl_aplicacao_concedente` (08) por plano | 9.068 planos em comum; 9.005 (99,3%) com diferença < R$ 0,01; 63 (0,7%) divergem | ALERTA — ver D6. |
| **V12** varredura de sentinelas (`'null'`, `'?'`, `'-'`, `' '`) | 1 `'null'` em `sigcon_convenio_geral.tx_justificativa_alteracao` | Sem `sentinelas:` pedido para a coluna; mantido. |
| **V13** `ds_esfera` | `Municipal` 861, `Privada` 226, `Federal` 127, `Estadual` 68, `Não Informado` 1 | 5 valores, não 4 (D4). |
| **V14** grão do plano de aplicação com `nr_ano_exercicio` | 24.969 linhas, grão único, 0 duplicadas | Perfeito. |

## 3. Divergências registradas (não corrigidas)

- **D3** — `sigcon_plano_aplicacao`: 1 linha-sentinela `9999999999`/`99999999` sem regra de sentinela.
- **D4** — `sigcon_concedente.ds_esfera` tem 5 valores (`Não Informado`, 1 linha).
- **D5** — colunas de texto longo com `sentinelas:` customizado ficam com `''` em vez de nulo,
  porque o override substitui o conjunto global (`tx_objeto`: 295 linhas; `tx_justificativa` de
  `sigcon_plano_trabalho`: 8.251; de `sigcon_termo_aditivo`: 179; `tx_observacao` de
  `sigcon_declaracao_contrapartida`: 3.581). Comportamento testado, não alterado.
- **D6** — 63 planos com soma divergente entre cronograma e plano de aplicação, padrão de fator ~100
  em vários (separador decimal trocado na origem); 2 planos com valor negativo.
- **D7** — "4 linhas sem SIAFI" da tabela 01 são 8 na base real.

(D1 e D2, sobre `depara_siafi`, ficam para a onda TransfereGov.)

## 4. Regressão

- GRP: 22/22 hashes idênticos à linha de base.
- A Silver das 15 tabelas não foi regenerada nesta revisão; os números acima vêm da Silver
  existente em `data/silver/` e do V6/V10 recalculados sobre ela.

## 5. Correção anterior — datas ISO (Fase 8)

As fontes vindas de Excel entregam datas ISO (`2003-02-14 00:00:00`) e o motor as lia com
`dayfirst=True`; no pandas 3.0.3 a primeira data decide o formato da coluna inteira. Efeito
medido: de 109.935 datas válidas, 32.062 viraram nulo (29,2%) e 18.446 saíram com dia e mês
trocados (16,8%), em 9 colunas. Correção: `core/transform/silver.py::_converter_datas` decide o
formato por valor. Verificação: GRP 22/22 idêntico; 24 colunas ISO comparadas com o Bronze, 0
diferenças. O V8 anterior (100%) era falso-positivo e foi refeito depois da correção.
