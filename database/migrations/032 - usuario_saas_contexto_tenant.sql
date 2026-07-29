BEGIN;

ALTER TABLE auth.usuario
    ADD COLUMN IF NOT EXISTS usuario_plataforma_id BIGINT
        REFERENCES auth.usuario(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_usuario_plataforma_tenant
    ON auth.usuario (usuario_plataforma_id, tenant_id)
    WHERE usuario_plataforma_id IS NOT NULL AND excluido_em IS NULL;

COMMENT ON COLUMN auth.usuario.usuario_plataforma_id IS
    'Identidade raiz do colaborador da fornecedora para contas técnicas criadas ao acessar tenants.';

COMMIT;
