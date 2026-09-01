BEGIN;

ALTER TABLE agenda.agenda
    DROP CONSTRAINT IF EXISTS agenda_frente_comunidade_check;
ALTER TABLE agenda.agenda
    DROP CONSTRAINT IF EXISTS ck_agenda_frente_comunidade;

ALTER TABLE agenda.agenda
    ADD CONSTRAINT ck_agenda_frente_comunidade
    CHECK (frente_comunidade IN (
        'geral', 'juventude', 'sindicalista', 'cultura', 'engenharia',
        'saude', 'educacao', 'dobradas'
    ));

COMMIT;
