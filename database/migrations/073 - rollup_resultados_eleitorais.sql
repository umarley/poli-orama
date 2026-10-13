-- Rollups versionados dos resultados eleitorais. A tabela bruta
-- tse.resultados_eleicoes continua sendo a fonte de verdade.
BEGIN;

CREATE SEQUENCE tse.resultado_rollup_generation_seq AS BIGINT;

CREATE TABLE tse.resultado_rollup_controle (
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    status              VARCHAR(16) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'refreshing', 'ready')),
    active_generation   BIGINT,
    solicitado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    iniciado_em         TIMESTAMPTZ,
    concluido_em        TIMESTAMPTZ,
    ultima_mensagem     TEXT,
    PRIMARY KEY (aa_eleicao, cd_eleicao, nr_turno)
);

CREATE TABLE tse.resultado_rollup_catalogo (
    generation          BIGINT NOT NULL,
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    ds_cargo            VARCHAR(80) NOT NULL,
    ds_eleicao          VARCHAR(150),
    dt_eleicao          TIMESTAMP,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo)
);

CREATE TABLE tse.resultado_rollup_localidade (
    generation          BIGINT NOT NULL,
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    cd_municipio        INTEGER NOT NULL,
    nm_municipio        VARCHAR(120),
    nr_zona             SMALLINT NOT NULL,
    nr_local_votacao    INTEGER,
    nm_local_votacao    VARCHAR(200),
    ds_local_votacao_endereco VARCHAR(300),
    nr_secao            SMALLINT NOT NULL,
    PRIMARY KEY (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
        cd_municipio, nr_zona, nr_secao
    )
);

CREATE TABLE tse.resultado_rollup_municipio_candidato (
    generation          BIGINT NOT NULL,
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    cd_municipio        INTEGER NOT NULL,
    ds_cargo            VARCHAR(80) NOT NULL,
    nr_votavel          INTEGER NOT NULL,
    nm_votavel          VARCHAR(200),
    sq_candidato        BIGINT,
    qt_votos            BIGINT NOT NULL CHECK (qt_votos >= 0),
    PRIMARY KEY (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
        cd_municipio, ds_cargo, nr_votavel
    )
);

CREATE TABLE tse.resultado_rollup_zona_candidato (
    generation          BIGINT NOT NULL,
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    cd_municipio        INTEGER NOT NULL,
    nr_zona             SMALLINT NOT NULL,
    ds_cargo            VARCHAR(80) NOT NULL,
    nr_votavel          INTEGER NOT NULL,
    nm_votavel          VARCHAR(200),
    sq_candidato        BIGINT,
    qt_votos            BIGINT NOT NULL CHECK (qt_votos >= 0),
    PRIMARY KEY (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
        cd_municipio, nr_zona, ds_cargo, nr_votavel
    )
);

CREATE TABLE tse.resultado_rollup_local_candidato (
    generation          BIGINT NOT NULL,
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    cd_municipio        INTEGER NOT NULL,
    nr_zona             SMALLINT NOT NULL,
    nr_local_votacao    INTEGER NOT NULL,
    ds_cargo            VARCHAR(80) NOT NULL,
    nr_votavel          INTEGER NOT NULL,
    nm_votavel          VARCHAR(200),
    sq_candidato        BIGINT,
    qt_votos            BIGINT NOT NULL CHECK (qt_votos >= 0),
    PRIMARY KEY (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
        cd_municipio, nr_zona, nr_local_votacao, ds_cargo, nr_votavel
    )
);

CREATE TABLE tse.resultado_rollup_secao_candidato (
    generation          BIGINT NOT NULL,
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    cd_municipio        INTEGER NOT NULL,
    nr_zona             SMALLINT NOT NULL,
    nr_local_votacao    INTEGER NOT NULL,
    nr_secao            SMALLINT NOT NULL,
    ds_cargo            VARCHAR(80) NOT NULL,
    nr_votavel          INTEGER NOT NULL,
    nm_votavel          VARCHAR(200),
    sq_candidato        BIGINT,
    qt_votos            BIGINT NOT NULL CHECK (qt_votos >= 0),
    PRIMARY KEY (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
        cd_municipio, nr_zona, nr_local_votacao, nr_secao,
        ds_cargo, nr_votavel
    )
);

