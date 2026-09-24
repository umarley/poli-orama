-- Evidencias em foto e video para execucoes de rotas de comunicacao.
INSERT INTO arquivo.tipo_anexo (codigo, nome)
VALUES ('video', 'Video')
ON CONFLICT (codigo) WHERE tenant_id IS NULL DO NOTHING;
