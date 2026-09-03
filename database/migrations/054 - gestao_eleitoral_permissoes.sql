BEGIN;

INSERT INTO auth.permissao (codigo, modulo, acao, descricao)
VALUES (
    'gestao_eleitoral.visualizar',
    'gestao_eleitoral',
    'visualizar',
    'Consultar estatisticas de eleicoes anteriores'
)
ON CONFLICT (codigo) DO UPDATE SET
    modulo = EXCLUDED.modulo,
    acao = EXCLUDED.acao,
    descricao = EXCLUDED.descricao;

INSERT INTO auth.perfil_permissao (perfil_acesso_id, permissao_id)
SELECT pa.id, p.id
FROM auth.perfil_acesso pa
JOIN auth.permissao p ON p.codigo = 'gestao_eleitoral.visualizar'
WHERE pa.tenant_id IS NULL
  AND pa.codigo IN ('gestor_saas', 'gestor', 'coordenador_territorial')
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS ix_resultados_eleicoes_eleicao_turno
    ON tse.resultados_eleicoes (aa_eleicao, cd_eleicao, nr_turno);

CREATE INDEX IF NOT EXISTS ix_resultados_eleicoes_nome_votavel
    ON tse.resultados_eleicoes (aa_eleicao, cd_eleicao, nr_turno, nm_votavel);

COMMIT;
