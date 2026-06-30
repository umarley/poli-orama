BEGIN;

-- AUTH-001/012: forca troca da senha emitida pelo reset administrativo.
ALTER TABLE auth.usuario
    ADD COLUMN IF NOT EXISTS deve_alterar_senha BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_usuario_tenant_status
    ON auth.usuario (tenant_id, status)
    WHERE excluido_em IS NULL;

CREATE INDEX IF NOT EXISTS ix_sessao_usuario_validacao
    ON auth.sessao_usuario (id, tenant_id, usuario_id, expira_em)
    WHERE revogada_em IS NULL;

-- PostgreSQL permite varios NULL em UNIQUE(tenant_id, codigo). Este indice torna
-- os perfis globais idempotentes e impede codigos globais duplicados.
CREATE UNIQUE INDEX IF NOT EXISTS uq_perfil_acesso_codigo_global
    ON auth.perfil_acesso (codigo)
    WHERE tenant_id IS NULL;

INSERT INTO auth.permissao (codigo, modulo, acao, descricao) VALUES
    ('usuarios.visualizar', 'usuarios', 'visualizar', 'Consultar usuarios e perfis'),
    ('usuarios.criar', 'usuarios', 'criar', 'Criar usuarios'),
    ('usuarios.editar', 'usuarios', 'editar', 'Editar usuarios e associar perfis'),
    ('usuarios.excluir', 'usuarios', 'excluir', 'Inativar e excluir usuarios'),
    ('usuarios.administrar', 'usuarios', 'administrar', 'Redefinir senhas e administrar acessos'),
    ('configuracoes.visualizar', 'configuracoes', 'visualizar', 'Consultar configuracoes do tenant'),
    ('configuracoes.editar', 'configuracoes', 'editar', 'Editar configuracoes do tenant'),
    ('configuracoes.administrar', 'configuracoes', 'administrar', 'Administrar o tenant'),
    ('cadastro.visualizar', 'cadastro', 'visualizar', 'Consultar cadastros'),
    ('cadastro.criar', 'cadastro', 'criar', 'Criar cadastros'),
    ('cadastro.editar', 'cadastro', 'editar', 'Editar cadastros'),
    ('cadastro.excluir', 'cadastro', 'excluir', 'Excluir cadastros'),
    ('cadastro.exportar', 'cadastro', 'exportar', 'Exportar cadastros'),
    ('territorio.visualizar', 'territorio', 'visualizar', 'Consultar territorios'),
    ('territorio.criar', 'territorio', 'criar', 'Criar territorios'),
    ('territorio.editar', 'territorio', 'editar', 'Editar territorios'),
    ('territorio.excluir', 'territorio', 'excluir', 'Excluir territorios'),
    ('metas.visualizar', 'metas', 'visualizar', 'Consultar metas'),
    ('metas.criar', 'metas', 'criar', 'Criar metas'),
    ('metas.editar', 'metas', 'editar', 'Editar metas'),
    ('metas.aprovar', 'metas', 'aprovar', 'Aprovar metas'),
    ('agenda.visualizar', 'agenda', 'visualizar', 'Consultar agenda'),
    ('agenda.criar', 'agenda', 'criar', 'Criar eventos'),
    ('agenda.editar', 'agenda', 'editar', 'Editar eventos'),
    ('agenda.excluir', 'agenda', 'excluir', 'Excluir eventos'),
    ('demandas.visualizar', 'demandas', 'visualizar', 'Consultar demandas'),
    ('demandas.criar', 'demandas', 'criar', 'Criar demandas'),
    ('demandas.editar', 'demandas', 'editar', 'Editar demandas'),
    ('demandas.excluir', 'demandas', 'excluir', 'Excluir demandas'),
    ('dashboard.visualizar', 'dashboard', 'visualizar', 'Consultar dashboards'),
    ('dashboard.exportar', 'dashboard', 'exportar', 'Exportar dados de dashboards'),
    ('auditoria.visualizar', 'auditoria', 'visualizar', 'Consultar auditoria'),
    ('tenants.administrar', 'tenants', 'administrar', 'Administrar todos os tenants')
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo,
    acao = EXCLUDED.acao,
    descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_acesso
    (tenant_id, nome, codigo, descricao, nivel, sistema)
VALUES
    (NULL, 'Gestor SaaS', 'gestor_saas', 'Administracao da plataforma e dos tenants', 0, TRUE),
    (NULL, 'Gestor', 'gestor', 'Administracao completa da campanha', 1, TRUE),
    (NULL, 'Coordenador territorial', 'coordenador_territorial', 'Coordenacao operacional por territorio', 2, TRUE),
    (NULL, 'Lider', 'lider', 'Operacao de lideranca e liderados', 3, TRUE),
    (NULL, 'Telefonista/Atendimento', 'telefonista', 'Cadastro, contato e atendimento', 4, TRUE),
    (NULL, 'Administrativo/RH', 'administrativo', 'Rotinas administrativas da campanha', 4, TRUE)
ON CONFLICT (codigo) WHERE tenant_id IS NULL DO UPDATE SET
    nome = EXCLUDED.nome,
    descricao = EXCLUDED.descricao,
    nivel = EXCLUDED.nivel,
    sistema = TRUE,
    atualizado_em = now();

-- Gestores recebem todas as permissoes. O gestor SaaS tambem pode operar o
-- proprio tenant, alem de administrar a plataforma.
INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('gestor_saas', 'gestor')
ON CONFLICT DO NOTHING;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo = ANY (
    CASE pa.codigo
        WHEN 'coordenador_territorial' THEN ARRAY[
            'usuarios.visualizar',
            'cadastro.visualizar','cadastro.criar','cadastro.editar','cadastro.exportar',
            'territorio.visualizar','territorio.criar','territorio.editar',
            'metas.visualizar','metas.criar','metas.editar','metas.aprovar',
            'agenda.visualizar','agenda.criar','agenda.editar',
            'demandas.visualizar','demandas.criar','demandas.editar',
            'dashboard.visualizar'
        ]
        WHEN 'lider' THEN ARRAY[
            'cadastro.visualizar','cadastro.criar','cadastro.editar',
            'territorio.visualizar','metas.visualizar','metas.editar',
            'agenda.visualizar','agenda.criar','agenda.editar',
            'demandas.visualizar','demandas.criar','demandas.editar',
            'dashboard.visualizar'
        ]
        WHEN 'telefonista' THEN ARRAY[
            'cadastro.visualizar','cadastro.criar','cadastro.editar',
            'agenda.visualizar',
            'demandas.visualizar','demandas.criar','demandas.editar'
        ]
        WHEN 'administrativo' THEN ARRAY[
            'usuarios.visualizar',
            'cadastro.visualizar',
            'agenda.visualizar','agenda.criar','agenda.editar',
            'demandas.visualizar','demandas.criar','demandas.editar',
            'dashboard.visualizar'
        ]
        ELSE ARRAY[]::TEXT[]
    END
)
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('coordenador_territorial', 'lider', 'telefonista', 'administrativo')
ON CONFLICT DO NOTHING;

COMMIT;
