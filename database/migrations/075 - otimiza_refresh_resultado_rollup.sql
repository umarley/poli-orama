-- Reduz as leituras da tabela bruta durante o refresh eleitoral.
--
-- A versao anterior agregava tse.resultados_eleicoes separadamente para cada
-- granularidade. Esta versao materializa uma unica fotografia da eleicao em
-- tabela temporaria e deriva os niveis superiores a partir do rollup de secao.
-- A troca de active_generation continua sendo o ultimo passo visivel da mesma
-- transacao, portanto leitores nunca observam uma geracao parcial.
BEGIN;

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
    v_lock_name TEXT := format(
        'tse-rollup:%s:%s:%s', p_aa_eleicao, p_cd_eleicao, p_nr_turno
    );
BEGIN
    -- O worker ja adquire este mesmo lock. A aquisicao e reentrante na mesma
    -- transacao e protege tambem chamadas diretas da funcao.
    IF NOT pg_try_advisory_xact_lock(hashtextextended(v_lock_name, 0)) THEN
        RAISE EXCEPTION 'refresh ja esta em execucao para (%, %, %)',
            p_aa_eleicao, p_cd_eleicao, p_nr_turno
            USING ERRCODE = '55P03';
    END IF;

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

    -- Uma conexao pode chamar a funcao mais de uma vez na mesma transacao.
    DROP TABLE IF EXISTS pg_temp.resultado_rollup_fonte;
    CREATE TEMP TABLE resultado_rollup_fonte ON COMMIT DROP AS
    SELECT aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           nm_municipio, nr_zona, nr_local_votacao, nm_local_votacao,
           ds_local_votacao_endereco, nr_secao, ds_cargo, nr_votavel,
           nm_votavel, sq_candidato, qt_votos, ds_eleicao, dt_eleicao
      FROM tse.resultados_eleicoes
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno;

    ANALYZE pg_temp.resultado_rollup_fonte;

    SELECT COALESCE(SUM(qt_votos), 0)
      INTO v_source_votes
      FROM pg_temp.resultado_rollup_fonte;

    -- O catalogo de autocomplete passa a refletir exatamente a fotografia
    -- consolidada, inclusive quando uma carga futura remover um votavel.
    DELETE FROM tse.resultado_votavel
     WHERE aa_eleicao = p_aa_eleicao
       AND cd_eleicao = p_cd_eleicao
       AND nr_turno = p_nr_turno;

    INSERT INTO tse.resultado_votavel (
        aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo, nr_votavel,
        nm_votavel, nm_votavel_busca
    )
    SELECT aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo, nr_votavel,
           MAX(btrim(nm_votavel)),
           lower(public.unaccent(MAX(btrim(nm_votavel))))
      FROM pg_temp.resultado_rollup_fonte
     WHERE sg_uf IS NOT NULL
       AND ds_cargo IS NOT NULL
       AND nr_votavel IS NOT NULL
       AND nm_votavel IS NOT NULL
       AND btrim(nm_votavel) <> ''
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo, nr_votavel;

    INSERT INTO tse.resultado_rollup_catalogo (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo,
        ds_eleicao, dt_eleicao
    )
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo,
           MAX(ds_eleicao), MAX(dt_eleicao)
      FROM pg_temp.resultado_rollup_fonte
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo;

    INSERT INTO tse.resultado_rollup_localidade (
        generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
        nm_municipio, nr_zona, nr_local_votacao, nm_local_votacao,
        ds_local_votacao_endereco, nr_secao
    )
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           MAX(nm_municipio), nr_zona, MAX(nr_local_votacao),
           MAX(nm_local_votacao), MAX(ds_local_votacao_endereco), nr_secao
      FROM pg_temp.resultado_rollup_fonte
     GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nr_zona, nr_secao;

    -- A restricao resultados_eleicoes_uk garante uma linha por secao, cargo e
    -- votavel. Assim, este primeiro nivel nao precisa de nova agregacao.
    INSERT INTO tse.resultado_rollup_secao_candidato
    SELECT v_generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           nr_zona, COALESCE(nr_local_votacao, -1), nr_secao,
           ds_cargo, nr_votavel, nm_votavel, sq_candidato,
           COALESCE(qt_votos, 0)
      FROM pg_temp.resultado_rollup_fonte;

    INSERT INTO tse.resultado_rollup_local_candidato
    SELECT generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           nr_zona, nr_local_votacao, ds_cargo, nr_votavel,
           MAX(nm_votavel), MAX(sq_candidato), SUM(qt_votos)
      FROM tse.resultado_rollup_secao_candidato
     WHERE generation = v_generation
     GROUP BY generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
              cd_municipio, nr_zona, nr_local_votacao, ds_cargo, nr_votavel;

    INSERT INTO tse.resultado_rollup_zona_candidato
    SELECT generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           nr_zona, ds_cargo, nr_votavel, MAX(nm_votavel),
           MAX(sq_candidato), SUM(qt_votos)
      FROM tse.resultado_rollup_local_candidato
     WHERE generation = v_generation
     GROUP BY generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
              cd_municipio, nr_zona, ds_cargo, nr_votavel;

    INSERT INTO tse.resultado_rollup_municipio_candidato
    SELECT generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
           ds_cargo, nr_votavel, MAX(nm_votavel), MAX(sq_candidato),
           SUM(qt_votos)
      FROM tse.resultado_rollup_zona_candidato
     WHERE generation = v_generation
     GROUP BY generation, aa_eleicao, cd_eleicao, nr_turno, sg_uf,
              cd_municipio, ds_cargo, nr_votavel;

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

REVOKE ALL ON FUNCTION tse.fn_refresh_resultado_rollup(SMALLINT, INTEGER, SMALLINT)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION tse.fn_refresh_resultado_rollup(SMALLINT, INTEGER, SMALLINT)
    TO app_inteligencia;

COMMIT;
