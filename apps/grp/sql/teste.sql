SELECT nr_grp,
        SUM(vl_total_item) AS vl_total_item
FROM grp_item_executar
WHERE nr_grp = '1085520'
GROUP BY nr_grp
;

-- SELECT table_name
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
-- ORDER BY ordinal_position;

-- SELECT * 
-- FROM grp_item_executar
-- WHERE nr_grp =  '1085086';
-- SELECT nr_grp,
--         vl_instrumento_total
-- FROM grp_instrumento
-- WHERE nr_grp = '1085086';



-- DROP SCHEMA gold CASCADE;

-- SELECT md5(string_agg(linha, '|' ORDER BY linha))
-- FROM (SELECT (to_jsonb(t) - 'id')::text AS linha FROM grp_emenda t) x;

-- SELECT table_name
-- FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name LIKE 'convenios\_%'
-- ORDER BY 1;

-- T-H01 | ALERTA | quantidade de instrumentos por situação: legado × novo
-- WITH novo AS (
--     SELECT ds_situacao_instrumento AS situacao, COUNT(*) AS qt
--     FROM grp_instrumento
--     WHERE nr_grp IS NOT NULL
--     GROUP BY 1
-- ),
-- legado AS (
--     SELECT situacao, COUNT(*) AS qt_convenios   -- a mesma pergunta na base antiga
--     FROM convenios_convenio 
--     WHERE siafi IS NOT NULL
--     GROUP BY 1
-- )
-- SELECT COALESCE(n.situacao, l.situacao) AS situacao, n.qt AS qt_novo, l.qt AS qt_legado
-- FROM novo n
-- FULL OUTER JOIN legado l ON novo
-- WHERE ___

--  WITH etapas_por_meta AS (
--     SELECT nr_grp,
--            tx_meta_especificacao,
--            MAX(vl_meta)        AS vl_meta,
--            SUM(vl_etapa)       AS vl_soma_etapas
--     FROM grp_cronograma_fisico
--     GROUP BY nr_grp, tx_meta_especificacao
-- )
-- SELECT nr_grp,
--        tx_meta_especificacao,
--        vl_meta,
--        vl_soma_etapas,
--        vl_meta - vl_soma_etapas AS diferenca
-- FROM etapas_por_meta
-- WHERE ABS(vl_meta - COALESCE(vl_soma_etapas, 0)) > 0.01

  -- SELECT pg_typeof(qt_item), pg_typeof(vl_unitario_item), pg_typeof(vl_total_item)
  -- FROM grp_item_executar
  -- LIMIT 1;

  -- SELECT nr_grp,
  --       cd_catmas,
  --       qt_item,
  --       vl_unitario_item,
  --       qt_item * vl_unitario_item                    AS vl_calculado,
  --       vl_total_item,
  --       vl_total_item - qt_item * vl_unitario_item    AS diferenca
  -- FROM grp_item_executar
  -- WHERE ABS(vl_total_item - qt_item * vl_unitario_item) > 0.01

-- SELECT cd_uo, nm_uo FROM grp_tabela_uo WHERE cd_uo = '40121';

-- -- sentido 1: flag diz que tem emenda, mas não tem linha na grp_emenda
-- SELECT i.nr_grp, i.fl_emenda_parlamentar, 'flag TRUE sem emenda na tabela' AS motivo
-- FROM grp_instrumento i
-- WHERE i.nr_grp IS NOT NULL
--   AND i.fl_emenda_parlamentar IS TRUE
--   AND NOT EXISTS (SELECT 1 FROM grp_emenda e WHERE e.nr_grp = i.nr_grp)

-- UNION ALL

-- -- sentido 2: tem linha na grp_emenda, mas flag diz que não tem
-- SELECT i.nr_grp, i.fl_emenda_parlamentar, 'emenda na tabela com flag FALSE ou NULL' AS motivo
-- FROM grp_instrumento i
-- WHERE i.nr_grp IS NOT NULL
--   AND i.fl_emenda_parlamentar IS NOT TRUE
--   AND EXISTS (SELECT 1 FROM grp_emenda e WHERE e.nr_grp = i.nr_grp);


-- SELECT nr_grp,
--         vl_instrumento_total,
--         COALESCE(vl_instrumento_concedente, 0)
--           + COALESCE(vl_instrumento_contrapartida_fin, 0)
--           + COALESCE(vl_instrumento_contrapartida_nao_fin, 0) AS vl_soma_partes,
--         vl_instrumento_total
--           - COALESCE(vl_instrumento_concedente, 0)
--           - COALESCE(vl_instrumento_contrapartida_fin, 0)
--           - COALESCE(vl_instrumento_contrapartida_nao_fin, 0) AS diferenca
-- FROM grp_instrumento
-- WHERE nr_grp IS NOT NULL
--   AND ABS(
--         vl_instrumento_total
--         - COALESCE(vl_instrumento_concedente, 0)
--         - COALESCE(vl_instrumento_contrapartida_fin, 0)
--         - COALESCE(vl_instrumento_contrapartida_nao_fin, 0)
--       ) > 0.01

