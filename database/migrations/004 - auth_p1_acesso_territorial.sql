BEGIN;

ALTER TABLE auth.politica_acesso_territorial
    DROP CONSTRAINT IF EXISTS ck_politica_escopo_identificador;

ALTER TABLE auth.politica_acesso_territorial
    ADD CONSTRAINT ck_politica_escopo_identificador CHECK (
        (tipo_escopo = 'global' AND num_nonnulls(
            estado_id, municipio_id, bairro_id, zona_eleitoral_id,
            secao_eleitoral_id, territorio_id
        ) = 0)
        OR
        (tipo_escopo <> 'global' AND num_nonnulls(
            estado_id, municipio_id, bairro_id, zona_eleitoral_id,
            secao_eleitoral_id, territorio_id
        ) = 1 AND
            CASE tipo_escopo
                WHEN 'estado' THEN estado_id IS NOT NULL
                WHEN 'municipio' THEN municipio_id IS NOT NULL
                WHEN 'bairro' THEN bairro_id IS NOT NULL
                WHEN 'zona_eleitoral' THEN zona_eleitoral_id IS NOT NULL
                WHEN 'secao_eleitoral' THEN secao_eleitoral_id IS NOT NULL
                WHEN 'territorio' THEN territorio_id IS NOT NULL
                ELSE FALSE
            END
        )
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_politica_acesso_territorial_escopo
    ON auth.politica_acesso_territorial (
        tenant_id,
        usuario_id,
        tipo_escopo,
        COALESCE(estado_id::BIGINT, 0),
        COALESCE(municipio_id::BIGINT, 0),
        COALESCE(bairro_id::BIGINT, 0),
        COALESCE(zona_eleitoral_id::BIGINT, 0),
        COALESCE(secao_eleitoral_id, 0),
        COALESCE(territorio_id, 0)
    );

COMMIT;
