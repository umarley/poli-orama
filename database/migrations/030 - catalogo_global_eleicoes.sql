-- Transforma eleicao.eleicao em catalogo oficial e global da plataforma.

BEGIN;

ALTER TABLE eleicao.eleicao
    ADD COLUMN IF NOT EXISTS uuid_publico UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_por BIGINT REFERENCES auth.usuario(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

-- Registros anteriores passam a integrar o catalogo compartilhado. Eventuais
-- duplicidades sao consolidadas, preservando o menor identificador referenciado.
CREATE TEMP TABLE eleicoes_duplicadas ON COMMIT DROP AS
SELECT id,
       min(id) OVER (
           PARTITION BY ano, tipo, turno, data_eleicao,
                        COALESCE(codigo_uf_ibge, -1),
                        COALESCE(codigo_municipio_ibge, -1)
       ) AS id_canonico
FROM eleicao.eleicao;

UPDATE eleicao.campanha_eleicao AS campanha
SET eleicao_id = duplicada.id_canonico
FROM eleicoes_duplicadas AS duplicada
WHERE campanha.eleicao_id = duplicada.id
  AND duplicada.id <> duplicada.id_canonico
  AND NOT EXISTS (
      SELECT 1
      FROM eleicao.campanha_eleicao AS existente
      WHERE existente.tenant_id = campanha.tenant_id
        AND existente.eleicao_id = duplicada.id_canonico
        AND existente.id <> campanha.id
  );

UPDATE etl.staging_eleitorado_tse AS base
SET eleicao_id = duplicada.id_canonico
FROM eleicoes_duplicadas AS duplicada
WHERE base.eleicao_id = duplicada.id
  AND duplicada.id <> duplicada.id_canonico;

UPDATE dw.perfil_eleitorado_tse AS base
SET eleicao_id = duplicada.id_canonico
FROM eleicoes_duplicadas AS duplicada
WHERE base.eleicao_id = duplicada.id
  AND duplicada.id <> duplicada.id_canonico;

UPDATE dw.perfil_eleitorado_secao_tse AS base
SET eleicao_id = duplicada.id_canonico
FROM eleicoes_duplicadas AS duplicada
WHERE base.eleicao_id = duplicada.id
  AND duplicada.id <> duplicada.id_canonico;

-- Uma campanha duplicada para o mesmo tenant/eleicao nao pode ser fundida
-- automaticamente, portanto a migration para antes de apagar seu registro.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM eleicao.campanha_eleicao AS campanha
        JOIN eleicoes_duplicadas AS duplicada
          ON duplicada.id = campanha.eleicao_id
        WHERE duplicada.id <> duplicada.id_canonico
    ) THEN
        RAISE EXCEPTION
            'Existem campanhas duplicadas que impedem consolidar o catalogo global de eleicoes.';
    END IF;
END
$$;

DELETE FROM eleicao.eleicao AS eleicao
USING eleicoes_duplicadas AS duplicada
WHERE eleicao.id = duplicada.id
  AND duplicada.id <> duplicada.id_canonico;

ALTER TABLE eleicao.eleicao
    DROP COLUMN IF EXISTS tenant_id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_eleicao_uuid_publico
    ON eleicao.eleicao (uuid_publico);

CREATE UNIQUE INDEX IF NOT EXISTS uq_eleicao_oficial_escopo
    ON eleicao.eleicao (
        ano, tipo, turno, data_eleicao,
        COALESCE(codigo_uf_ibge, -1),
        COALESCE(codigo_municipio_ibge, -1)
    );

CREATE INDEX IF NOT EXISTS ix_eleicao_oficial_ativa_data
    ON eleicao.eleicao (ativo, data_eleicao DESC);

DROP TRIGGER IF EXISTS trg_eleicao_atualiza ON eleicao.eleicao;
CREATE TRIGGER trg_eleicao_atualiza
BEFORE UPDATE ON eleicao.eleicao
FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

COMMENT ON TABLE eleicao.eleicao IS
    'Catalogo global de eleicoes oficiais, mantido exclusivamente pela plataforma (gestor_saas) e compartilhado por todos os tenants.';
COMMENT ON COLUMN eleicao.eleicao.criado_por IS
    'Usuario gestor_saas responsavel pelo cadastro oficial.';

COMMIT;
