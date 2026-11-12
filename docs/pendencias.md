# Pendências — pipeline de extração/relacionamento

> Levantadas em 2026-06-19, durante o trabalho de Fase 6 (extração→bronze) e do
> fix de `convenio_codigo` 1:1 em Plano de Aplicação/Cronograma. Nenhum item
> abaixo foi implementado ainda — só diagnosticado/registrado.

## 1. [INSUMO MANUAL] chaves_convenio e siafi2 fora do pipeline de extração

`chaves_convenio` e `siafi2` (principalmente o SIAFI 2) são arquivos inseridos
manualmente em `data/raw/`, fora do que `rodar_pipeline` extrai automaticamente
(Gmail + Transferegov). Precisam estar no Bronze **antes** do Silver/Gold.

Sem eles, `carregar_relacionamento` (R0–R4) falha e `convenio_codigo` fica
`NULL` em `PlanoAplicacao`/`CronogramaDesembolso`. **Convênios não é afetado**
— ali o código é coluna nativa de `dcgce_convenio`, sem depender desse join.

## 2. [BUG] Orquestrador reporta sucesso com Gold falhando

`core/pipeline.py::atualizar_painel()` / `rodar_pipeline` reportou "Pipeline
concluído com sucesso" mesmo com `carregar_relacionamento` falhando dentro da
etapa Gold/ORM. Um passo de Gold que falha não pode ser reportado como
sucesso — precisa sinalizar e/ou abortar com status de falha.

(Provável causa: `_etapa_gold_orm()` hoje só usa `carregar_convenios` como
critério de sucesso da etapa — `carregar_relacionamento` falhar não é
suficiente para marcar a etapa como falha. Avaliar se `carregar_relacionamento`
deveria ser tratado como crítico, igual a `carregar_convenios`.)

## 3. [GUARDA] rodar_pipeline deve checar Bronze de chaves_convenio/siafi2 antes do Gold

`rodar_pipeline` deveria checar a presença de `chaves_convenio` e `siafi2` no
Bronze e avisar/abortar com mensagem clara se faltarem, em vez de seguir
silenciosamente e só quebrar mais tarde, na etapa Gold.

## 4. [VALIDAR] Depois de inserir os dois arquivos manuais

Sequência de validação, após colocar `chaves_convenio` e `siafi2` no Bronze:

```bash
python manage.py rodar_silver chaves_convenio
python manage.py rodar_silver siafi2
python manage.py carregar_relacionamento --construir
```

Confirmar que `convenio_codigo` preenche corretamente em Plano de Aplicação e
Cronograma. Testar com **SIAFI 9481207** — lembrar que SIAFI→convênio é 1:N,
então convênios diferentes sob esse SIAFI devem mostrar códigos SIGCON
diferentes (mesma validação já feita de forma sintética, sem dado real, ao
implementar `core/gold/relacionamento.py::carimbar_convenio_codigo`).

## 5. [FASE 6 EM ABERTO] Mapeamento Gmail→Bronze incompleto

`core/ingestion/ponte_extracao.py::MAPA_GMAIL_PARA_FONTE` cobre só parte do
grupo `sigcon`. Sem `FonteDados` cadastrada (TODO já no código):

- Grupo `sigcon`: `tabelauo2`, `dcgce_Chave` (2 assuntos).
- Grupo `siafi`: todos os 8 assuntos.
- Grupo `siad`: todos os 5 assuntos.

Cadastrar uma fonte exige confirmar formato/separador/encoding reais
(`gerar_schemas`) — não dá pra fazer sem uma amostra real do arquivo.


---

# Pendências abertas em 12/11/2026 (refatoração SIGCON)

## 5. [FORA DE ESCOPO, v1.2] Gold de indicadores desligado

`core/gold/convenios.py` (`kpis`, `por_situacao`, `por_ano`, `recentes`) está inteiro
comentado desde a migração para os models `Sigcon*`, porque dependia do model `Convenio`
antigo. Os indicadores são da v1.2.

Para a tela não quebrar, `apps/painel/services.py` define `_GOLD_INDICADORES_ATIVO` e
`get_indicadores` devolve `{"vazio": True}` enquanto as quatro funções não existirem.
Foram apagados `tests/test_gold_convenios.py` e o teste de recálculo do cache; o
`test_cache_invalidacao.py` ganhou um teste do estado desligado.

Quando o Gold voltar: reescrever `core/gold/convenios.py` sobre `SigconConvenio`, devolver
o teste de recálculo após invalidação e o `test_gold_convenios.py`, e remover o guarda.

## 6. [BUG] `rodar_pipeline` chama comandos de carga que não existem

`core/pipeline.py::CARGAS_ORM` ainda chama `carregar_convenios`, `carregar_fonte`,
`carregar_cronograma` e outros, removidos na refatoração (`carregar_sigcon` os substituiu).
A etapa de carga do pipeline falha depois de extrair e ingerir. O teste
`test_cargas_orm_do_pipeline_apontam_para_comandos_existentes` está como `xfail(strict)`
e passará quando o pipeline for ligado ao `carregar_sigcon`; aí remova o `xfail`.
`FONTES_SILVER` também lista `depara_siafi`, `controle_sei` e `siconv_convenio`
(fontes de ondas futuras).

## 7. Resíduos da fonte `sigcon_chave_siconv`

Saiu de `core/ingestion/sources.py` e de `FONTES_SILVER`, mas continuam referenciando-a:
o YAML `core/transform/schemas/sigcon_chave_siconv.yaml`, `core/gold/relacionamento.py` e
seu teste `tests/test_gold_preservacao.py`, e três menções no `CLAUDE.md`. Pertencem à
onda TransfereGov; limpar quando ela começar.

## 8. Mojibake no plano de trabalho e no termo aditivo

5.009 células (ver `docs/qualidade_dados.md`, S4). Descobrir se o defeito nasce no
relatório do BO, no Excel ou na leitura, e decidir limite temporário ou correção na origem.

## 9. Datas com hora entram como horário ingênuo

O loader recebe `dh_*` como datetime sem fuso e o Django avisa
(`RuntimeWarning: DateTimeField ... received a naive datetime`, milhares de vezes por
carga). O valor é gravado como UTC. O teste T-G09 depende de as `dh_` estarem em UTC;
confirmar com a equipe e tornar a conversão explícita no loader.

## 10. Telas GRP que leem views do schema `gold`

`grp_dados`, `grp_instrumentos` e `grp_plano_aplicacao` dependem de `gold.vw_*`, criadas
por `aplicar_gold` e não pelas migrations. O smoke test as pula quando a view não existe.
Se quiser cobertura, rode `aplicar_gold` numa fixture do banco de teste.
