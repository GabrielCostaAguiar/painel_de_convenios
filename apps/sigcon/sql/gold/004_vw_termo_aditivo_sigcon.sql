-- gold.vw_termo_aditivo_sigcon
-- grão: 1 linha por convênio × termo aditivo | chave: (siafi_uo, cd_termo_aditivo); id = ROW_NUMBER()
-- fontes: sigcon_chave_termo_aditivo, sigcon_chave_convenio, sigcon_termo_aditivo
--         | tela: sigcon › Termo Aditivo
-- validação: SELECT COUNT(*), COUNT(DISTINCT (siafi_uo, cd_termo_aditivo)) FROM gold.vw_termo_aditivo_sigcon;  -- esperado: n = n
--   conferência de perda: SELECT COUNT(*) FROM sigcon_termo_aditivo;  -- 7.113; a diferença são os termos
--   sem ponte ou sem siafi_uo (inventário: 8 sem ponte), que ficam fora como na ponte de planos.
--
-- O termo aditivo não traz convênio: chega a ele por sigcon_chave_termo_aditivo (siafi_uo).
-- Mesmo critério de vw_plano_trabalho_sigcon: só entra termo com siafi_uo. A ponte é agregada em CTE
-- por (siafi_uo, cd_termo_aditivo) antes da junção, para garantir 1 linha por convênio × termo.
-- cd_plano_trabalho é o plano do próprio aditivo (liga a gold.vw_plano_trabalho_sigcon).
-- Valores aditados somam por siafi_uo. Sem matrícula (LGPD).

CREATE OR REPLACE VIEW gold.vw_termo_aditivo_sigcon AS
WITH convenio AS (
    SELECT siafi_uo,
        MIN(nr_convenio) AS nr_convenio
    FROM sigcon_chave_convenio
    WHERE siafi_uo IS NOT NULL
    GROUP BY siafi_uo
),
ponte AS (
    SELECT siafi_uo,
        cd_termo_aditivo,
        MIN(nr_siafi) AS nr_siafi,
        MIN(cd_uo) AS cd_uo,
        MIN(cd_plano_trabalho) AS cd_plano_trabalho
    FROM sigcon_chave_termo_aditivo
    WHERE siafi_uo IS NOT NULL
      AND cd_termo_aditivo IS NOT NULL
    GROUP BY siafi_uo, cd_termo_aditivo
),
termo AS (
    -- grão declarado da fonte é 1 por cd_termo_aditivo; MIN garante a unicidade na junção
    SELECT cd_termo_aditivo,
        MIN(nr_termo_aditivo) AS nr_termo_aditivo,
        MIN(nr_ano_termo_aditivo) AS nr_ano_termo_aditivo,
        MIN(tp_termo_aditivo) AS tp_termo_aditivo,
        MIN(tx_justificativa) AS tx_justificativa,
        MIN(dt_assinatura) AS dt_assinatura,
        MIN(dt_vigencia_inicio) AS dt_vigencia_inicio,
        MIN(dt_vigencia_termino) AS dt_vigencia_termino,
        MIN(dh_registro) AS dh_registro,
        MIN(vl_aditivo_concedente) AS vl_aditivo_concedente,
        MIN(vl_aditivo_proponente) AS vl_aditivo_proponente
    FROM sigcon_termo_aditivo
    GROUP BY cd_termo_aditivo
)
SELECT ROW_NUMBER() OVER (ORDER BY p.siafi_uo, p.cd_termo_aditivo) AS id,
    p.siafi_uo,
    p.nr_siafi,
    p.cd_uo,
    cv.nr_convenio,
    p.cd_termo_aditivo,
    p.cd_plano_trabalho,
    t.nr_termo_aditivo,
    t.nr_ano_termo_aditivo,
    t.tp_termo_aditivo,
    t.tx_justificativa,
    t.dt_assinatura,
    t.dt_vigencia_inicio,
    t.dt_vigencia_termino,
    t.dh_registro,
    t.vl_aditivo_concedente,
    t.vl_aditivo_proponente,
    COALESCE(t.vl_aditivo_concedente, 0) + COALESCE(t.vl_aditivo_proponente, 0)
        AS vl_aditivo_total
