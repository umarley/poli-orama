-- Marca o instante em que o atendente abriu o atendimento.
-- Usado pela fila em /comunicacao/atendimento para contar mensagens
-- de entrada nao lidas (i.data_interacao > ultima_visualizacao_em).
-- Idempotente: a 058 ja tenta criar a coluna; esta migration cobre
-- ambientes em que a 058 nao foi aplicada.

BEGIN;

ALTER TABLE comunicacao.atendimento_eleitor
    ADD COLUMN IF NOT EXISTS ultima_visualizacao_em TIMESTAMPTZ;

COMMENT ON COLUMN comunicacao.atendimento_eleitor.ultima_visualizacao_em IS
    'Ultima vez que o atendente visualizou o atendimento. Usado para mensagens nao lidas.';

COMMIT;
