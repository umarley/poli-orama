-- SOMENTE PARA AMBIENTE DE DESENVOLVIMENTO.
-- Define a senha TroqueAgora#2026 para todos os usuarios.
--
-- Hash Argon2id gerado com os mesmos parametros do backend:
--   memory_cost=65536, time_cost=3, parallelism=4
--
-- Nao execute este script em producao.

BEGIN;

UPDATE auth.usuario
SET hash_senha = '$argon2id$v=19$m=65536,t=3,p=4$k9GbqcL7ytGJxJ2e1ooVrg$ihtXonLIXu9E7OrIXsDFUNMof/jfaZVbbVcibXZVddM',
    senha_alterada_em = now(),
    deve_alterar_senha = FALSE,
    tentativas_login = 0,
    atualizado_em = now();

COMMIT;
