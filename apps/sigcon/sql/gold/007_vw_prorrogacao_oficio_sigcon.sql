-- gold.vw_prorrogacao_oficio_sigcon
-- grão: 1 linha por convênio × prorrogação de ofício | chave: (siafi_uo, cd_prorrogacao_oficio); id = ROW_NUMBER()
-- fontes: sigcon_prorrogacao_oficio, sigcon_chave_convenio, sigcon_convenio | tela: sigcon › Prorrogação de Ofício
-- validação: SELECT COUNT(*), COUNT(DISTINCT (siafi_uo, cd_prorrogacao_oficio)) FROM gold.vw_prorrogacao_oficio_sigcon;  -- esperado: n = n
--   conferência de perda: SELECT COUNT(*) FROM sigcon_prorrogacao_oficio;  -- 660; a diferença é a prorrogação
--   sem ponte (1 órfã conhecida, P7) ou sem siafi_uo.
--
-- A prorrogação não traz siafi_uo: chega ao convênio por cd_convenio_sequencial (código sequencial, não o
-- número legível) em sigcon_chave_convenio. A ponte é 1:1 (cada sequencial tem um só siafi_uo) e é agregada
-- em CTE por cd_convenio_sequencial antes da junção. Só entra prorrogação com siafi_uo.
-- Datas de vigência são do ofício; a vigência original do convênio fica em vw_convenio_sigcon.

CREATE OR REPLACE VIEW gold.vw_prorrogacao_oficio_sigcon AS
WITH ponte AS (
    SELECT cd_convenio_sequencial,
        MIN(siafi_uo) AS siafi_uo,
        MIN(nr_siafi) AS nr_siafi,
        MIN(cd_uo) AS cd_uo
    FROM sigcon_chave_convenio
    WHERE siafi_uo IS NOT NULL
      AND cd_convenio_sequencial IS NOT NULL
    GROUP BY cd_convenio_sequencial
),
convenio AS (
    SELECT siafi_uo,
        MIN(nr_convenio) AS nr_convenio
    FROM sigcon_convenio
    WHERE siafi_uo IS NOT NULL
    GROUP BY siafi_uo
),
prorrogacao AS (
    -- grão declarado da fonte é 1 por cd_prorrogacao_oficio; MIN garante a unicidade na junção
    SELECT cd_prorrogacao_oficio,
        MIN(cd_convenio_sequencial) AS cd_convenio_sequencial,
        MIN(dt_vigencia_inicio) AS dt_vigencia_inicio,
        MIN(dt_vigencia_termino) AS dt_vigencia_termino,
        MIN(dt_envio) AS dt_envio,
        MIN(dt_parecer) AS dt_parecer,
        MIN(dt_publicacao) AS dt_publicacao
    FROM sigcon_prorrogacao_oficio
    WHERE cd_prorrogacao_oficio IS NOT NULL
    GROUP BY cd_prorrogacao_oficio
)
SELECT ROW_NUMBER() OVER (ORDER BY pt.siafi_uo, p.cd_prorrogacao_oficio) AS id,
    pt.siafi_uo,
    pt.nr_siafi,
    pt.cd_uo,
    cv.nr_convenio,
    p.cd_convenio_sequencial,
    p.cd_prorrogacao_oficio,
    p.dt_vigencia_inicio,
    p.dt_vigencia_termino,
    p.dt_envio,
    p.dt_parecer,
    p.dt_publicacao
FROM prorrogacao p
JOIN ponte pt ON pt.cd_convenio_sequencial = p.cd_convenio_sequencial
LEFT JOIN convenio cv ON cv.siafi_uo = pt.siafi_uo
;

-- ---------------------------------------------------------------------
-- Validação (só SELECT). Esperado indicado em cada item.
-- ---------------------------------------------------------------------
-- 1. grão preservado: as três contagens devem ser iguais
SELECT COUNT(*) AS linhas,
    COUNT(DISTINCT id) AS ids,
    COUNT(DISTINCT (siafi_uo, cd_prorrogacao_oficio)) AS chaves
FROM gold.vw_prorrogacao_oficio_sigcon;

-- 2. conferência de perda: esperado fora_da_gold = 1 (órfã conhecida, P7)
SELECT (SELECT COUNT(*) FROM sigcon_prorrogacao_oficio) AS prorrogacoes_fonte,
    (SELECT COUNT(DISTINCT cd_prorrogacao_oficio) FROM gold.vw_prorrogacao_oficio_sigcon) AS prorrogacoes_gold,
    (SELECT COUNT(*) FROM sigcon_prorrogacao_oficio)
    - (SELECT COUNT(DISTINCT cd_prorrogacao_oficio) FROM gold.vw_prorrogacao_oficio_sigcon) AS fora_da_gold;

-- 3. prorrogações que ficaram fora, por motivo; informativo
SELECT CASE WHEN k.cd_convenio_sequencial IS NULL THEN 'sem ponte' ELSE 'ponte sem siafi_uo' END AS motivo,
    COUNT(DISTINCT p.cd_prorrogacao_oficio) AS qt
FROM sigcon_prorrogacao_oficio p
LEFT JOIN sigcon_chave_convenio k ON k.cd_convenio_sequencial = p.cd_convenio_sequencial
WHERE NOT EXISTS (
    SELECT 1 FROM gold.vw_prorrogacao_oficio_sigcon g WHERE g.cd_prorrogacao_oficio = p.cd_prorrogacao_oficio
)
GROUP BY 1;

-- 4. todo convênio da gold existe em gold.vw_convenio_sigcon (esperado: 0 linhas)
SELECT g.siafi_uo, g.cd_prorrogacao_oficio
FROM gold.vw_prorrogacao_oficio_sigcon g
WHERE NOT EXISTS (
    SELECT 1 FROM gold.vw_convenio_sigcon c WHERE c.siafi_uo = g.siafi_uo
);

-- 5. datas: sem perda de preenchimento em relação à fonte (esperado: diferenças = 0)
SELECT
    (SELECT COUNT(dt_vigencia_termino) FROM gold.vw_prorrogacao_oficio_sigcon)
    - (SELECT COUNT(dt_vigencia_termino) FROM sigcon_prorrogacao_oficio
        WHERE cd_prorrogacao_oficio IN (SELECT cd_prorrogacao_oficio FROM gold.vw_prorrogacao_oficio_sigcon)) AS dif_termino,
    (SELECT COUNT(dt_publicacao) FROM gold.vw_prorrogacao_oficio_sigcon)
    - (SELECT COUNT(dt_publicacao) FROM sigcon_prorrogacao_oficio
        WHERE cd_prorrogacao_oficio IN (SELECT cd_prorrogacao_oficio FROM gold.vw_prorrogacao_oficio_sigcon)) AS dif_publicacao;