-- WITH desembolso AS (
--     SELECT nr_grp, SUM(vl_desembolso ) AS vl_soma
--     FROM grp_cronograma_desembolso
--     GROUP BY nr_grp
-- )
-- SELECT i.nr_grp,
--        i.ds_status_instrumento,
--        i.vl_instrumento_concedente + i.vl_instrumento_contrapartida_fin AS valor_desembolso_instrumento,
--        r.vl_soma,
--        i.vl_instrumento_concedente + i.vl_instrumento_contrapartida_fin - COALESCE(r.vl_soma, 0) AS diferenca
-- FROM grp_instrumento i
-- LEFT JOIN desembolso r ON r.nr_grp = i.nr_grp
-- WHERE i.nr_grp IS NOT NULL
--   AND ABS(i.vl_instrumento_total - COALESCE(i.vl_instrumento_contrapartida_nao_fin) - COALESCE(i.vl_instrumento_concedente_executado) - COALESCE(r.vl_soma, 0)) > 0.01;

-- SELECT  *
-- FROM grp_recurso_contrapartida
-- ORDER BY 1;

-- WITH recurso_contrapartida AS (
--     SELECT nr_grp, SUM(vl_contrapartida_financeira) AS vl_soma
--     FROM grp_recurso_contrapartida
--     GROUP BY nr_grp
-- )
-- SELECT i.nr_grp,
--        i.ds_status_instrumento,
--        i.vl_instrumento_contrapartida_fin,
--        r.vl_soma,
--        i.vl_instrumento_contrapartida_fin - COALESCE(r.vl_soma, 0) AS diferenca
-- FROM grp_instrumento i
-- LEFT JOIN recurso_contrapartida r ON r.nr_grp = i.nr_grp
-- WHERE i.nr_grp IS NOT NULL
--   AND ABS(i.vl_instrumento_contrapartida_fin - COALESCE(r.vl_soma, 0)) > 0.01;

-- SELECT i.nr_grp, i.ds_situacao_instrumento, i.vl_instrumento_concedente
-- FROM grp_instrumento i
-- WHERE i.nr_grp IN ('20354', '20431', '20463', '20465', '834405', '834408', '834410')
-- ORDER BY 1;

-- SELECT DISTINCT ds_situacao_recurso_concedente
-- FROM grp_recurso_concedente
-- ORDER BY 1;

-- WITH recurso AS (
--     SELECT nr_grp, SUM(vl_recurso_concedente) AS vl_soma
--     FROM grp_recurso_concedente
--     GROUP BY nr_grp
-- )
-- SELECT i.nr_grp,
--        i.ds_status_instrumento,
--        i.vl_instrumento_concedente,
--        r.vl_soma,
--        i.vl_instrumento_concedente - COALESCE(r.vl_soma, 0) AS diferenca
-- FROM grp_instrumento i
-- LEFT JOIN recurso r ON r.nr_grp = i.nr_grp
-- WHERE i.nr_grp IS NOT NULL
--   AND ABS(i.vl_instrumento_concedente - COALESCE(r.vl_soma, 0)) > 0.01;


-- CREATE TEMP TABLE financiados_teste AS
-- SELECT * FROM grp_instrumento_financiado;

-- INSERT INTO financiados_teste (nr_grp, nr_instrumento_financiado)
-- VALUES ('QUALQUER-1', 'ORFAO-999');

-- SELECT f.*
-- FROM financiados_teste f
-- WHERE f.nr_instrumento_financiado IS NOT NULL
--   AND NOT EXISTS (
--       SELECT 1
--       FROM grp_instrumento p
--       WHERE p.nr_grp = f.nr_instrumento_financiado
--   );
--   SELECT * FROM grp_instrumento_financiado;

-- SELECT id_teste, COUNT(*)
-- FROM dq_resultado_validacao
-- WHERE execucao = (SELECT execucao FROM dq_resultado_validacao ORDER BY dt_execucao DESC LIMIT 1)
-- GROUP BY 1
-- HAVING COUNT(*) > 1;

-- CREATE TEMP TABLE emenda_teste AS SELECT * FROM grp_emenda;
-- INSERT INTO emenda_teste (nr_grp, nr_emenda) VALUES ('ORFAO-999', 'X');

