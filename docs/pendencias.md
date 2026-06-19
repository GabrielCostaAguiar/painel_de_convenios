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
