BEGIN;

ALTER TABLE anuncio.rota_comunicacao_planejamento_ponto
    ADD COLUMN origem_ponto VARCHAR(24) NOT NULL DEFAULT 'PLANEJADO',
    ADD CONSTRAINT ck_planejamento_ponto_origem
        CHECK (origem_ponto IN ('PLANEJADO','ADICIONADO_EXECUCAO'));

DO $$
DECLARE
    restricao RECORD;
BEGIN
    FOR restricao IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'anuncio.rota_comunicacao_planejamento_ponto_material'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) LIKE '%quantidade_planejada > 0%'
    LOOP
        EXECUTE format(
            'ALTER TABLE anuncio.rota_comunicacao_planejamento_ponto_material DROP CONSTRAINT %I',
            restricao.conname
        );
    END LOOP;
END $$;

ALTER TABLE anuncio.rota_comunicacao_planejamento_ponto_material
    ADD CONSTRAINT ck_planejamento_material_quantidade_planejada
        CHECK (quantidade_planejada >= 0);

COMMIT;
