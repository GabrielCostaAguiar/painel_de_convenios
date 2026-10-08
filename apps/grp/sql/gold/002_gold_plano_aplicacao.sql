-- DROP VIEW IF EXISTS gold.vw_recurso_concedente;

CREATE OR REPLACE VIEW gold.vw_recurso_concedente AS
WITH concedente_agg AS (
    SELECT nr_grp,
        MIN(nm_concedente) AS nm_concedente,
        MIN(nr_cnpj_concedente) AS nr_cnpj_concedente
    FROM grp_concedente
    GROUP BY nr_grp
)
SELECT
    r.nr_grp,
    r.cd_uo_arrecadacao,
    r.nm_uo_arrecadacao,
    r.cd_fonte_recurso,
    r.cd_ipu,
    c.nm_concedente,
    c.nr_cnpj_concedente,
    r.vl_recurso_concedente,
    r.ds_situacao_recurso_concedente
FROM grp_recurso_concedente r
LEFT JOIN concedente_agg c ON r.nr_grp = c.nr_grp;

SELECT * FROM gold.vw_recurso_concedente;

CREATE OR REPLACE VIEW gold.vw_recurso_contrapartida AS
SELECT
    r.nr_grp,
    r.cd_uo_financiadora,
    r.nm_uo_financiadora,
    r.cd_fonte_recurso_contrapartida,
    r.cd_ipu_contrapartida,
    r.vl_contrapartida_financeira,
    r.ds_situacao_contrapartida
    -- colunas da tabela de recurso que interessam
    -- opcionalmente, colunas do instrumento para contexto
FROM grp_recurso_contrapartida r
WHERE r.cd_uo_financiadora IS NOT NULL;

SELECT * FROM gold.vw_recurso_contrapartida;

CREATE OR REPLACE VIEW gold.vw_acao_orcamentaria AS
SELECT
    a.nr_grp,
    a.cd_uo_execucao,
    a.nm_uo_execucao,
    a.cd_acao,
    a.ds_situacao_acao,
    a.vl_execucao_orcamentaria
    -- colunas da tabela de recurso que interessam
    -- opcionalmente, colunas do instrumento para contexto
FROM grp_acao_orcamentaria a;

SELECT * FROM gold.vw_acao_orcamentaria;

CREATE OR REPLACE VIEW gold.vw_plano_aplicacao AS
SELECT
    r.nr_grp,
    r.nr_cnpj_beneficiario,
    r.cd_catmas,
    r.tp_despesa,
    r.cd_categoria_economica,
    r.cd_grupo_despesa,
    r.cd_modalidade_aplicacao,
    r.cd_elemento_despesa,
    r.cd_elemento_item,
    r.ds_item,
    r.ds_origem_recurso,
    r.ds_situacao_item,
    r.qt_item,
    r.vl_unitario_item,
    r.vl_total_item

    -- colunas da tabela de recurso que interessam
    -- opcionalmente, colunas do instrumento para contexto
FROM grp_item_executar r;

SELECT * FROM gold.vw_plano_aplicacao;