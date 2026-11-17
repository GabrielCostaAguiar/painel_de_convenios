-- gold.vw_cronograma_desembolso_sigcon
-- grão: 1 linha por convênio × plano de trabalho × ano × mês de desembolso
-- chave: (siafi_uo, cd_plano_trabalho, nr_ano_desembolso, nr_mes_desembolso); id = ROW_NUMBER()
-- fontes: sigcon_cronograma_desembolso, gold.vw_plano_trabalho_sigcon | tela: sigcon › Cronograma de Desembolso
-- validação: SELECT COUNT(*), COUNT(DISTINCT (siafi_uo, cd_plano_trabalho, nr_ano_desembolso,
--   nr_mes_desembolso)) FROM gold.vw_cronograma_desembolso_sigcon;  -- esperado: n = n
--   (se n > distintos, a fonte repete o mês dentro do plano: agregar em CTE antes da junção)
--
-- Só linhas válidas (ds_alerta_linha IS NULL): o bloco desalinhado do relatório do BO fica fora.
-- Entra pela ponte vw_plano_trabalho_sigcon com join interno: só ficam os planos que chegam a um
-- siafi_uo (mesmo critério de vw_plano_aplicacao_sigcon). A ponte é 1 linha por convênio × plano,
-- então não há fan-out. Plano compartilhado por vários SIAFI (erro de origem, ex.: 7964) repete a
-- linha em cada SIAFI: some valores sempre por siafi_uo, nunca por cd_plano_trabalho.
-- dt_desembolso = 1º dia do mês, para ordenação e filtros de período na tela.

CREATE OR REPLACE VIEW gold.vw_cronograma_desembolso_sigcon AS
SELECT ROW_NUMBER() OVER (
        ORDER BY p.siafi_uo, p.cd_plano_trabalho, cd.nr_ano_desembolso, cd.nr_mes_desembolso
    ) AS id,
    p.siafi_uo,
    p.nr_siafi,
    p.nr_convenio,
    p.cd_plano_trabalho,
    p.origem,
    p.cd_termo_aditivo,
    cd.nr_ano_desembolso,
    cd.nr_mes_desembolso,
    MAKE_DATE(cd.nr_ano_desembolso, cd.nr_mes_desembolso, 1) AS dt_desembolso,
    cd.vl_desembolso_concedente,
    cd.vl_desembolso_proponente,
    COALESCE(cd.vl_desembolso_concedente, 0) + COALESCE(cd.vl_desembolso_proponente, 0)
        AS vl_desembolso_total
FROM sigcon_cronograma_desembolso cd
JOIN gold.vw_plano_trabalho_sigcon p ON p.cd_plano_trabalho = cd.cd_plano_trabalho
WHERE cd.ds_alerta_linha IS NULL
;

-- ---------------------------------------------------------------------
-- Validação (só SELECT). Esperado indicado em cada item.
-- ---------------------------------------------------------------------
-- 1. grão preservado: as três contagens devem ser iguais
SELECT COUNT(*) AS linhas,
    COUNT(DISTINCT id) AS ids,
    COUNT(DISTINCT (siafi_uo, cd_plano_trabalho, nr_ano_desembolso, nr_mes_desembolso)) AS chaves
FROM gold.vw_cronograma_desembolso_sigcon;

-- 2. sem fan-out: linhas da gold = linhas válidas da fonte x SIAFI do plano (esperado: diferenca = 0)
WITH siafi_por_plano AS (
    SELECT cd_plano_trabalho, COUNT(*) AS qt
    FROM gold.vw_plano_trabalho_sigcon
    GROUP BY cd_plano_trabalho
)
SELECT (SELECT COUNT(*) FROM gold.vw_cronograma_desembolso_sigcon) AS linhas_gold,
    SUM(s.qt) AS linhas_esperadas,
    (SELECT COUNT(*) FROM gold.vw_cronograma_desembolso_sigcon) - SUM(s.qt) AS diferenca
FROM sigcon_cronograma_desembolso cd
JOIN siafi_por_plano s ON s.cd_plano_trabalho = cd.cd_plano_trabalho
WHERE cd.ds_alerta_linha IS NULL;

-- 3. valores: soma da gold = soma da fonte nos planos de 1 só SIAFI (esperado: diferenças = 0)
WITH plano_unico AS (
    SELECT cd_plano_trabalho
    FROM gold.vw_plano_trabalho_sigcon
    GROUP BY cd_plano_trabalho
    HAVING COUNT(*) = 1
)
SELECT
    (SELECT SUM(vl_desembolso_concedente) FROM gold.vw_cronograma_desembolso_sigcon
        WHERE cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico))
    - (SELECT SUM(vl_desembolso_concedente) FROM sigcon_cronograma_desembolso
        WHERE ds_alerta_linha IS NULL
          AND cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico)) AS dif_concedente,
    (SELECT SUM(vl_desembolso_proponente) FROM gold.vw_cronograma_desembolso_sigcon
        WHERE cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico))
    - (SELECT SUM(vl_desembolso_proponente) FROM sigcon_cronograma_desembolso
        WHERE ds_alerta_linha IS NULL
          AND cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico)) AS dif_proponente;

-- 4. linhas válidas da fonte que ficaram fora (plano sem siafi_uo); informativo
SELECT COUNT(*) AS fora_da_gold
FROM sigcon_cronograma_desembolso cd
WHERE cd.ds_alerta_linha IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM gold.vw_plano_trabalho_sigcon p WHERE p.cd_plano_trabalho = cd.cd_plano_trabalho
);

-- 5. mês entre 1 e 12 e dt_desembolso preenchida (esperado: 0 linhas)
SELECT siafi_uo, cd_plano_trabalho, nr_ano_desembolso, nr_mes_desembolso
FROM gold.vw_cronograma_desembolso_sigcon
WHERE nr_mes_desembolso NOT BETWEEN 1 AND 12 OR dt_desembolso IS NULL;
