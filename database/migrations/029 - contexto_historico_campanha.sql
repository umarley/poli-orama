-- Contextualiza dados eleitorais por campanha sem alterar os cadastros permanentes.
-- PostgreSQL 14+

BEGIN;

-- A aplicacao trabalha com uma campanha corrente por tenant.
WITH campanhas_ativas AS (
    SELECT id,
           row_number() OVER (
               PARTITION BY tenant_id
               ORDER BY data_ativacao DESC NULLS LAST, id DESC
           ) AS ordem
    FROM eleicao.campanha_eleicao
    WHERE ativa
)
UPDATE eleicao.campanha_eleicao AS ce
SET ativa = FALSE,
    data_encerramento = COALESCE(ce.data_encerramento, now()),
    atualizado_em = now()
FROM campanhas_ativas AS ca
WHERE ca.id = ce.id AND ca.ordem > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_campanha_eleicao_ativa_tenant
    ON eleicao.campanha_eleicao (tenant_id)
    WHERE ativa = TRUE;

-- 1. A meta pertence diretamente a uma campanha. O periodo e apenas operacional.
ALTER TABLE meta.meta_voto
    ADD COLUMN IF NOT EXISTS campanha_eleicao_id BIGINT;

UPDATE meta.meta_voto AS m
SET campanha_eleicao_id = ce.id
FROM meta.periodo_meta AS pm
JOIN eleicao.campanha_eleicao AS ce
  ON ce.eleicao_id = pm.eleicao_id
 AND ce.tenant_id = pm.tenant_id
WHERE pm.id = m.periodo_meta_id
  AND m.campanha_eleicao_id IS NULL;

UPDATE meta.meta_voto AS m
SET campanha_eleicao_id = unica.id
FROM (
    SELECT tenant_id, min(id) AS id
    FROM eleicao.campanha_eleicao
    GROUP BY tenant_id
    HAVING count(*) = 1
) AS unica
WHERE unica.tenant_id = m.tenant_id
  AND m.campanha_eleicao_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM meta.meta_voto WHERE campanha_eleicao_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Existem metas sem campanha inferivel. Cadastre/associe a campanha antes de executar a migration 029.';
    END IF;
END
$$;

ALTER TABLE meta.meta_voto
    ALTER COLUMN campanha_eleicao_id SET NOT NULL,
    ADD CONSTRAINT fk_meta_voto_campanha
        FOREIGN KEY (campanha_eleicao_id)
        REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS ix_meta_voto_campanha_status
    ON meta.meta_voto (tenant_id, campanha_eleicao_id, status);

COMMENT ON COLUMN meta.meta_voto.campanha_eleicao_id IS
    'Campanha proprietaria da meta; fonte oficial do contexto eleitoral da meta.';

ALTER TABLE meta.periodo_meta
    DROP CONSTRAINT IF EXISTS fk_periodo_meta_eleicao,
    DROP COLUMN IF EXISTS eleicao_id;

COMMENT ON TABLE meta.periodo_meta IS
    'Subdivisao operacional reutilizavel para organizar o acompanhamento de metas.';

-- 2. Organizacao eleitoral historica, separada da lideranca permanente.
CREATE TABLE IF NOT EXISTS eleicao.campanha_lideranca (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id     BIGINT NOT NULL
                            REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    lideranca_id            BIGINT NOT NULL
                            REFERENCES cadastro.lideranca(id) ON DELETE CASCADE,
    tipo_lideranca          VARCHAR(40) NOT NULL
                            CHECK (tipo_lideranca IN (
                                'coordenador_geral',
                                'coordenador_territorial',
                                'lider',
                                'sublider'
                            )),
    coordenador_id          BIGINT REFERENCES cadastro.lideranca(id) ON DELETE SET NULL,
    apelido_campanha        VARCHAR(120),
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_campanha_lideranca
        UNIQUE (campanha_eleicao_id, lideranca_id)
);

CREATE INDEX IF NOT EXISTS ix_campanha_lideranca_coordenador
    ON eleicao.campanha_lideranca
       (tenant_id, campanha_eleicao_id, coordenador_id)
    WHERE ativo = TRUE;

