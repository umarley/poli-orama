-- Converte comunicacao.atendimento_eleitor.canal de codigo textual para FK
-- de comunicacao.canal_comunicacao, reutilizando o catalogo ja existente.

BEGIN;

INSERT INTO comunicacao.canal_comunicacao (tenant_id, codigo, nome, descricao)
SELECT NULL, v.codigo, v.nome, v.descricao
FROM (
    VALUES
        ('mensagem', 'Mensagem', 'Mensagem de texto ou aplicativo.'),
        ('outro', 'Outro meio', 'Canal complementar informado no atendimento.')
) AS v(codigo, nome, descricao)
WHERE NOT EXISTS (
    SELECT 1
      FROM comunicacao.canal_comunicacao atual
     WHERE atual.tenant_id IS NULL
       AND atual.codigo = v.codigo
);

ALTER TABLE comunicacao.atendimento_eleitor
    ADD COLUMN IF NOT EXISTS canal_comunicacao_id SMALLINT
        REFERENCES comunicacao.canal_comunicacao(id);

UPDATE comunicacao.atendimento_eleitor a
SET canal_comunicacao_id = c.id
FROM comunicacao.canal_comunicacao c
WHERE a.canal_comunicacao_id IS NULL
  AND c.tenant_id IS NULL
  AND c.codigo = CASE a.canal::text
        WHEN 'ligacao' THEN 'telefone'
        WHEN 'mensagem' THEN 'mensagem'
        WHEN 'whatsapp' THEN 'whatsapp'
        WHEN 'presencial' THEN 'presencial'
        WHEN 'outro' THEN 'outro'
        ELSE a.canal::text
      END;

UPDATE comunicacao.atendimento_eleitor a
SET canal_comunicacao_id = (
    SELECT c.id
      FROM comunicacao.canal_comunicacao c
     WHERE c.tenant_id IS NULL
       AND c.codigo = 'telefone'
     ORDER BY c.id
     LIMIT 1
)
WHERE a.canal_comunicacao_id IS NULL;

ALTER TABLE comunicacao.atendimento_eleitor
    DROP CONSTRAINT IF EXISTS atendimento_eleitor_canal_check;

DROP INDEX IF EXISTS ix_atendimento_eleitor_indicadores;

ALTER TABLE comunicacao.atendimento_eleitor
    DROP COLUMN canal;

ALTER TABLE comunicacao.atendimento_eleitor
    RENAME COLUMN canal_comunicacao_id TO canal;

ALTER TABLE comunicacao.atendimento_eleitor
    ALTER COLUMN canal SET NOT NULL;

ALTER TABLE comunicacao.atendimento_eleitor
    DROP CONSTRAINT IF EXISTS atendimento_eleitor_canal_fkey;

ALTER TABLE comunicacao.atendimento_eleitor
    ADD CONSTRAINT atendimento_eleitor_canal_fkey
        FOREIGN KEY (canal) REFERENCES comunicacao.canal_comunicacao(id);

CREATE INDEX IF NOT EXISTS ix_atendimento_eleitor_indicadores
    ON comunicacao.atendimento_eleitor
        (tenant_id, campanha_eleicao_id, situacao, canal, resultado, intencao_voto, iniciado_em);

CREATE INDEX IF NOT EXISTS ix_atendimento_eleitor_canal
    ON comunicacao.atendimento_eleitor (canal);

COMMENT ON COLUMN comunicacao.atendimento_eleitor.canal IS
    'Canal utilizado no atendimento; referencia comunicacao.canal_comunicacao.';

COMMIT;
