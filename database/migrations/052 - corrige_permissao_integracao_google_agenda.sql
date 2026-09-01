BEGIN;

INSERT INTO auth.permissao (codigo, modulo, acao, descricao)
VALUES (
    'agenda.integrar_google',
    'agenda',
    'administrar',
    'Configurar e sincronizar Google Agenda'
)
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo,
    acao = EXCLUDED.acao,
    descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo = 'agenda.integrar_google'
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('gestor_saas', 'gestor')
ON CONFLICT DO NOTHING;

COMMIT;
