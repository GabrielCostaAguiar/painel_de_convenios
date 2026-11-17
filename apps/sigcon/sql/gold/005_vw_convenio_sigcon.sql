-- gold.vw_convenio_sigcon
-- grão: 1 linha por convênio | chave: siafi_uo; id = ROW_NUMBER()
-- fontes: sigcon_convenio, sigcon_chave_convenio, sigcon_convenio_geral, sigcon_plano_trabalho,
--         sigcon_concedente, sigcon_tabela_uo, sigcon_unidade_executora | tela: sigcon › Convênios
-- validação: SELECT COUNT(*), COUNT(DISTINCT siafi_uo) FROM gold.vw_convenio_sigcon;  -- esperado: n = n
--   conferência de perda: SELECT COUNT(*) FROM sigcon_convenio;  -- 5.353; a diferença são os convênios
--   sem siafi_uo (8), que ficam fora como nas demais views SIGCON.
--
-- View principal do painel. Base = sigcon_convenio (situação, vigência e valores). O plano de trabalho é
-- o ORIGINAL (sigcon_convenio_geral.cd_plano_trabalho); os planos dos aditivos ficam em
-- vw_plano_trabalho_sigcon.
-- Plano compartilhado: o mesmo cd_plano_trabalho pode constar em convênios com siafi_uo diferentes (erro
-- conhecido do SIGCON, ver qualidade_dados.md S7). NÃO é filtrado nem deduplicado: cada convênio mostra o
-- seu plano, e fl_plano_compartilhado / qt_convenios_mesmo_plano sinalizam o caso para o analista.
-- Convênio sem plano (código vazio/0) ou com plano ausente em sigcon_plano_trabalho entra com os campos
-- do plano nulos (LEFT JOIN).
-- Valores aditados por termo ficam em vw_termo_aditivo_sigcon; aqui só os valores de sigcon_convenio.
-- Proponente: o SIGCON só traz o CNPJ (não há nome em nenhuma tabela). Sem matrícula (LGPD).
--
-- Campos previstos e ainda não existentes (acrescentar NO FINAL da lista do SELECT final, para
-- CREATE OR REPLACE VIEW continuar válido): cd_uniao (Código União), nr_sei (SEI).

