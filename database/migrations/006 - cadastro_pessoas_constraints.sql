BEGIN;

-- CAD-024: registra a justificativa/observacao de vinculos familiares multiplos.
ALTER TABLE cadastro.pessoa_nucleo_familiar
    ADD COLUMN IF NOT EXISTS observacao VARCHAR(255);

-- CAD-025: comunidade pode ser associada ao territorio operacional.
ALTER TABLE cadastro.comunidade
    ADD COLUMN IF NOT EXISTS territorio_id BIGINT
        REFERENCES territorio.territorio(id) ON DELETE SET NULL;

-- CAD-043: tags podem ser inativadas sem perder os vinculos historicos.
ALTER TABLE cadastro.tag
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

-- CAD-016: o titulo eleitoral e uma identidade forte dentro do tenant.
CREATE UNIQUE INDEX IF NOT EXISTS uq_eleitor_titulo_tenant
    ON cadastro.eleitor (tenant_id, titulo_eleitor)
    WHERE titulo_eleitor IS NOT NULL;

-- Evita registrar a mesma suspeita varias vezes enquanto ela estiver pendente.
CREATE UNIQUE INDEX IF NOT EXISTS uq_suspeita_duplicidade_pendente
    ON cadastro.suspeita_duplicidade (
        tenant_id,
        LEAST(pessoa_id, pessoa_duplicada_id),
        GREATEST(pessoa_id, pessoa_duplicada_id),
        criterio
    )
    WHERE status = 'pendente';

COMMIT;
