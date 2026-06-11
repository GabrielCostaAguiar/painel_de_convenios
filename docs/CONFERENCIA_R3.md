# Conferência R3 — Tabela Integrada vs. QlikView

Este documento guia a conferência dos campos G_/A_ produzidos pelo Python
contra o painel QlikView atual. Preencha a coluna **Valor Python** após rodar
`construir_tabela_integrada()` com os dados reais.

## Como rodar a conferência

```python
# python manage.py shell
from pathlib import Path
from django.conf import settings
import pandas as pd
from core.gold.relacionamento import construir_tabela_integrada, gravar_tabela_integrada

DATA = Path(settings.DATA_DIR)

df_chaves    = pd.read_parquet(DATA / "silver/chaves_convenio.parquet")
df_siafi2    = pd.read_parquet(DATA / "silver/siafi2.parquet")
df_convenio  = pd.read_parquet(DATA / "silver/dcgce_convenio.parquet")
df_cod_conv  = pd.read_parquet(DATA / "silver/dcgce_codigo_convenio.parquet")
df_geral     = pd.read_parquet(DATA / "silver/dcgce_geral.parquet")
df_plano     = pd.read_parquet(DATA / "silver/dcgce_plano_trabalho.parquet")
df_esfera    = pd.read_parquet(DATA / "silver/dcgce_esfera.parquet")
# df_siconv = pd.read_parquet(DATA / "silver/siconv_convenio.parquet")  # opcional

tabela = construir_tabela_integrada(
    df_chaves, df_siafi2, df_convenio, df_cod_conv, df_geral, df_plano, df_esfera,
    # df_siconv=df_siconv,  # descomentar quando disponível
)

print(f"Total convênios: {len(tabela)}")
print(f"Colunas G_: {[c for c in tabela.columns if c.startswith('g_')]}")
gravar_tabela_integrada(tabela)
```

## Validação de fan-out

```python
n_total    = len(tabela)
n_distintos = tabela["siafi_uo"].nunique()
print(f"Total linhas: {n_total} | Distintos por siafi_uo: {n_distintos}")
assert n_total == n_distintos, "FAN-OUT DETECTADO"
```

## Campos a conferir (amostra de 3–5 convênios conhecidos)

Para cada convênio de referência, anote o valor no QlikView e compare
com o valor Python usando:

```python
conv = tabela[tabela["siafi_uo"] == "<siafi_uo_aqui>"].iloc[0]
print(conv[["g_situacao_convenio", "g_valor_global", "g_fim_vigencia",
            "g_concedente", "g_instrumento", "siafi_uo_atual"]])
```

| SIAFI_UO | Campo | Valor QlikView | Valor Python | Status |
|---|---|---|---|---|
| (preencher) | g_situacao_convenio | | | ⬜ |
| (preencher) | g_valor_global | | | ⬜ |
| (preencher) | g_fim_vigencia | | | ⬜ |
| (preencher) | g_concedente | | | ⬜ |
| (preencher) | g_instrumento | | | ⬜ |
| (preencher) | siafi_uo_atual | | | ⬜ |

**Status legend:** ✅ OK | ❌ Divergência | ⚠️ Diferença esperada (fonte diferente)

## Divergências esperadas (não são bugs)

1. **g_situacao_convenio**: O QlikView pode ter situações desatualizadas se a
   carga do SIGCON não ocorreu na mesma data. Diferenças de "VIGENTE" vs
   "ADIMPLENTE" são normais se as extrações foram em datas diferentes.

2. **g_concedente / g_proponente**: Se `siconv_convenio.csv` não tiver
   `nm_proponente` e `desc_orgao_sup` (eles vêm de `siconv_proposta.csv`),
   estes campos usarão fallback SIGCON, diferente do QlikView que tem SICONV.

3. **g_fim_vigencia com SICONV**: O QlikView usa `DIA_FIM_VIGENC_CONV` do
   SICONV quando disponível. Sem o SICONV carregado, o Python usa
   `data_real_convenio` do SIGCON — pode divergir para convênios com dados
   diferentes nas duas plataformas.

4. **siafi_uo_atual**: Confira especialmente convênios que mudaram de SIAFI.
   Ver aviso do desenvolvedor no QlikView linha 2799 (coluna pode estar errada).

## Contagem esperada de convênios

Compare com a contagem do QlikView antes de avançar para R4:

```python
print("Por situação G_:")
print(tabela["g_situacao_convenio_categorizado"].value_counts())

print("\nPor vigência:")
print(tabela["g_vigencia"].value_counts())

print("\nPor ano convênio:")
print(tabela["g_ano_convenio"].value_counts().sort_index())
```

## Checklist antes de avançar para R4

- [ ] Total de convênios bate com o QlikView (±5% tolerado por diferença de data)
- [ ] Fan-out validado: 0 linhas duplicadas por siafi_uo
- [ ] Pelo menos 3 convênios conhecidos com valores corretos nos 6 campos acima
- [ ] limpeza_g: % de linhas removidas é razoável (< 2%)
- [ ] siafi_uo_atual: ao menos 1 convênio com substituição SIAFI verificado manualmente
