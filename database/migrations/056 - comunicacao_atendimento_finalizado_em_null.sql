-- Remove o DEFAULT now() de finalizado_em, que preenchia atendimentos abertos
-- e violava atendimento_eleitor_ativo_check (em_atendimento exige finalizado_em nulo).

BEGIN;

ALTER TABLE comunicacao.atendimento_eleitor
    ALTER COLUMN finalizado_em DROP DEFAULT;

COMMIT;