FROM ponte p
JOIN termo t ON t.cd_termo_aditivo = p.cd_termo_aditivo
LEFT JOIN convenio cv ON cv.siafi_uo = p.siafi_uo
;

-- ---------------------------------------------------------------------
-- Validação (só SELECT). Esperado indicado em cada item.
-- ---------------------------------------------------------------------
-- 1. grão preservado: as três contagens devem ser iguais
SELECT COUNT(*) AS linhas,
    COUNT(DISTINCT id) AS ids,
    COUNT(DISTINCT (siafi_uo, cd_termo_aditivo)) AS chaves
FROM gold.vw_termo_aditivo_sigcon;

-- 2. conferência de perda: termos da fonte x gold (a diferença são termos sem ponte ou sem siafi_uo)
SELECT (SELECT COUNT(*) FROM sigcon_termo_aditivo) AS termos_fonte,
    (SELECT COUNT(DISTINCT cd_termo_aditivo) FROM gold.vw_termo_aditivo_sigcon) AS termos_gold,
    (SELECT COUNT(*) FROM sigcon_termo_aditivo)
    - (SELECT COUNT(DISTINCT cd_termo_aditivo) FROM gold.vw_termo_aditivo_sigcon) AS fora_da_gold;

-- 3. termos que ficaram fora, por motivo; informativo
SELECT CASE WHEN k.cd_termo_aditivo IS NULL THEN 'sem ponte' ELSE 'ponte sem siafi_uo' END AS motivo,
    COUNT(DISTINCT t.cd_termo_aditivo) AS qt
FROM sigcon_termo_aditivo t
LEFT JOIN sigcon_chave_termo_aditivo k ON k.cd_termo_aditivo = t.cd_termo_aditivo
WHERE NOT EXISTS (
    SELECT 1 FROM gold.vw_termo_aditivo_sigcon g WHERE g.cd_termo_aditivo = t.cd_termo_aditivo
)
GROUP BY 1;

-- 4. valores: soma da gold (1 linha por termo) = soma da fonte nos termos que entram
--    (esperado: diferenças = 0; DISTINCT ON evita contar em dobro termo ligado a mais de um convênio)
SELECT
    (SELECT SUM(vl_aditivo_concedente) FROM (
        SELECT DISTINCT ON (cd_termo_aditivo) cd_termo_aditivo, vl_aditivo_concedente
        FROM gold.vw_termo_aditivo_sigcon ORDER BY cd_termo_aditivo) g)
    - (SELECT SUM(vl_aditivo_concedente) FROM sigcon_termo_aditivo
        WHERE cd_termo_aditivo IN (SELECT cd_termo_aditivo FROM gold.vw_termo_aditivo_sigcon)) AS dif_concedente,
    (SELECT SUM(vl_aditivo_proponente) FROM (
        SELECT DISTINCT ON (cd_termo_aditivo) cd_termo_aditivo, vl_aditivo_proponente
        FROM gold.vw_termo_aditivo_sigcon ORDER BY cd_termo_aditivo) g)
    - (SELECT SUM(vl_aditivo_proponente) FROM sigcon_termo_aditivo
        WHERE cd_termo_aditivo IN (SELECT cd_termo_aditivo FROM gold.vw_termo_aditivo_sigcon)) AS dif_proponente;

-- 5. todo termo da gold liga a um plano da ponte gold.vw_plano_trabalho_sigcon (esperado: 0 linhas)
SELECT g.siafi_uo, g.cd_termo_aditivo, g.cd_plano_trabalho
FROM gold.vw_termo_aditivo_sigcon g
WHERE g.cd_plano_trabalho IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM gold.vw_plano_trabalho_sigcon p
    WHERE p.siafi_uo = g.siafi_uo AND p.cd_plano_trabalho = g.cd_plano_trabalho
);
