-- Malhas desenhadas para territorios operacionais customizados e bairros.
-- area_mapa: microrregiao, comunidade e area_personalizada (1 malha por territorio).
-- bairro.limite_geom: malha desenhada para territorios tipo bairro.

BEGIN;

ALTER TABLE territorio.area_mapa
    ADD COLUMN IF NOT EXISTS territorio_id BIGINT
    REFERENCES territorio.territorio(id) ON DELETE CASCADE;

COMMENT ON COLUMN territorio.area_mapa.territorio_id IS
    'Territorio operacional dono da malha customizada desenhada no sistema.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_area_mapa_territorio
    ON territorio.area_mapa (tenant_id, territorio_id)
    WHERE territorio_id IS NOT NULL;

ALTER TABLE global.bairro
    ADD COLUMN IF NOT EXISTS limite_geom geography(MultiPolygon, 4326);

COMMENT ON COLUMN global.bairro.limite_geom IS
    'Limite geografico desenhado do bairro (WGS84), vinculado ao territorio operacional.';

CREATE INDEX IF NOT EXISTS ix_bairro_limite_geom
    ON global.bairro
    USING GIST (limite_geom);

COMMIT;
