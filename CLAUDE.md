# CLAUDE.md · Painel de Convênios (DCGCE · SG-MG)

Painel web Django + PostgreSQL que substitui o QlikView da DCGCE. Reúne dados de convênios de entrada
(SIGCON, GRP, execução estadual, TransfereGov, planilhas internas). Desenvolvedor único: Gabriel.
Usuários: setorialistas da DCGCE e órgãos executores.

Arquitetura completa em `docs/ARQUITETURA.md`. **Não leia o arquivo inteiro**: abra só a seção indicada
na tabela da seção 9 deste arquivo.

---

## 1. Economia de contexto (obrigatório)

- Não explore o repositório com `tree`, `ls -R` ou buscas amplas. Use o mapa da seção 3. Se o mapa
  estiver errado, avise em uma linha e corrija-o aqui.
- Nunca abra arquivos de `data/` (raw, bronze, silver), `.parquet`, `.xlsx` ou `.csv` inteiros.
  Para inspecionar: `df.shape`, `df.dtypes`, `df.head(5)`, `read_csv(..., nrows=20)`.
- Não abra os PDFs de `docs/`. A verdade operacional está nos YAMLs de schema e nos `docs/*.md`.
- Para seguir um padrão, leia só o arquivo de referência da seção 5, não o app inteiro.
- Em arquivos grandes, localize a função ou classe com `grep -n` e leia só o trecho.
- Saída de comando longa: filtre (`Select-Object -First 30`, `grep`, `tail`).
- Respostas curtas: diff ou trecho alterado, nunca o arquivo inteiro. Ao final, só a lista de arquivos
  tocados. Não repita este arquivo e não reexplique passos que o Gabriel já concluiu.

## 2. Modos de trabalho

O Gabriel indica o modo na primeira palavra do pedido. Sem indicação, use `executar`.

| Pedido começa com | O que fazer | Edita? |
|---|---|---|
| `ensinar:` | Ele escreve o código. Dê **um passo por vez**: o que fazer, por que (1–2 linhas) e o critério de pronto. Espere ele mandar o resultado. Não entregue a solução completa, salvo se ele pedir. | Não |
| `revisar <alvo>` | Confira o que ele fez contra o checklist do tipo de artefato (ARQUITETURA §9) e rode os testes permitidos (seção 6). Responda em tabela: item, ✅/⚠/❌, `arquivo:linha`, correção em 1 linha. | Não |
| `testar <fonte, app ou view>` | Rode a bateria de validação (ARQUITETURA §10). Só `SELECT`. Mostre os números e uma conclusão de 1 linha por teste. Registre em `docs/qualidade_dados.md` só se ele pedir. | Não |
| `replicar <novo> como <referência>` | Copie a estrutura da referência (seção 5) trocando nomes, tipos e chaves. Liste as diferenças intencionais em relação à referência. Pare antes de qualquer comando que mexa no banco. | Sim |
| `executar` ou sem prefixo | Descobrir → relatar → ⛔ parar para aprovação → implementar → ⛔ parar com `git diff --stat`. Pedido explícito que toca um arquivo só pode ir direto para a implementação, com parada no diff. | Sim |

Em qualquer modo: se encontrar algo fora do padrão que não foi pedido, **aponte em uma linha e não corrija**.

## 3. Mapa do repositório

```
config/                        settings e urls do projeto
apps/dashboard/                casca do painel: layout, menu lateral, início
apps/grp/                      ⭐ APP DE REFERÊNCIA (copie daqui)
  models.py                    tabelas grp_* e models gold (managed=False)
  loader.py                    partials por fonte, _LOADERS_GRP, FONTES_GRP
  views/_filtros.py            _grp_render, _ler_filtros_grp
  validacao/catalogo.py        testes do app (usam core/validacao)
  sql/gold/NNN_*.sql           views do schema gold
  management/commands/carregar_grp.py
apps/sigcon/                   15 tabelas das consultas dcgce_* do SIGCON (+ sigcon_tabela_uo na S3)
core/                          app Django sem models: tudo que é global
  management/commands/         rodar_ingestao, rodar_silver, rodar_pipeline, gerar_schemas
  ingestion/sources.py         registro de fontes (FonteDados)
  transform/schemas/           um YAML por fonte
  carga/                       loader.py (carregar_tabela_generica), comando.py (ComandoCarga)
  validacao/                   construtores de teste e comando.py/executor.py (ComandoValidacao)
  web/                         formatar_celula, exportação CSV/XLSX, paginação
  templatetags/                painel_filters.py
data/raw|bronze|silver/        dados (fora do Git; não abrir)
docs/                          ARQUITETURA.md, qualidade_dados.md, TRILHA_PAINEL.md, modelos de extração
templates/  static/
```

## 4. Regras que não mudam

- A fonte nunca é alterada: correção vai para curadoria; problema vai para quarentena. Nada é excluído
  para "limpar" a fonte (exigência de auditoria do TCE).
