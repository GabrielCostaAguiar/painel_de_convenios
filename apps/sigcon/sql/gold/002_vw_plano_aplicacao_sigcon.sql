-- gold.vw_plano_aplicacao_sigcon
-- grão: 1 linha por convênio × plano de trabalho × classificação orçamentária × ano
-- chave: (siafi_uo, cd_plano_trabalho, cd_uo_aplicacao, classificação funcional-programática e
--        da despesa, nr_ano_exercicio); id = ROW_NUMBER()
-- fontes: sigcon_plano_aplicacao, gold.vw_plano_trabalho_sigcon | tela: sigcon › Plano de Aplicação
-- validação: SELECT COUNT(*), COUNT(DISTINCT (siafi_uo, cd_plano_trabalho, cd_uo_aplicacao, cd_funcao,
--   cd_subfuncao, cd_programa, cd_identificador_projeto_atividade, cd_projeto_atividade,
--   cd_subprojeto_subatividade, cd_categoria_economica, cd_grupo_despesa, cd_modalidade_aplicacao,
--   cd_elemento_despesa, cd_identificador_orcamento, cd_fonte_recurso, cd_procedencia,
--   nr_ano_exercicio)) FROM gold.vw_plano_aplicacao_sigcon;  -- esperado: n = n
--
-- Entra pela ponte vw_plano_trabalho_sigcon com join interno: só ficam as linhas de plano que chega
-- a um siafi_uo. Planos de cadastro, suplementação e remanejamento (sem vínculo por SIAFI) ficam
-- fora (docs/qualidade_dados.md S7). A ponte é 1 linha por convênio × plano, então não há fan-out.
-- Plano compartilhado por vários SIAFI (erro de origem, ex.: 7964) repete a linha em cada SIAFI:
-- some valores sempre por siafi_uo, nunca por cd_plano_trabalho.
-- cd_uo_aplicacao é a UO da dotação (do plano de aplicação); a UO do convênio está em siafi_uo.

CREATE OR REPLACE VIEW gold.vw_plano_aplicacao_sigcon AS
SELECT ROW_NUMBER() OVER (
        ORDER BY p.siafi_uo, p.cd_plano_trabalho, pa.nr_ano_exercicio, pa.cd_funcional_programatica,
            pa.cd_uo, pa.cd_categoria_economica, pa.cd_grupo_despesa, pa.cd_modalidade_aplicacao,
            pa.cd_elemento_despesa, pa.cd_identificador_orcamento, pa.cd_fonte_recurso,
            pa.cd_procedencia
    ) AS id,
    p.siafi_uo,
    p.nr_siafi,
    p.nr_convenio,
    p.cd_plano_trabalho,
    p.origem,
    p.cd_termo_aditivo,
    pa.cd_uo AS cd_uo_aplicacao,
    pa.nr_ano_exercicio,
    pa.cd_funcao,
    pa.cd_subfuncao,
    pa.cd_programa,
    pa.cd_identificador_projeto_atividade,
    pa.cd_projeto_atividade,
    pa.cd_subprojeto_subatividade,
    pa.cd_categoria_economica,
    pa.cd_grupo_despesa,
    pa.cd_modalidade_aplicacao,
    pa.cd_elemento_despesa,
    pa.cd_identificador_orcamento,
    pa.cd_fonte_recurso,
    pa.cd_procedencia,
    pa.cd_funcional_programatica AS dotacao_orcamentaria,
    REPLACE(SUBSTR(pa.cd_funcional_programatica, 12, 5), '.', '') AS acao_orcamentaria,
    pa.vl_aplicacao_concedente,
    pa.vl_aplicacao_proponente
FROM sigcon_plano_aplicacao pa
JOIN gold.vw_plano_trabalho_sigcon p ON p.cd_plano_trabalho = pa.cd_plano_trabalho
;

-- ---------------------------------------------------------------------
-- Validação (só SELECT). Esperado indicado em cada item.
-- ---------------------------------------------------------------------
-- 1. grão preservado: id único e linhas = linhas distintas da chave completa
SELECT COUNT(*) AS linhas,
    COUNT(DISTINCT id) AS ids,
    COUNT(DISTINCT (siafi_uo, cd_plano_trabalho, cd_uo_aplicacao, cd_funcao, cd_subfuncao,
        cd_programa, cd_identificador_projeto_atividade, cd_projeto_atividade,
        cd_subprojeto_subatividade, cd_categoria_economica, cd_grupo_despesa,
        cd_modalidade_aplicacao, cd_elemento_despesa, cd_identificador_orcamento,
        cd_fonte_recurso, cd_procedencia, nr_ano_exercicio)) AS chaves
FROM gold.vw_plano_aplicacao_sigcon;

-- 2. sem fan-out: linhas da gold = soma, por linha da fonte, de quantos SIAFI têm o plano
--    (esperado: diferenca = 0)
WITH siafi_por_plano AS (
    SELECT cd_plano_trabalho, COUNT(*) AS qt
    FROM gold.vw_plano_trabalho_sigcon
    GROUP BY cd_plano_trabalho
)
SELECT (SELECT COUNT(*) FROM gold.vw_plano_aplicacao_sigcon) AS linhas_gold,
    SUM(s.qt) AS linhas_esperadas,
    (SELECT COUNT(*) FROM gold.vw_plano_aplicacao_sigcon) - SUM(s.qt) AS diferenca
FROM sigcon_plano_aplicacao pa
JOIN siafi_por_plano s ON s.cd_plano_trabalho = pa.cd_plano_trabalho;

-- 3. valores: soma da gold = soma da fonte nos planos de 1 só SIAFI (esperado: diferenças = 0)
WITH plano_unico AS (
    SELECT cd_plano_trabalho
    FROM gold.vw_plano_trabalho_sigcon
    GROUP BY cd_plano_trabalho
    HAVING COUNT(*) = 1
)
SELECT
    (SELECT SUM(vl_aplicacao_concedente) FROM gold.vw_plano_aplicacao_sigcon
        WHERE cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico))
    - (SELECT SUM(vl_aplicacao_concedente) FROM sigcon_plano_aplicacao
        WHERE cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico)) AS dif_concedente,
    (SELECT SUM(vl_aplicacao_proponente) FROM gold.vw_plano_aplicacao_sigcon
        WHERE cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico))
    - (SELECT SUM(vl_aplicacao_proponente) FROM sigcon_plano_aplicacao
        WHERE cd_plano_trabalho IN (SELECT cd_plano_trabalho FROM plano_unico)) AS dif_proponente;

-- 4. linhas da fonte que ficaram fora (plano sem siafi_uo na ponte); informativo (S7)
SELECT COUNT(*) AS fora_da_gold
FROM sigcon_plano_aplicacao pa
WHERE NOT EXISTS (
    SELECT 1 FROM gold.vw_plano_trabalho_sigcon p WHERE p.cd_plano_trabalho = pa.cd_plano_trabalho
);

-- 5. cd_uo_aplicacao com 4 caracteres (esperado: só o sentinela 9999999999, ver limites.py)
SELECT cd_uo_aplicacao, COUNT(*)
FROM gold.vw_plano_aplicacao_sigcon
WHERE cd_uo_aplicacao IS NULL OR LENGTH(cd_uo_aplicacao) <> 4
GROUP BY cd_uo_aplicacao;
