BEGIN;

ALTER TABLE auth.sessao_usuario
    ADD COLUMN IF NOT EXISTS ultimo_uso_em TIMESTAMPTZ;

UPDATE auth.sessao_usuario
SET ultimo_uso_em = criado_em
WHERE ultimo_uso_em IS NULL;

ALTER TABLE auth.sessao_usuario
    ALTER COLUMN ultimo_uso_em SET DEFAULT now(),
    ALTER COLUMN ultimo_uso_em SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_sessao_usuario_historico
    ON auth.sessao_usuario (tenant_id, usuario_id, criado_em DESC);

COMMIT;
