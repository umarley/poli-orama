BEGIN;

ALTER TABLE arquivo.tipo_anexo
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS descricao VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE arquivo.tipo_anexo DROP CONSTRAINT IF EXISTS uq_tipo_anexo_codigo;
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_anexo_global
    ON arquivo.tipo_anexo(codigo) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_anexo_tenant
    ON arquivo.tipo_anexo(tenant_id, codigo) WHERE tenant_id IS NOT NULL;

ALTER TABLE arquivo.anexo
    ADD COLUMN IF NOT EXISTS excluido_em TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_arquivo_hash_tenant
    ON arquivo.arquivo(tenant_id, hash_sha256) WHERE excluido_em IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_anexo_ativo_arquivo_entidade
    ON arquivo.anexo(arquivo_id, entidade_tipo, entidade_id) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_documento_extraido_busca
    ON arquivo.documento_extraido
    USING GIN (to_tsvector('portuguese', COALESCE(texto_extraido, '')));

INSERT INTO auth.permissao(codigo, modulo, acao, descricao) VALUES
    ('arquivo.visualizar', 'arquivo', 'visualizar', 'Consultar tipos e documentos extraidos'),
    ('arquivo.administrar', 'arquivo', 'administrar', 'Administrar tipos de anexo')
ON CONFLICT(codigo) DO UPDATE SET descricao=EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao(perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('gestor', 'gestor_saas')
  AND p.modulo='arquivo'
ON CONFLICT DO NOTHING;

INSERT INTO auth.perfil_permissao(perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo='arquivo.visualizar'
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('coordenador_territorial', 'lider', 'operador', 'administrativo')
ON CONFLICT DO NOTHING;

ALTER TABLE arquivo.tipo_anexo ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pol_isolamento_tenant ON arquivo.tipo_anexo;
CREATE POLICY pol_isolamento_tenant ON arquivo.tipo_anexo
    USING (tenant_id IS NULL OR tenant_id=global.tenant_atual())
    WITH CHECK (tenant_id IS NULL OR tenant_id=global.tenant_atual());

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA arquivo TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA arquivo TO app_inteligencia;

COMMIT;
