-- =====================================================================
-- De-para convenente x UO (premissa P5)
--
-- Liga o CNPJ do convenente de cada instrumento a uma UO. Não existe
-- consulta no GRP que traga UO e CNPJ juntos; a única chave comum entre
-- grp_convenente_cnpj e grp_tabela_uo é o NOME.
--
-- Grão: 1 linha por convenente (CNPJ não nulo) x UO encontrada.
--   * Convenente sem CNPJ fica FORA da view (sem chave, não serve ao
--     de-para CNPJ x UO).
--   * Convenente sem par fica com cd_uo/nm_uo nulos e tp_vinculo 'SEM_UO'.
--   * Dois CNPJs com o mesmo nome (ex.: Secretaria de Justiça e Segurança
--     Pública) geram duas linhas, uma por CNPJ, podendo apontar para a mesma UO.
--   * Um nome que casa com mais de uma UO gera mais de uma linha para o
--     mesmo CNPJ; o T-C24 acusa esse caso.
--
-- Normalização do nome (dos dois lados): sem acento (translate, sem
-- extensão do Postgres), maiúsculas, sem espaços nas pontas e com
-- espaços repetidos reduzidos a um.
--
-- tp_vinculo: 'MANUAL' (ajuste da CTE ajuste_manual, tem prioridade),
--             'AUTOMATICO' (nome normalizado igual) ou 'SEM_UO'.
-- =====================================================================

DROP VIEW IF EXISTS gold.vw_depara_convenente_uo;

CREATE VIEW gold.vw_depara_convenente_uo AS
WITH
-- ---------------------------------------------------------------------
-- Ajustes manuais: nome normalizado do convenente -> cd_uo.
-- Têm prioridade sobre o casamento automático. Começa vazia: o SELECT
-- tipado com WHERE FALSE mantém o SQL válido sem nenhuma linha.
--
-- Para acrescentar um ajuste, troque o bloco abaixo por VALUES. O nome
-- precisa estar JÁ normalizado (maiúsculas, sem acento, espaços únicos):
--
--   ajuste_manual (nome_norm_convenente, cd_uo) AS (
--       VALUES
--           ('SECRETARIA DE ESTADO DE ESPORTES E DA JUVENTUDE', '1371'),
--           ('ENCARGOS GERAIS DO ESTADO', '1031')
--   ),
-- ---------------------------------------------------------------------
ajuste_manual AS (
    SELECT NULL::text AS nome_norm_convenente,
           NULL::text AS cd_uo
    WHERE FALSE
),

convenente AS (
    SELECT
        c.nr_cnpj_convenente,
        c.nm_convenente,
        btrim(regexp_replace(upper(translate(
            c.nm_convenente,
            'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑáàâãäéèêëíìîïóòôõöúùûüçñ',
            'AAAAAEEEEIIIIOOOOOUUUUCNaaaaaeeeeiiiiooooouuuucn'
        )), '\s+', ' ', 'g')) AS nome_norm
    FROM grp_convenente_cnpj c
    WHERE c.nr_cnpj_convenente IS NOT NULL
),

-- UO por nome normalizado. O mesmo cd_uo pode ter dois nomes na
-- grp_tabela_uo (T-C22): cada nome casa com o seu convenente, e o
-- GROUP BY evita repetir a mesma dupla (nome, cd_uo).
uo_por_nome AS (
    SELECT
        btrim(regexp_replace(upper(translate(
            u.nm_uo,
            'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑáàâãäéèêëíìîïóòôõöúùûüçñ',
            'AAAAAEEEEIIIIOOOOOUUUUCNaaaaaeeeeiiiiooooouuuucn'
        )), '\s+', ' ', 'g')) AS nome_norm,
        u.cd_uo,
        MIN(u.nm_uo) AS nm_uo
    FROM grp_tabela_uo u
    WHERE u.cd_uo IS NOT NULL
      AND u.nm_uo IS NOT NULL
    GROUP BY 1, u.cd_uo
),

-- Nome da UO de um ajuste manual (que aponta só o cd_uo).
uo_por_codigo AS (
    SELECT u.cd_uo, MIN(u.nm_uo) AS nm_uo
    FROM grp_tabela_uo u
    WHERE u.cd_uo IS NOT NULL
    GROUP BY u.cd_uo
)

SELECT
    c.nr_cnpj_convenente,
    c.nm_convenente,
    COALESCE(m.cd_uo, a.cd_uo)                  AS cd_uo,
    COALESCE(mu.nm_uo, a.nm_uo)                 AS nm_uo,
    CASE
        WHEN m.cd_uo IS NOT NULL THEN 'MANUAL'
        WHEN a.cd_uo IS NOT NULL THEN 'AUTOMATICO'
        ELSE 'SEM_UO'
    END                                         AS tp_vinculo
FROM convenente c
LEFT JOIN ajuste_manual m
       ON m.nome_norm_convenente = c.nome_norm
LEFT JOIN uo_por_codigo mu
       ON mu.cd_uo = m.cd_uo
-- o casamento automático só vale quando não há ajuste manual
LEFT JOIN uo_por_nome a
       ON m.cd_uo IS NULL
      AND a.nome_norm = c.nome_norm;
