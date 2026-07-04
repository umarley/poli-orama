BEGIN;

ALTER TABLE demanda.categoria_demanda ADD COLUMN IF NOT EXISTS descricao VARCHAR(255),
 ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
 ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
 ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE demanda.categoria_demanda DROP CONSTRAINT IF EXISTS uq_categoria_demanda_codigo;
CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_demanda_global ON demanda.categoria_demanda(codigo) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_demanda_tenant ON demanda.categoria_demanda(tenant_id,codigo) WHERE tenant_id IS NOT NULL;

ALTER TABLE demanda.status_demanda ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
 ADD COLUMN IF NOT EXISTS descricao VARCHAR(255), ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
 ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(), ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE demanda.prioridade_demanda ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
 ADD COLUMN IF NOT EXISTS descricao VARCHAR(255), ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
 ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(), ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE demanda.origem_demanda ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
 ADD COLUMN IF NOT EXISTS descricao VARCHAR(255), ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
 ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(), ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE demanda.resultado_atendimento ADD COLUMN IF NOT EXISTS tenant_id BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
 ADD COLUMN IF NOT EXISTS descricao VARCHAR(255), ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
 ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT now(), ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE demanda.demanda ADD COLUMN IF NOT EXISTS responsavel_atendimento_id BIGINT REFERENCES demanda.responsavel_atendimento(id),
 ADD COLUMN IF NOT EXISTS resultado_atendimento_id SMALLINT REFERENCES demanda.resultado_atendimento(id),
 ADD COLUMN IF NOT EXISTS classificacao_detalhes JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE demanda.movimentacao_demanda ADD COLUMN IF NOT EXISTS prazo_anterior DATE,
 ADD COLUMN IF NOT EXISTS prazo_novo DATE, ADD COLUMN IF NOT EXISTS resultado_anterior_id SMALLINT REFERENCES demanda.resultado_atendimento(id),
 ADD COLUMN IF NOT EXISTS resultado_novo_id SMALLINT REFERENCES demanda.resultado_atendimento(id);
ALTER TABLE demanda.responsavel_atendimento ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE,
 ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS demanda.alerta_prazo (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tenant_id BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
 demanda_id BIGINT NOT NULL REFERENCES demanda.demanda(id) ON DELETE CASCADE,
 responsavel_atendimento_id BIGINT REFERENCES demanda.responsavel_atendimento(id),
 tipo VARCHAR(20) NOT NULL CHECK(tipo IN ('vencendo','vencido')), mensagem VARCHAR(255) NOT NULL,
 data_referencia DATE NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'aberto' CHECK(status IN ('aberto','lido','resolvido')),
 criado_em TIMESTAMPTZ NOT NULL DEFAULT now(), lido_em TIMESTAMPTZ,
 CONSTRAINT uq_alerta_prazo UNIQUE(tenant_id,demanda_id,tipo,data_referencia)
);

INSERT INTO demanda.categoria_demanda(tenant_id,codigo,nome) SELECT NULL,x.c,x.n FROM (VALUES
 ('saude','Saude'),('educacao','Educacao'),('infraestrutura','Infraestrutura'),('emprego','Emprego'),
 ('seguranca','Seguranca'),('assistencia_social','Assistencia social'),('transporte','Transporte'),('habitacao','Habitacao')) x(c,n)
WHERE NOT EXISTS(SELECT 1 FROM demanda.categoria_demanda d WHERE d.tenant_id IS NULL AND d.codigo=x.c);

INSERT INTO auth.permissao(codigo,modulo,acao,descricao) VALUES
 ('demandas.exportar','demandas','exportar','Exportar demandas'),('demandas.administrar','demandas','administrar','Administrar catalogos')
ON CONFLICT(codigo) DO UPDATE SET descricao=EXCLUDED.descricao;
INSERT INTO auth.perfil_permissao(perfil_acesso_id,permissao_id)
SELECT pa.id,p.id FROM auth.perfil_acesso pa CROSS JOIN auth.permissao p
WHERE pa.tenant_id IS NULL AND pa.codigo IN ('gestor','gestor_saas') AND p.modulo='demandas' ON CONFLICT DO NOTHING;
INSERT INTO auth.perfil_permissao(perfil_acesso_id,permissao_id)
SELECT pa.id,p.id FROM auth.perfil_acesso pa JOIN auth.permissao p ON p.codigo='demandas.exportar'
WHERE pa.tenant_id IS NULL AND pa.codigo IN ('coordenador_territorial','administrativo') ON CONFLICT DO NOTHING;

DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['status_demanda','prioridade_demanda','origem_demanda','resultado_atendimento'] LOOP
  EXECUTE format('ALTER TABLE demanda.%I DROP CONSTRAINT IF EXISTS uq_%I_codigo',t,t);
  EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS uq_%I_global ON demanda.%I(codigo) WHERE tenant_id IS NULL',t,t);
  EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS uq_%I_tenant ON demanda.%I(tenant_id,codigo) WHERE tenant_id IS NOT NULL',t,t);
 END LOOP;
END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['categoria_demanda','status_demanda','prioridade_demanda','origem_demanda','resultado_atendimento','alerta_prazo'] LOOP
  EXECUTE format('ALTER TABLE demanda.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('DROP POLICY IF EXISTS pol_isolamento_tenant ON demanda.%I',t);
  EXECUTE format('CREATE POLICY pol_isolamento_tenant ON demanda.%I USING(tenant_id IS NULL OR tenant_id=global.tenant_atual()) WITH CHECK(tenant_id IS NULL OR tenant_id=global.tenant_atual())',t);
 END LOOP;
END $$;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA demanda TO app_inteligencia;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA demanda TO app_inteligencia;
COMMIT;
