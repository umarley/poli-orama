-- Catalogo compacto para os filtros de municipios e zonas eleitorais.
-- Uma linha representa uma zona existente em uma eleicao e evita agrupar os
-- fatos por candidato/secao a cada abertura dos filtros.
BEGIN;

CREATE TABLE tse.resultado_localidade_eleitoral (
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    cd_municipio        INTEGER NOT NULL,
    nm_municipio        VARCHAR(120),
    nr_zona             SMALLINT NOT NULL,
    PRIMARY KEY (
        aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nr_zona
    )
);

CREATE INDEX ix_resultado_localidade_eleitoral_municipio
    ON tse.resultado_localidade_eleitoral
       (aa_eleicao, cd_eleicao, nr_turno, cd_municipio, nr_zona);

CREATE OR REPLACE FUNCTION tse.fn_sync_resultado_localidade_eleitoral()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, tse
AS $$
BEGIN
    IF NEW.status <> 'ready' OR NEW.active_generation IS NULL THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF OLD.status = 'ready'
           AND OLD.active_generation IS NOT DISTINCT FROM NEW.active_generation THEN
            RETURN NEW;
        END IF;
    END IF;

    DELETE FROM tse.resultado_localidade_eleitoral
     WHERE aa_eleicao = NEW.aa_eleicao
       AND cd_eleicao = NEW.cd_eleicao
       AND nr_turno = NEW.nr_turno;

    INSERT INTO tse.resultado_localidade_eleitoral (
        aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio,
        nm_municipio, nr_zona
    )
    SELECT l.aa_eleicao, l.cd_eleicao, l.nr_turno, l.sg_uf, l.cd_municipio,
           MAX(l.nm_municipio), l.nr_zona
      FROM tse.resultado_rollup_localidade l
     WHERE l.generation = NEW.active_generation
       AND l.aa_eleicao = NEW.aa_eleicao
       AND l.cd_eleicao = NEW.cd_eleicao
       AND l.nr_turno = NEW.nr_turno
     GROUP BY l.aa_eleicao, l.cd_eleicao, l.nr_turno, l.sg_uf,
              l.cd_municipio, l.nr_zona;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sync_resultado_localidade_eleitoral
AFTER INSERT OR UPDATE ON tse.resultado_rollup_controle
FOR EACH ROW
EXECUTE FUNCTION tse.fn_sync_resultado_localidade_eleitoral();

-- Aproveita somente geracoes prontas. O trigger e criado antes do backfill
-- para nao perder um refresh que termine durante a aplicacao da migration.
-- Eleicoes ainda sem rollup continuam no fallback ate o primeiro refresh.
INSERT INTO tse.resultado_localidade_eleitoral (
    aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nm_municipio, nr_zona
)
SELECT l.aa_eleicao, l.cd_eleicao, l.nr_turno, l.sg_uf, l.cd_municipio,
       MAX(l.nm_municipio), l.nr_zona
  FROM tse.resultado_rollup_localidade l
  JOIN tse.resultado_rollup_controle c
    ON c.aa_eleicao = l.aa_eleicao
   AND c.cd_eleicao = l.cd_eleicao
   AND c.nr_turno = l.nr_turno
   AND c.status = 'ready'
   AND c.active_generation = l.generation
 GROUP BY l.aa_eleicao, l.cd_eleicao, l.nr_turno, l.sg_uf,
          l.cd_municipio, l.nr_zona
ON CONFLICT (aa_eleicao, cd_eleicao, nr_turno, sg_uf, cd_municipio, nr_zona)
DO UPDATE SET nm_municipio = EXCLUDED.nm_municipio;

COMMENT ON TABLE tse.resultado_localidade_eleitoral IS
    'Municipios e zonas distintos por eleicao para filtros de baixa latencia.';

GRANT SELECT ON tse.resultado_localidade_eleitoral TO app_inteligencia;
REVOKE ALL ON FUNCTION tse.fn_sync_resultado_localidade_eleitoral() FROM PUBLIC;

COMMIT;
