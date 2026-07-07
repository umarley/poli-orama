BEGIN;

ALTER TABLE comunicacao.canal_comunicacao
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS descricao VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE comunicacao.tipo_interacao
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS descricao VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE comunicacao.canal_comunicacao
    DROP CONSTRAINT IF EXISTS uq_canal_comunicacao_codigo;
ALTER TABLE comunicacao.tipo_interacao
    DROP CONSTRAINT IF EXISTS uq_tipo_interacao_codigo;

CREATE UNIQUE INDEX IF NOT EXISTS uq_canal_comunicacao_tenant_codigo
    ON comunicacao.canal_comunicacao (tenant_id, codigo);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_interacao_tenant_codigo
    ON comunicacao.tipo_interacao (tenant_id, codigo);

CREATE INDEX IF NOT EXISTS ix_canal_comunicacao_tenant_codigo
    ON comunicacao.canal_comunicacao (tenant_id, codigo);
CREATE INDEX IF NOT EXISTS ix_tipo_interacao_tenant_codigo
    ON comunicacao.tipo_interacao (tenant_id, codigo);

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON comunicacao.canal_comunicacao;
CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON comunicacao.canal_comunicacao
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

DROP TRIGGER IF EXISTS trg_atualiza_timestamp ON comunicacao.tipo_interacao;
CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON comunicacao.tipo_interacao
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

INSERT INTO global.categoria_data_comemorativa (nome, descricao) VALUES
    ('Civica', 'Datas civicas nacionais relevantes para relacionamento institucional.'),
    ('Cultural', 'Datas culturais e comunitarias.'),
    ('Saude', 'Datas de mobilizacao social e saude publica.'),
    ('Municipal', 'Datas locais ou municipais.')
ON CONFLICT (nome) DO NOTHING;

INSERT INTO global.data_comemorativa (categoria_id, nome, descricao, dia, mes, ambito, ativo)
SELECT c.id, v.nome, v.descricao, v.dia, v.mes, v.ambito, TRUE
FROM (
    VALUES
        ('Civica', 'Confraternizacao Universal', 'Feriado nacional.', 1, 1, 'nacional'),
        ('Civica', 'Dia de Tiradentes', 'Feriado nacional.', 21, 4, 'nacional'),
        ('Civica', 'Dia do Trabalhador', 'Feriado nacional.', 1, 5, 'nacional'),
        ('Civica', 'Independencia do Brasil', 'Feriado nacional.', 7, 9, 'nacional'),
        ('Civica', 'Nossa Senhora Aparecida', 'Feriado nacional.', 12, 10, 'nacional'),
        ('Civica', 'Finados', 'Feriado nacional.', 2, 11, 'nacional'),
        ('Civica', 'Proclamacao da Republica', 'Feriado nacional.', 15, 11, 'nacional'),
        ('Cultural', 'Dia das Maes', 'Data comercial e comunitaria; ajustar data movel operacionalmente.', 10, 5, 'nacional'),
        ('Cultural', 'Dia dos Pais', 'Data comercial e comunitaria; ajustar data movel operacionalmente.', 9, 8, 'nacional'),
        ('Saude', 'Outubro Rosa', 'Inicio da campanha de prevencao ao cancer de mama.', 1, 10, 'nacional'),
        ('Saude', 'Novembro Azul', 'Inicio da campanha de prevencao ao cancer de prostata.', 1, 11, 'nacional')
) AS v(categoria, nome, descricao, dia, mes, ambito)
JOIN global.categoria_data_comemorativa c ON c.nome = v.categoria
WHERE NOT EXISTS (
    SELECT 1 FROM global.data_comemorativa d
    WHERE d.nome = v.nome AND d.dia = v.dia AND d.mes = v.mes AND d.ambito = v.ambito
);

INSERT INTO auth.permissao(codigo, modulo, acao, descricao) VALUES
    ('comunicacao.visualizar', 'comunicacao', 'visualizar', 'Consultar comunicacao e interacoes'),
    ('comunicacao.criar', 'comunicacao', 'criar', 'Registrar interacoes e criar catalogos de comunicacao'),
    ('comunicacao.editar', 'comunicacao', 'editar', 'Editar catalogos de comunicacao'),
    ('comunicacao.excluir', 'comunicacao', 'excluir', 'Inativar catalogos de comunicacao')
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo,
    acao = EXCLUDED.acao,
    descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao(perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('gestor_saas', 'gestor')
  AND p.modulo = 'comunicacao'
ON CONFLICT DO NOTHING;

INSERT INTO auth.perfil_permissao(perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo = ANY (
    CASE pa.codigo
        WHEN 'coordenador_territorial' THEN ARRAY[
            'comunicacao.visualizar','comunicacao.criar','comunicacao.editar'
        ]
        WHEN 'lider' THEN ARRAY[
            'comunicacao.visualizar','comunicacao.criar'
        ]
        WHEN 'telefonista' THEN ARRAY[
            'comunicacao.visualizar','comunicacao.criar'
        ]
        WHEN 'administrativo' THEN ARRAY[
            'comunicacao.visualizar'
        ]
        ELSE ARRAY[]::TEXT[]
    END
)
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('coordenador_territorial', 'lider', 'telefonista', 'administrativo')
ON CONFLICT DO NOTHING;

COMMIT;
