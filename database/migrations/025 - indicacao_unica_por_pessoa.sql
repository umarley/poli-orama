BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_indicacao_pessoa_indicada_tenant
    ON cadastro.indicacao (tenant_id, pessoa_indicada_id);

COMMIT;
