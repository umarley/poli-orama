BEGIN;

ALTER TABLE auth.sessao_usuario
    DROP CONSTRAINT IF EXISTS sessao_usuario_origem_login_check;

ALTER TABLE auth.sessao_usuario
    ADD CONSTRAINT sessao_usuario_origem_login_check
    CHECK (origem_login IN ('web', 'app_lider', 'pwa_lider'));

COMMENT ON COLUMN auth.sessao_usuario.origem_login IS
    'Canal de origem. pwa_lider usa cookie HttpOnly e permanece valido ate a expiracao absoluta ou revogacao.';

COMMIT;
