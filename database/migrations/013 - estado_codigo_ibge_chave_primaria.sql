BEGIN;

-- Adiciona as novas referencias antes de remover estado.id, preservando os dados
-- atualmente armazenados nas colunas que apontam para a chave artificial.
ALTER TABLE global.municipio
    ADD COLUMN codigo_uf_ibge SMALLINT;

ALTER TABLE global.zona_eleitoral
    ADD COLUMN codigo_uf_ibge SMALLINT;

ALTER TABLE global.data_comemorativa
    ADD COLUMN codigo_uf_ibge SMALLINT;

ALTER TABLE auth.politica_acesso_territorial
    ADD COLUMN codigo_uf_ibge SMALLINT;

ALTER TABLE territorio.territorio
    ADD COLUMN codigo_uf_ibge SMALLINT;

ALTER TABLE eleicao.eleicao
    ADD COLUMN codigo_uf_ibge SMALLINT;

ALTER TABLE dw.perfil_eleitorado_tse
    ADD COLUMN codigo_uf_ibge SMALLINT;

ALTER TABLE dw.perfil_eleitorado_secao_tse
    ADD COLUMN codigo_uf_ibge SMALLINT;

UPDATE global.municipio AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.estado_id = estado.id;

UPDATE global.zona_eleitoral AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.estado_id = estado.id;

UPDATE global.data_comemorativa AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.estado_id = estado.id;

UPDATE auth.politica_acesso_territorial AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.estado_id = estado.id;

UPDATE territorio.territorio AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.estado_id = estado.id;

UPDATE eleicao.eleicao AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.escopo_uf_id = estado.id;

UPDATE dw.perfil_eleitorado_tse AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.estado_id = estado.id;

UPDATE dw.perfil_eleitorado_secao_tse AS destino
SET codigo_uf_ibge = estado.codigo_ibge
FROM global.estado AS estado
WHERE destino.estado_id = estado.id;

-- As duas referencias originalmente obrigatorias continuam obrigatorias.
ALTER TABLE global.municipio
    ALTER COLUMN codigo_uf_ibge SET NOT NULL;

ALTER TABLE global.zona_eleitoral
    ALTER COLUMN codigo_uf_ibge SET NOT NULL;

-- Remove todas as FKs que dependem de global.estado(id).
ALTER TABLE global.municipio
    DROP CONSTRAINT IF EXISTS municipio_estado_id_fkey;

ALTER TABLE global.zona_eleitoral
    DROP CONSTRAINT IF EXISTS zona_eleitoral_estado_id_fkey;

ALTER TABLE global.data_comemorativa
    DROP CONSTRAINT IF EXISTS data_comemorativa_estado_id_fkey;

ALTER TABLE auth.politica_acesso_territorial
    DROP CONSTRAINT IF EXISTS politica_acesso_territorial_estado_id_fkey;

ALTER TABLE territorio.territorio
    DROP CONSTRAINT IF EXISTS territorio_estado_id_fkey;

ALTER TABLE eleicao.eleicao
    DROP CONSTRAINT IF EXISTS eleicao_escopo_uf_id_fkey;

ALTER TABLE dw.perfil_eleitorado_tse
    DROP CONSTRAINT IF EXISTS perfil_eleitorado_tse_estado_id_fkey;

ALTER TABLE dw.perfil_eleitorado_secao_tse
    DROP CONSTRAINT IF EXISTS perfil_eleitorado_secao_tse_estado_id_fkey;

-- Recria objetos que continham as colunas antigas.
ALTER TABLE global.zona_eleitoral
    DROP CONSTRAINT uq_zona_eleitoral;

ALTER TABLE auth.politica_acesso_territorial
    DROP CONSTRAINT ck_politica_escopo_identificador;

DROP INDEX auth.uq_politica_acesso_territorial_escopo;

DROP INDEX dw.ix_perfil_eleitorado_tse_dim;

ALTER TABLE global.municipio
    DROP COLUMN estado_id;

ALTER TABLE global.zona_eleitoral
    DROP COLUMN estado_id;

