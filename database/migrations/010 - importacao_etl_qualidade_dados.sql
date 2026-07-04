BEGIN;

ALTER TABLE etl.fonte_dado
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE etl.fonte_dado DROP CONSTRAINT IF EXISTS uq_fonte_dado_codigo;
CREATE UNIQUE INDEX IF NOT EXISTS uq_fonte_dado_codigo_global
    ON etl.fonte_dado (codigo) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_fonte_dado_codigo_tenant
    ON etl.fonte_dado (tenant_id, codigo) WHERE tenant_id IS NOT NULL;

ALTER TABLE etl.importacao
    ADD COLUMN IF NOT EXISTS parametros JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS mapeamento_colunas JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS linhas_duplicadas INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS linhas_pendentes INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS linhas_carregadas INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS aprovado_por BIGINT REFERENCES auth.usuario(id),
    ADD COLUMN IF NOT EXISTS aprovado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE etl.importacao_arquivo
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE;
UPDATE etl.importacao_arquivo ia SET tenant_id = i.tenant_id
FROM etl.importacao i WHERE ia.importacao_id = i.id AND ia.tenant_id IS NULL;
ALTER TABLE etl.importacao_linha
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE;
UPDATE etl.importacao_linha il SET tenant_id = i.tenant_id
FROM etl.importacao i WHERE il.importacao_id = i.id AND il.tenant_id IS NULL;
ALTER TABLE etl.erro_importacao
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS valor TEXT,
    ADD COLUMN IF NOT EXISTS severidade VARCHAR(10) NOT NULL DEFAULT 'erro'
        CHECK (severidade IN ('aviso', 'erro'));
UPDATE etl.erro_importacao ei SET tenant_id = i.tenant_id
FROM etl.importacao i WHERE ei.importacao_id = i.id AND ei.tenant_id IS NULL;

ALTER TABLE etl.staging_pessoa
    ADD COLUMN IF NOT EXISTS importacao_linha_id BIGINT
        REFERENCES etl.importacao_linha(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS logradouro VARCHAR(180),
    ADD COLUMN IF NOT EXISTS numero VARCHAR(20),
    ADD COLUMN IF NOT EXISTS complemento VARCHAR(120),
    ADD COLUMN IF NOT EXISTS bairro VARCHAR(150),
    ADD COLUMN IF NOT EXISTS cep VARCHAR(9),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE etl.resultado_deduplicacao
    ADD COLUMN IF NOT EXISTS staging_pessoa_id BIGINT
        REFERENCES etl.staging_pessoa(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS pessoa_candidata_id BIGINT
        REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS detalhes JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS ix_importacao_tenant_status
    ON etl.importacao (tenant_id, status, criado_em DESC);
CREATE INDEX IF NOT EXISTS ix_erro_importacao_tenant
    ON etl.erro_importacao (tenant_id, importacao_id, severidade);
CREATE INDEX IF NOT EXISTS ix_resultado_dedup_staging
    ON etl.resultado_deduplicacao (tenant_id, staging_pessoa_id);

INSERT INTO etl.fonte_dado (tenant_id, codigo, nome, tipo, descricao) VALUES
    (NULL, 'planilha', 'Planilha', 'planilha', 'Importacao manual CSV ou Excel'),
    (NULL, 'gesped', 'GESPED', 'gesped', 'Exportacao ou API GESPED'),
    (NULL, 'tse', 'Tribunal Superior Eleitoral', 'tse', 'Dados publicos eleitorais'),
    (NULL, 'ibge', 'IBGE', 'ibge', 'Dados publicos territoriais e demograficos'),
    (NULL, 'formulario', 'Formulario', 'formulario', 'Captura por formulario')
ON CONFLICT (codigo) WHERE tenant_id IS NULL DO UPDATE SET
    nome = EXCLUDED.nome, tipo = EXCLUDED.tipo, descricao = EXCLUDED.descricao, ativo = TRUE;

INSERT INTO etl.regra_deduplicacao
    (tenant_id, nome, criterio, limiar_score, configuracao)
SELECT NULL, seed.nome, seed.criterio, seed.limiar, seed.configuracao
FROM (VALUES
    ('CPF exato', 'cpf', 100.00::numeric, '{"peso": 100}'::jsonb),
    ('Titulo eleitoral exato', 'titulo_eleitor', 100.00::numeric, '{"peso": 100}'::jsonb),
    ('Telefone exato', 'telefone', 100.00::numeric, '{"peso": 90}'::jsonb),
    ('E-mail exato', 'email', 100.00::numeric, '{"peso": 90}'::jsonb),
    ('Nome e data de nascimento', 'nome_data_nascimento', 100.00::numeric,
        '{"peso": 95}'::jsonb),
    ('Nome semelhante', 'fuzzy', 85.00::numeric, '{"algoritmo": "sequencematcher"}'::jsonb)
) AS seed(nome, criterio, limiar, configuracao)
WHERE NOT EXISTS (
    SELECT 1 FROM etl.regra_deduplicacao r
    WHERE r.tenant_id IS NULL AND r.criterio = seed.criterio
);

INSERT INTO auth.permissao (codigo, modulo, acao, descricao) VALUES
    ('etl.visualizar', 'etl', 'visualizar', 'Consultar importacoes e qualidade'),
    ('etl.criar', 'etl', 'criar', 'Enviar arquivos e configurar importacoes'),
    ('etl.editar', 'etl', 'editar', 'Mapear colunas e cancelar importacoes'),
    ('etl.aprovar', 'etl', 'aprovar', 'Aprovar carga definitiva no cadastro'),
    ('etl.exportar', 'etl', 'exportar', 'Exportar relatorios de erros')
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo, acao = EXCLUDED.acao, descricao = EXCLUDED.descricao;
INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id FROM auth.perfil_acesso pa CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL AND pa.codigo IN ('gestor_saas', 'gestor')
  AND p.modulo = 'etl' ON CONFLICT DO NOTHING;
INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id FROM auth.perfil_acesso pa JOIN auth.permissao p ON p.codigo = ANY (
    CASE pa.codigo
        WHEN 'coordenador_territorial' THEN ARRAY[
            'etl.visualizar', 'etl.criar', 'etl.editar', 'etl.exportar']
        WHEN 'administrativo' THEN ARRAY[
            'etl.visualizar', 'etl.criar', 'etl.editar', 'etl.exportar']
        ELSE ARRAY[]::TEXT[]
    END)
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('coordenador_territorial', 'administrativo')
ON CONFLICT DO NOTHING;

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON etl.fonte_dado;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON etl.fonte_dado
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON etl.importacao;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON etl.importacao
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();
DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON etl.staging_pessoa;
CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON etl.staging_pessoa
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DO $$
DECLARE item RECORD;
BEGIN
    FOR item IN SELECT * FROM (VALUES
        ('etl', 'fonte_dado'), ('etl', 'importacao'),
        ('etl', 'importacao_arquivo'), ('etl', 'importacao_linha'),
        ('etl', 'erro_importacao'), ('etl', 'staging_pessoa'),
        ('etl', 'resultado_deduplicacao')
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

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA etl TO app_inteligencia;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA arquivo TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA etl TO app_inteligencia;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA arquivo TO app_inteligencia;

COMMIT;
