BEGIN;

-- Resolve o evento anonimamente sem expor outras tabelas protegidas por RLS.
-- As operacoes posteriores configuram o tenant retornado nesta mesma transacao.
CREATE OR REPLACE FUNCTION agenda.fn_evento_publico(p_uuid UUID)
RETURNS TABLE (
    id BIGINT,
    uuid_publico UUID,
    tenant_id BIGINT,
    titulo VARCHAR(180),
    data_inicio TIMESTAMPTZ,
    data_fim TIMESTAMPTZ,
    local_nome VARCHAR(180)
)
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = pg_catalog, public, agenda
AS $$
    SELECT e.id, e.uuid_publico, e.tenant_id, e.titulo,
           e.data_inicio, e.data_fim, e.local_nome
      FROM agenda.evento e
      JOIN public.tenant t ON t.id = e.tenant_id
     WHERE e.uuid_publico = p_uuid
       AND e.excluido_em IS NULL
       AND e.cancelado_em IS NULL
       AND t.excluido_em IS NULL
       AND t.status IN ('ativo', 'trial')
     LIMIT 1
$$;

REVOKE ALL ON FUNCTION agenda.fn_evento_publico(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION agenda.fn_evento_publico(UUID) TO app_inteligencia;

COMMIT;