ALTER TABLE global.data_comemorativa
    DROP COLUMN estado_id;

ALTER TABLE auth.politica_acesso_territorial
    DROP COLUMN estado_id;

ALTER TABLE territorio.territorio
    DROP COLUMN estado_id;

ALTER TABLE eleicao.eleicao
    DROP COLUMN escopo_uf_id;

ALTER TABLE dw.perfil_eleitorado_tse
    DROP COLUMN estado_id;

ALTER TABLE dw.perfil_eleitorado_secao_tse
    DROP COLUMN estado_id;

-- Substitui a chave artificial pela chave oficial do IBGE.
ALTER TABLE global.estado
    DROP CONSTRAINT estado_pkey;

ALTER TABLE global.estado
    DROP CONSTRAINT uq_estado_codigo_ibge;

ALTER TABLE global.estado
    DROP COLUMN id;

ALTER TABLE global.estado
    ADD CONSTRAINT estado_pkey PRIMARY KEY (codigo_ibge);

-- Cria as novas FKs somente depois de codigo_ibge tornar-se a chave primaria.
ALTER TABLE global.municipio
    ADD CONSTRAINT municipio_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE global.zona_eleitoral
    ADD CONSTRAINT zona_eleitoral_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE global.data_comemorativa
    ADD CONSTRAINT data_comemorativa_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE auth.politica_acesso_territorial
    ADD CONSTRAINT politica_acesso_territorial_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE territorio.territorio
    ADD CONSTRAINT territorio_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE eleicao.eleicao
    ADD CONSTRAINT eleicao_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE dw.perfil_eleitorado_tse
    ADD CONSTRAINT perfil_eleitorado_tse_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE dw.perfil_eleitorado_secao_tse
    ADD CONSTRAINT perfil_eleitorado_secao_tse_codigo_uf_ibge_fkey
    FOREIGN KEY (codigo_uf_ibge) REFERENCES global.estado(codigo_ibge);

ALTER TABLE global.zona_eleitoral
    ADD CONSTRAINT uq_zona_eleitoral
    UNIQUE (codigo_uf_ibge, numero_zona);

ALTER TABLE auth.politica_acesso_territorial
    ADD CONSTRAINT ck_politica_escopo_identificador CHECK (
        (tipo_escopo = 'global' AND num_nonnulls(
            codigo_uf_ibge, municipio_id, bairro_id, zona_eleitoral_id,
            secao_eleitoral_id, territorio_id
        ) = 0)
        OR
        (tipo_escopo <> 'global' AND num_nonnulls(
            codigo_uf_ibge, municipio_id, bairro_id, zona_eleitoral_id,
            secao_eleitoral_id, territorio_id
        ) = 1 AND
            CASE tipo_escopo
                WHEN 'estado' THEN codigo_uf_ibge IS NOT NULL
                WHEN 'municipio' THEN municipio_id IS NOT NULL
                WHEN 'bairro' THEN bairro_id IS NOT NULL
                WHEN 'zona_eleitoral' THEN zona_eleitoral_id IS NOT NULL
                WHEN 'secao_eleitoral' THEN secao_eleitoral_id IS NOT NULL
                WHEN 'territorio' THEN territorio_id IS NOT NULL
                ELSE FALSE
            END
        )
    );

CREATE UNIQUE INDEX uq_politica_acesso_territorial_escopo
    ON auth.politica_acesso_territorial (
        tenant_id,
        usuario_id,
        tipo_escopo,
        COALESCE(codigo_uf_ibge::BIGINT, 0),
        COALESCE(municipio_id::BIGINT, 0),
        COALESCE(bairro_id::BIGINT, 0),
        COALESCE(zona_eleitoral_id::BIGINT, 0),
        COALESCE(secao_eleitoral_id, 0),
        COALESCE(territorio_id, 0)
    );

CREATE INDEX ix_perfil_eleitorado_tse_dim
    ON dw.perfil_eleitorado_tse
    (ano, codigo_uf_ibge, municipio_id, zona_eleitoral_id);

COMMIT;
