-- Carga bruta de votacao por secao eleitoral (TSE / dados abertos).
-- Fonte: data/resultados-eleicoes/*.csv
-- Campos nao informados no CSV (#NE, #NULO#, -1, -3) sao gravados como NULL.

BEGIN;

CREATE TABLE tse.resultados_eleicoes (
    id                          BIGSERIAL PRIMARY KEY,
    aa_eleicao                  SMALLINT,
    cd_tipo_eleicao             SMALLINT,
    nm_tipo_eleicao             VARCHAR(80),
    cd_eleicao                  INTEGER,
    ds_eleicao                  VARCHAR(150),
    dt_eleicao                  TIMESTAMP,
    sg_uf                       CHAR(2),
    cd_municipio                INTEGER,
    nm_municipio                VARCHAR(120),
    nr_zona                     SMALLINT,
    nm_local_votacao            VARCHAR(200),
    ds_local_votacao_endereco   VARCHAR(300),
    nr_secao                    SMALLINT,
    nr_local_votacao            INTEGER,
    cd_modelo_urna              INTEGER,
    ds_modelo_urna              VARCHAR(80),
    nr_turno                    SMALLINT,
    ds_cargo                    VARCHAR(80),
    nr_votavel                  INTEGER,
    nm_votavel                  VARCHAR(200),
    sq_candidato                BIGINT,
    qt_aptos                    INTEGER,
    qt_comparecimento           INTEGER,
    qt_abstencoes               INTEGER,
    qt_votos_nominais           INTEGER,
    qt_votos                    INTEGER,
    dt_carga                    TIMESTAMP,
    qt_registros                INTEGER,
    carregado_em                TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT resultados_eleicoes_uk UNIQUE NULLS NOT DISTINCT (
        aa_eleicao,
        cd_eleicao,
        nr_turno,
        sg_uf,
        cd_municipio,
        nr_zona,
        nr_secao,
        ds_cargo,
        nr_votavel
    )
);

COMMENT ON TABLE tse.resultados_eleicoes IS
    'Carga bruta de votacao por secao eleitoral, com os mesmos campos do CSV TSE (votacao_secao). Valores nao informados (#NE, #NULO#, -1, -3) ficam NULL.';

COMMENT ON COLUMN tse.resultados_eleicoes.aa_eleicao IS
    'Ano da eleicao (AA_ELEICAO).';

COMMENT ON COLUMN tse.resultados_eleicoes.cd_tipo_eleicao IS
    'Codigo do tipo de eleicao (CD_TIPO_ELEICAO).';

COMMENT ON COLUMN tse.resultados_eleicoes.nm_tipo_eleicao IS
    'Nome do tipo de eleicao (NM_TIPO_ELEICAO).';

COMMENT ON COLUMN tse.resultados_eleicoes.cd_eleicao IS
    'Codigo da eleicao (CD_ELEICAO).';

COMMENT ON COLUMN tse.resultados_eleicoes.ds_eleicao IS
    'Descricao da eleicao (DS_ELEICAO).';

COMMENT ON COLUMN tse.resultados_eleicoes.dt_eleicao IS
    'Data da eleicao (DT_ELEICAO).';

COMMENT ON COLUMN tse.resultados_eleicoes.sg_uf IS
    'Sigla da unidade da federacao (SG_UF).';

COMMENT ON COLUMN tse.resultados_eleicoes.cd_municipio IS
    'Codigo TSE do municipio (CD_MUNICIPIO).';

COMMENT ON COLUMN tse.resultados_eleicoes.nm_municipio IS
    'Nome do municipio conforme o CSV (NM_MUNICIPIO).';

COMMENT ON COLUMN tse.resultados_eleicoes.nr_zona IS
    'Numero da zona eleitoral (NR_ZONA).';

COMMENT ON COLUMN tse.resultados_eleicoes.nm_local_votacao IS
    'Nome do local de votacao (NM_LOCAL_VOTACAO). NULL quando o CSV traz #NE ou equivalente.';

COMMENT ON COLUMN tse.resultados_eleicoes.ds_local_votacao_endereco IS
    'Endereco do local de votacao (DS_LOCAL_VOTACAO_ENDERECO). NULL quando o CSV traz #NE, #NULO# ou equivalente.';

COMMENT ON COLUMN tse.resultados_eleicoes.nr_secao IS
    'Numero da secao eleitoral (NR_SECAO).';

COMMENT ON COLUMN tse.resultados_eleicoes.nr_local_votacao IS
    'Codigo do local de votacao (NR_LOCAL_VOTACAO). NULL quando o CSV traz -3, #NE ou equivalente.';

COMMENT ON COLUMN tse.resultados_eleicoes.cd_modelo_urna IS
    'Codigo do modelo da urna (CD_MODELO_URNA). NULL quando o CSV traz -1, #NE ou equivalente.';

COMMENT ON COLUMN tse.resultados_eleicoes.ds_modelo_urna IS
    'Descricao do modelo da urna (DS_MODELO_URNA). NULL quando o CSV traz #NE, #NULO# ou equivalente.';

COMMENT ON COLUMN tse.resultados_eleicoes.nr_turno IS
    'Numero do turno (NR_TURNO).';

COMMENT ON COLUMN tse.resultados_eleicoes.ds_cargo IS
    'Descricao do cargo (DS_CARGO).';

COMMENT ON COLUMN tse.resultados_eleicoes.nr_votavel IS
    'Numero do votavel (candidato, partido, branco ou nulo) (NR_VOTAVEL).';

COMMENT ON COLUMN tse.resultados_eleicoes.nm_votavel IS
    'Nome do votavel (NM_VOTAVEL).';

COMMENT ON COLUMN tse.resultados_eleicoes.sq_candidato IS
    'Sequencial do candidato no TSE (SQ_CANDIDATO). NULL quando o CSV traz -1 ou equivalente.';

COMMENT ON COLUMN tse.resultados_eleicoes.qt_aptos IS
    'Quantidade de eleitores aptos na secao (QT_APTOS).';

COMMENT ON COLUMN tse.resultados_eleicoes.qt_comparecimento IS
    'Quantidade de comparecimentos na secao (QT_COMPARECIMENTO).';

COMMENT ON COLUMN tse.resultados_eleicoes.qt_abstencoes IS
    'Quantidade de abstencoes na secao (QT_ABSTENCOES).';

COMMENT ON COLUMN tse.resultados_eleicoes.qt_votos_nominais IS
    'Quantidade de votos nominais na secao (QT_VOTOS_NOMINAIS).';

COMMENT ON COLUMN tse.resultados_eleicoes.qt_votos IS
    'Quantidade de votos do votavel na secao (QT_VOTOS).';

COMMENT ON COLUMN tse.resultados_eleicoes.dt_carga IS
    'Data de carga do registro na fonte TSE (DT_CARGA).';

COMMENT ON COLUMN tse.resultados_eleicoes.qt_registros IS
    'Quantidade de registros agregados na fonte (QT_REGISTROS).';

COMMENT ON COLUMN tse.resultados_eleicoes.carregado_em IS
    'Data e hora em que o registro foi gravado nesta base.';

CREATE INDEX ix_resultados_eleicoes_municipio
    ON tse.resultados_eleicoes (aa_eleicao, sg_uf, cd_municipio);

CREATE INDEX ix_resultados_eleicoes_secao
    ON tse.resultados_eleicoes (cd_municipio, nr_zona, nr_secao);

CREATE INDEX ix_resultados_eleicoes_votavel
    ON tse.resultados_eleicoes (aa_eleicao, ds_cargo, nr_votavel);

GRANT SELECT ON tse.resultados_eleicoes TO app_inteligencia;

COMMIT;
