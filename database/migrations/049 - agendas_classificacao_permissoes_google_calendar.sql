BEGIN;

CREATE TABLE IF NOT EXISTS agenda.agenda (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome VARCHAR(120) NOT NULL,
    descricao TEXT,
    natureza_candidato VARCHAR(20) NOT NULL DEFAULT 'rede'
        CHECK (natureza_candidato IN ('rede', 'recurso', 'rua')),
    frente_comunidade VARCHAR(30) NOT NULL DEFAULT 'juventude'
        CHECK (frente_comunidade IN (
            'juventude', 'sindicalista', 'cultura', 'engenharia',
            'saude', 'educacao', 'dobradas'
        )),
    tipo_agenda VARCHAR(30) NOT NULL DEFAULT 'agenda_candidato'
        CHECK (tipo_agenda IN (
            'fixa_campanha', 'agenda_aberta', 'agenda_candidato'
        )),
    visibilidade VARCHAR(12) NOT NULL DEFAULT 'publica'
        CHECK (visibilidade IN ('publica', 'restrita')),
    cor VARCHAR(7) NOT NULL DEFAULT '#1677ff'
        CHECK (cor ~ '^#[0-9A-Fa-f]{6}$'),
    padrao BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por BIGINT REFERENCES auth.usuario(id),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_agenda_nome_ativa
    ON agenda.agenda (tenant_id, lower(nome)) WHERE excluido_em IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_agenda_padrao_tenant
    ON agenda.agenda (tenant_id) WHERE padrao AND excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_agenda_classificacao
    ON agenda.agenda (tenant_id, visibilidade, frente_comunidade, tipo_agenda)
    WHERE excluido_em IS NULL;

INSERT INTO agenda.agenda (
    tenant_id, nome, descricao, natureza_candidato, frente_comunidade,
    tipo_agenda, visibilidade, cor, padrao
)
SELECT t.id, 'Agenda geral',
       'Agenda padrao criada para preservar os compromissos existentes.',
       'rede', 'juventude', 'agenda_candidato', 'publica', '#1677ff', TRUE
FROM public.tenant t
WHERE NOT EXISTS (
    SELECT 1 FROM agenda.agenda a
    WHERE a.tenant_id = t.id AND a.padrao AND a.excluido_em IS NULL
);

ALTER TABLE agenda.evento
    ADD COLUMN IF NOT EXISTS agenda_id BIGINT REFERENCES agenda.agenda(id);
UPDATE agenda.evento e
SET agenda_id = a.id
FROM agenda.agenda a
WHERE e.agenda_id IS NULL AND a.tenant_id = e.tenant_id AND a.padrao;
ALTER TABLE agenda.evento ALTER COLUMN agenda_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_evento_agenda_data
    ON agenda.evento (tenant_id, agenda_id, data_inicio)
    WHERE excluido_em IS NULL;

-- Links anonimos de presenca nunca podem expor compromissos de agenda restrita.
CREATE OR REPLACE FUNCTION agenda.fn_evento_publico(p_uuid UUID)
RETURNS TABLE (
    id BIGINT,
    uuid_publico UUID,
    tenant_id BIGINT,
    titulo VARCHAR(180),
    data_inicio TIMESTAMPTZ,
    data_fim TIMESTAMPTZ,
    local_nome VARCHAR(180)
)
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = pg_catalog, public, agenda
AS $$
    SELECT e.id, e.uuid_publico, e.tenant_id, e.titulo,
           e.data_inicio, e.data_fim, e.local_nome
      FROM agenda.evento e
      JOIN agenda.agenda a ON a.id = e.agenda_id
      JOIN public.tenant t ON t.id = e.tenant_id
     WHERE e.uuid_publico = p_uuid
       AND a.visibilidade = 'publica'
       AND a.ativo
       AND a.excluido_em IS NULL
       AND e.excluido_em IS NULL
       AND e.cancelado_em IS NULL
       AND t.excluido_em IS NULL
       AND t.status IN ('ativo', 'trial')
     LIMIT 1
$$;

CREATE TABLE IF NOT EXISTS agenda.agenda_usuario (
    agenda_id BIGINT NOT NULL REFERENCES agenda.agenda(id) ON DELETE CASCADE,
    usuario_id BIGINT NOT NULL REFERENCES auth.usuario(id) ON DELETE CASCADE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pode_visualizar BOOLEAN NOT NULL DEFAULT TRUE,
    pode_criar BOOLEAN NOT NULL DEFAULT FALSE,
    pode_editar BOOLEAN NOT NULL DEFAULT FALSE,
    pode_alterar_classificacao BOOLEAN NOT NULL DEFAULT FALSE,
    pode_excluir BOOLEAN NOT NULL DEFAULT FALSE,
    pode_administrar_usuarios BOOLEAN NOT NULL DEFAULT FALSE,
    pode_administrar_agenda BOOLEAN NOT NULL DEFAULT FALSE,
    criado_por BIGINT REFERENCES auth.usuario(id),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (agenda_id, usuario_id)
);
CREATE INDEX IF NOT EXISTS ix_agenda_usuario_usuario
    ON agenda.agenda_usuario (tenant_id, usuario_id, agenda_id);

-- Uma autorizacao Google pertence a um usuario. Uma mesma conta pode vincular
-- varias agendas do sistema, cada uma a um calendario Google diferente.
CREATE TABLE IF NOT EXISTS agenda.google_conta_usuario (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    usuario_id BIGINT NOT NULL REFERENCES auth.usuario(id) ON DELETE CASCADE,
    google_subject VARCHAR(255) NOT NULL,
    email VARCHAR(180),
    refresh_token_criptografado TEXT NOT NULL,
    access_token_criptografado TEXT,
    access_token_expira_em TIMESTAMPTZ,
    escopos TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ativa'
        CHECK (status IN ('ativa', 'revogada', 'erro')),
    ultimo_erro TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, usuario_id),
    UNIQUE (tenant_id, google_subject)
);