CREATE OR REPLACE VIEW gold.vw_convenio_sigcon AS
WITH ponte AS (
    -- chave_convenio tem 1 linha por convênio; agrega por siafi_uo para garantir 1:1
    SELECT siafi_uo,
        MIN(cd_convenio_sequencial) AS cd_convenio_sequencial
    FROM sigcon_chave_convenio
    WHERE siafi_uo IS NOT NULL
    GROUP BY siafi_uo
),
geral AS (
    -- grão da fonte: 1 por cd_convenio_sequencial; MIN garante a unicidade na junção
    SELECT cd_convenio_sequencial,
        MIN(NULLIF(NULLIF(cd_plano_trabalho, ''), '0')) AS cd_plano_trabalho,
        MIN(nr_ano_convenio) AS nr_ano_convenio,
        MIN(dt_assinatura) AS dt_assinatura,
        MIN(dt_publicacao) AS dt_publicacao
    FROM sigcon_convenio_geral
    GROUP BY cd_convenio_sequencial
),
plano AS (
    -- 1 linha por cd_plano_trabalho (confirmado: 18.291 linhas = 18.291 códigos)
    SELECT cd_plano_trabalho,
        MIN(nm_plano_trabalho) AS nm_plano_trabalho,
        MIN(tx_objeto) AS tx_objeto,
        MIN(tp_instrumento_siafi) AS tp_instrumento_siafi,
        MIN(ds_caracteristica_contrapartida) AS ds_caracteristica_contrapartida,
        MIN(nr_cnpj_concedente) AS nr_cnpj_concedente,
        MIN(nm_concedente) AS nm_concedente,
        MIN(nr_cnpj_proponente) AS nr_cnpj_proponente
    FROM sigcon_plano_trabalho
    GROUP BY cd_plano_trabalho
),
concedente AS (
    SELECT nr_cnpj_concedente,
        MIN(ds_esfera) AS ds_esfera
    FROM sigcon_concedente
    GROUP BY nr_cnpj_concedente
),
uo AS (
    -- nome da UO no exercício mais recente (sigcon_tabela_uo tem 1 linha por UO × ano)
    SELECT DISTINCT ON (cd_uo) cd_uo,
        nm_uo
    FROM sigcon_tabela_uo
    ORDER BY cd_uo, nr_ano_exercicio DESC
),
unidade_executora AS (
    -- 1:N agregada por convênio antes da junção
    SELECT siafi_uo,
        COUNT(DISTINCT cd_unidade_executora) AS qt_unidades_executoras
    FROM sigcon_unidade_executora
    WHERE siafi_uo IS NOT NULL
    GROUP BY siafi_uo
),
plano_compartilhado AS (
    -- quantos convênios (siafi_uo) apontam para o mesmo plano original
    SELECT g.cd_plano_trabalho,
        COUNT(DISTINCT p.siafi_uo) AS qt_convenios_mesmo_plano
    FROM geral g
    JOIN ponte p ON p.cd_convenio_sequencial = g.cd_convenio_sequencial
    WHERE g.cd_plano_trabalho IS NOT NULL
    GROUP BY g.cd_plano_trabalho
)
SELECT ROW_NUMBER() OVER (ORDER BY c.siafi_uo) AS id,
    -- identificação
    c.siafi_uo,
    c.cd_uo,
    uo.nm_uo,
    c.nr_convenio,                      -- Código SIGCON (ex.: 'CV 98/2020')
    p.cd_convenio_sequencial,
    c.nr_siafi,                         -- Código SIAFI
    g.cd_plano_trabalho,
    g.nr_ano_convenio,
    -- plano de trabalho original
    pl.nm_plano_trabalho,               -- Título
    pl.tx_objeto,                       -- Objeto
    pl.tp_instrumento_siafi,            -- Instrumento (tipo)
    pl.ds_caracteristica_contrapartida, -- Tipo de contrapartida
    -- partes
    pl.nr_cnpj_proponente,
    pl.nr_cnpj_concedente,
    pl.nm_concedente,
    cc.ds_esfera AS ds_esfera_concedente,
    -- situação e datas
    c.ds_situacao_convenio,
    g.dt_assinatura,
    g.dt_publicacao,
    c.dt_vigencia_inicio,
    c.dt_vigencia_termino_inicial,
    c.dt_vigencia_termino,
    -- negativo = já vencido
    (c.dt_vigencia_termino - CURRENT_DATE) AS qt_dias_para_vencer,
    -- valores (sigcon_convenio)
    c.vl_convenio_proponente_inicial,
    c.vl_convenio_proponente_aditado,
    c.vl_convenio_proponente,
    c.vl_convenio_concedente_inicial,
    c.vl_convenio_concedente_aditado,
    c.vl_convenio_concedente,
    c.vl_convenio_total,
    -- apoio e alertas
    COALESCE(ue.qt_unidades_executoras, 0) AS qt_unidades_executoras,
    COALESCE(pc.qt_convenios_mesmo_plano, 0) AS qt_convenios_mesmo_plano,
    COALESCE(pc.qt_convenios_mesmo_plano, 0) > 1 AS fl_plano_compartilhado
FROM sigcon_convenio c
JOIN ponte p ON p.siafi_uo = c.siafi_uo
LEFT JOIN geral g ON g.cd_convenio_sequencial = p.cd_convenio_sequencial
LEFT JOIN plano pl ON pl.cd_plano_trabalho = g.cd_plano_trabalho
LEFT JOIN concedente cc ON cc.nr_cnpj_concedente = pl.nr_cnpj_concedente
LEFT JOIN uo ON uo.cd_uo = c.cd_uo
LEFT JOIN unidade_executora ue ON ue.siafi_uo = c.siafi_uo
LEFT JOIN plano_compartilhado pc ON pc.cd_plano_trabalho = g.cd_plano_trabalho
WHERE c.siafi_uo IS NOT NULL
;

