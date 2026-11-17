-- gold.vw_plano_trabalho_sigcon
-- grão: 1 linha por convênio × plano de trabalho | chave: (siafi_uo, cd_plano_trabalho); id = ROW_NUMBER()
-- fontes: sigcon_chave_convenio, sigcon_convenio_geral, sigcon_chave_termo_aditivo,
--         sigcon_plano_trabalho | tela: sigcon › Plano de Trabalho
-- validação: SELECT COUNT(*), COUNT(DISTINCT (siafi_uo, cd_plano_trabalho)) FROM gold.vw_plano_trabalho_sigcon;  -- esperado: n = n
--
-- Planos de um convênio = plano original (geral + chave_convenio) UNION planos dos aditivos
-- (chave_termo_aditivo). Plano compartilhado por mais de um convênio aparece uma vez por convênio
-- (ex.: plano 7964, erro conhecido do SIGCON; ver docs/qualidade_dados.md S7): é o grão, não fan-out.
-- Ficam fora: convênios sem siafi_uo (8, 3 de teste; T-D01) e planos que nenhum convênio
-- nem aditivo referencia. Sem matrícula (LGPD).

CREATE OR REPLACE VIEW gold.vw_plano_trabalho_sigcon AS
WITH convenio AS (
    -- chave_convenio tem 1 linha por convênio; agrega por siafi_uo para garantir 1:1 na junção final
    SELECT siafi_uo,
        MIN(nr_convenio) AS nr_convenio
    FROM sigcon_chave_convenio
    WHERE siafi_uo IS NOT NULL
    GROUP BY siafi_uo
),
plano_convenio AS (
    -- plano original do convênio
    SELECT k.siafi_uo,
        k.nr_siafi,
        k.cd_uo,
        g.cd_plano_trabalho,
        'original'::text AS origem,
        NULL::text AS cd_termo_aditivo
    FROM sigcon_convenio_geral g
    JOIN sigcon_chave_convenio k ON k.cd_convenio_sequencial = g.cd_convenio_sequencial
    WHERE k.siafi_uo IS NOT NULL
      AND g.cd_plano_trabalho IS NOT NULL
      AND g.cd_plano_trabalho NOT IN ('', '0')
    UNION ALL
    -- plano de cada termo aditivo
    SELECT t.siafi_uo,
        t.nr_siafi,
        t.cd_uo,
        t.cd_plano_trabalho,
        'aditivo'::text,
        t.cd_termo_aditivo
    FROM sigcon_chave_termo_aditivo t
    WHERE t.siafi_uo IS NOT NULL
      AND t.cd_plano_trabalho IS NOT NULL
      AND t.cd_plano_trabalho NOT IN ('', '0')
),
ponte AS (
    -- 1 linha por (siafi_uo, cd_plano_trabalho); o mesmo plano em mais de um aditivo do
    -- mesmo convênio (1 caso) lista os termos, sem duplicar a linha
    SELECT siafi_uo,
        cd_plano_trabalho,
        MIN(nr_siafi) AS nr_siafi,
        MIN(cd_uo) AS cd_uo,
        CASE WHEN BOOL_OR(origem = 'original') THEN 'original' ELSE 'aditivo' END AS origem,
        STRING_AGG(DISTINCT cd_termo_aditivo, '; ' ORDER BY cd_termo_aditivo) AS cd_termo_aditivo
    FROM plano_convenio
    GROUP BY siafi_uo, cd_plano_trabalho
)
SELECT ROW_NUMBER() OVER (ORDER BY b.siafi_uo, b.cd_plano_trabalho) AS id,
    b.siafi_uo,
    b.nr_siafi,
    b.cd_uo,
    cv.nr_convenio,
    b.cd_plano_trabalho,
    b.origem,
    b.cd_termo_aditivo,
    pt.nm_plano_trabalho,
    pt.tx_objeto,
    pt.tx_justificativa,
    pt.cd_execucao_exercicio,
    pt.nr_ano_plano_trabalho,
    pt.ds_status_plano_trabalho,
    pt.ds_caracteristica_contrapartida,
    pt.tp_plano_trabalho,
    pt.tp_instrumento_siafi,
    pt.ds_origem_cadastro,
    pt.ds_alteracao_termo_aditivo,
    pt.dh_cadastro,
    pt.dh_envio_sccg,
    pt.dh_cancelamento_sccg,
    pt.tx_justificativa_cancelamento,
    pt.ds_cancelamento_sccg,
    pt.nr_cnpj_concedente,
    pt.nm_concedente,
    pt.nr_cnpj_proponente
FROM ponte b
LEFT JOIN convenio cv ON cv.siafi_uo = b.siafi_uo
LEFT JOIN sigcon_plano_trabalho pt ON pt.cd_plano_trabalho = b.cd_plano_trabalho
;

-- ---------------------------------------------------------------------
-- Validação (só SELECT). Esperado indicado em cada item.
-- ---------------------------------------------------------------------
-- 1. grão preservado: as três contagens devem ser iguais
SELECT COUNT(*) AS linhas,
    COUNT(DISTINCT id) AS ids,
    COUNT(DISTINCT (siafi_uo, cd_plano_trabalho)) AS chaves
FROM gold.vw_plano_trabalho_sigcon;

-- 2. chave nunca nula e origem só 'original' ou 'aditivo' (esperado: 0 linhas)
SELECT siafi_uo, cd_plano_trabalho, origem
FROM gold.vw_plano_trabalho_sigcon
WHERE siafi_uo IS NULL OR cd_plano_trabalho IS NULL
   OR origem NOT IN ('original', 'aditivo');

-- 3. perda na ponte: planos da fonte (geral + aditivos) que não chegaram à gold (esperado: 0)
WITH esperado AS (
    SELECT DISTINCT k.siafi_uo, g.cd_plano_trabalho
    FROM sigcon_convenio_geral g
    JOIN sigcon_chave_convenio k ON k.cd_convenio_sequencial = g.cd_convenio_sequencial
    WHERE k.siafi_uo IS NOT NULL
      AND g.cd_plano_trabalho IS NOT NULL
      AND g.cd_plano_trabalho NOT IN ('', '0')
    UNION
    SELECT DISTINCT siafi_uo, cd_plano_trabalho
    FROM sigcon_chave_termo_aditivo
    WHERE siafi_uo IS NOT NULL
      AND cd_plano_trabalho IS NOT NULL
      AND cd_plano_trabalho NOT IN ('', '0')
)
SELECT COUNT(*) AS planos_fora_da_gold
FROM esperado e
WHERE NOT EXISTS (
    SELECT 1 FROM gold.vw_plano_trabalho_sigcon v
    WHERE v.siafi_uo = e.siafi_uo AND v.cd_plano_trabalho = e.cd_plano_trabalho
);

-- 4. planos da gold sem cadastro em sigcon_plano_trabalho (LEFT JOIN deixa os campos nulos); informativo
SELECT COUNT(*) AS planos_sem_cadastro
FROM gold.vw_plano_trabalho_sigcon
WHERE nm_plano_trabalho IS NULL AND ds_status_plano_trabalho IS NULL;

-- 5. planos compartilhados por mais de um SIAFI (erro de origem, ex.: 7964); informativo
SELECT cd_plano_trabalho, COUNT(*) AS qt_siafi
FROM gold.vw_plano_trabalho_sigcon
GROUP BY cd_plano_trabalho
HAVING COUNT(*) > 1
ORDER BY 2 DESC;