INSERT INTO eleicao.campanha_lideranca (
    tenant_id, campanha_eleicao_id, lideranca_id, tipo_lideranca,
    coordenador_id, apelido_campanha, ativo
)
SELECT l.tenant_id, ce.id, l.id, l.tipo_lideranca,
       l.coordenador_id, l.apelido_campanha, l.ativo
FROM cadastro.lideranca AS l
JOIN eleicao.campanha_eleicao AS ce
  ON ce.tenant_id = l.tenant_id
 AND ce.ativa
ON CONFLICT (campanha_eleicao_id, lideranca_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS eleicao.campanha_liderado (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id     BIGINT NOT NULL
                            REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    lideranca_id            BIGINT NOT NULL
                            REFERENCES cadastro.lideranca(id) ON DELETE RESTRICT,
    pessoa_id               BIGINT NOT NULL
                            REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    data_inicio             DATE NOT NULL DEFAULT CURRENT_DATE,
    data_fim                DATE,
    origem                  VARCHAR(30) NOT NULL DEFAULT 'migracao'
                            CHECK (origem IN (
                                'migracao','lider_mobile','cadastro_web',
                                'importacao','call_center','manual'
                            )),
    ativo                   BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por              BIGINT REFERENCES auth.usuario(id) ON DELETE SET NULL,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (data_fim IS NULL OR data_fim >= data_inicio)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_campanha_liderado_pessoa_ativa
    ON eleicao.campanha_liderado (campanha_eleicao_id, pessoa_id)
    WHERE ativo = TRUE;

CREATE INDEX IF NOT EXISTS ix_campanha_liderado_lideranca
    ON eleicao.campanha_liderado
       (tenant_id, campanha_eleicao_id, lideranca_id)
    WHERE ativo = TRUE;

INSERT INTO eleicao.campanha_liderado (
    tenant_id, campanha_eleicao_id, lideranca_id, pessoa_id,
    data_inicio, data_fim, origem, ativo
)
SELECT h.tenant_id, ce.id, h.lideranca_superior_id, h.pessoa_subordinada_id,
       h.data_inicio, h.data_fim, 'migracao', h.ativo
FROM cadastro.hierarquia_lideranca AS h
JOIN eleicao.campanha_eleicao AS ce
  ON ce.tenant_id = h.tenant_id
 AND ce.ativa
WHERE NOT EXISTS (
    SELECT 1
    FROM eleicao.campanha_liderado AS cl
    WHERE cl.campanha_eleicao_id = ce.id
      AND cl.pessoa_id = h.pessoa_subordinada_id
      AND cl.ativo
)
ORDER BY h.criado_em DESC, h.id DESC
ON CONFLICT DO NOTHING;

COMMENT ON TABLE eleicao.campanha_lideranca IS
    'Papel e hierarquia de uma lideranca dentro de uma campanha especifica.';
COMMENT ON TABLE eleicao.campanha_liderado IS
    'Atribuicao historica e exclusiva de uma pessoa a uma lideranca na campanha.';

-- 3. Contexto politico mutavel da pessoa na campanha.
CREATE TABLE IF NOT EXISTS eleicao.pessoa_contexto_campanha (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id     BIGINT NOT NULL
                            REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    pessoa_id               BIGINT NOT NULL
                            REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    nivel_engajamento       SMALLINT CHECK (nivel_engajamento BETWEEN 0 AND 10),
    situacao_apoio          VARCHAR(30) NOT NULL DEFAULT 'nao_informado'
                            CHECK (situacao_apoio IN (
                                'nao_informado','possivel_apoio','indeciso',
                                'apoia','nao_apoia','confirmado'
                            )),
    lideranca_id            BIGINT REFERENCES cadastro.lideranca(id) ON DELETE SET NULL,
    observacoes             TEXT,
    atualizado_por          BIGINT REFERENCES auth.usuario(id) ON DELETE SET NULL,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_pessoa_contexto_campanha
        UNIQUE (campanha_eleicao_id, pessoa_id)
);

CREATE INDEX IF NOT EXISTS ix_pessoa_contexto_campanha_apoio
    ON eleicao.pessoa_contexto_campanha
       (tenant_id, campanha_eleicao_id, situacao_apoio);

-- Indicacoes permanentes continuam intactas; apenas a leitura eleitoral e associada.
CREATE TABLE IF NOT EXISTS eleicao.campanha_indicacao (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id     BIGINT NOT NULL
                            REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    indicacao_id            BIGINT NOT NULL
                            REFERENCES cadastro.indicacao(id) ON DELETE CASCADE,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_campanha_indicacao
        UNIQUE (campanha_eleicao_id, indicacao_id)
);

-- Comunidades e tags permanecem globais no tenant, com associacao eleitoral opcional.
CREATE TABLE IF NOT EXISTS eleicao.campanha_comunidade (
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id     BIGINT NOT NULL
                            REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    comunidade_id           BIGINT NOT NULL
                            REFERENCES cadastro.comunidade(id) ON DELETE CASCADE,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (campanha_eleicao_id, comunidade_id)
);

CREATE TABLE IF NOT EXISTS eleicao.campanha_tag (
    tenant_id               BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id     BIGINT NOT NULL
                            REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    tag_id                  BIGINT NOT NULL
                            REFERENCES cadastro.tag(id) ON DELETE CASCADE,
    criado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (campanha_eleicao_id, tag_id)
);

-- 4. Ranking historico e isolado por campanha.
ALTER TABLE meta.ranking_lideranca
    ADD COLUMN IF NOT EXISTS campanha_eleicao_id BIGINT;

UPDATE meta.ranking_lideranca AS r
SET campanha_eleicao_id = unica.id
FROM (
    SELECT tenant_id, min(id) AS id
    FROM eleicao.campanha_eleicao
    WHERE ativa
    GROUP BY tenant_id
    HAVING count(*) = 1
) AS unica
WHERE unica.tenant_id = r.tenant_id
  AND r.campanha_eleicao_id IS NULL;

-- Ranking e uma projecao recalculavel. Linhas sem campanha segura nao devem ser
-- atribuidas arbitrariamente a uma eleicao.
DELETE FROM meta.ranking_lideranca WHERE campanha_eleicao_id IS NULL;

ALTER TABLE meta.ranking_lideranca
    ALTER COLUMN campanha_eleicao_id SET NOT NULL,
    ADD CONSTRAINT fk_ranking_lideranca_campanha
        FOREIGN KEY (campanha_eleicao_id)
        REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    DROP CONSTRAINT IF EXISTS uq_ranking_lideranca,
    ADD CONSTRAINT uq_ranking_lideranca_campanha
        UNIQUE (campanha_eleicao_id, lideranca_id, data_referencia);

CREATE INDEX IF NOT EXISTS ix_ranking_lideranca_campanha_data
    ON meta.ranking_lideranca
       (tenant_id, campanha_eleicao_id, data_referencia DESC);

-- 5. Bases TSE pertencem a eleicao, nunca a campanha de um candidato.
ALTER TABLE etl.staging_eleitorado_tse
    ADD COLUMN IF NOT EXISTS eleicao_id BIGINT
        REFERENCES eleicao.eleicao(id) ON DELETE RESTRICT;
ALTER TABLE dw.perfil_eleitorado_tse
    ADD COLUMN IF NOT EXISTS eleicao_id BIGINT
        REFERENCES eleicao.eleicao(id) ON DELETE RESTRICT;
ALTER TABLE dw.perfil_eleitorado_secao_tse
    ADD COLUMN IF NOT EXISTS eleicao_id BIGINT
        REFERENCES eleicao.eleicao(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS ix_staging_eleitorado_eleicao
    ON etl.staging_eleitorado_tse (eleicao_id);
CREATE INDEX IF NOT EXISTS ix_perfil_eleitorado_eleicao
    ON dw.perfil_eleitorado_tse (eleicao_id);
CREATE INDEX IF NOT EXISTS ix_perfil_eleitorado_secao_eleicao
    ON dw.perfil_eleitorado_secao_tse (eleicao_id);

-- 6. Modulos mistos recebem contexto opcional; registros institucionais continuam globais.
ALTER TABLE agenda.evento
    ADD COLUMN IF NOT EXISTS contexto VARCHAR(20) NOT NULL DEFAULT 'institucional',
    ADD COLUMN IF NOT EXISTS campanha_eleicao_id BIGINT
        REFERENCES eleicao.campanha_eleicao(id) ON DELETE SET NULL,
    ADD CONSTRAINT ck_evento_contexto
        CHECK (contexto IN ('campanha','gabinete','institucional')),
    ADD CONSTRAINT ck_evento_campanha_contexto
        CHECK (contexto <> 'campanha' OR campanha_eleicao_id IS NOT NULL);

ALTER TABLE demanda.demanda
    ADD COLUMN IF NOT EXISTS origem_contexto VARCHAR(20) NOT NULL DEFAULT 'institucional',
    ADD COLUMN IF NOT EXISTS campanha_eleicao_id BIGINT
        REFERENCES eleicao.campanha_eleicao(id) ON DELETE SET NULL,
    ADD CONSTRAINT ck_demanda_origem_contexto
        CHECK (origem_contexto IN ('campanha','gabinete','institucional')),
    ADD CONSTRAINT ck_demanda_campanha_contexto
        CHECK (origem_contexto <> 'campanha' OR campanha_eleicao_id IS NOT NULL);

ALTER TABLE comunicacao.campanha_comunicacao
    ADD COLUMN IF NOT EXISTS campanha_eleicao_id BIGINT
        REFERENCES eleicao.campanha_eleicao(id) ON DELETE SET NULL;

ALTER TABLE etl.importacao
    ADD COLUMN IF NOT EXISTS campanha_eleicao_id BIGINT
        REFERENCES eleicao.campanha_eleicao(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_evento_campanha
    ON agenda.evento (tenant_id, campanha_eleicao_id, data_inicio);
CREATE INDEX IF NOT EXISTS ix_demanda_campanha
    ON demanda.demanda (tenant_id, campanha_eleicao_id, criado_em);
CREATE INDEX IF NOT EXISTS ix_campanha_comunicacao_eleitoral
    ON comunicacao.campanha_comunicacao (tenant_id, campanha_eleicao_id);
CREATE INDEX IF NOT EXISTS ix_importacao_campanha
    ON etl.importacao (tenant_id, campanha_eleicao_id);

-- Triggers e RLS para as novas tabelas privadas.
CREATE TRIGGER trg_campanha_lideranca_atualiza
BEFORE UPDATE ON eleicao.campanha_lideranca
FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

CREATE TRIGGER trg_campanha_liderado_atualiza
BEFORE UPDATE ON eleicao.campanha_liderado
FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

CREATE TRIGGER trg_pessoa_contexto_campanha_atualiza
BEFORE UPDATE ON eleicao.pessoa_contexto_campanha
FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

ALTER TABLE eleicao.campanha_lideranca ENABLE ROW LEVEL SECURITY;
ALTER TABLE eleicao.campanha_liderado ENABLE ROW LEVEL SECURITY;
ALTER TABLE eleicao.pessoa_contexto_campanha ENABLE ROW LEVEL SECURITY;
ALTER TABLE eleicao.campanha_indicacao ENABLE ROW LEVEL SECURITY;
ALTER TABLE eleicao.campanha_comunidade ENABLE ROW LEVEL SECURITY;
ALTER TABLE eleicao.campanha_tag ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_campanha_lideranca
    ON eleicao.campanha_lideranca
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_campanha_liderado
    ON eleicao.campanha_liderado
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_pessoa_contexto_campanha
    ON eleicao.pessoa_contexto_campanha
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_campanha_indicacao
    ON eleicao.campanha_indicacao
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_campanha_comunidade
    ON eleicao.campanha_comunidade
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_campanha_tag
    ON eleicao.campanha_tag
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());

GRANT SELECT, INSERT, UPDATE, DELETE ON
    eleicao.campanha_lideranca,
    eleicao.campanha_liderado,
    eleicao.pessoa_contexto_campanha,
    eleicao.campanha_indicacao,
    eleicao.campanha_comunidade,
    eleicao.campanha_tag
TO app_inteligencia;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA eleicao TO app_inteligencia;

COMMIT;
