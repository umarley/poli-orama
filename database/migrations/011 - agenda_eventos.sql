BEGIN;

ALTER TABLE agenda.tipo_evento
    ADD COLUMN IF NOT EXISTS descricao VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE agenda.tipo_evento DROP CONSTRAINT IF EXISTS uq_tipo_evento_codigo;
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_evento_codigo_global
    ON agenda.tipo_evento (codigo) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_evento_codigo_tenant
    ON agenda.tipo_evento (tenant_id, codigo) WHERE tenant_id IS NOT NULL;

ALTER TABLE agenda.status_evento
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS descricao VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE agenda.status_evento DROP CONSTRAINT IF EXISTS uq_status_evento_codigo;
CREATE UNIQUE INDEX IF NOT EXISTS uq_status_evento_codigo_global
    ON agenda.status_evento (codigo) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_status_evento_codigo_tenant
    ON agenda.status_evento (tenant_id, codigo) WHERE tenant_id IS NOT NULL;

ALTER TABLE agenda.evento
    ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT,
    ADD COLUMN IF NOT EXISTS cancelado_por BIGINT REFERENCES auth.usuario(id),
    ADD COLUMN IF NOT EXISTS cancelado_em TIMESTAMPTZ;

ALTER TABLE agenda.evento_participante
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE agenda.evento_lideranca
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE agenda.convite
    ADD COLUMN IF NOT EXISTS descricao TEXT,
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE agenda.pauta_evento
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS agenda.lembrete_evento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    evento_id BIGINT NOT NULL REFERENCES agenda.evento(id) ON DELETE CASCADE,
    usuario_id BIGINT REFERENCES auth.usuario(id) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL DEFAULT 'evento_proximo'
        CHECK (tipo IN ('evento_proximo','evento_hoje','evento_atrasado')),
    mensagem VARCHAR(255) NOT NULL,
    agendado_para TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente','gerado','lido','cancelado')),
    gerado_em TIMESTAMPTZ,
    lido_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lembrete_evento UNIQUE
        (tenant_id, evento_id, usuario_id, tipo, agendado_para)
);
CREATE INDEX IF NOT EXISTS ix_lembrete_evento_pendente
    ON agenda.lembrete_evento (tenant_id, status, agendado_para);

CREATE TABLE IF NOT EXISTS agenda.insight_evento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    evento_id BIGINT REFERENCES agenda.evento(id) ON DELETE CASCADE,
    tipo VARCHAR(30) NOT NULL
        CHECK (tipo IN ('tema_recorrente','demanda_recorrente','palavra_chave')),
    tema VARCHAR(120) NOT NULL,
    frequencia INTEGER NOT NULL DEFAULT 1 CHECK (frequencia > 0),
    score NUMERIC(5,2) CHECK (score BETWEEN 0 AND 100),
    detalhes JSONB NOT NULL DEFAULT '{}'::jsonb,
    gerado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_insight_evento UNIQUE (tenant_id, tipo, tema)
);
CREATE INDEX IF NOT EXISTS ix_insight_evento_tenant
    ON agenda.insight_evento (tenant_id, frequencia DESC, score DESC);

INSERT INTO agenda.tipo_evento
    (tenant_id, codigo, nome, descricao)
SELECT NULL, seed.codigo, seed.nome, seed.descricao
FROM (VALUES
    ('politico', 'Politico', 'Agenda politica e reunioes institucionais'),
    ('religioso', 'Religioso', 'Cultos, celebracoes e encontros religiosos'),
    ('comunitario', 'Comunitario', 'Atividades com bairros e comunidades'),
    ('partidario', 'Partidario', 'Reunioes e atividades partidarias'),
    ('institucional', 'Institucional', 'Compromissos com orgaos e entidades'),
    ('cultural', 'Cultural', 'Eventos culturais e comemorativos')
) AS seed(codigo, nome, descricao)
WHERE NOT EXISTS (
    SELECT 1 FROM agenda.tipo_evento t
    WHERE t.tenant_id IS NULL AND t.codigo = seed.codigo
);

INSERT INTO auth.permissao (codigo, modulo, acao, descricao) VALUES
    ('agenda.exportar', 'agenda', 'exportar', 'Exportar agenda e eventos'),
    ('agenda.administrar', 'agenda', 'administrar', 'Administrar catalogos da agenda')
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo, acao = EXCLUDED.acao, descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id FROM auth.perfil_acesso pa CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL AND pa.codigo IN ('gestor_saas', 'gestor')
  AND p.modulo = 'agenda'
ON CONFLICT DO NOTHING;
INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id FROM auth.perfil_acesso pa JOIN auth.permissao p
  ON p.codigo = 'agenda.exportar'
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('coordenador_territorial', 'administrativo')
ON CONFLICT DO NOTHING;

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.tipo_evento;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.tipo_evento
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.status_evento;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.status_evento
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.evento_participante;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.evento_participante
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.convite;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.convite
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.pauta_evento;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.pauta_evento
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DO $$
DECLARE item RECORD;
BEGIN
    FOR item IN SELECT * FROM (VALUES
        ('agenda', 'tipo_evento'), ('agenda', 'status_evento'),
        ('agenda', 'lembrete_evento'), ('agenda', 'insight_evento')
    ) AS scoped(schema_name, table_name)
    LOOP
        EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
                       item.schema_name, item.table_name);
        EXECUTE format('DROP POLICY IF EXISTS pol_isolamento_tenant ON %I.%I',
                       item.schema_name, item.table_name);
        EXECUTE format(
            'CREATE POLICY pol_isolamento_tenant ON %I.%I '
            'USING (tenant_id IS NULL OR tenant_id = global.tenant_atual()) '
            'WITH CHECK (tenant_id IS NULL OR tenant_id = global.tenant_atual())',
            item.schema_name, item.table_name);
    END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA agenda TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA agenda TO app_inteligencia;

COMMIT;
