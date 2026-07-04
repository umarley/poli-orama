BEGIN;

-- Tipos padrao continuam globais; tipos personalizados pertencem ao tenant.
ALTER TABLE territorio.tipo_territorio
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE territorio.tipo_territorio
    DROP CONSTRAINT IF EXISTS uq_tipo_territorio_codigo;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_territorio_codigo_global
    ON territorio.tipo_territorio (codigo)
    WHERE tenant_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_territorio_codigo_tenant
    ON territorio.tipo_territorio (tenant_id, codigo)
    WHERE tenant_id IS NOT NULL;

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON territorio.tipo_territorio;
CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON territorio.tipo_territorio
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

-- Uma arvore possui no maximo um pai direto por territorio.
CREATE UNIQUE INDEX IF NOT EXISTS uq_territorio_hierarquia_filho_tenant
    ON territorio.territorio_hierarquia (tenant_id, territorio_filho_id);

CREATE INDEX IF NOT EXISTS ix_territorio_hierarquia_pai
    ON territorio.territorio_hierarquia (tenant_id, territorio_pai_id);

CREATE INDEX IF NOT EXISTS ix_pessoa_territorio_consulta
    ON territorio.pessoa_territorio (tenant_id, territorio_id, pessoa_id);

CREATE INDEX IF NOT EXISTS ix_lideranca_territorio_consulta
    ON territorio.lideranca_territorio (tenant_id, territorio_id, lideranca_id);

-- Mantem o ponto PostGIS sincronizado quando coordenadas manuais forem informadas.
CREATE OR REPLACE FUNCTION territorio.fn_sincroniza_ponto_geografico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    ELSE
        NEW.geom := NULL;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sincroniza_ponto ON cadastro.endereco;
CREATE TRIGGER trg_sincroniza_ponto
    BEFORE INSERT OR UPDATE OF latitude, longitude ON cadastro.endereco
    FOR EACH ROW EXECUTE FUNCTION territorio.fn_sincroniza_ponto_geografico();

DROP TRIGGER IF EXISTS trg_sincroniza_ponto ON territorio.geocodificacao;
CREATE TRIGGER trg_sincroniza_ponto
    BEFORE INSERT OR UPDATE OF latitude, longitude ON territorio.geocodificacao
    FOR EACH ROW EXECUTE FUNCTION territorio.fn_sincroniza_ponto_geografico();

COMMIT;