-- As tabelas estao vazias durante a migration; indices normais evitam a
-- restricao do runner para CREATE INDEX CONCURRENTLY dentro de BEGIN.
CREATE INDEX ix_resultado_rollup_controle_pending
    ON tse.resultado_rollup_controle (solicitado_em)
    WHERE status = 'pending';
CREATE INDEX ix_resultado_rollup_catalogo_eleicao
    ON tse.resultado_rollup_catalogo
       (aa_eleicao, cd_eleicao, nr_turno, generation, sg_uf, ds_cargo);
CREATE INDEX ix_resultado_rollup_localidade_busca
    ON tse.resultado_rollup_localidade
       (aa_eleicao, cd_eleicao, nr_turno, generation, sg_uf, cd_municipio, nr_zona);
CREATE INDEX ix_resultado_rollup_municipio_busca
    ON tse.resultado_rollup_municipio_candidato
       (aa_eleicao, cd_eleicao, nr_turno, generation, ds_cargo, nr_votavel);
CREATE INDEX ix_resultado_rollup_zona_busca
    ON tse.resultado_rollup_zona_candidato
       (aa_eleicao, cd_eleicao, nr_turno, generation, sg_uf, cd_municipio, nr_zona);
CREATE INDEX ix_resultado_rollup_local_busca
    ON tse.resultado_rollup_local_candidato
       (aa_eleicao, cd_eleicao, nr_turno, generation, sg_uf, cd_municipio, nr_zona);
CREATE INDEX ix_resultado_rollup_secao_busca
    ON tse.resultado_rollup_secao_candidato
       (aa_eleicao, cd_eleicao, nr_turno, generation, sg_uf,
        cd_municipio, nr_zona, nr_local_votacao, nr_secao);

