-- Inclui 'integracao' em ck_pessoa_origem_cadastro.
-- Cadastros originados pelo site externo (chave auth.api_key) usam
-- origem_cadastro = 'integracao' e fonte_dado site_integracao.

BEGIN;

ALTER TABLE cadastro.pessoa
    DROP CONSTRAINT IF EXISTS ck_pessoa_origem_cadastro;

ALTER TABLE cadastro.pessoa
    ADD CONSTRAINT ck_pessoa_origem_cadastro
    CHECK (
        origem_cadastro IS NULL
        OR origem_cadastro IN (
            'manual',
            'cadastro_web',
            'lider_mobile',
            'importacao',
            'site',
            'call_center',
            'formulario',
            'migracao',
            'integracao'
        )
    );

COMMENT ON COLUMN cadastro.pessoa.origem_cadastro IS
    'Canal de origem do cadastro. Site externo autenticado com chave de integracao usa integracao.';

COMMIT;
