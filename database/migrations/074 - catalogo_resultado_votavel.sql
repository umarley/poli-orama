-- Catalogo enxuto de votaveis para a busca de candidatos.
-- A tabela de secao repete o mesmo nome milhoes de vezes; o autocomplete
-- consulta apenas uma linha por eleicao, UF, cargo e numero.
BEGIN;

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE tse.resultado_votavel (
    aa_eleicao          SMALLINT NOT NULL,
    cd_eleicao          INTEGER NOT NULL,
    nr_turno            SMALLINT NOT NULL,
    sg_uf               CHAR(2) NOT NULL,
    ds_cargo            VARCHAR(80) NOT NULL,
    nr_votavel          INTEGER NOT NULL,
    nm_votavel          VARCHAR(200) NOT NULL,
    nm_votavel_busca    TEXT NOT NULL,
    PRIMARY KEY (aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo, nr_votavel)
);

CREATE INDEX ix_resultado_votavel_nome_trgm
    ON tse.resultado_votavel USING gin (nm_votavel_busca gin_trgm_ops);

INSERT INTO tse.resultado_votavel (
    aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo, nr_votavel,
    nm_votavel, nm_votavel_busca
)
SELECT
    aa_eleicao,
    cd_eleicao,
    nr_turno,
    sg_uf,
    ds_cargo,
    nr_votavel,
    MAX(btrim(nm_votavel)),
    lower(unaccent(MAX(btrim(nm_votavel))))
FROM tse.resultados_eleicoes
WHERE aa_eleicao IS NOT NULL
  AND cd_eleicao IS NOT NULL
  AND nr_turno IS NOT NULL
  AND sg_uf IS NOT NULL
  AND ds_cargo IS NOT NULL
  AND nr_votavel IS NOT NULL
  AND nm_votavel IS NOT NULL
  AND btrim(nm_votavel) <> ''
GROUP BY aa_eleicao, cd_eleicao, nr_turno, sg_uf, ds_cargo, nr_votavel;

ANALYZE tse.resultado_votavel;

COMMENT ON TABLE tse.resultado_votavel IS
    'Nomes distintos de votaveis por eleicao, UF e cargo, usados na busca de candidatos.';

GRANT SELECT, INSERT, UPDATE, DELETE ON tse.resultado_votavel TO app_inteligencia;

COMMIT;
