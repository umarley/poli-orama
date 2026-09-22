BEGIN;

-- Evolui a estrutura criada pela migration 063 sem exigir sua reexecucao.
-- Cada rota operacional existente origina um template e um planejamento. Os IDs e
-- UUIDs dos registros operacionais sao reutilizados nas tabelas de snapshot para
-- preservar URLs, filas offline, execucoes, movimentacoes, fotografias e auditoria.
DO $$
BEGIN
    IF to_regclass('anuncio.rota_comunicacao') IS NULL
       OR NOT EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema = 'anuncio'
             AND table_name = 'rota_comunicacao'
             AND column_name = 'data_execucao'
       ) THEN
        RAISE EXCEPTION
            'A migration 064 requer a estrutura operacional original da migration 063';
    END IF;
END $$;

COMMENT ON SCHEMA anuncio IS 'Templates, planejamentos e execucoes de rotas de comunicacao.';

-- Instancia operacional datada e atribuida, criada a partir do template.
CREATE TABLE anuncio.rota_comunicacao_planejamento (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    rota_id BIGINT NOT NULL,
    rota_nome VARCHAR(180) NOT NULL,
    rota_descricao TEXT,
    territorio_id BIGINT,
    territorio_nome VARCHAR(180),
    equipe_id BIGINT,
    usuario_responsavel_id BIGINT,
    data_execucao DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PLANEJADA'
        CHECK (status IN ('PLANEJADA','LIBERADA','EM_EXECUCAO','CONCLUIDA','CANCELADA')),
    observacao TEXT,
    criado_por BIGINT NOT NULL,
    atualizado_por BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_planejamento_atribuicao
        CHECK (equipe_id IS NOT NULL OR usuario_responsavel_id IS NOT NULL),
    CONSTRAINT fk_planejamento_rota_tenant FOREIGN KEY (tenant_id, rota_id)
        REFERENCES anuncio.rota_comunicacao(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_planejamento_equipe_tenant FOREIGN KEY (tenant_id, equipe_id)
        REFERENCES cadastro.equipe(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_planejamento_usuario_tenant FOREIGN KEY (tenant_id, usuario_responsavel_id)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_planejamento_criado_por_tenant FOREIGN KEY (tenant_id, criado_por)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_planejamento_atualizado_por_tenant FOREIGN KEY (tenant_id, atualizado_por)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE SET NULL (atualizado_por),
    CONSTRAINT uq_planejamento_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_planejamento_tenant_rota_id UNIQUE (tenant_id, rota_id, id)
);

-- Snapshot estrutural: alteracoes posteriores no template nao afetam o historico.
CREATE TABLE anuncio.rota_comunicacao_planejamento_ponto (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    planejamento_id BIGINT NOT NULL,
    rota_id BIGINT NOT NULL,
    rota_ponto_origem_id BIGINT,
    ordem INTEGER NOT NULL CHECK (ordem >= 1),
    descricao_local VARCHAR(180) NOT NULL,
    endereco TEXT,
    latitude_planejada NUMERIC(10,7),
    longitude_planejada NUMERIC(10,7),
    observacao TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDENTE'
        CHECK (status IN ('PENDENTE','EM_EXECUCAO','INSTALADO','RECOLHIDO',
                          'RECOLHIDO_PARCIALMENTE','COM_EXTRAVIO','NAO_EXECUTADO')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_planejamento_ponto_planejamento_tenant
        FOREIGN KEY (tenant_id, rota_id, planejamento_id)
        REFERENCES anuncio.rota_comunicacao_planejamento(tenant_id, rota_id, id)
        ON DELETE CASCADE,
    CONSTRAINT fk_planejamento_ponto_origem_tenant
        FOREIGN KEY (tenant_id, rota_ponto_origem_id)
        REFERENCES anuncio.rota_comunicacao_ponto(tenant_id, id)
        ON DELETE SET NULL (rota_ponto_origem_id),
    CONSTRAINT uq_planejamento_ponto_ordem UNIQUE (planejamento_id, ordem),
    CONSTRAINT uq_planejamento_ponto_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_planejamento_ponto_cadeia UNIQUE (tenant_id, planejamento_id, rota_id, id),
    CONSTRAINT ck_planejamento_ponto_coordenadas CHECK (
        (latitude_planejada IS NULL AND longitude_planejada IS NULL)
        OR (latitude_planejada BETWEEN -90 AND 90 AND longitude_planejada BETWEEN -180 AND 180)
    )
);

CREATE TABLE anuncio.rota_comunicacao_planejamento_ponto_material (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    ponto_id BIGINT NOT NULL,
    material_id BIGINT NOT NULL,
    quantidade_planejada INTEGER NOT NULL CHECK (quantidade_planejada > 0),
    quantidade_instalada INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_instalada >= 0),
    quantidade_recolhida INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_recolhida >= 0),
    quantidade_extraviada INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_extraviada >= 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_planejamento_material_ponto_tenant FOREIGN KEY (tenant_id, ponto_id)
        REFERENCES anuncio.rota_comunicacao_planejamento_ponto(tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_planejamento_material_material_tenant FOREIGN KEY (tenant_id, material_id)
        REFERENCES anuncio.material_comunicacao(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT uq_planejamento_ponto_material UNIQUE (ponto_id, material_id),
    CONSTRAINT uq_planejamento_material_tenant_ponto UNIQUE (tenant_id, ponto_id, material_id),
    CONSTRAINT ck_planejamento_material_baixas CHECK (
        quantidade_recolhida + quantidade_extraviada <= quantidade_instalada
    ),
    CONSTRAINT ck_planejamento_material_instalacao CHECK (
        quantidade_instalada <= quantidade_planejada
    )
);

-- Um planejamento e um snapshot sao criados para cada rota operacional legada.
INSERT INTO anuncio.rota_comunicacao_planejamento (
    id, uuid_publico, tenant_id, rota_id, rota_nome, rota_descricao,
    territorio_id, territorio_nome, equipe_id, usuario_responsavel_id,
    data_execucao, status, observacao, criado_por, atualizado_por,
    criado_em, atualizado_em
)
OVERRIDING SYSTEM VALUE
SELECT
    r.id, r.uuid_publico, r.tenant_id, r.id, r.nome, r.descricao,
    r.territorio_id, t.nome, r.equipe_id, r.usuario_responsavel_id,
    r.data_execucao, r.status, NULL, r.criado_por, r.atualizado_por,
    r.criado_em, r.atualizado_em
FROM anuncio.rota_comunicacao r
LEFT JOIN territorio.territorio t
  ON t.tenant_id = r.tenant_id AND t.id = r.territorio_id;

INSERT INTO anuncio.rota_comunicacao_planejamento_ponto (
    id, uuid_publico, tenant_id, planejamento_id, rota_id,
    rota_ponto_origem_id, ordem, descricao_local, endereco,
    latitude_planejada, longitude_planejada, observacao, status,
    criado_em, atualizado_em
)
OVERRIDING SYSTEM VALUE
SELECT
    p.id, p.uuid_publico, p.tenant_id, p.rota_id, p.rota_id,
    p.id, p.ordem, p.descricao_local, p.endereco,
    p.latitude_planejada, p.longitude_planejada, p.observacao, p.status,
    p.criado_em, p.atualizado_em
FROM anuncio.rota_comunicacao_ponto p;

INSERT INTO anuncio.rota_comunicacao_planejamento_ponto_material (
    id, tenant_id, ponto_id, material_id, quantidade_planejada,
    quantidade_instalada, quantidade_recolhida, quantidade_extraviada,
    criado_em, atualizado_em
)
OVERRIDING SYSTEM VALUE
SELECT
    pm.id, pm.tenant_id, pm.ponto_id, pm.material_id, pm.quantidade_planejada,
    pm.quantidade_instalada, pm.quantidade_recolhida, pm.quantidade_extraviada,
    pm.criado_em, pm.atualizado_em
FROM anuncio.rota_comunicacao_ponto_material pm;

-- Mantem as sequencias coerentes depois da reutilizacao dos IDs legados.
SELECT setval(
    pg_get_serial_sequence('anuncio.rota_comunicacao_planejamento', 'id'),
    COALESCE((SELECT max(id) FROM anuncio.rota_comunicacao_planejamento), 1),
    EXISTS (SELECT 1 FROM anuncio.rota_comunicacao_planejamento)
);
SELECT setval(
    pg_get_serial_sequence('anuncio.rota_comunicacao_planejamento_ponto', 'id'),
    COALESCE((SELECT max(id) FROM anuncio.rota_comunicacao_planejamento_ponto), 1),
    EXISTS (SELECT 1 FROM anuncio.rota_comunicacao_planejamento_ponto)
);
SELECT setval(
    pg_get_serial_sequence('anuncio.rota_comunicacao_planejamento_ponto_material', 'id'),
    COALESCE((SELECT max(id) FROM anuncio.rota_comunicacao_planejamento_ponto_material), 1),
    EXISTS (SELECT 1 FROM anuncio.rota_comunicacao_planejamento_ponto_material)
);

-- Associa execucoes e movimentacoes existentes ao planejamento migrado.
ALTER TABLE anuncio.rota_comunicacao_execucao
    ADD COLUMN planejamento_id BIGINT;
ALTER TABLE anuncio.rota_comunicacao_material_movimentacao
    ADD COLUMN planejamento_id BIGINT;

-- A 063 associava indevidamente o trigger de atualizado_em a esta tabela,
-- que possui apenas criado_em. Remove-o antes do backfill.
DROP TRIGGER IF EXISTS trg_atualiza_timestamp
    ON anuncio.rota_comunicacao_material_movimentacao;

UPDATE anuncio.rota_comunicacao_execucao
SET planejamento_id = rota_id;
UPDATE anuncio.rota_comunicacao_material_movimentacao
SET planejamento_id = rota_id;

ALTER TABLE anuncio.rota_comunicacao_execucao
    ALTER COLUMN planejamento_id SET NOT NULL;
ALTER TABLE anuncio.rota_comunicacao_material_movimentacao
    ALTER COLUMN planejamento_id SET NOT NULL;

-- Troca as cadeias de integridade para que a execucao aponte ao snapshot.
-- As primeiras versoes da 063 usaram nomes diferentes (ou nomes automaticos)
-- para estas FKs. Localiza-as pelas tabelas referenciadas, sem depender do nome.
DO $$
DECLARE
    restricao RECORD;
BEGIN
    FOR restricao IN
        SELECT c.conname
        FROM pg_constraint c
        WHERE c.conrelid =
                  'anuncio.rota_comunicacao_material_movimentacao'::regclass
          AND c.contype = 'f'
          AND c.confrelid IN (
              'anuncio.rota_comunicacao_execucao'::regclass,
              'anuncio.rota_comunicacao_ponto_material'::regclass
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE anuncio.rota_comunicacao_material_movimentacao '
            'DROP CONSTRAINT %I',
            restricao.conname
        );
    END LOOP;

    FOR restricao IN
        SELECT c.conname
        FROM pg_constraint c
        WHERE c.conrelid = 'anuncio.rota_comunicacao_execucao'::regclass
          AND c.contype = 'f'
          AND c.confrelid = 'anuncio.rota_comunicacao_ponto'::regclass
    LOOP
        EXECUTE format(
            'ALTER TABLE anuncio.rota_comunicacao_execucao '
            'DROP CONSTRAINT %I',
            restricao.conname
        );
    END LOOP;
END $$;

-- A chave unica antiga pode existir com este nome mesmo quando a FK acima nao
-- existe. IF EXISTS permite a evolucao de todas as variantes ja implantadas.
ALTER TABLE anuncio.rota_comunicacao_execucao
    DROP CONSTRAINT IF EXISTS uq_execucao_cadeia;

ALTER TABLE anuncio.rota_comunicacao_execucao
    ADD CONSTRAINT fk_execucao_ponto_cadeia FOREIGN KEY
        (tenant_id, planejamento_id, rota_id, ponto_id)
        REFERENCES anuncio.rota_comunicacao_planejamento_ponto
        (tenant_id, planejamento_id, rota_id, id) ON DELETE CASCADE,
    ADD CONSTRAINT uq_execucao_cadeia
        UNIQUE (tenant_id, id, planejamento_id, rota_id, ponto_id, usuario_id);

ALTER TABLE anuncio.rota_comunicacao_material_movimentacao
    ADD CONSTRAINT fk_movimentacao_execucao_cadeia FOREIGN KEY
        (tenant_id, execucao_id, planejamento_id, rota_id, ponto_id, usuario_id)
        REFERENCES anuncio.rota_comunicacao_execucao
        (tenant_id, id, planejamento_id, rota_id, ponto_id, usuario_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_movimentacao_material_ponto_tenant FOREIGN KEY
        (tenant_id, ponto_id, material_id)
        REFERENCES anuncio.rota_comunicacao_planejamento_ponto_material
        (tenant_id, ponto_id, material_id) ON DELETE RESTRICT;

-- A estrutura original passa a representar somente o template reutilizavel.
ALTER TABLE anuncio.rota_comunicacao
    ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT TRUE;

DROP INDEX IF EXISTS anuncio.ix_rota_comunicacao_tenant_data_status;
DROP INDEX IF EXISTS anuncio.ix_rota_comunicacao_equipe;
DROP INDEX IF EXISTS anuncio.ix_rota_comunicacao_usuario;
DROP INDEX IF EXISTS anuncio.ix_rota_ponto_status;
DROP INDEX IF EXISTS anuncio.ix_execucao_rota_ponto_data;

ALTER TABLE anuncio.rota_comunicacao
    DROP COLUMN data_execucao,
    DROP COLUMN status,
    DROP COLUMN equipe_id,
    DROP COLUMN usuario_responsavel_id;
ALTER TABLE anuncio.rota_comunicacao_ponto
    DROP COLUMN status;
ALTER TABLE anuncio.rota_comunicacao_ponto_material
    DROP COLUMN quantidade_instalada,
    DROP COLUMN quantidade_recolhida,
    DROP COLUMN quantidade_extraviada;

CREATE INDEX ix_rota_comunicacao_tenant_ativo
    ON anuncio.rota_comunicacao(tenant_id, ativo, nome);
CREATE INDEX ix_planejamento_tenant_data_status
    ON anuncio.rota_comunicacao_planejamento(tenant_id, data_execucao, status);
CREATE INDEX ix_planejamento_equipe
    ON anuncio.rota_comunicacao_planejamento(tenant_id, equipe_id, data_execucao);
CREATE INDEX ix_planejamento_usuario
    ON anuncio.rota_comunicacao_planejamento(tenant_id, usuario_responsavel_id, data_execucao);
CREATE INDEX ix_planejamento_rota
    ON anuncio.rota_comunicacao_planejamento(tenant_id, rota_id, data_execucao);
CREATE INDEX ix_planejamento_ponto_status
    ON anuncio.rota_comunicacao_planejamento_ponto
       (tenant_id, planejamento_id, status, ordem);
CREATE INDEX ix_execucao_planejamento_ponto_data
    ON anuncio.rota_comunicacao_execucao(tenant_id, planejamento_id, ponto_id, executado_em DESC);

DO $$
DECLARE tabela TEXT;
BEGIN
    FOREACH tabela IN ARRAY ARRAY[
        'rota_comunicacao_planejamento',
        'rota_comunicacao_planejamento_ponto',
        'rota_comunicacao_planejamento_ponto_material'
    ] LOOP
        EXECUTE format('CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON anuncio.%I '
                       'FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp()', tabela);
        EXECUTE format('ALTER TABLE anuncio.%I ENABLE ROW LEVEL SECURITY', tabela);
        EXECUTE format('ALTER TABLE anuncio.%I FORCE ROW LEVEL SECURITY', tabela);
        EXECUTE format('CREATE POLICY pol_isolamento_tenant ON anuncio.%I '
                       'USING (tenant_id = global.tenant_atual()) '
                       'WITH CHECK (tenant_id = global.tenant_atual())', tabela);
        EXECUTE format('CREATE TRIGGER trg_preenche_tenant BEFORE INSERT ON anuncio.%I '
                       'FOR EACH ROW EXECUTE FUNCTION global.fn_preenche_tenant()', tabela);
    END LOOP;
END $$;

UPDATE auth.perfil_acesso
SET descricao = 'Executa planejamentos de instalacao e recolhimento de materiais.'
WHERE tenant_id IS NULL AND codigo = 'motorista_motociclista';

UPDATE auth.permissao
SET descricao = 'Gerenciar templates e planejamentos'
WHERE codigo = 'anuncios.rota.gerenciar';

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA anuncio TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA anuncio TO app_inteligencia;

COMMIT;