CREATE OR REPLACE FUNCTION tse.fn_refresh_resultado_rollup(
    p_aa_eleicao SMALLINT,
    p_cd_eleicao INTEGER,
    p_nr_turno SMALLINT
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, tse
AS $$
DECLARE
    v_generation BIGINT := nextval('tse.resultado_rollup_generation_seq');
    v_old_generation BIGINT;
    v_source_votes BIGINT;
    v_rollup_votes BIGINT;
BEGIN
    SELECT active_generation
      INTO v_old_generation
      FROM tse.resultado_rollup_controle
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'chave de rollup nao cadastrada: (%, %, %)',
            p_aa_eleicao, p_cd_eleicao, p_nr_turno;
    END IF;

    UPDATE tse.resultado_rollup_controle
       SET status = 'refreshing', iniciado_em = clock_timestamp(), ultima_mensagem = NULL
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno;

    SELECT COALESCE(SUM(qt_votos), 0)
      INTO v_source_votes
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno;

    INSERT INTO tse.resultado_rollup_catalogo (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo,
        ds_eleicao, dt_eleicao
    )
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo,
           MAX(ds_eleicao), MAX(dt_eleicao)
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo;

    INSERT INTO tse.resultado_rollup_localidade (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
        nm_municipio, nr_zona, nr_local_votacao, nm_local_votacao,
        ds_local_votacao_endereco, nr_secao
    )
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           MAX(nm_municipio), nr_zona, MAX(nr_local_votacao),
           MAX(nm_local_votacao), MAX(ds_local_votacao_endereco), nr_secao
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nr_zona, nr_secao;

    INSERT INTO tse.resultado_rollup_municipio_candidato
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           ds_cargo, nr_votavel, MAX(nm_votavel), MAX(sq_candidato),
           SUM(COALESCE(qt_votos, 0))
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
              ds_cargo, nr_votavel;

    INSERT INTO tse.resultado_rollup_zona_candidato
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           nr_zona, ds_cargo, nr_votavel, MAX(nm_votavel), MAX(sq_candidato),
           SUM(COALESCE(qt_votos, 0))
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nr_zona,
              ds_cargo, nr_votavel;

    INSERT INTO tse.resultado_rollup_local_candidato
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           nr_zona, COALESCE(nr_local_votacao, -1), ds_cargo, nr_votavel,
           MAX(nm_votavel), MAX(sq_candidato), SUM(COALESCE(qt_votos, 0))
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nr_zona,
              COALESCE(nr_local_votacao, -1), ds_cargo, nr_votavel;

    INSERT INTO tse.resultado_rollup_secao_candidato
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           nr_zona, COALESCE(nr_local_votacao, -1), nr_secao,
           ds_cargo, nr_votavel, MAX(nm_votavel),
           MAX(sq_candidato), SUM(COALESCE(qt_votos, 0))
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nr_zona,
              COALESCE(nr_local_votacao, -1), nr_secao, ds_cargo, nr_votavel;

    FOR v_rollup_votes IN
        SELECT COALESCE(SUM(qt_votos), 0) FROM tse.resultado_rollup_municipio_candidato WHERE generation = v_generation
        UNION ALL
        SELECT COALESCE(SUM(qt_votos), 0) FROM tse.resultado_rollup_zona_candidato WHERE generation = v_generation
        UNION ALL
        SELECT COALESCE(SUM(qt_votos), 0) FROM tse.resultado_rollup_local_candidato WHERE generation = v_generation
        UNION ALL
        SELECT COALESCE(SUM(qt_votos), 0) FROM tse.resultado_rollup_secao_candidato WHERE generation = v_generation
    LOOP
        IF v_rollup_votes <> v_source_votes THEN
            RAISE EXCEPTION
                'validacao de votos falhou para geracao %: fonte=%, rollup=%',
                v_generation, v_source_votes, v_rollup_votes;
        END IF;
    END LOOP;

    UPDATE tse.resultado_rollup_controle
       SET active_generation = v_generation,
           status = 'ready',
           concluido_em = clock_timestamp(),
           ultima_mensagem = format('geracao %s; votos %s', v_generation, v_source_votes)
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno;

    IF v_old_generation IS NOT NULL AND v_old_generation <> v_generation THEN
        DELETE FROM tse.resultado_rollup_secao_candidato WHERE generation = v_old_generation;
        DELETE FROM tse.resultado_rollup_local_candidato WHERE generation = v_old_generation;
        DELETE FROM tse.resultado_rollup_zona_candidato WHERE generation = v_old_generation;
        DELETE FROM tse.resultado_rollup_municipio_candidato WHERE generation = v_old_generation;
        DELETE FROM tse.resultado_rollup_localidade WHERE generation = v_old_generation;
        DELETE FROM tse.resultado_rollup_catalogo WHERE generation = v_old_generation;
    END IF;

    RETURN v_generation;
END;
$$;

COMMENT ON TABLE tse.resultado_rollup_controle IS
    'Fila e ponteiro atomico para a geracao ativa dos rollups eleitorais.';
COMMENT ON COLUMN tse.resultado_rollup_local_candidato.nr_local_votacao IS
    'Codigo TSE do local; -1 representa local nao informado na fonte.';

GRANT SELECT ON tse.resultado_rollup_catalogo,
    tse.resultado_rollup_localidade,
    tse.resultado_rollup_municipio_candidato,
    tse.resultado_rollup_zona_candidato,
    tse.resultado_rollup_local_candidato,
    tse.resultado_rollup_secao_candidato TO app_inteligencia;
GRANT SELECT, INSERT, UPDATE ON tse.resultado_rollup_controle TO app_inteligencia;
GRANT USAGE, SELECT ON SEQUENCE tse.resultado_rollup_generation_seq TO app_inteligencia;
REVOKE ALL ON FUNCTION tse.fn_refresh_resultado_rollup(SMALLINT, INTEGER, SMALLINT)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION tse.fn_refresh_resultado_rollup(SMALLINT, INTEGER, SMALLINT)
    TO app_inteligencia;

COMMIT;
