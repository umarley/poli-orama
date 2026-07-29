-- Garante que uma pessoa possua somente uma lideranca ativa dentro do tenant.
-- Em duplicidades preexistentes, preserva o vinculo criado mais recentemente.
WITH vinculos_duplicados AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY tenant_id, pessoa_subordinada_id
               ORDER BY criado_em DESC, id DESC
           ) AS ordem
    FROM cadastro.hierarquia_lideranca
    WHERE ativo = TRUE
)
UPDATE cadastro.hierarquia_lideranca AS h
SET ativo = FALSE,
    data_fim = COALESCE(h.data_fim, CURRENT_DATE)
FROM vinculos_duplicados AS d
WHERE h.id = d.id
  AND d.ordem > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_hierarquia_pessoa_ativa_tenant
    ON cadastro.hierarquia_lideranca (tenant_id, pessoa_subordinada_id)
    WHERE ativo = TRUE;

COMMENT ON INDEX cadastro.uq_hierarquia_pessoa_ativa_tenant IS
    'Impede que uma pessoa possua mais de uma lideranca ativa no mesmo tenant.';
