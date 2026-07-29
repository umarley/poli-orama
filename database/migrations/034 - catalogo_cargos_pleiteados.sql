BEGIN;

CREATE TABLE IF NOT EXISTS eleicao.cargo_pleiteado (
    id              SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo          VARCHAR(40) NOT NULL UNIQUE,
    nome            VARCHAR(80) NOT NULL,
    tipo_eleicao    VARCHAR(30) NOT NULL
                    CHECK (tipo_eleicao IN ('municipal', 'federal')),
    ordem           SMALLINT NOT NULL DEFAULT 0,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE eleicao.cargo_pleiteado IS
    'Catalogo global de cargos eletivos disponiveis conforme o tipo da eleicao oficial.';
COMMENT ON COLUMN eleicao.cargo_pleiteado.tipo_eleicao IS
    'municipal para prefeito e vereador; federal representa as eleicoes gerais.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_cargo_pleiteado_tipo_nome
    ON eleicao.cargo_pleiteado (tipo_eleicao, lower(nome));
CREATE INDEX IF NOT EXISTS ix_cargo_pleiteado_tipo_ativo
    ON eleicao.cargo_pleiteado (tipo_eleicao, ativo, ordem);

INSERT INTO eleicao.cargo_pleiteado (codigo, nome, tipo_eleicao, ordem) VALUES
    ('prefeito', 'Prefeito', 'municipal', 10),
    ('vereador', 'Vereador', 'municipal', 20),
    ('deputado_estadual', 'Deputado estadual', 'federal', 10),
    ('deputado_federal', 'Deputado federal', 'federal', 20),
    ('senador', 'Senador', 'federal', 30),
    ('governador', 'Governador', 'federal', 40),
    ('presidente_republica', 'Presidente da República', 'federal', 50)
ON CONFLICT (codigo) DO UPDATE SET
    nome = EXCLUDED.nome,
    tipo_eleicao = EXCLUDED.tipo_eleicao,
    ordem = EXCLUDED.ordem,
    ativo = TRUE,
    atualizado_em = now();

ALTER TABLE eleicao.campanha_eleicao
    ADD COLUMN IF NOT EXISTS cargo_pleiteado_id SMALLINT
    REFERENCES eleicao.cargo_pleiteado(id);

UPDATE eleicao.campanha_eleicao AS campanha
SET cargo_pleiteado_id = cargo.id
FROM eleicao.cargo_pleiteado AS cargo
WHERE campanha.cargo_pleiteado_id IS NULL
  AND lower(trim(campanha.cargo_pleiteado)) = lower(cargo.nome);

CREATE INDEX IF NOT EXISTS ix_campanha_eleicao_cargo
    ON eleicao.campanha_eleicao (cargo_pleiteado_id);

DROP TRIGGER IF EXISTS trg_cargo_pleiteado_atualiza ON eleicao.cargo_pleiteado;
CREATE TRIGGER trg_cargo_pleiteado_atualiza
BEFORE UPDATE ON eleicao.cargo_pleiteado
FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

GRANT SELECT ON eleicao.cargo_pleiteado TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA eleicao TO app_inteligencia;

COMMIT;
