DROP VIEW IF EXISTS gold.vw_instrumento;

CREATE VIEW gold.vw_instrumento AS
-- Consulta dos dados básicos dos instrumentos GRP
-- Grão: 1 linha por instrumento (nr_grp)
WITH concedente_agg AS (
    -- grp_concedente é 1:N: agrega para 1 linha por instrumento
    SELECT nr_grp,
        MIN(nm_concedente)      AS nm_concedente,
        MIN(nr_cnpj_concedente) AS nr_cnpj_concedente,
        MIN(ds_esfera_atuacao)  AS ds_esfera_atuacao
    FROM grp_concedente
    GROUP BY nr_grp
),
uo_execucao AS (
    -- fonte principal da UO: ação orçamentária, ligada por nr_grp
    -- só preenche se o instrumento tiver um único código de UO
    SELECT nr_grp,
        CASE WHEN COUNT(DISTINCT cd_uo_execucao) = 1
             THEN MIN(cd_uo_execucao) END AS cd_uo
    FROM grp_acao_orcamentaria
    GROUP BY nr_grp
),
uo_por_nome AS (
    -- fonte reserva: nome do convenente x tabela de UO
    -- nomes com mais de um código ficam NULL (sem chute)
    SELECT UPPER(TRIM(nm_uo)) AS nm_uo_norm,
        CASE WHEN COUNT(DISTINCT cd_uo) = 1
             THEN MIN(cd_uo) END AS cd_uo
    FROM grp_tabela_uo
    GROUP BY UPPER(TRIM(nm_uo))
)
SELECT i.nr_grp,
    COALESCE(e.cd_uo, u.cd_uo) AS cd_uo,
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
    i.vl_instrumento_contrapartida_nao_fin,
    i.vl_instrumento_total
FROM grp_instrumento i
LEFT JOIN concedente_agg c ON c.nr_grp = i.nr_grp
LEFT JOIN uo_execucao    e ON e.nr_grp = i.nr_grp
LEFT JOIN uo_por_nome    u ON u.nm_uo_norm = UPPER(TRIM(i.nm_convenente));

-- 1. grão preservado: as duas contagens devem dar 4876
SELECT COUNT(*), COUNT(DISTINCT nr_grp) FROM gold.vw_instrumento;

-- 2. instrumentos que ficaram sem UO
SELECT nm_convenente, COUNT(*)
FROM gold.vw_instrumento
WHERE cd_uo IS NULL
GROUP BY nm_convenente
ORDER BY 2 DESC;