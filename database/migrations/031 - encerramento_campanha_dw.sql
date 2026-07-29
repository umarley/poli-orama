-- Rotina assincrona e idempotente de encerramento e consolidacao analitica.

BEGIN;

CREATE TABLE eleicao.encerramento_campanha (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id         BIGINT NOT NULL
                                REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT,
    job_processamento_id        BIGINT REFERENCES etl.job_processamento(id) ON DELETE SET NULL,
    votos_obtidos               INTEGER NOT NULL CHECK (votos_obtidos >= 0),
    total_votos_validos         INTEGER CHECK (
                                    total_votos_validos IS NULL
                                    OR total_votos_validos >= votos_obtidos
                                ),
    eleito                      BOOLEAN NOT NULL,
    colocacao                   INTEGER CHECK (colocacao IS NULL OR colocacao > 0),
    resultado_oficial_em        TIMESTAMPTZ,
    fonte_resultado             VARCHAR(255),
    observacao                  TEXT,
    status                      VARCHAR(20) NOT NULL DEFAULT 'enfileirado'
                                CHECK (status IN (
                                    'enfileirado','processando','concluido','falha'
                                )),
    erro                        TEXT,
    solicitado_por              BIGINT REFERENCES auth.usuario(id) ON DELETE SET NULL,
    solicitado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    iniciado_em                 TIMESTAMPTZ,
    concluido_em                TIMESTAMPTZ,
    atualizado_em               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_encerramento_campanha UNIQUE (campanha_eleicao_id)
);

CREATE INDEX ix_encerramento_campanha_status
    ON eleicao.encerramento_campanha (tenant_id, status, solicitado_em DESC);

CREATE TRIGGER trg_encerramento_campanha_atualiza
BEFORE UPDATE ON eleicao.encerramento_campanha
FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

ALTER TABLE eleicao.encerramento_campanha ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_encerramento_campanha
    ON eleicao.encerramento_campanha
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());

CREATE TABLE dw.campanha_consolidada (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id         BIGINT NOT NULL
                                REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT,
    eleicao_id                  BIGINT NOT NULL
                                REFERENCES eleicao.eleicao(id) ON DELETE RESTRICT,
    encerramento_campanha_id    BIGINT NOT NULL
                                REFERENCES eleicao.encerramento_campanha(id) ON DELETE RESTRICT,
    nome_campanha               VARCHAR(180) NOT NULL,
    cargo_pleiteado             VARCHAR(120) NOT NULL,
    ano_eleicao                 SMALLINT NOT NULL,
    tipo_eleicao                VARCHAR(30) NOT NULL,
    turno                       SMALLINT NOT NULL,
    data_eleicao                DATE NOT NULL,
    votos_obtidos               INTEGER NOT NULL,
    total_votos_validos         INTEGER,
    percentual_votos_validos    NUMERIC(9,4),
    eleito                      BOOLEAN NOT NULL,
    colocacao                   INTEGER,
    total_pessoas_vinculadas    INTEGER NOT NULL DEFAULT 0,
    total_intencoes_confirmadas INTEGER NOT NULL DEFAULT 0,
    total_liderancas            INTEGER NOT NULL DEFAULT 0,
    total_metas                 INTEGER NOT NULL DEFAULT 0,
    quantidade_meta_total       INTEGER NOT NULL DEFAULT 0,
    total_eventos               INTEGER NOT NULL DEFAULT 0,
    total_demandas              INTEGER NOT NULL DEFAULT 0,
    total_interacoes            INTEGER NOT NULL DEFAULT 0,
    indicadores                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    consolidado_em              TIMESTAMPTZ NOT NULL DEFAULT now(),
    versao_modelo               SMALLINT NOT NULL DEFAULT 1,
    CONSTRAINT uq_dw_campanha_consolidada UNIQUE (campanha_eleicao_id)
);

