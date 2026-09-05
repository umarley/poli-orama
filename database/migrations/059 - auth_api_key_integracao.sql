-- Chaves de integracao para cadastro de pessoas a partir de sites externos.
-- O segredo e persistido apenas como hash em token_api; o valor em claro
-- e exibido uma unica vez ao gestor SaaS no momento da criacao.
--
-- A tabela nao recebe RLS de tenant: a busca por hash ocorre antes do
-- contexto de tenant ser definido, e a administracao e exclusiva do
-- gestor_saas em todos os tenants.

BEGIN;

CREATE TABLE IF NOT EXISTS auth.api_key (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico    UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome            VARCHAR(120) NOT NULL,
    token_prefix    VARCHAR(16) NOT NULL,
    token_api       TEXT NOT NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_uso_em   TIMESTAMPTZ,
    revogada_em     TIMESTAMPTZ,
    criado_por      BIGINT NOT NULL REFERENCES auth.usuario(id) ON DELETE RESTRICT,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_api_key_uuid UNIQUE (uuid_publico),
    CONSTRAINT uq_api_key_token UNIQUE (token_api),
    CONSTRAINT ck_api_key_nome CHECK (length(btrim(nome)) >= 2)
);

CREATE INDEX IF NOT EXISTS ix_api_key_tenant
    ON auth.api_key (tenant_id, ativo)
    WHERE revogada_em IS NULL;

COMMENT ON TABLE auth.api_key IS
    'Chaves de integracao (sites externos) para autenticar cadastro de pessoas no tenant associado.';
COMMENT ON COLUMN auth.api_key.token_api IS
    'Hash SHA-256 do segredo enviado no cabecalho Authorization: Bearer.';
COMMENT ON COLUMN auth.api_key.token_prefix IS
    'Prefixo visivel da chave para identificacao no painel, sem expor o segredo.';
COMMENT ON COLUMN auth.api_key.tenant_id IS
    'Tenant em que os cadastros recebidos pela integracao serao persistidos.';

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON auth.api_key;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON auth.api_key
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

INSERT INTO etl.fonte_dado (tenant_id, codigo, nome, tipo, descricao)
VALUES (
    NULL,
    'site_integracao',
    'Site de integracao',
    'api',
    'Cadastro de pessoas enviado por site externo autenticado com chave de integracao'
)
ON CONFLICT (codigo) WHERE tenant_id IS NULL DO UPDATE
SET nome = EXCLUDED.nome,
    tipo = EXCLUDED.tipo,
    descricao = EXCLUDED.descricao,
    ativo = TRUE;

COMMIT;
