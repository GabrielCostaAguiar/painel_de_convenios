DROP VIEW IF EXISTS gold.vw_instrumento;

CREATE VIEW gold.vw_instrumento AS
-- Consulta dos dados básicos dos instrumentos grp
WITH concedente_agg AS (
    SELECT nr_grp,
        MIN(nm_concedente) AS nm_concedente,
        MIN(nr_cnpj_concedente) AS nr_cnpj_concedente,
        MIN(ds_esfera_atuacao) AS ds_esfera_atuacao
    FROM grp_concedente
    GROUP BY nr_grp
)
SELECT i.nr_grp,
    i.ds_tipo_instrumento_juridico,
    i.nr_instrumento,
    i.nr_instrumento_transferegov,
    i.nm_projeto,
    i.tx_objeto_projeto,
    i.nm_convenente,
    c.nm_concedente,
    c.ds_esfera_atuacao,
    i.ds_status_instrumento,
    i.ds_situacao_instrumento,
    i.ds_origem_instrumento,
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
SELECT * FROM gold.vw_instrumento;