-- CREATE TEMP TABLE pai_teste AS SELECT nr_grp FROM grp_instrumento;
-- INSERT INTO pai_teste VALUES (NULL);

-- -- versão com NOT IN
-- SELECT * FROM emenda_teste
-- WHERE nr_grp NOT IN (SELECT nr_grp FROM pai_teste);

-- -- versão com NOT EXISTS
-- SELECT * FROM emenda_teste f
-- WHERE NOT EXISTS (SELECT 1 FROM pai_teste p WHERE p.nr_grp = f.nr_grp);


--         SELECT f.*
--         FROM emenda_teste f
--         WHERE f.nr_grp IS NOT NULL
--           AND NOT EXISTS (
--             SELECT 1
--             FROM grp_instrumento p
--             WHERE p.nr_grp = f.nr_grp
--           )

-- SELECT nr_ano_desembolso, COUNT(*)
-- FROM grp_cronograma_desembolso
-- WHERE nr_ano_desembolso NOT BETWEEN 2000 AND 2035
-- GROUP BY 1
-- ORDER BY 1;

-- SELECT * FROM grp_instrumento_financiado;

-- SELECT id_teste, tabela, qt_falhas, amostra
-- FROM dq_resultado_validacao
-- WHERE status = 'FALHOU'
--   AND execucao = (SELECT execucao FROM dq_resultado_validacao ORDER BY dt_execucao DESC LIMIT 1)
-- ORDER BY id_teste;

-- SELECT * FROM grp_tabela_uo WHERE cd_uo IS NULL;
-- DELETE FROM dq_resultado_validacao
-- WHERE id_teste ~ '^T-D(0[3-9]|1[0-9]|2[01])$';
        -- SELECT * 
        -- FROM grp_municipio_atendido
        -- WHERE nr_grp IS NULL

        -- SELECT *
        -- FROM grp_concedente
        -- WHERE NOT (nr_cnpj_concedente ~ '^\d{14}$');

        -- SELECT *
        -- FROM grp_municipio_atendido
        -- WHERE sg_uf NOT IN (['MG', 'SP']);

-- SELECT cd_uo, COUNT(*) AS linhas, COUNT(DISTINCT nm_uo) AS nomes
-- FROM grp_tabela_uo
-- GROUP BY cd_uo
-- HAVING COUNT(*) > 1;

-- SELECT linhas, linhas_distintas, COUNT(*) AS grupos
-- FROM (
--     SELECT COUNT(*) AS linhas,
--            COUNT(DISTINCT to_jsonb(t) - 'id') AS linhas_distintas
--     FROM grp_cronograma_fisico t
--     GROUP BY nr_grp, cd_proposta, tp_meta_etapa,
--              tx_meta_especificacao, tx_etapa_especificacao
--     HAVING COUNT(*) > 1
-- ) g
-- GROUP BY 1, 2
-- ORDER BY grupos DESC;

-- SELECT nr_grp, 
--     cd_proposta, 
--     tp_meta_etapa, 
--     tx_meta_especificacao, 
--     tx_etapa_especificacao,
--     COUNT(*) AS qt
-- FROM grp_cronograma_fisico
-- GROUP BY nr_grp, 
--     cd_proposta, 
--     tp_meta_etapa, 
--     tx_meta_especificacao, 
--     tx_etapa_especificacao
-- HAVING COUNT(*) > 1;

-- SELECT MAX(qt_meta_duracao), MAX(qt_etapa_duracao)
-- FROM grp_cronograma_fisico;


-- SELECT 'nr_parcela' AS coluna, nr_parcela AS valor, COUNT(*) AS qt
-- FROM grp_cronograma_desembolso
-- WHERE nr_parcela !~ '^\d+$'
-- GROUP BY 2
-- UNION ALL
-- SELECT 'nr_ano_desembolso' AS coluna, nr_ano_desembolso AS valor, COUNT(*) AS qt
-- FROM grp_cronograma_desembolso
-- WHERE nr_ano_desembolso !~ '^\d+$'
-- GROUP BY 2
-- UNION ALL
-- SELECT 'nr_mes_desembolso' AS coluna, nr_mes_desembolso AS valor, COUNT(*) AS qt
-- FROM grp_cronograma_desembolso
-- WHERE nr_mes_desembolso !~ '^\d+$'
-- GROUP BY 2
-- UNION ALL
-- SELECT 'nr_ano_emenda' AS coluna, nr_ano_emenda AS valor, COUNT(*) AS qt
-- FROM grp_emenda
-- WHERE nr_ano_emenda !~ '^\d+$'
-- GROUP BY 2;