CREATE TABLE IF NOT EXISTS agenda.google_oauth_estado (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    usuario_id BIGINT NOT NULL REFERENCES auth.usuario(id) ON DELETE CASCADE,
    estado_hash CHAR(64) NOT NULL UNIQUE,
    code_verifier_criptografado TEXT NOT NULL,
    expira_em TIMESTAMPTZ NOT NULL,
    consumido_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_google_oauth_estado_expiracao
    ON agenda.google_oauth_estado (expira_em) WHERE consumido_em IS NULL;

CREATE OR REPLACE FUNCTION agenda.fn_consumir_google_oauth_estado(p_estado_hash TEXT)
RETURNS TABLE (
    tenant_id BIGINT,
    usuario_id BIGINT,
    code_verifier_criptografado TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, agenda
AS $$
BEGIN
    RETURN QUERY
    UPDATE agenda.google_oauth_estado s
       SET consumido_em = now()
     WHERE s.estado_hash = p_estado_hash
       AND s.consumido_em IS NULL
       AND s.expira_em > now()
    RETURNING s.tenant_id, s.usuario_id, s.code_verifier_criptografado;
END;
$$;
REVOKE ALL ON FUNCTION agenda.fn_consumir_google_oauth_estado(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION agenda.fn_consumir_google_oauth_estado(TEXT) TO app_inteligencia;

CREATE TABLE IF NOT EXISTS agenda.google_integracao_agenda (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    agenda_id BIGINT NOT NULL REFERENCES agenda.agenda(id) ON DELETE CASCADE,
    google_conta_id BIGINT NOT NULL REFERENCES agenda.google_conta_usuario(id) ON DELETE CASCADE,
    google_calendar_id VARCHAR(1024) NOT NULL,
    google_calendar_nome VARCHAR(255) NOT NULL,
    direcao VARCHAR(20) NOT NULL DEFAULT 'bidirecional'
        CHECK (direcao IN ('sistema_google', 'google_sistema', 'bidirecional')),
    sync_token TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ativa'
        CHECK (status IN ('ativa', 'pausada', 'erro')),
    ultima_sincronizacao_em TIMESTAMPTZ,
    ultimo_erro TEXT,
    criado_por BIGINT REFERENCES auth.usuario(id),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (agenda_id),
    UNIQUE (google_conta_id, google_calendar_id)
);

CREATE TABLE IF NOT EXISTS agenda.google_evento_vinculo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    integracao_id BIGINT NOT NULL REFERENCES agenda.google_integracao_agenda(id) ON DELETE CASCADE,
    evento_id BIGINT REFERENCES agenda.evento(id) ON DELETE CASCADE,
    google_event_id VARCHAR(1024) NOT NULL,
    google_etag VARCHAR(255),
    google_atualizado_em TIMESTAMPTZ,
    sistema_atualizado_em TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'sincronizado'
        CHECK (status IN ('pendente', 'sincronizado', 'conflito', 'excluido', 'erro')),
    ultimo_erro TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (integracao_id, evento_id),
    UNIQUE (integracao_id, google_event_id)
);

INSERT INTO auth.permissao (codigo, modulo, acao, descricao) VALUES
    ('agenda.alterar_classificacao', 'agenda', 'editar', 'Alterar classificacoes de agendas'),
    ('agenda.excluir', 'agenda', 'excluir', 'Excluir agendas e compromissos'),
    ('agenda.administrar_usuarios', 'agenda', 'administrar', 'Administrar usuarios das agendas'),
    ('agenda.integrar_google', 'agenda', 'administrar', 'Configurar e sincronizar Google Agenda')
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo, acao = EXCLUDED.acao, descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('gestor_saas', 'gestor')
  AND p.codigo IN (
      'agenda.alterar_classificacao', 'agenda.excluir',
      'agenda.administrar_usuarios', 'agenda.integrar_google'
  )
ON CONFLICT DO NOTHING;

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.agenda;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.agenda
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.agenda_usuario;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.agenda_usuario
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.google_conta_usuario;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.google_conta_usuario
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.google_integracao_agenda;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.google_integracao_agenda
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON agenda.google_evento_vinculo;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON agenda.google_evento_vinculo
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DO $$
DECLARE item RECORD;
BEGIN
    FOR item IN SELECT * FROM (VALUES
        ('agenda'), ('agenda_usuario'), ('google_conta_usuario'),
        ('google_oauth_estado'), ('google_integracao_agenda'), ('google_evento_vinculo')
    ) AS scoped(table_name)
    LOOP
        EXECUTE format('ALTER TABLE agenda.%I ENABLE ROW LEVEL SECURITY', item.table_name);
        EXECUTE format('DROP POLICY IF EXISTS pol_isolamento_tenant ON agenda.%I', item.table_name);
        EXECUTE format(
            'CREATE POLICY pol_isolamento_tenant ON agenda.%I '
            'USING (tenant_id = global.tenant_atual()) '
            'WITH CHECK (tenant_id = global.tenant_atual())', item.table_name
        );
    END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA agenda TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA agenda TO app_inteligencia;

COMMIT;
