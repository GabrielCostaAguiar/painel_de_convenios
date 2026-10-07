CREATE OR REPLACE VIEW gold.vw_instrumento AS
-- Consulta dos dados básicos dos instrumentos grp
WITH concedente_agg AS (
    SELECT nr_grp,
        MIN(nm_concedente) AS nm_concedente,
        MIN(nr_cnpj_concedente) AS nr_cnpj_concedente
    FROM grp_concedente
    GROUP BY nr_grp
)
SELECT i.nr_grp,
    i.ds_tipo_instrumento_juridico,
    i.nr_instrumento,
    i.nr_instrumento_transferegov,
    i.nm_projeto,
    i.tx_objeto_projeto,
    c.nm_concedente,
    i.nm_convenente,
    i.ds_situacao_instrumento,
    i.dt_assinatura,
    i.dt_publicacao,
    i.dt_vigencia_inicio,
    i.dt_vigencia_termino,
    i.dt_vigencia_termino_inicial,
    i.vl_rendimento_autorizado,
    i.vl_instrumento_concedente,
    i.vl_instrumento_contrapartida_fin,
    i.vl_instrumento_total
FROM grp_instrumento i
LEFT JOIN concedente_agg c ON i.nr_grp = c.nr_grp;

-- 1. contagem total (deve dar 4876)
SELECT COUNT(*) FROM gold.vw_instrumento;
