-- Schema gold (compartilhado por todos os apps).
-- Aplicar UMA vez, antes das views de qualquer app. Idempotente: nunca derruba nada.
-- Não use DROP SCHEMA aqui: o CASCADE apagaria as views de todos os apps.
CREATE SCHEMA IF NOT EXISTS gold;