- Sem `ForeignKey` entre tabelas de dados: as ligações ficam na gold, em SQL.
- Regra contra fan-out: tabela 1:N é agregada (CTE) antes de qualquer junção.
- Códigos (`nr_`, `cd_`, CNPJ, UO, município) são texto. Nunca numéricos.
- O nome da fonte é idêntico em 4 lugares: chave do `sources.py`, nome do YAML, nome do parquet e
  string do `partial`. Nunca deduza prefixo: confira no `sources.py` (as fontes GRP **não** têm `dcgce_`).
- `pandas` é importado dentro das funções de ETL, nunca no topo de módulo carregado pelo servidor web.
- Telas em Django puro (views + templates). Sem DRF, React ou Celery.
- O Django nunca importa nada de `etl/` (a partir da v1.1).
- `core` nunca importa `apps.*`; um app nunca importa outro app. Função usada por dois apps vai
  para o `core`. `apps/dashboard` (casca) pode ler dos demais.
- Senhas e tokens fora do Git (`secrets/`, `.env`).
- Decisão de modelagem nova vira uma linha em ARQUITETURA §16.

## 5. Referências para replicar

| Para criar... | Copie de... |
|---|---|
| YAML de fonte | YAML de `grp_instrumento` |
| Model de tabela 1:1 / 1:N | `GrpInstrumento` / `GrpRecursoConcedente` |
| Loader | `carregar_grp_instrumento = partial(...)` + entrada em `_LOADERS_GRP` (`apps/grp/loader.py`) |
| Comando de carga | `carregar_grp.py` (subclasse de `ComandoCarga`; um comando por app, nunca por tabela) |
| Comando e catálogo de validação | `validar_grp.py` (`ComandoValidacao`) + `validacao/catalogo.py` |
| View gold | `apps/grp/sql/gold/001_gold_instrumento.sql` (CTE de agregação) |
| Model gold | `GoldInstrumento` |
| Aba ou sub-aba | views do GRP com `_filtros.py` (após a S1-10: o componente de consulta compartilhado) |
| Testes de validação | bateria do GRP registrada em `docs/qualidade_dados.md` |

## 6. O que o Claude pode executar

- **Sem perguntar:** `manage.py check`, `showmigrations`, `sqlmigrate`, `makemigrations <app>` (e mostrar
  o arquivo gerado), `rodar_ingestao`, `rodar_silver`, `gerar_schemas` sem `--sobrescrever`, `SELECT`
  no banco, `git status|diff|log`, `pytest`.
- **Perguntar antes:** `carregar_<app>` (apaga e recarrega tabelas), `gerar_schemas --sobrescrever`
  (perde as edições do YAML), aplicar `CREATE OR REPLACE VIEW`, `pip install`, criar branch.
- **Nunca:** `migrate`, `DROP`, `DELETE`, `TRUNCATE`, `UPDATE`, `ALTER`, mexer em `django_migrations`,
  `git commit|push|merge` sem ordem, apagar arquivos de `data/raw`. Gere o comando ou o SQL e o
  Gabriel executa. Script destrutivo: `pg_dump -Fc` comentado no topo, `BEGIN; … ROLLBACK;` com
  `COMMIT;` comentado.

## 7. Ambiente

Windows + PowerShell, venv `.venv`, PostgreSQL local, projeto em
`C:\projetos\Projetos DCGCE\painel_de_convenios`. Caminhos sempre com `pathlib`.
Exportação do BusinessObjects: separador `;`, sem qualificador de texto. Saída sempre em UTF-8.

## 8. Estado atual (atualizar a cada sprint)

- **Sprint S1** (11–24/11/2026), rumo à **v1.0 em 31/12/2026** (SIGCON + Execução Estadual + GRP pronto).
- **GRP:** 22 tabelas carregadas; `gold.vw_instrumento` pronta; golds restantes na S4-03.
  Pendente: mês descritivo do cronograma de desembolso (S2-13).
- **SIGCON:** 15 tabelas com YAML, silver, models, migration e carga feitos; validação em andamento
  (S1-07). Próximas: ponte de planos (S1-08), `vw_convenio` (S1-09), componente de consulta (S1-10),
  aba Convênios (S1-11). `sigcon_tabela_uo` na S3-11.
- **Execução Estadual:** inventário e modelo de extração na S2.

## 9. Onde buscar em `docs/ARQUITETURA.md`

| Tarefa | Seção |
|---|---|
| Entender camadas e fluxo | §2 |
| Qual app recebe o quê | §4 |
| Criar ou revisar YAML, model, migration, loader | §5 e §6 |
| Criar view gold | §7 |
| Criar aba ou mexer em tela | §8 |
| Checklist do modo `revisar` | §9 |
| Bateria do modo `testar` | §10 |
| Chaves e ligações entre sistemas | §11 |
| Nomes de colunas, arquivos e objetos | §12 |
| ETL de produção, agendamento, carga sem apagar | §13 |
| Banco, segurança, deploy | §14 e §15 |
| Decisões já tomadas | §16 |