-- ---------------------------------------------------------------------
-- Validação (só SELECT). Esperado indicado em cada item.
-- ---------------------------------------------------------------------
-- 1. grão preservado: as três contagens devem ser iguais
SELECT COUNT(*) AS linhas,
    COUNT(DISTINCT id) AS ids,
    COUNT(DISTINCT siafi_uo) AS chaves
FROM gold.vw_convenio_sigcon;

-- 2. conferência de perda: esperado fora_da_gold = 8 (convênios sem siafi_uo)
SELECT (SELECT COUNT(*) FROM sigcon_convenio) AS convenios_fonte,
    (SELECT COUNT(*) FROM gold.vw_convenio_sigcon) AS convenios_gold,
    (SELECT COUNT(*) FROM sigcon_convenio) - (SELECT COUNT(*) FROM gold.vw_convenio_sigcon) AS fora_da_gold,
    (SELECT COUNT(*) FROM sigcon_convenio WHERE siafi_uo IS NULL) AS sem_siafi_uo;

-- 3. valores: gold = fonte nos convênios que entram (esperado: diferenças = 0)
SELECT (SELECT SUM(vl_convenio_total) FROM gold.vw_convenio_sigcon)
        - (SELECT SUM(vl_convenio_total) FROM sigcon_convenio WHERE siafi_uo IS NOT NULL) AS dif_total,
    (SELECT SUM(vl_convenio_concedente) FROM gold.vw_convenio_sigcon)
        - (SELECT SUM(vl_convenio_concedente) FROM sigcon_convenio WHERE siafi_uo IS NOT NULL) AS dif_concedente,
    (SELECT SUM(vl_convenio_proponente) FROM gold.vw_convenio_sigcon)
        - (SELECT SUM(vl_convenio_proponente) FROM sigcon_convenio WHERE siafi_uo IS NOT NULL) AS dif_proponente;

-- 4. preenchimento dos campos de junção; informativo (nulos esperados: planos ausentes/sem código)
SELECT COUNT(*) FILTER (WHERE cd_plano_trabalho IS NULL) AS sem_cd_plano,
    COUNT(*) FILTER (WHERE cd_plano_trabalho IS NOT NULL AND nm_plano_trabalho IS NULL) AS plano_ausente_na_fonte,
    COUNT(*) FILTER (WHERE nm_uo IS NULL) AS sem_nm_uo,
    COUNT(*) FILTER (WHERE nr_cnpj_concedente IS NOT NULL AND ds_esfera_concedente IS NULL) AS concedente_sem_esfera
FROM gold.vw_convenio_sigcon;

-- 5. alerta de plano compartilhado; informativo (esperado: ~18 planos, cada um em 2+ convênios)
SELECT cd_plano_trabalho, qt_convenios_mesmo_plano, STRING_AGG(siafi_uo, '; ' ORDER BY siafi_uo) AS convenios
FROM gold.vw_convenio_sigcon
WHERE fl_plano_compartilhado
GROUP BY cd_plano_trabalho, qt_convenios_mesmo_plano
ORDER BY cd_plano_trabalho;

-- 6. todo plano da gold existe na ponte de planos (esperado: 0 linhas)
SELECT g.siafi_uo, g.cd_plano_trabalho
FROM gold.vw_convenio_sigcon g
WHERE g.cd_plano_trabalho IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM gold.vw_plano_trabalho_sigcon p
    WHERE p.siafi_uo = g.siafi_uo AND p.cd_plano_trabalho = g.cd_plano_trabalho
);
