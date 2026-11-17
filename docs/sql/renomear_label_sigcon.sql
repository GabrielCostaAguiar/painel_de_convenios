-- =====================================================================
-- Renomear o label do app SIGCON: 'convenios' -> 'sigcon'
-- Roda UMA vez, ANTES de qualquer `manage.py migrate` com o código novo.
-- Não altera tabelas de dados: só o controle interno do Django.
--
-- 1) Backup (rode no PowerShell, fora do psql):
--    pg_dump -Fc -U <usuario> -d painel_convenios -f painel_convenios_antes_label.dump
--
-- 2) Rode este script (psql -d painel_convenios -f docs/sql/renomear_label_sigcon.sql).
--    Ele termina em ROLLBACK. Confira os números e, se estiverem certos,
--    troque ROLLBACK por COMMIT e rode de novo.
-- =====================================================================

BEGIN;

-- Antes (esperado: 21 e 35 conforme o diagnóstico da fase 6)
SELECT 'django_migrations convenios' AS tabela, count(*) FROM django_migrations WHERE app = 'convenios'
UNION ALL
SELECT 'django_content_type convenios', count(*) FROM django_content_type WHERE app_label = 'convenios'
UNION ALL
SELECT 'django_migrations sigcon (deve ser 0)', count(*) FROM django_migrations WHERE app = 'sigcon'
UNION ALL
SELECT 'django_content_type sigcon (deve ser 0)', count(*) FROM django_content_type WHERE app_label = 'sigcon';

UPDATE django_migrations   SET app       = 'sigcon' WHERE app       = 'convenios';
UPDATE django_content_type SET app_label = 'sigcon' WHERE app_label = 'convenios';

-- Depois (esperado: 0 e 0 em convenios; 21 e 35 em sigcon)
SELECT 'django_migrations sigcon' AS tabela, count(*) FROM django_migrations WHERE app = 'sigcon'
UNION ALL
SELECT 'django_content_type sigcon', count(*) FROM django_content_type WHERE app_label = 'sigcon'
UNION ALL
SELECT 'restantes convenios', count(*) FROM django_migrations WHERE app = 'convenios';

ROLLBACK;
-- COMMIT;
