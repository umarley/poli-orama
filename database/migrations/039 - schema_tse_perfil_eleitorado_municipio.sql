-- Schema dedicado a dados estatisticos do TSE (Tribunal Superior Eleitoral).
-- Primeira tabela: quantidade de eleitores aptos por municipio.
-- Fonte: data/perfil_eleitorado_2026/perfil_eleitorado_2026_municipios.csv

BEGIN;

CREATE SCHEMA IF NOT EXISTS tse;

COMMENT ON SCHEMA tse IS 'Dados estatisticos oficiais do TSE: perfil do eleitorado, quantitativos por municipio e demais agregados publicos.';

CREATE TABLE tse.perfil_eleitorado_municipio (
    ano                     SMALLINT NOT NULL,
    codigo_uf_ibge          SMALLINT NOT NULL REFERENCES global.estado(codigo_ibge),
    codigo_municipio_ibge   INTEGER NOT NULL REFERENCES global.municipio(codigo_ibge),
    codigo_municipio_tse    INTEGER NOT NULL,
    uf                      CHAR(2) NOT NULL,
    municipio               VARCHAR(120) NOT NULL,
    quantidade_eleitores    INTEGER NOT NULL CHECK (quantidade_eleitores >= 0),
    carregado_em            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT perfil_eleitorado_municipio_pkey
        PRIMARY KEY (ano, codigo_municipio_ibge)
);

COMMENT ON TABLE tse.perfil_eleitorado_municipio IS
    'Quantidade de eleitores aptos a votar por municipio, conforme perfil do eleitorado publicado pelo TSE.';

COMMENT ON COLUMN tse.perfil_eleitorado_municipio.ano IS
    'Ano de referencia da eleicao / corte do perfil do eleitorado (ex.: 2026).';

COMMENT ON COLUMN tse.perfil_eleitorado_municipio.codigo_municipio_tse IS
    'Codigo do municipio no cadastro eleitoral do TSE (CD_MUNICIPIO).';

COMMENT ON COLUMN tse.perfil_eleitorado_municipio.municipio IS
    'Nome do municipio conforme publicado pelo TSE na fonte importada.';

COMMENT ON COLUMN tse.perfil_eleitorado_municipio.quantidade_eleitores IS
    'Total de eleitores aptos a votar no municipio (QT_ELEITORES agregado por municipio).';

CREATE INDEX ix_perfil_eleitorado_municipio_uf
    ON tse.perfil_eleitorado_municipio (codigo_uf_ibge);

GRANT USAGE ON SCHEMA tse TO app_inteligencia;
GRANT SELECT ON ALL TABLES IN SCHEMA tse TO app_inteligencia;
ALTER DEFAULT PRIVILEGES IN SCHEMA tse
    GRANT SELECT ON TABLES TO app_inteligencia;

COMMIT;
