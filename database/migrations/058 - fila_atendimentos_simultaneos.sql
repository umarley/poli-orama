-- Permite vários atendimentos "em_atendimento" por telefonista.
-- O limite simultâneo passa a ser configurável em tenant_configuracao.preferencias
-- (chave maximo_atendimentos_simultaneos, padrão 10), validado no backend.

DROP INDEX IF EXISTS comunicacao.uq_atendimento_eleitor_atendente_ativo;

CREATE INDEX IF NOT EXISTS ix_atendimento_eleitor_atendente_ativo
    ON comunicacao.atendimento_eleitor (tenant_id, atendente_usuario_id, iniciado_em DESC)
    WHERE situacao = 'em_atendimento' AND finalizado_em IS NULL;

ALTER TABLE comunicacao.atendimento_eleitor
    ADD COLUMN IF NOT EXISTS ultima_visualizacao_em TIMESTAMPTZ;

UPDATE public.tenant_configuracao
   SET preferencias = COALESCE(preferencias, '{}'::jsonb)
                    || jsonb_build_object('maximo_atendimentos_simultaneos', 10),
       atualizado_em = now()
 WHERE NOT (COALESCE(preferencias, '{}'::jsonb) ? 'maximo_atendimentos_simultaneos');
