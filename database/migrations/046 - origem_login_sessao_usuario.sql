BEGIN;

ALTER TABLE auth.sessao_usuario
    ADD COLUMN IF NOT EXISTS origem_login VARCHAR(20) NOT NULL DEFAULT 'web';

ALTER TABLE auth.sessao_usuario
    DROP CONSTRAINT IF EXISTS sessao_usuario_origem_login_check;

ALTER TABLE auth.sessao_usuario
    ADD CONSTRAINT sessao_usuario_origem_login_check
    CHECK (origem_login IN ('web', 'app_lider'));

COMMENT ON COLUMN auth.sessao_usuario.origem_login IS
    'Canal que originou a sessao. app_lider ativa as restricoes operacionais do aplicativo mobile.';

COMMIT;
