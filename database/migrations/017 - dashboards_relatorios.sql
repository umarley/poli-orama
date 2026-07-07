BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_indicador_valor_recorte
ON dw.indicador_valor (
    tenant_id, indicador_id, data_referencia,
    COALESCE(territorio_id, 0), COALESCE(lideranca_id, 0), recorte
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_configuracao_perfil
ON dw.dashboard_configuracao (tenant_id, COALESCE(perfil_acesso_id, 0));

CREATE INDEX IF NOT EXISTS ix_dashboard_pessoa_periodo
ON cadastro.pessoa (tenant_id, criado_em) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_dashboard_demanda_periodo
ON demanda.demanda (tenant_id, data_solicitacao, territorio_id) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_dashboard_evento_periodo
ON agenda.evento (tenant_id, data_inicio, territorio_id) WHERE excluido_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_dashboard_hierarquia_ativa
ON cadastro.hierarquia_lideranca (tenant_id, lideranca_superior_id, pessoa_subordinada_id)
WHERE ativo;

INSERT INTO dw.indicador (codigo,nome,descricao,unidade) VALUES
('cadastros_total','Cadastros totais','Pessoas ativas cadastradas','pessoas'),
('cadastros_novos','Novos cadastros','Pessoas cadastradas na data','pessoas'),
('lideres_ativos','Liderancas ativas','Liderancas ativas na campanha','lideres'),
('liderados_ativos','Liderados ativos','Pessoas vinculadas a liderancas','pessoas'),
('demandas_pendentes','Demandas pendentes','Demandas ainda nao finalizadas','demandas'),
('eventos_realizados','Eventos realizados','Eventos com status realizado','eventos'),
('metas_em_risco','Metas em risco','Metas abaixo do esperado','metas')
ON CONFLICT (codigo) DO UPDATE SET
nome=EXCLUDED.nome, descricao=EXCLUDED.descricao, unidade=EXCLUDED.unidade;

INSERT INTO dw.relatorio
    (tenant_id,codigo,nome,descricao,tipo,formato_saida,parametros_definicao)
SELECT v.* FROM (VALUES
(NULL::bigint,'metas_por_lider','Metas por lider','Meta, realizado, percentual e risco por lideranca',
 'metas','dashboard','{"filtros":["periodo","territorio","lideranca"]}'::jsonb),
(NULL,'demandas_status_responsavel','Demandas por status e responsavel',
 'Demandas agregadas por status, categoria, responsavel e prazo',
 'demandas','dashboard','{"filtros":["periodo","territorio","lideranca"]}'::jsonb),
(NULL,'agenda_periodo','Agenda diaria e mensal','Eventos, convites, pautas e responsaveis',
 'agenda','dashboard','{"filtros":["periodo","territorio","lideranca"]}'::jsonb),
(NULL,'evolucao_cadastros','Evolucao de cadastros','Serie temporal de cadastros por origem',
 'cadastros','dashboard','{"filtros":["periodo","territorio","lideranca"]}'::jsonb),
(NULL,'ranking_lideres','Ranking de lideres','Desempenho consolidado das liderancas',
 'ranking','dashboard','{"filtros":["periodo","territorio","lideranca"]}'::jsonb)
) AS v(tenant_id,codigo,nome,descricao,tipo,formato_saida,parametros_definicao)
WHERE NOT EXISTS (
    SELECT 1 FROM dw.relatorio r
    WHERE r.codigo=v.codigo AND r.tenant_id IS NOT DISTINCT FROM v.tenant_id
);

COMMIT;
