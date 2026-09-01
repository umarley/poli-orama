BEGIN;

CREATE SCHEMA IF NOT EXISTS contrato;

CREATE TABLE IF NOT EXISTS contrato.pessoa_juridica (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    razao_social VARCHAR(180) NOT NULL,
    nome_fantasia VARCHAR(180),
    cnpj VARCHAR(14) NOT NULL CHECK (cnpj ~ '^[0-9]{14}$'),
    telefone VARCHAR(20),
    cep VARCHAR(9),
    logradouro VARCHAR(180),
    numero VARCHAR(20),
    complemento VARCHAR(120),
    bairro_texto VARCHAR(150),
    codigo_municipio_ibge INTEGER REFERENCES global.municipio(codigo_ibge),
    latitude NUMERIC(10,7) CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude NUMERIC(10,7) CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    geom geography(Point, 4326),
    criado_por BIGINT REFERENCES auth.usuario(id),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pessoa_juridica_cnpj_ativa
    ON contrato.pessoa_juridica (tenant_id, cnpj) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_pessoa_juridica_nome
    ON contrato.pessoa_juridica (tenant_id, razao_social) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_pessoa_juridica_geom
    ON contrato.pessoa_juridica USING gist (geom);

CREATE TABLE IF NOT EXISTS contrato.contrato (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id BIGINT NOT NULL
        REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT,
    tipo_contratado VARCHAR(2) NOT NULL CHECK (tipo_contratado IN ('pf', 'pj')),
    pessoa_id BIGINT REFERENCES cadastro.pessoa(id) ON DELETE RESTRICT,
    pessoa_juridica_id BIGINT REFERENCES contrato.pessoa_juridica(id) ON DELETE RESTRICT,
    funcao_cargo VARCHAR(180) NOT NULL,
    valor_parcela NUMERIC(14,2) NOT NULL CHECK (valor_parcela > 0),
    quantidade_parcelas SMALLINT NOT NULL CHECK (quantidade_parcelas IN (1, 2, 3)),
    valor_total NUMERIC(16,2) GENERATED ALWAYS AS
        (valor_parcela * quantidade_parcelas) STORED,
    data_inicio DATE NOT NULL,
    data_termino DATE NOT NULL,
    dias_trabalho INTEGER GENERATED ALWAYS AS (data_termino - data_inicio) STORED,
    valor_diaria NUMERIC(16,2) GENERATED ALWAYS AS
        (round(
            (valor_parcela * quantidade_parcelas)
            / NULLIF(data_termino - data_inicio, 0),
            2
        )) STORED,
    status VARCHAR(20) NOT NULL DEFAULT 'ativo'
        CHECK (status IN ('rascunho', 'ativo', 'encerrado', 'cancelado')),
    observacoes TEXT,
    criado_por BIGINT NOT NULL REFERENCES auth.usuario(id),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em TIMESTAMPTZ,
    CONSTRAINT ck_contrato_periodo CHECK (data_termino > data_inicio),
    CONSTRAINT ck_contrato_tipo_pessoa CHECK (
        (tipo_contratado = 'pf' AND pessoa_id IS NOT NULL AND pessoa_juridica_id IS NULL)
        OR
        (tipo_contratado = 'pj' AND pessoa_id IS NULL AND pessoa_juridica_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS ix_contrato_tenant_status
    ON contrato.contrato (tenant_id, status, data_inicio) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_contrato_campanha
    ON contrato.contrato (tenant_id, campanha_eleicao_id) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_contrato_pessoa
    ON contrato.contrato (tenant_id, pessoa_id) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_contrato_pessoa_juridica
    ON contrato.contrato (tenant_id, pessoa_juridica_id) WHERE excluido_em IS NULL;

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON contrato.pessoa_juridica;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON contrato.pessoa_juridica
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON contrato.contrato;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON contrato.contrato
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_sincroniza_ponto ON contrato.pessoa_juridica;
CREATE TRIGGER trg_sincroniza_ponto
    BEFORE INSERT OR UPDATE OF latitude, longitude ON contrato.pessoa_juridica
    FOR EACH ROW EXECUTE FUNCTION territorio.fn_sincroniza_ponto_geografico();

ALTER TABLE arquivo.anexo DROP CONSTRAINT IF EXISTS anexo_entidade_tipo_check;
ALTER TABLE arquivo.anexo
    ADD CONSTRAINT anexo_entidade_tipo_check CHECK (
        entidade_tipo IN (
            'pessoa', 'evento', 'demanda', 'interacao', 'importacao',
            'comunidade', 'lideranca', 'convite', 'tenant', 'contrato'
        )
    );

INSERT INTO arquivo.tipo_anexo (codigo, nome) VALUES
    ('contrato_rg_frente', 'RG - frente'),
    ('contrato_rg_verso', 'RG - verso'),
    ('contrato_cnh', 'CNH'),
    ('contrato_cpf', 'CPF'),
    ('contrato_comprovante_endereco', 'Comprovante de endereco'),
    ('contrato_foto', 'Foto do contratado'),
    ('contrato_cartao_cnpj', 'Cartao CNPJ'),
    ('contrato_social', 'Contrato social')
ON CONFLICT (codigo) WHERE tenant_id IS NULL DO UPDATE SET
    nome = EXCLUDED.nome, ativo = TRUE, atualizado_em = now();

INSERT INTO auth.perfil_acesso
    (tenant_id, nome, codigo, descricao, nivel, sistema)
VALUES
    (NULL, 'Tesoureiro', 'tesoureiro',
     'Acesso exclusivo a contratos e documentos financeiros da campanha', 2, TRUE)
ON CONFLICT (codigo) WHERE tenant_id IS NULL DO UPDATE SET
    nome = EXCLUDED.nome, descricao = EXCLUDED.descricao,
    nivel = EXCLUDED.nivel, sistema = TRUE, atualizado_em = now();

INSERT INTO auth.permissao (codigo, modulo, acao, descricao) VALUES
    ('contrato.visualizar', 'contrato', 'visualizar', 'Consultar contratos e contratados'),
    ('contrato.criar', 'contrato', 'criar', 'Cadastrar contratos e contratados'),
    ('contrato.editar', 'contrato', 'editar', 'Editar contratos e contratados'),
    ('contrato.excluir', 'contrato', 'excluir', 'Excluir contratos'),
    ('contrato.administrar', 'contrato', 'administrar', 'Administrar documentos contratuais')
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo, acao = EXCLUDED.acao, descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL AND pa.codigo = 'tesoureiro' AND p.modulo = 'contrato'
ON CONFLICT DO NOTHING;

ALTER TABLE contrato.pessoa_juridica ENABLE ROW LEVEL SECURITY;
CREATE POLICY pol_isolamento_tenant ON contrato.pessoa_juridica
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
ALTER TABLE contrato.contrato ENABLE ROW LEVEL SECURITY;
CREATE POLICY pol_isolamento_tenant ON contrato.contrato
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());

GRANT USAGE ON SCHEMA contrato TO app_inteligencia;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA contrato TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA contrato TO app_inteligencia;

COMMENT ON SCHEMA contrato IS 'Contratos sensiveis da campanha, acessiveis apenas ao perfil tesoureiro.';
COMMENT ON TABLE contrato.pessoa_juridica IS 'Empresas contratadas, separadas do cadastro de pessoas e eleitores.';
COMMENT ON TABLE contrato.contrato IS 'Contratos PF/PJ com valores derivados e periodo de vigencia.';

COMMIT;
