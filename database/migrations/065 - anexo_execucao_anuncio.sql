BEGIN;

-- Permite associar a foto registrada no app a uma execucao de anuncio.
-- O tipo ja faz parte do contrato da API desde a migration 063, mas ainda nao
-- havia sido incluido na restricao polimorfica criada para arquivo.anexo.
ALTER TABLE arquivo.anexo
    DROP CONSTRAINT IF EXISTS anexo_entidade_tipo_check;

ALTER TABLE arquivo.anexo
    ADD CONSTRAINT anexo_entidade_tipo_check
    CHECK (
        entidade_tipo IN (
            'pessoa',
            'evento',
            'demanda',
            'interacao',
            'importacao',
            'comunidade',
            'lideranca',
            'convite',
            'tenant',
            'contrato',
            'anuncio_execucao'
        )
    );

COMMIT;
