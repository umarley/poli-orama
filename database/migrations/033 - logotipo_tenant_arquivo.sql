BEGIN;

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
            'tenant'
        )
    );

COMMIT;
