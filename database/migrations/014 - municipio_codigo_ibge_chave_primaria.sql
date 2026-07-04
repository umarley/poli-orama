BEGIN;

-- Adiciona as novas referencias antes de remover global.municipio.id,
-- preservando os dados atualmente armazenados nas chaves artificiais.
ALTER TABLE global.bairro
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE global.zona_eleitoral
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE global.local_votacao
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE global.data_comemorativa
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE auth.politica_acesso_territorial
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE cadastro.endereco
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE cadastro.eleitor
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE cadastro.comunidade
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE territorio.territorio
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE agenda.evento
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE demanda.demanda
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE meta.meta_voto
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE eleicao.eleicao
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE dw.perfil_eleitorado_tse
    ADD COLUMN codigo_municipio_ibge INTEGER;

ALTER TABLE dw.perfil_eleitorado_secao_tse
    ADD COLUMN codigo_municipio_ibge INTEGER;

UPDATE global.bairro AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE global.zona_eleitoral AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE global.local_votacao AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE global.data_comemorativa AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE auth.politica_acesso_territorial AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE cadastro.endereco AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE cadastro.eleitor AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_voto_id = municipio.id;

UPDATE cadastro.comunidade AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE territorio.territorio AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE agenda.evento AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE demanda.demanda AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE meta.meta_voto AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE eleicao.eleicao AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.escopo_municipio_id = municipio.id;

UPDATE dw.perfil_eleitorado_tse AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

UPDATE dw.perfil_eleitorado_secao_tse AS destino
SET codigo_municipio_ibge = municipio.codigo_ibge
FROM global.municipio AS municipio
WHERE destino.municipio_id = municipio.id;

-- As duas referencias originalmente obrigatorias continuam obrigatorias.
ALTER TABLE global.bairro
    ALTER COLUMN codigo_municipio_ibge SET NOT NULL;

ALTER TABLE global.local_votacao
    ALTER COLUMN codigo_municipio_ibge SET NOT NULL;

-- Remove todas as FKs que dependem de global.municipio(id).
ALTER TABLE global.bairro
    DROP CONSTRAINT IF EXISTS bairro_municipio_id_fkey;

ALTER TABLE global.zona_eleitoral
    DROP CONSTRAINT IF EXISTS zona_eleitoral_municipio_id_fkey;

ALTER TABLE global.local_votacao
    DROP CONSTRAINT IF EXISTS local_votacao_municipio_id_fkey;

ALTER TABLE global.data_comemorativa
    DROP CONSTRAINT IF EXISTS data_comemorativa_municipio_id_fkey;

ALTER TABLE auth.politica_acesso_territorial
    DROP CONSTRAINT IF EXISTS politica_acesso_territorial_municipio_id_fkey;

ALTER TABLE cadastro.endereco
    DROP CONSTRAINT IF EXISTS endereco_municipio_id_fkey;

ALTER TABLE cadastro.eleitor
    DROP CONSTRAINT IF EXISTS eleitor_municipio_voto_id_fkey;

ALTER TABLE cadastro.comunidade
    DROP CONSTRAINT IF EXISTS comunidade_municipio_id_fkey;

ALTER TABLE territorio.territorio
    DROP CONSTRAINT IF EXISTS territorio_municipio_id_fkey;

ALTER TABLE agenda.evento
    DROP CONSTRAINT IF EXISTS evento_municipio_id_fkey;

ALTER TABLE demanda.demanda
    DROP CONSTRAINT IF EXISTS demanda_municipio_id_fkey;

ALTER TABLE meta.meta_voto
    DROP CONSTRAINT IF EXISTS meta_voto_municipio_id_fkey;

ALTER TABLE eleicao.eleicao
    DROP CONSTRAINT IF EXISTS eleicao_escopo_municipio_id_fkey;

ALTER TABLE dw.perfil_eleitorado_tse
    DROP CONSTRAINT IF EXISTS perfil_eleitorado_tse_municipio_id_fkey;

ALTER TABLE dw.perfil_eleitorado_secao_tse
    DROP CONSTRAINT IF EXISTS perfil_eleitorado_secao_tse_municipio_id_fkey;

-- Remove objetos que dependem das colunas antigas para recria-los em seguida.
ALTER TABLE global.bairro
    DROP CONSTRAINT uq_bairro_municipio_nome;

ALTER TABLE global.local_votacao
    DROP CONSTRAINT uq_local_votacao;

ALTER TABLE auth.politica_acesso_territorial
    DROP CONSTRAINT ck_politica_escopo_identificador;

DROP INDEX auth.uq_politica_acesso_territorial_escopo;
DROP INDEX cadastro.ix_endereco_municipio;
DROP INDEX dw.ix_perfil_eleitorado_tse_dim;

ALTER TABLE global.bairro
    DROP COLUMN municipio_id;

ALTER TABLE global.zona_eleitoral
    DROP COLUMN municipio_id;

