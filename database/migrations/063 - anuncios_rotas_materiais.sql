BEGIN;

CREATE SCHEMA IF NOT EXISTS anuncio;
COMMENT ON SCHEMA anuncio IS 'Materiais, equipes e rotas de comunicacao.';

-- Reutiliza as equipes compartilhadas pelo Poliorama.
ALTER TABLE cadastro.equipe
    ADD COLUMN IF NOT EXISTS uuid_publico UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS descricao TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_equipe_uuid_publico ON cadastro.equipe(uuid_publico);
CREATE UNIQUE INDEX IF NOT EXISTS uq_equipe_tenant_id ON cadastro.equipe(tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_tenant_id ON auth.usuario(tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_territorio_tenant_id ON territorio.territorio(tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_lideranca_tenant_id ON cadastro.lideranca(tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pessoa_tenant_id ON cadastro.pessoa(tenant_id, id);

ALTER TABLE cadastro.equipe
    ADD CONSTRAINT fk_equipe_lideranca_tenant FOREIGN KEY (tenant_id, lideranca_id)
        REFERENCES cadastro.lideranca(tenant_id, id) ON DELETE SET NULL (lideranca_id),
    ADD CONSTRAINT fk_equipe_territorio_tenant FOREIGN KEY (tenant_id, territorio_id)
        REFERENCES territorio.territorio(tenant_id, id) ON DELETE SET NULL (territorio_id);
ALTER TABLE cadastro.equipe_pessoa
    ADD CONSTRAINT fk_equipe_pessoa_equipe_tenant FOREIGN KEY (tenant_id, equipe_id)
        REFERENCES cadastro.equipe(tenant_id, id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_equipe_pessoa_pessoa_tenant FOREIGN KEY (tenant_id, pessoa_id)
        REFERENCES cadastro.pessoa(tenant_id, id) ON DELETE CASCADE;

CREATE TABLE anuncio.material_comunicacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome VARCHAR(120) NOT NULL,
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_material_criado_por_tenant FOREIGN KEY (tenant_id, criado_por)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE SET NULL (criado_por),
    CONSTRAINT uq_material_comunicacao_nome UNIQUE (tenant_id, nome),
    CONSTRAINT uq_material_comunicacao_tenant_id UNIQUE (tenant_id, id)
);

-- Na versao inicial cada rota tambem era sua propria instancia operacional.
CREATE TABLE anuncio.rota_comunicacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome VARCHAR(180) NOT NULL,
    descricao TEXT,
    data_execucao DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PLANEJADA'
        CHECK (status IN ('PLANEJADA','LIBERADA','EM_EXECUCAO','CONCLUIDA','CANCELADA')),
    equipe_id BIGINT,
    usuario_responsavel_id BIGINT,
    territorio_id BIGINT,
    criado_por BIGINT NOT NULL,
    atualizado_por BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_rota_atribuicao CHECK (equipe_id IS NOT NULL OR usuario_responsavel_id IS NOT NULL),
    CONSTRAINT fk_rota_equipe_tenant FOREIGN KEY (tenant_id, equipe_id)
        REFERENCES cadastro.equipe(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_rota_usuario_tenant FOREIGN KEY (tenant_id, usuario_responsavel_id)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_rota_territorio_tenant FOREIGN KEY (tenant_id, territorio_id)
        REFERENCES territorio.territorio(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_rota_criado_por_tenant FOREIGN KEY (tenant_id, criado_por)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT fk_rota_atualizado_por_tenant FOREIGN KEY (tenant_id, atualizado_por)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE SET NULL (atualizado_por),
    CONSTRAINT uq_rota_comunicacao_nome UNIQUE (tenant_id, nome),
    CONSTRAINT uq_rota_comunicacao_tenant_id UNIQUE (tenant_id, id)
);

CREATE TABLE anuncio.rota_comunicacao_ponto (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    rota_id BIGINT NOT NULL,
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
    CONSTRAINT fk_rota_ponto_rota_tenant FOREIGN KEY (tenant_id, rota_id)
        REFERENCES anuncio.rota_comunicacao(tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT uq_rota_ponto_ordem UNIQUE (rota_id, ordem),
    CONSTRAINT uq_rota_ponto_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_rota_ponto_cadeia UNIQUE (tenant_id, rota_id, id),
    CONSTRAINT ck_rota_ponto_coordenadas CHECK (
        (latitude_planejada IS NULL AND longitude_planejada IS NULL)
        OR (latitude_planejada BETWEEN -90 AND 90 AND longitude_planejada BETWEEN -180 AND 180)
    )
);

CREATE TABLE anuncio.rota_comunicacao_ponto_material (
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
    CONSTRAINT fk_rota_ponto_material_ponto_tenant FOREIGN KEY (tenant_id, ponto_id)
        REFERENCES anuncio.rota_comunicacao_ponto(tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_rota_ponto_material_material_tenant FOREIGN KEY (tenant_id, material_id)
        REFERENCES anuncio.material_comunicacao(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT uq_rota_ponto_material UNIQUE (ponto_id, material_id),
    CONSTRAINT uq_rota_ponto_material_tenant_ponto UNIQUE (tenant_id, ponto_id, material_id),
    CONSTRAINT ck_rota_ponto_material_baixas CHECK (
        quantidade_recolhida + quantidade_extraviada <= quantidade_instalada
    ),
    CONSTRAINT ck_rota_ponto_material_instalacao CHECK (quantidade_instalada <= quantidade_planejada)
);

CREATE TABLE anuncio.rota_comunicacao_execucao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    rota_id BIGINT NOT NULL,
    ponto_id BIGINT NOT NULL,
    usuario_id BIGINT NOT NULL,
    tipo_operacao VARCHAR(20) NOT NULL CHECK (tipo_operacao IN ('INSTALACAO','RETIRADA')),
    chave_idempotencia VARCHAR(64) NOT NULL,
    latitude NUMERIC(10,7) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude NUMERIC(10,7) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    precisao NUMERIC(10,2) CHECK (precisao IS NULL OR precisao >= 0),
    observacao TEXT,
    executado_em TIMESTAMPTZ NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_execucao_ponto_cadeia FOREIGN KEY (tenant_id, rota_id, ponto_id)
        REFERENCES anuncio.rota_comunicacao_ponto(tenant_id, rota_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_execucao_usuario_tenant FOREIGN KEY (tenant_id, usuario_id)
        REFERENCES auth.usuario(tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT uq_execucao_idempotencia UNIQUE (tenant_id, usuario_id, chave_idempotencia),
    CONSTRAINT uq_execucao_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_execucao_cadeia UNIQUE (tenant_id, id, rota_id, ponto_id, usuario_id)
);

CREATE TABLE anuncio.rota_comunicacao_material_movimentacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    execucao_id BIGINT NOT NULL,
    rota_id BIGINT NOT NULL,
    ponto_id BIGINT NOT NULL,
    material_id BIGINT NOT NULL,
    usuario_id BIGINT NOT NULL,
    tipo_movimentacao VARCHAR(20) NOT NULL
        CHECK (tipo_movimentacao IN ('INSTALACAO','RECOLHIMENTO','EXTRAVIO')),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    latitude NUMERIC(10,7) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude NUMERIC(10,7) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    observacao TEXT,
    registrado_em TIMESTAMPTZ NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_movimentacao_execucao_cadeia FOREIGN KEY
        (tenant_id, execucao_id, rota_id, ponto_id, usuario_id)
        REFERENCES anuncio.rota_comunicacao_execucao
        (tenant_id, id, rota_id, ponto_id, usuario_id) ON DELETE CASCADE,
    CONSTRAINT fk_movimentacao_material_ponto_tenant FOREIGN KEY
        (tenant_id, ponto_id, material_id)
        REFERENCES anuncio.rota_comunicacao_ponto_material
        (tenant_id, ponto_id, material_id) ON DELETE RESTRICT,
    CONSTRAINT uq_execucao_material_movimentacao UNIQUE
        (execucao_id, material_id, tipo_movimentacao)
);

CREATE INDEX ix_material_comunicacao_tenant_ativo
    ON anuncio.material_comunicacao(tenant_id, ativo, nome);
CREATE INDEX ix_rota_comunicacao_tenant_data_status
    ON anuncio.rota_comunicacao(tenant_id, data_execucao, status);
CREATE INDEX ix_rota_comunicacao_equipe
    ON anuncio.rota_comunicacao(tenant_id, equipe_id, data_execucao);
CREATE INDEX ix_rota_comunicacao_usuario
    ON anuncio.rota_comunicacao(tenant_id, usuario_responsavel_id, data_execucao);
CREATE INDEX ix_rota_comunicacao_territorio
    ON anuncio.rota_comunicacao(tenant_id, territorio_id);
CREATE INDEX ix_rota_ponto_rota_ordem
    ON anuncio.rota_comunicacao_ponto(tenant_id, rota_id, ordem);
CREATE INDEX ix_rota_ponto_status
    ON anuncio.rota_comunicacao_ponto(tenant_id, rota_id, status, ordem);
CREATE INDEX ix_execucao_rota_ponto_data
    ON anuncio.rota_comunicacao_execucao(tenant_id, rota_id, ponto_id, executado_em DESC);
CREATE INDEX ix_movimentacao_material_data
    ON anuncio.rota_comunicacao_material_movimentacao(tenant_id, material_id, registrado_em DESC);

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON cadastro.equipe;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON cadastro.equipe
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DO $$
DECLARE tabela TEXT;
BEGIN
    FOREACH tabela IN ARRAY ARRAY[
        'material_comunicacao', 'rota_comunicacao', 'rota_comunicacao_ponto',
        'rota_comunicacao_ponto_material', 'rota_comunicacao_execucao',
        'rota_comunicacao_material_movimentacao'
    ] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON anuncio.%I', tabela);
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

INSERT INTO auth.perfil_acesso(tenant_id, nome, codigo, descricao, nivel, sistema)
SELECT NULL, 'Motorista / Motociclista', 'motorista_motociclista',
       'Executa rotas de instalacao e recolhimento de materiais.', 7, TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM auth.perfil_acesso
    WHERE tenant_id IS NULL AND codigo = 'motorista_motociclista'
);

INSERT INTO auth.permissao(codigo, modulo, acao, descricao) VALUES
    ('anuncios.visualizar', 'anuncios', 'visualizar', 'Visualizar o modulo de anuncios'),
    ('anuncios.gerenciar', 'anuncios', 'administrar', 'Administrar o modulo de anuncios'),
    ('anuncios.material.gerenciar', 'anuncios', 'administrar', 'Gerenciar materiais de comunicacao'),
    ('anuncios.equipe.gerenciar', 'anuncios', 'administrar', 'Gerenciar equipes de campo'),
    ('anuncios.rota.gerenciar', 'anuncios', 'administrar', 'Gerenciar rotas de comunicacao'),
    ('anuncios.execucao.visualizar', 'anuncios', 'visualizar', 'Visualizar execucoes e historico'),
    ('anuncios.execucao.registrar', 'anuncios', 'criar', 'Registrar instalacao, recolhimento e extravio')
ON CONFLICT(codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo,
    acao = EXCLUDED.acao,
    descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao(perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo = 'anuncios.execucao.registrar'
WHERE pa.tenant_id IS NULL AND pa.codigo = 'motorista_motociclista'
ON CONFLICT DO NOTHING;

INSERT INTO auth.perfil_permissao(perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('gestor', 'gestor_saas', 'coordenador_territorial')
  AND p.modulo = 'anuncios'
ON CONFLICT DO NOTHING;

INSERT INTO anuncio.material_comunicacao(tenant_id, nome, descricao)
SELECT t.id, material.nome, material.descricao
FROM public.tenant t
CROSS JOIN (VALUES
    ('Wind Banner', 'Wind banner para instalacao em campo'),
    ('Banner', 'Banner de comunicacao visual'),
    ('Bandeira', 'Bandeira de campanha')
) AS material(nome, descricao)
WHERE t.excluido_em IS NULL
ON CONFLICT(tenant_id, nome) DO NOTHING;

GRANT USAGE ON SCHEMA anuncio TO app_inteligencia;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA anuncio TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA anuncio TO app_inteligencia;

COMMIT;