-- SELECT id_teste, status, qt_falhas, amostra, dt_execucao
-- FROM dq_resultado_validacao
-- ORDER BY dt_execucao DESC;

-- -- T-C01 | ERRO | grp_instrumento tem uma linha por nr_grp (premissa P3)
-- -- Devolve os nr_grp repetidos. Zero linhas = passou.
-- SELECT nr_grp, COUNT(*) AS qt
-- FROM grp_instrumento
-- WHERE nr_grp IS NOT NULL
-- GROUP BY nr_grp
-- HAVING COUNT(*) > 1;

-- -- T-D01 | ERRO | toda linha tem nr_grp ou cd_proposta (chave por tipo de linha)
-- SELECT nr_grp, tp_proposta_instrumento, nr_instrumento, nr_instrumento_transferegov, ds_situacao_proposta, ds_situacao_instrumento, ds_status_instrumento
-- FROM grp_instrumento
-- WHERE COALESCE(nr_grp, cd_proposta) IS NULL;

-- -- T-D02 | exploratório | o que são as linhas sem nr_grp? (premissa P4)
-- SELECT tp_proposta_instrumento, ds_situacao_proposta, COUNT(*) AS qt
-- FROM grp_instrumento
-- WHERE nr_grp IS NULL
-- GROUP BY tp_proposta_instrumento, ds_situacao_proposta
-- ORDER BY qt DESC;

-- -- T-D02 | ERRO | linhas sem nr_grp são sempre propostas (P4)
-- SELECT nr_grp, cd_proposta, tp_proposta_instrumento, ds_situacao_proposta
-- FROM grp_instrumento
-- WHERE nr_grp IS NULL AND tp_proposta_instrumento IS DISTINCT FROM 'PROPOSTA'
-- ;

-- -- exploratório | Encontrando registro de algum código de proposta
-- SELECT
--     COUNT(*) FILTER (WHERE nr_grp IS NOT NULL)                 AS qt_instrumentos,
--     COUNT(cd_proposta_origem) FILTER (WHERE nr_grp IS NOT NULL) AS origem_preenchida_instr,
--     COUNT(nr_proposta_instrumento) FILTER (WHERE nr_grp IS NOT NULL) AS nr_proposta,
--     COUNT(tp_proposta_instrumento) FILTER (WHERE nr_grp IS NOT NULL) AS tp_proposta
-- FROM grp_instrumento;

-- -- exploratório | Visualizando registros que tem nr_proposta_instrumento
-- SELECT *
-- FROM grp_instrumento
-- WHERE nr_proposta_instrumento IS NOT NULL
-- ORDER BY nr_grp;

-- SELECT DISTINCT tp_proposta_instrumento FROM grp_instrumento;

-- T-A02 | Must não vazias
-- SELECT 'grp_instrumento' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_instrumento)
-- UNION ALL
-- SELECT 'grp_concedente' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_concedente)
-- UNION ALL
-- SELECT 'grp_emenda' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_emenda)
-- UNION ALL
-- SELECT 'grp_recurso_concedente' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_recurso_concedente)
-- UNION ALL
-- SELECT 'grp_recurso_contrapartida' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_recurso_contrapartida)
-- UNION ALL
-- SELECT 'grp_acao_orcamentaria' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_acao_orcamentaria)
-- UNION ALL
-- SELECT 'grp_cronograma_desembolso' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_cronograma_desembolso)
-- UNION ALL
-- SELECT 'grp_tabela_uo' AS tabela WHERE NOT EXISTS (SELECT 1 FROM grp_tabela_uo);

-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name LIKE 'grp\_%'
--   AND (
--        (column_name LIKE 'vl\_%' AND data_type <> 'numeric')
--     OR (column_name LIKE 'dt\_%' AND data_type <> 'date')   -- dt_ precisa ser date
--     OR (column_name LIKE 'fl\_%' AND data_type <> 'boolean')   -- fl_ precisa ser boolean
--     OR (column_name ~ '^(cd|sg|nr_cnpj|nr_cpf)_' AND data_type NOT IN ('character varying', 'text'))   -- cd_, sg_, nr_cnpj_ e nr_cpf_ precisam ser texto
--   )

-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--     AND (table_name, column_name) IN (
--     ('grp_emenda', 'nr_ano_emenda'),
--     ('grp_cronograma_desembolso', 'nr_parcela'),
--     ('grp_cronograma_desembolso', 'nr_ano_desembolso'),
--     ('grp_cronograma_desembolso', 'nr_mes_desembolso')
-- )
--   )
--   AND data_type NOT IN ('integer', 'bigint', 'smallint')