BEGIN;

-- Centraliza metas de lideranca no modulo de metas.
-- Valores legados sao preservados como metas formais no ano da migracao.

INSERT INTO meta.periodo_meta (
    tenant_id,
    nome,
    data_inicio,
    data_fim,
    ciclo,
    ativo
)
SELECT DISTINCT
    l.tenant_id,
    'Migração de metas legadas ' || EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER,
    make_date(EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 1, 1),
    make_date(EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 12, 31),
    'anual',
    TRUE
FROM cadastro.lideranca l
WHERE l.meta_votos IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM meta.periodo_meta pm
      WHERE pm.tenant_id = l.tenant_id
        AND pm.nome =
            'Migração de metas legadas ' || EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
  );

WITH metas_migradas AS (
    INSERT INTO meta.meta_voto (
        tenant_id,
        tipo_meta_voto_id,
        periodo_meta_id,
        titulo,
        quantidade_meta,
        lideranca_id,
        status
    )
    SELECT
        l.tenant_id,
        tm.id,
        pm.id,
        'Meta legada da liderança #' || l.id,
        l.meta_votos,
        l.id,
        'ativa'
    FROM cadastro.lideranca l
    JOIN meta.tipo_meta_voto tm
      ON tm.codigo = 'lider'
     AND tm.tenant_id IS NULL
    JOIN meta.periodo_meta pm
      ON pm.tenant_id = l.tenant_id
     AND pm.nome =
        'Migração de metas legadas ' || EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
    WHERE l.meta_votos IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM meta.meta_voto mv
          WHERE mv.tenant_id = l.tenant_id
            AND mv.lideranca_id = l.id
            AND mv.titulo = 'Meta legada da liderança #' || l.id
      )
    RETURNING id, tenant_id, lideranca_id, quantidade_meta
)
INSERT INTO meta.meta_voto_alvo (
    tenant_id,
    meta_voto_id,
    tipo_alvo,
    alvo_id,
    quantidade_atribuida
)
SELECT
    tenant_id,
    id,
    'lideranca',
    lideranca_id,
    quantidade_meta
FROM metas_migradas
ON CONFLICT (meta_voto_id, tipo_alvo, alvo_id) DO NOTHING;

ALTER TABLE cadastro.lideranca
    DROP CONSTRAINT IF EXISTS ck_lideranca_meta_votos,
    DROP CONSTRAINT IF EXISTS lideranca_meta_votos_check,
    DROP COLUMN IF EXISTS meta_votos;

COMMENT ON COLUMN meta.meta_voto.quantidade_meta IS
    'Quantidade oficial da meta. Metas de lideranca devem ser vinculadas por meta.meta_voto_alvo.';

COMMIT;