ALTER TABLE global.local_votacao
    DROP COLUMN municipio_id;

ALTER TABLE global.data_comemorativa
    DROP COLUMN municipio_id;

ALTER TABLE auth.politica_acesso_territorial
    DROP COLUMN municipio_id;

ALTER TABLE cadastro.endereco
    DROP COLUMN municipio_id;

ALTER TABLE cadastro.eleitor
    DROP COLUMN municipio_voto_id;

ALTER TABLE cadastro.comunidade
    DROP COLUMN municipio_id;

ALTER TABLE territorio.territorio
    DROP COLUMN municipio_id;

ALTER TABLE agenda.evento
    DROP COLUMN municipio_id;

ALTER TABLE demanda.demanda
    DROP COLUMN municipio_id;

ALTER TABLE meta.meta_voto
    DROP COLUMN municipio_id;

ALTER TABLE eleicao.eleicao
    DROP COLUMN escopo_municipio_id;

ALTER TABLE dw.perfil_eleitorado_tse
    DROP COLUMN municipio_id;

ALTER TABLE dw.perfil_eleitorado_secao_tse
    DROP COLUMN municipio_id;

-- Substitui a chave artificial pela chave oficial do IBGE.
ALTER TABLE global.municipio
    DROP CONSTRAINT municipio_pkey;

ALTER TABLE global.municipio
    DROP CONSTRAINT uq_municipio_codigo_ibge;

ALTER TABLE global.municipio
    DROP COLUMN id;

ALTER TABLE global.municipio
    ADD CONSTRAINT municipio_pkey PRIMARY KEY (codigo_ibge);

-- Cria as novas FKs somente depois de codigo_ibge tornar-se a chave primaria.
ALTER TABLE global.bairro
    ADD CONSTRAINT bairro_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE global.zona_eleitoral
    ADD CONSTRAINT zona_eleitoral_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE global.local_votacao
    ADD CONSTRAINT local_votacao_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE global.data_comemorativa
    ADD CONSTRAINT data_comemorativa_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE auth.politica_acesso_territorial
    ADD CONSTRAINT politica_acesso_territorial_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE cadastro.endereco
    ADD CONSTRAINT endereco_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE cadastro.eleitor
    ADD CONSTRAINT eleitor_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE cadastro.comunidade
    ADD CONSTRAINT comunidade_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE territorio.territorio
    ADD CONSTRAINT territorio_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE agenda.evento
    ADD CONSTRAINT evento_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE demanda.demanda
    ADD CONSTRAINT demanda_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE meta.meta_voto
    ADD CONSTRAINT meta_voto_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE eleicao.eleicao
    ADD CONSTRAINT eleicao_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE dw.perfil_eleitorado_tse
    ADD CONSTRAINT perfil_eleitorado_tse_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE dw.perfil_eleitorado_secao_tse
    ADD CONSTRAINT perfil_eleitorado_secao_tse_codigo_municipio_ibge_fkey
    FOREIGN KEY (codigo_municipio_ibge)
    REFERENCES global.municipio(codigo_ibge);

ALTER TABLE global.bairro
    ADD CONSTRAINT uq_bairro_municipio_nome
    UNIQUE (codigo_municipio_ibge, nome);

ALTER TABLE global.local_votacao
    ADD CONSTRAINT uq_local_votacao
    UNIQUE (codigo_municipio_ibge, zona_eleitoral_id, codigo_local);

ALTER TABLE auth.politica_acesso_territorial
    ADD CONSTRAINT ck_politica_escopo_identificador CHECK (
        (tipo_escopo = 'global' AND num_nonnulls(
            codigo_uf_ibge, codigo_municipio_ibge, bairro_id,
            zona_eleitoral_id, secao_eleitoral_id, territorio_id
        ) = 0)
        OR
        (tipo_escopo <> 'global' AND num_nonnulls(
            codigo_uf_ibge, codigo_municipio_ibge, bairro_id,
            zona_eleitoral_id, secao_eleitoral_id, territorio_id
        ) = 1 AND
            CASE tipo_escopo
                WHEN 'estado' THEN codigo_uf_ibge IS NOT NULL
                WHEN 'municipio' THEN codigo_municipio_ibge IS NOT NULL
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
        COALESCE(codigo_municipio_ibge::BIGINT, 0),
        COALESCE(bairro_id::BIGINT, 0),
        COALESCE(zona_eleitoral_id::BIGINT, 0),
        COALESCE(secao_eleitoral_id, 0),
        COALESCE(territorio_id, 0)
    );

CREATE INDEX ix_endereco_municipio
    ON cadastro.endereco (codigo_municipio_ibge);

CREATE INDEX ix_perfil_eleitorado_tse_dim
    ON dw.perfil_eleitorado_tse
    (ano, codigo_uf_ibge, codigo_municipio_ibge, zona_eleitoral_id);

COMMIT;
