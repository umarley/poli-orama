-- Evolui o atendimento ao eleitor para sessao operacional (lock, intencao de voto e indicadores).
-- Nao duplica dados de cadastro.pessoa: o atendimento apenas referencia a pessoa.

BEGIN;

INSERT INTO auth.permissao (codigo, modulo, acao, descricao)
VALUES
    (
        'comunicacao.atender',
        'comunicacao',
        'criar',
        'Iniciar, atualizar e encerrar atendimento ao eleitor'
    ),
    (
        'comunicacao.relatorios',
        'comunicacao',
        'visualizar',
        'Consultar indicadores e relatorios de atendimento'
    )
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo,
    acao = EXCLUDED.acao,
    descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo = 'comunicacao.atender'
WHERE pa.tenant_id IS NULL
  AND pa.codigo = 'telefonista'
ON CONFLICT DO NOTHING;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo = 'comunicacao.relatorios'
WHERE pa.tenant_id IS NULL
  AND pa.codigo = 'gestor'
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS comunicacao.motivo_rejeicao_voto (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    codigo          VARCHAR(40) NOT NULL,
    nome            VARCHAR(120) NOT NULL,
    descricao       VARCHAR(255),
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_motivo_rejeicao_voto_tenant_codigo UNIQUE (tenant_id, codigo)
);

