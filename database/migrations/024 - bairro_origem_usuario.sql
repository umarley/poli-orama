BEGIN;

ALTER TABLE global.bairro
    DROP CONSTRAINT IF EXISTS bairro_origem_check;

ALTER TABLE global.bairro
    ADD CONSTRAINT bairro_origem_check
    CHECK (origem IN ('oficial', 'manual', 'importado', 'usuario'));

COMMIT;
