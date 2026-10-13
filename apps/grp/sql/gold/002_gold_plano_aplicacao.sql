-- =====================================================================
-- Views gold do Plano de Aplicação
-- O id é gerado por ROW_NUMBER() ordenado pelos atributos do grão (G),
-- para ser estável entre cargas e servir de PK no Django (managed=False).
-- =====================================================================

DROP VIEW IF EXISTS gold.vw_recurso_concedente;
DROP VIEW IF EXISTS gold.vw_recurso_contrapartida;
DROP VIEW IF EXISTS gold.vw_acao_orcamentaria;
DROP VIEW IF EXISTS gold.vw_plano_aplicacao;

-- ---------------------------------------------------------------------
-- Grão: instrumento x UO arrecadação x fonte x IPU x situação
-- ---------------------------------------------------------------------
CREATE VIEW gold.vw_recurso_concedente AS
WITH concedente_agg AS (
    SELECT nr_grp,
        MIN(nm_concedente)      AS nm_concedente,
        MIN(nr_cnpj_concedente) AS nr_cnpj_concedente
    FROM grp_concedente
    GROUP BY nr_grp
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY r.nr_grp, r.cd_uo_arrecadacao, r.cd_fonte_recurso,
                 r.cd_ipu, r.ds_situacao_recurso_concedente
    ) AS id,
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

-- ---------------------------------------------------------------------
-- Grão: instrumento x UO financiadora x fonte x IPU x situação
-- ---------------------------------------------------------------------
CREATE VIEW gold.vw_recurso_contrapartida AS
SELECT
    ROW_NUMBER() OVER (
        ORDER BY r.nr_grp, r.cd_uo_financiadora, r.cd_fonte_recurso_contrapartida,
                 r.cd_ipu_contrapartida, r.ds_situacao_contrapartida
    ) AS id,
    r.nr_grp,
    r.cd_uo_financiadora,
    r.nm_uo_financiadora,
    r.cd_fonte_recurso_contrapartida,
    r.cd_ipu_contrapartida,
    r.vl_contrapartida_financeira,
    r.ds_situacao_contrapartida
FROM grp_recurso_contrapartida r
WHERE r.cd_uo_financiadora IS NOT NULL;

-- ---------------------------------------------------------------------
-- Grão: instrumento x ação x UO execução x situação
-- ---------------------------------------------------------------------
CREATE VIEW gold.vw_acao_orcamentaria AS
SELECT
    ROW_NUMBER() OVER (
        ORDER BY a.nr_grp, a.cd_acao, a.cd_uo_execucao, a.ds_situacao_acao
    ) AS id,
    a.nr_grp,
    a.cd_uo_execucao,
    a.nm_uo_execucao,
    a.cd_acao,
    a.ds_situacao_acao,
    a.vl_execucao_orcamentaria
FROM grp_acao_orcamentaria a;

-- ---------------------------------------------------------------------
-- Grão: instrumento x item a executar (sem ID na fonte: todos os G)
-- ---------------------------------------------------------------------
CREATE VIEW gold.vw_plano_aplicacao AS
SELECT
    ROW_NUMBER() OVER (
        ORDER BY r.nr_grp, r.cd_catmas, r.tp_despesa, r.nr_cnpj_beneficiario,
                 r.ds_item, r.ds_origem_recurso, r.ds_situacao_item,
                 r.cd_categoria_economica, r.cd_grupo_despesa,
                 r.cd_modalidade_aplicacao, r.cd_elemento_despesa,
                 r.cd_elemento_item
    ) AS id,
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
FROM grp_item_executar r;

-- ---------------------------------------------------------------------
-- Validação: o id deve ser único (as 4 consultas devem retornar 0 linhas)
-- ---------------------------------------------------------------------
SELECT id FROM gold.vw_recurso_concedente    GROUP BY id HAVING COUNT(*) > 1;
SELECT id FROM gold.vw_recurso_contrapartida GROUP BY id HAVING COUNT(*) > 1;
SELECT id FROM gold.vw_acao_orcamentaria     GROUP BY id HAVING COUNT(*) > 1;
SELECT id FROM gold.vw_plano_aplicacao       GROUP BY id HAVING COUNT(*) > 1;