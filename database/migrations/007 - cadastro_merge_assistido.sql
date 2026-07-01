BEGIN;

ALTER TABLE auditoria.log_auditoria
    DROP CONSTRAINT IF EXISTS log_auditoria_acao_check;
ALTER TABLE auditoria.log_auditoria
    DROP CONSTRAINT IF EXISTS ck_log_auditoria_acao;
ALTER TABLE auditoria.log_auditoria
    ADD CONSTRAINT ck_log_auditoria_acao
    CHECK (
        acao IN (
            'criar', 'editar', 'excluir', 'acessar', 'exportar',
            'login', 'logout', 'confirmar', 'mesclar'
        )
    );

CREATE TABLE IF NOT EXISTS cadastro.pessoa_merge (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_principal_id BIGINT NOT NULL REFERENCES cadastro.pessoa(id),
    pessoa_origem_id    BIGINT NOT NULL REFERENCES cadastro.pessoa(id),
    suspeita_duplicidade_id BIGINT REFERENCES cadastro.suspeita_duplicidade(id),
    campos_origem       JSONB NOT NULL DEFAULT '[]'::jsonb,
    snapshot_principal  JSONB NOT NULL,
    snapshot_origem     JSONB NOT NULL,
    resumo_operacao     JSONB NOT NULL DEFAULT '{}'::jsonb,
    executado_por       BIGINT REFERENCES auth.usuario(id),
    executado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_pessoa_merge_distinta
        CHECK (pessoa_principal_id <> pessoa_origem_id)
);

CREATE INDEX IF NOT EXISTS ix_pessoa_merge_principal
    ON cadastro.pessoa_merge (tenant_id, pessoa_principal_id, executado_em DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pessoa_merge_origem
    ON cadastro.pessoa_merge (tenant_id, pessoa_origem_id);

ALTER TABLE cadastro.pessoa_merge ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadastro.pessoa_merge FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_isolamento_tenant ON cadastro.pessoa_merge;
CREATE POLICY pol_isolamento_tenant ON cadastro.pessoa_merge
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());

DROP TRIGGER IF EXISTS trg_preenche_tenant ON cadastro.pessoa_merge;
CREATE TRIGGER trg_preenche_tenant
    BEFORE INSERT ON cadastro.pessoa_merge
    FOR EACH ROW EXECUTE FUNCTION global.fn_preenche_tenant();

GRANT SELECT, INSERT, UPDATE, DELETE ON cadastro.pessoa_merge TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA cadastro TO app_inteligencia;

COMMIT;
