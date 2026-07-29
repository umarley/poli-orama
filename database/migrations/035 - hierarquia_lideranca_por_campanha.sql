-- Vincula a hierarquia operacional a campanha e preserva seu retrato no DW.

BEGIN;

ALTER TABLE cadastro.hierarquia_lideranca
    ADD COLUMN IF NOT EXISTS campanha_eleicao_id BIGINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_hierarquia_lideranca_campanha'
           AND conrelid = 'cadastro.hierarquia_lideranca'::regclass
    ) THEN
        ALTER TABLE cadastro.hierarquia_lideranca
            ADD CONSTRAINT fk_hierarquia_lideranca_campanha
            FOREIGN KEY (campanha_eleicao_id)
            REFERENCES eleicao.campanha_eleicao(id)
            ON DELETE RESTRICT;
    END IF;
END
$$;

UPDATE cadastro.hierarquia_lideranca AS h
   SET campanha_eleicao_id = (
      SELECT cl.campanha_eleicao_id
        FROM eleicao.campanha_liderado AS cl
       WHERE cl.tenant_id = h.tenant_id
         AND cl.lideranca_id = h.lideranca_superior_id
         AND cl.pessoa_id = h.pessoa_subordinada_id
       ORDER BY cl.ativo DESC, cl.criado_em DESC, cl.id DESC
       LIMIT 1
   )
 WHERE h.campanha_eleicao_id IS NULL
   AND EXISTS (
       SELECT 1
         FROM eleicao.campanha_liderado AS cl
        WHERE cl.tenant_id = h.tenant_id
          AND cl.lideranca_id = h.lideranca_superior_id
          AND cl.pessoa_id = h.pessoa_subordinada_id
   );

UPDATE cadastro.hierarquia_lideranca AS h
   SET campanha_eleicao_id = (
      SELECT ce.id
        FROM eleicao.campanha_eleicao AS ce
       WHERE ce.tenant_id = h.tenant_id
         AND ce.ativa
         AND ce.data_encerramento IS NULL
       ORDER BY ce.data_ativacao DESC NULLS LAST, ce.id DESC
       LIMIT 1
   )
 WHERE h.campanha_eleicao_id IS NULL
   AND h.ativo
   AND EXISTS (
       SELECT 1
         FROM eleicao.campanha_eleicao AS ce
        WHERE ce.tenant_id = h.tenant_id
          AND ce.ativa
          AND ce.data_encerramento IS NULL
   );

CREATE INDEX IF NOT EXISTS ix_hierarquia_campanha_lideranca
    ON cadastro.hierarquia_lideranca
       (tenant_id, campanha_eleicao_id, lideranca_superior_id);

CREATE INDEX IF NOT EXISTS ix_hierarquia_campanha_pessoa
    ON cadastro.hierarquia_lideranca
       (campanha_eleicao_id, pessoa_subordinada_id);

COMMENT ON COLUMN cadastro.hierarquia_lideranca.campanha_eleicao_id IS
    'Campanha a que pertence o estado operacional atual do vinculo hierarquico.';

CREATE TABLE IF NOT EXISTS dw.hierarquia_lideranca_campanha_consolidada (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL
                                REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id         BIGINT NOT NULL
                                REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT,
    hierarquia_lideranca_id     BIGINT NOT NULL,
    lideranca_superior_id       BIGINT NOT NULL
                                REFERENCES cadastro.lideranca(id) ON DELETE RESTRICT,
    pessoa_subordinada_id       BIGINT NOT NULL
                                REFERENCES cadastro.pessoa(id) ON DELETE RESTRICT,
    papel_subordinado           VARCHAR(30) NOT NULL,
    data_inicio                 DATE NOT NULL,
    data_fim                    DATE,
    ativo_no_encerramento       BOOLEAN NOT NULL,
    intencao_confirmada         BOOLEAN NOT NULL DEFAULT FALSE,
    status_eleitoral            VARCHAR(30),
    consolidado_em              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dw_hierarquia_lideranca_campanha
        UNIQUE (campanha_eleicao_id, hierarquia_lideranca_id)
);

CREATE INDEX IF NOT EXISTS ix_dw_hierarquia_lideranca_resultado
    ON dw.hierarquia_lideranca_campanha_consolidada
       (campanha_eleicao_id, lideranca_superior_id, intencao_confirmada);

ALTER TABLE dw.hierarquia_lideranca_campanha_consolidada
    ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_dw_hierarquia_lideranca
    ON dw.hierarquia_lideranca_campanha_consolidada;

CREATE POLICY tenant_isolation_dw_hierarquia_lideranca
    ON dw.hierarquia_lideranca_campanha_consolidada
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());

INSERT INTO dw.hierarquia_lideranca_campanha_consolidada (
    tenant_id, campanha_eleicao_id, hierarquia_lideranca_id,
    lideranca_superior_id, pessoa_subordinada_id, papel_subordinado,
    data_inicio, data_fim, ativo_no_encerramento,
    intencao_confirmada, status_eleitoral
)
SELECT h.tenant_id, h.campanha_eleicao_id, h.id,
       h.lideranca_superior_id, h.pessoa_subordinada_id,
       h.papel_subordinado, h.data_inicio, h.data_fim, h.ativo,
       COALESCE(p.intencao_confirmada, FALSE), p.status_eleitoral
  FROM cadastro.hierarquia_lideranca AS h
  JOIN dw.campanha_consolidada AS c
    ON c.tenant_id = h.tenant_id
   AND c.campanha_eleicao_id = h.campanha_eleicao_id
  LEFT JOIN dw.pessoa_campanha_consolidada AS p
    ON p.campanha_eleicao_id = h.campanha_eleicao_id
   AND p.pessoa_id = h.pessoa_subordinada_id
ON CONFLICT (campanha_eleicao_id, hierarquia_lideranca_id) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON dw.hierarquia_lideranca_campanha_consolidada
    TO app_inteligencia;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA dw TO app_inteligencia;

COMMIT;
