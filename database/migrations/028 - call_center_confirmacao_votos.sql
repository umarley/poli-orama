-- Estrutura operacional para prospeccao e confirmacao declarada de votos.
-- A pessoa e unica por campanha; a lideranca ativa define a autoria da captacao.

ALTER TABLE eleicao.status_eleitor_eleicao
    DROP CONSTRAINT IF EXISTS status_eleitor_eleicao_status_check;

UPDATE eleicao.status_eleitor_eleicao
SET status = CASE status
    WHEN 'contatado' THEN 'indeciso'
    WHEN 'pendente' THEN 'retorno_agendado'
    WHEN 'precisa_apoio' THEN 'indeciso'
    WHEN 'sem_resposta' THEN 'tentativa_sem_resposta'
    ELSE status
END
WHERE status IN ('contatado','pendente','precisa_apoio','sem_resposta');

ALTER TABLE eleicao.status_eleitor_eleicao
    ADD CONSTRAINT status_eleitor_eleicao_status_check
    CHECK (status IN (
        'nao_contatado',
        'tentativa_sem_resposta',
        'retorno_agendado',
        'indeciso',
        'confirmado',
        'nao_apoia',
        'numero_invalido'
    ));

CREATE TABLE comunicacao.atendimento_eleitor (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id     BIGINT NOT NULL
                            REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    pessoa_id               BIGINT NOT NULL
                            REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    lideranca_id            BIGINT REFERENCES cadastro.lideranca(id) ON DELETE SET NULL,
    atendente_usuario_id    BIGINT NOT NULL REFERENCES auth.usuario(id),
    canal                   VARCHAR(20) NOT NULL DEFAULT 'ligacao'
                            CHECK (canal IN ('ligacao','whatsapp','presencial','outro')),
    resultado               VARCHAR(30) NOT NULL
                            CHECK (resultado IN (
                                'tentativa_sem_resposta',
                                'retorno_agendado',
                                'indeciso',
                                'confirmado',
                                'nao_apoia',
                                'numero_invalido'
                            )),
    observacao              TEXT,
    iniciado_em             TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    proximo_contato_em      TIMESTAMPTZ,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (finalizado_em >= iniciado_em),
    CHECK (resultado <> 'retorno_agendado' OR proximo_contato_em IS NOT NULL)
);

CREATE INDEX ix_atendimento_eleitor_fila
    ON comunicacao.atendimento_eleitor
    (tenant_id, campanha_eleicao_id, resultado, proximo_contato_em);

CREATE INDEX ix_atendimento_eleitor_pessoa
    ON comunicacao.atendimento_eleitor
    (tenant_id, campanha_eleicao_id, pessoa_id, finalizado_em DESC);

ALTER TABLE eleicao.confirmacao_operacional_voto
    ADD COLUMN IF NOT EXISTS lideranca_id BIGINT
        REFERENCES cadastro.lideranca(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS atendimento_eleitor_id BIGINT
        REFERENCES comunicacao.atendimento_eleitor(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS revogado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revogado_por_usuario_id BIGINT
        REFERENCES auth.usuario(id),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS ix_confirmacao_voto_lideranca
    ON eleicao.confirmacao_operacional_voto
    (tenant_id, campanha_eleicao_id, lideranca_id, confirmado)
    WHERE confirmado = TRUE AND revogado_em IS NULL;

COMMENT ON TABLE comunicacao.atendimento_eleitor IS
    'Historico imutavel das tentativas de contato do Call Center com cada eleitor.';
COMMENT ON COLUMN eleicao.confirmacao_operacional_voto.confirmado IS
    'Declaracao operacional de intencao de voto; nao comprova o voto depositado na urna.';
