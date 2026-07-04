BEGIN;

-- Tipos padrao permanecem globais; tenants podem criar tipos proprios.
ALTER TABLE meta.tipo_meta_voto
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS descricao VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE meta.tipo_meta_voto
    DROP CONSTRAINT IF EXISTS uq_tipo_meta_voto_codigo;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_meta_voto_codigo_global
    ON meta.tipo_meta_voto (codigo)
    WHERE tenant_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_meta_voto_codigo_tenant
    ON meta.tipo_meta_voto (tenant_id, codigo)
    WHERE tenant_id IS NOT NULL;

ALTER TABLE meta.periodo_meta
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS uq_periodo_meta_nome_tenant
    ON meta.periodo_meta (tenant_id, nome);

ALTER TABLE meta.acompanhamento_meta
    ADD COLUMN IF NOT EXISTS observacao TEXT,
    ADD COLUMN IF NOT EXISTS criado_por BIGINT REFERENCES auth.usuario(id);

ALTER TABLE meta.meta_voto
    ADD COLUMN IF NOT EXISTS score_risco NUMERIC(5,2)
        CHECK (score_risco IS NULL OR score_risco BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS fatores_risco JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS risco_calculado_em TIMESTAMPTZ;

ALTER TABLE meta.alerta_meta
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS uq_meta_voto_alvo
    ON meta.meta_voto_alvo (meta_voto_id, tipo_alvo, alvo_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_alerta_meta_aberto_tipo
    ON meta.alerta_meta (meta_voto_id, tipo_alerta)
    WHERE resolvido = FALSE;

CREATE INDEX IF NOT EXISTS ix_meta_voto_periodo_status
    ON meta.meta_voto (tenant_id, periodo_meta_id, status);

CREATE INDEX IF NOT EXISTS ix_acompanhamento_meta_data
    ON meta.acompanhamento_meta (tenant_id, meta_voto_id, data_referencia DESC);

-- Equipes eram um alvo previsto, mas nao possuíam entidade persistida.
CREATE TABLE IF NOT EXISTS cadastro.equipe (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome            VARCHAR(150) NOT NULL,
    lideranca_id    BIGINT REFERENCES cadastro.lideranca(id) ON DELETE SET NULL,
    territorio_id   BIGINT REFERENCES territorio.territorio(id) ON DELETE SET NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_equipe_nome_tenant UNIQUE (tenant_id, nome)
);

CREATE TABLE IF NOT EXISTS cadastro.equipe_pessoa (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    equipe_id   BIGINT NOT NULL REFERENCES cadastro.equipe(id) ON DELETE CASCADE,
    pessoa_id   BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_equipe_pessoa UNIQUE (equipe_id, pessoa_id)
);

CREATE INDEX IF NOT EXISTS ix_equipe_pessoa_tenant
    ON cadastro.equipe_pessoa (tenant_id, equipe_id, pessoa_id);

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON meta.tipo_meta_voto;
CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON meta.tipo_meta_voto
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON meta.periodo_meta;
CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON meta.periodo_meta
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON meta.alerta_meta;
CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON meta.alerta_meta
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON cadastro.equipe;
CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON cadastro.equipe
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

ALTER TABLE cadastro.equipe ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadastro.equipe FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pol_isolamento_tenant ON cadastro.equipe;
CREATE POLICY pol_isolamento_tenant ON cadastro.equipe
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
DROP TRIGGER IF EXISTS trg_preenche_tenant ON cadastro.equipe;
CREATE TRIGGER trg_preenche_tenant
    BEFORE INSERT ON cadastro.equipe
    FOR EACH ROW EXECUTE FUNCTION global.fn_preenche_tenant();

ALTER TABLE cadastro.equipe_pessoa ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadastro.equipe_pessoa FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pol_isolamento_tenant ON cadastro.equipe_pessoa;
CREATE POLICY pol_isolamento_tenant ON cadastro.equipe_pessoa
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
DROP TRIGGER IF EXISTS trg_preenche_tenant ON cadastro.equipe_pessoa;
CREATE TRIGGER trg_preenche_tenant
    BEFORE INSERT ON cadastro.equipe_pessoa
    FOR EACH ROW EXECUTE FUNCTION global.fn_preenche_tenant();

GRANT SELECT, INSERT, UPDATE, DELETE ON cadastro.equipe, cadastro.equipe_pessoa
    TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA cadastro TO app_inteligencia;

COMMIT;
