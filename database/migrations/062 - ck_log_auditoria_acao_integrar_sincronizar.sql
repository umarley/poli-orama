-- Inclui acoes de integracao Google Agenda em ck_log_auditoria_acao.
-- Vincular conta/agenda usa 'integrar'; sincronizar eventos usa 'sincronizar'.

BEGIN;

ALTER TABLE auditoria.log_auditoria
    DROP CONSTRAINT IF EXISTS log_auditoria_acao_check;
ALTER TABLE auditoria.log_auditoria
    DROP CONSTRAINT IF EXISTS ck_log_auditoria_acao;
ALTER TABLE auditoria.log_auditoria
    ADD CONSTRAINT ck_log_auditoria_acao
    CHECK (
        acao IN (
            'criar', 'editar', 'excluir', 'acessar', 'exportar',
            'login', 'logout', 'confirmar', 'mesclar',
            'integrar', 'sincronizar'
        )
    );

COMMIT;
