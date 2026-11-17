-- gold.vw_unidade_executora_sigcon
-- grão: 1 linha por convênio × unidade executora | chave: (siafi_uo, cd_unidade_executora); id = ROW_NUMBER()
-- fontes: sigcon_unidade_executora, sigcon_convenio | tela: sigcon › Unidades Executoras
-- validação: SELECT COUNT(*), COUNT(DISTINCT (siafi_uo, cd_unidade_executora)) FROM gold.vw_unidade_executora_sigcon;  -- esperado: n = n
--   conferência de perda: SELECT COUNT(*) FROM sigcon_unidade_executora;  -- 28.316; a diferença são as linhas
--   sem siafi_uo (1), que ficam fora como nas demais views SIGCON.
--
-- A unidade executora é 1:N com o convênio e chega a ele direto por siafi_uo. Só entra linha com siafi_uo.
-- A unidade executora tem só código (não há nome na fonte). nr_convenio vem de sigcon_convenio: o da
-- fonte é redundante. A tabela 1:N é agregada em CTE por (siafi_uo, cd_unidade_executora) antes da junção.

CREATE OR REPLACE VIEW gold.vw_unidade_executora_sigcon AS
WITH convenio AS (
    SELECT siafi_uo,
        MIN(nr_convenio) AS nr_convenio
    FROM sigcon_convenio
    WHERE siafi_uo IS NOT NULL
    GROUP BY siafi_uo
),
unidade AS (
    -- grão declarado da fonte é siafi_uo × cd_unidade_executora; MIN garante a unicidade na junção
    SELECT siafi_uo,
        cd_unidade_executora,
        MIN(nr_siafi) AS nr_siafi,
        MIN(cd_uo) AS cd_uo
    FROM sigcon_unidade_executora
    WHERE siafi_uo IS NOT NULL
      AND cd_unidade_executora IS NOT NULL
    GROUP BY siafi_uo, cd_unidade_executora
)
SELECT ROW_NUMBER() OVER (ORDER BY u.siafi_uo, u.cd_unidade_executora) AS id,
    u.siafi_uo,
    u.nr_siafi,
    u.cd_uo,
    cv.nr_convenio,
    u.cd_unidade_executora
FROM unidade u
JOIN convenio cv ON cv.siafi_uo = u.siafi_uo
;

-- ---------------------------------------------------------------------
-- Validação (só SELECT). Esperado indicado em cada item.
-- ---------------------------------------------------------------------
-- 1. grão preservado: as três contagens devem ser iguais
SELECT COUNT(*) AS linhas,
    COUNT(DISTINCT id) AS ids,
    COUNT(DISTINCT (siafi_uo, cd_unidade_executora)) AS chaves
FROM gold.vw_unidade_executora_sigcon;

-- 2. conferência de perda: esperado fora_da_gold = 1 (linha sem siafi_uo)
SELECT (SELECT COUNT(*) FROM sigcon_unidade_executora) AS linhas_fonte,
    (SELECT COUNT(*) FROM gold.vw_unidade_executora_sigcon) AS linhas_gold,
    (SELECT COUNT(*) FROM sigcon_unidade_executora)
    - (SELECT COUNT(*) FROM gold.vw_unidade_executora_sigcon) AS fora_da_gold,
    (SELECT COUNT(*) FROM sigcon_unidade_executora WHERE siafi_uo IS NULL) AS sem_siafi_uo;

-- 3. todo convênio da gold existe em gold.vw_convenio_sigcon (esperado: 0 linhas)
SELECT g.siafi_uo, g.cd_unidade_executora
FROM gold.vw_unidade_executora_sigcon g
WHERE NOT EXISTS (
    SELECT 1 FROM gold.vw_convenio_sigcon c WHERE c.siafi_uo = g.siafi_uo
);

-- 4. qt_unidades_executoras da vw_convenio_sigcon = contagem desta view (esperado: 0 linhas)
SELECT c.siafi_uo, c.qt_unidades_executoras, COUNT(g.id) AS qt_gold
FROM gold.vw_convenio_sigcon c
LEFT JOIN gold.vw_unidade_executora_sigcon g ON g.siafi_uo = c.siafi_uo
GROUP BY c.siafi_uo, c.qt_unidades_executoras
HAVING c.qt_unidades_executoras <> COUNT(g.id);
