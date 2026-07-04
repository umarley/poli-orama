BEGIN;

CREATE INDEX IF NOT EXISTS ix_demanda_tenant_prazo_aberta
    ON demanda.demanda (tenant_id, prazo)
    WHERE prazo IS NOT NULL AND excluido_em IS NULL;

CREATE INDEX IF NOT EXISTS ix_alerta_prazo_tenant_status
    ON demanda.alerta_prazo (tenant_id, status, tipo, data_referencia);

CREATE INDEX IF NOT EXISTS ix_demanda_classificacao_detalhes
    ON demanda.demanda USING gin (classificacao_detalhes);

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON demanda.responsavel_atendimento;
CREATE TRIGGER trg_atualiza_timestamp
BEFORE UPDATE ON demanda.responsavel_atendimento
FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

COMMIT;