INSERT INTO comunicacao.motivo_rejeicao_voto (tenant_id, codigo, nome, descricao)
SELECT NULL, v.codigo, v.nome, v.descricao
FROM (
    VALUES
        ('nao_conhece', 'Não conhece o candidato', 'O eleitor declarou não conhecer o candidato.'),
        ('prefere_outro', 'Prefere outro candidato', 'O eleitor declarou preferência por outro candidato.'),
        ('nao_confia', 'Não confia no candidato', 'O eleitor declarou desconfiança ou rejeição pessoal.'),
        ('discorda_propostas', 'Discorda das propostas', 'O eleitor rejeitou as propostas apresentadas.'),
        ('decepcionado', 'Decepcionado com a política', 'O eleitor recusou participar da escolha.'),
        ('outro', 'Outro motivo', 'Motivo complementar informado no atendimento.')
) AS v(codigo, nome, descricao)
WHERE NOT EXISTS (
    SELECT 1
      FROM comunicacao.motivo_rejeicao_voto atual
     WHERE atual.tenant_id IS NULL
       AND atual.codigo = v.codigo
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_motivo_rejeicao_voto_global_codigo
    ON comunicacao.motivo_rejeicao_voto (codigo)
    WHERE tenant_id IS NULL;

CREATE TABLE IF NOT EXISTS comunicacao.intencao_voto_historico (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    atendimento_id          BIGINT NOT NULL
                            REFERENCES comunicacao.atendimento_eleitor(id) ON DELETE CASCADE,
    pessoa_id               BIGINT NOT NULL
                            REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    intencao_voto           VARCHAR(30) NOT NULL
                            CHECK (intencao_voto IN (
                                'votara',
                                'nao_votara',
                                'indeciso',
                                'nao_respondeu'
                            )),
    motivo_rejeicao_id      BIGINT REFERENCES comunicacao.motivo_rejeicao_voto(id),
    motivo_observacao       TEXT,
    registrado_por          BIGINT REFERENCES auth.usuario(id),
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE
    constraint_row record;
BEGIN
    FOR constraint_row IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'comunicacao'
          AND t.relname = 'atendimento_eleitor'
          AND c.contype = 'c'
    LOOP
        EXECUTE format(
            'ALTER TABLE comunicacao.atendimento_eleitor DROP CONSTRAINT %I',
            constraint_row.conname
        );
    END LOOP;
END $$;

ALTER TABLE comunicacao.atendimento_eleitor
    ALTER COLUMN resultado DROP NOT NULL,
    ALTER COLUMN finalizado_em DROP NOT NULL,
    ALTER COLUMN finalizado_em DROP DEFAULT;

ALTER TABLE comunicacao.atendimento_eleitor
    ADD COLUMN IF NOT EXISTS situacao VARCHAR(30) NOT NULL DEFAULT 'concluido',
    ADD COLUMN IF NOT EXISTS canal_outro VARCHAR(80),
    ADD COLUMN IF NOT EXISTS intencao_voto VARCHAR(30),
    ADD COLUMN IF NOT EXISTS motivo_rejeicao_id BIGINT
        REFERENCES comunicacao.motivo_rejeicao_voto(id),
    ADD COLUMN IF NOT EXISTS motivo_observacao TEXT,
    ADD COLUMN IF NOT EXISTS motivo_encerramento TEXT,
    ADD COLUMN IF NOT EXISTS motivo_inativacao TEXT;

UPDATE comunicacao.atendimento_eleitor
SET situacao = CASE
    WHEN resultado = 'tentativa_sem_resposta' THEN 'sem_resposta'
    WHEN resultado = 'numero_invalido' THEN 'numero_invalido'
    ELSE 'concluido'
END
WHERE situacao = 'concluido'
  AND finalizado_em IS NOT NULL;

ALTER TABLE comunicacao.atendimento_eleitor
    ADD CONSTRAINT atendimento_eleitor_canal_check
        CHECK (canal IN ('ligacao', 'mensagem', 'whatsapp', 'presencial', 'outro')),
    ADD CONSTRAINT atendimento_eleitor_situacao_check
        CHECK (situacao IN (
            'em_atendimento',
            'concluido',
            'sem_resposta',
            'numero_invalido',
            'interrompido'
        )),
    ADD CONSTRAINT atendimento_eleitor_resultado_check
        CHECK (
            resultado IS NULL
            OR resultado IN (
                'tentativa_sem_resposta',
                'retorno_agendado',
                'indeciso',
                'confirmado',
                'nao_apoia',
                'numero_invalido',
                'contato_invalido',
                'concluido',
                'interrompido'
            )
        ),
    ADD CONSTRAINT atendimento_eleitor_intencao_check
        CHECK (
            intencao_voto IS NULL
            OR intencao_voto IN ('votara', 'nao_votara', 'indeciso', 'nao_respondeu')
        ),
    ADD CONSTRAINT atendimento_eleitor_periodo_check
        CHECK (finalizado_em IS NULL OR finalizado_em >= iniciado_em),
    ADD CONSTRAINT atendimento_eleitor_ativo_check
        CHECK (
            (situacao = 'em_atendimento' AND finalizado_em IS NULL)
            OR (situacao <> 'em_atendimento' AND finalizado_em IS NOT NULL)
        );

CREATE UNIQUE INDEX IF NOT EXISTS uq_atendimento_eleitor_pessoa_ativo
    ON comunicacao.atendimento_eleitor (tenant_id, pessoa_id)
    WHERE situacao = 'em_atendimento' AND finalizado_em IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_atendimento_eleitor_atendente_ativo
    ON comunicacao.atendimento_eleitor (tenant_id, atendente_usuario_id)
    WHERE situacao = 'em_atendimento' AND finalizado_em IS NULL;

CREATE INDEX IF NOT EXISTS ix_atendimento_eleitor_indicadores
    ON comunicacao.atendimento_eleitor
        (tenant_id, campanha_eleicao_id, situacao, canal, resultado, intencao_voto, iniciado_em);

CREATE INDEX IF NOT EXISTS ix_intencao_voto_historico_pessoa
    ON comunicacao.intencao_voto_historico (tenant_id, pessoa_id, criado_em DESC);

CREATE INDEX IF NOT EXISTS ix_intencao_voto_historico_atendimento
    ON comunicacao.intencao_voto_historico (tenant_id, atendimento_id);

CREATE INDEX IF NOT EXISTS ix_atendimento_eleitor_motivo_rejeicao
    ON comunicacao.atendimento_eleitor (motivo_rejeicao_id)
    WHERE motivo_rejeicao_id IS NOT NULL;

ALTER TABLE comunicacao.motivo_rejeicao_voto ENABLE ROW LEVEL SECURITY;
ALTER TABLE comunicacao.intencao_voto_historico ENABLE ROW LEVEL SECURITY;
ALTER TABLE comunicacao.atendimento_eleitor ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_isolamento_tenant ON comunicacao.motivo_rejeicao_voto;
CREATE POLICY pol_isolamento_tenant ON comunicacao.motivo_rejeicao_voto
    USING (tenant_id IS NULL OR tenant_id = global.tenant_atual());

DROP POLICY IF EXISTS pol_isolamento_tenant ON comunicacao.intencao_voto_historico;
CREATE POLICY pol_isolamento_tenant ON comunicacao.intencao_voto_historico
    USING (tenant_id = global.tenant_atual());

DROP POLICY IF EXISTS pol_isolamento_tenant ON comunicacao.atendimento_eleitor;
CREATE POLICY pol_isolamento_tenant ON comunicacao.atendimento_eleitor
    USING (tenant_id = global.tenant_atual());

GRANT SELECT, INSERT, UPDATE, DELETE ON comunicacao.motivo_rejeicao_voto TO app_inteligencia;
GRANT SELECT, INSERT, UPDATE, DELETE ON comunicacao.intencao_voto_historico TO app_inteligencia;
GRANT SELECT, INSERT, UPDATE, DELETE ON comunicacao.atendimento_eleitor TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA comunicacao TO app_inteligencia;

COMMENT ON TABLE comunicacao.motivo_rejeicao_voto IS
    'Catalogo de motivos para intencao negativa de voto, reutilizavel em filtros e relatorios.';
COMMENT ON TABLE comunicacao.intencao_voto_historico IS
    'Historico estruturado das respostas de intencao de voto ao longo dos atendimentos.';
COMMENT ON COLUMN comunicacao.atendimento_eleitor.situacao IS
    'Situacao operacional do atendimento: em andamento ou encerrado.';
COMMENT ON COLUMN comunicacao.atendimento_eleitor.intencao_voto IS
    'Intencao de voto declarada no atendimento; o historico fica em intencao_voto_historico.';

COMMIT;