CREATE TABLE dw.lideranca_campanha_consolidada (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id         BIGINT NOT NULL
                                REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT,
    lideranca_id                BIGINT NOT NULL REFERENCES cadastro.lideranca(id) ON DELETE RESTRICT,
    tipo_lideranca              VARCHAR(40) NOT NULL,
    total_liderados             INTEGER NOT NULL DEFAULT 0,
    total_confirmacoes          INTEGER NOT NULL DEFAULT 0,
    total_atendimentos          INTEGER NOT NULL DEFAULT 0,
    total_eventos               INTEGER NOT NULL DEFAULT 0,
    total_demandas              INTEGER NOT NULL DEFAULT 0,
    quantidade_meta             INTEGER NOT NULL DEFAULT 0,
    quantidade_confirmada_meta  INTEGER NOT NULL DEFAULT 0,
    percentual_meta             NUMERIC(9,4) NOT NULL DEFAULT 0,
    pontuacao_final             NUMERIC(12,2) NOT NULL DEFAULT 0,
    posicao_final               INTEGER,
    consolidado_em              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dw_lideranca_campanha
        UNIQUE (campanha_eleicao_id, lideranca_id)
);

CREATE TABLE dw.meta_campanha_consolidada (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id         BIGINT NOT NULL
                                REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT,
    meta_voto_id                BIGINT NOT NULL REFERENCES meta.meta_voto(id) ON DELETE RESTRICT,
    tipo_meta                   VARCHAR(30) NOT NULL,
    titulo                      VARCHAR(150) NOT NULL,
    quantidade_meta             INTEGER NOT NULL,
    quantidade_projetada        INTEGER NOT NULL DEFAULT 0,
    quantidade_confirmada       INTEGER NOT NULL DEFAULT 0,
    percentual_atingido         NUMERIC(9,4) NOT NULL DEFAULT 0,
    status_final                VARCHAR(20) NOT NULL,
    consolidado_em              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dw_meta_campanha UNIQUE (campanha_eleicao_id, meta_voto_id)
);

CREATE TABLE dw.pessoa_campanha_consolidada (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id         BIGINT NOT NULL
                                REFERENCES eleicao.campanha_eleicao(id) ON DELETE RESTRICT,
    pessoa_id                   BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE RESTRICT,
    lideranca_id                BIGINT REFERENCES cadastro.lideranca(id) ON DELETE SET NULL,
    situacao_apoio              VARCHAR(30),
    status_eleitoral            VARCHAR(30),
    intencao_confirmada         BOOLEAN NOT NULL DEFAULT FALSE,
    total_atendimentos          INTEGER NOT NULL DEFAULT 0,
    total_interacoes            INTEGER NOT NULL DEFAULT 0,
    consolidado_em              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dw_pessoa_campanha UNIQUE (campanha_eleicao_id, pessoa_id)
);

CREATE INDEX ix_dw_campanha_eleicao
    ON dw.campanha_consolidada (eleicao_id, eleito, votos_obtidos DESC);
CREATE INDEX ix_dw_lideranca_campanha_desempenho
    ON dw.lideranca_campanha_consolidada
       (campanha_eleicao_id, posicao_final, pontuacao_final DESC);
CREATE INDEX ix_dw_pessoa_campanha_status
    ON dw.pessoa_campanha_consolidada
       (campanha_eleicao_id, intencao_confirmada, status_eleitoral);

ALTER TABLE dw.campanha_consolidada ENABLE ROW LEVEL SECURITY;
ALTER TABLE dw.lideranca_campanha_consolidada ENABLE ROW LEVEL SECURITY;
ALTER TABLE dw.meta_campanha_consolidada ENABLE ROW LEVEL SECURITY;
ALTER TABLE dw.pessoa_campanha_consolidada ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_dw_campanha
    ON dw.campanha_consolidada
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_dw_lideranca_campanha
    ON dw.lideranca_campanha_consolidada
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_dw_meta_campanha
    ON dw.meta_campanha_consolidada
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());
CREATE POLICY tenant_isolation_dw_pessoa_campanha
    ON dw.pessoa_campanha_consolidada
    USING (tenant_id = global.tenant_atual())
    WITH CHECK (tenant_id = global.tenant_atual());

GRANT SELECT, INSERT, UPDATE, DELETE ON
    eleicao.encerramento_campanha,
    dw.campanha_consolidada,
    dw.lideranca_campanha_consolidada,
    dw.meta_campanha_consolidada,
    dw.pessoa_campanha_consolidada
TO app_inteligencia;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA eleicao, dw TO app_inteligencia;

COMMIT;
