BEGIN;

ALTER TABLE public.plano_assinatura
    ADD COLUMN slug VARCHAR(80),
    ADD COLUMN ordem_comercial INTEGER NOT NULL DEFAULT 100;

UPDATE public.plano_assinatura
SET slug = lower(regexp_replace(nome, '[^a-zA-Z0-9]+', '-', 'g'))
WHERE slug IS NULL;

ALTER TABLE public.plano_assinatura
    ALTER COLUMN slug SET NOT NULL,
    ADD CONSTRAINT uq_plano_assinatura_slug UNIQUE (slug);

ALTER TABLE public.tenant DROP CONSTRAINT IF EXISTS tenant_status_check;
ALTER TABLE public.tenant
    ADD CONSTRAINT tenant_status_check
    CHECK (status IN ('pendente','ativo','suspenso','cancelado','trial','inadimplente'));

CREATE TABLE public.lead_comercial (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico    UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    nome            VARCHAR(180) NOT NULL,
    email           VARCHAR(254) NOT NULL,
    telefone        VARCHAR(20),
    organizacao     VARCHAR(180),
    mensagem        TEXT,
    consentimento  BOOLEAN NOT NULL CHECK (consentimento),
    consentido_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    origem          JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_lead_comercial_email ON public.lead_comercial (lower(email));

CREATE TABLE public.contratacao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    plano_assinatura_id BIGINT NOT NULL REFERENCES public.plano_assinatura(id),
    tenant_id           BIGINT REFERENCES public.tenant(id),
    nome                VARCHAR(180) NOT NULL,
    email               VARCHAR(254) NOT NULL,
    telefone            VARCHAR(20),
    documento           VARCHAR(20),
    nome_campanha       VARCHAR(180) NOT NULL,
    slug_solicitado     VARCHAR(80) NOT NULL,
    consentimento      BOOLEAN NOT NULL CHECK (consentimento),
    origem              JSONB NOT NULL DEFAULT '{}'::jsonb,
    status              VARCHAR(20) NOT NULL DEFAULT 'pendente'
                        CHECK (status IN ('pendente','aprovada','pagamento_falhou','cancelada')),
    chave_idempotencia  VARCHAR(64) NOT NULL UNIQUE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_contratacao_status ON public.contratacao (status, criado_em);

CREATE TABLE public.checkout_session (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    contratacao_id      BIGINT NOT NULL REFERENCES public.contratacao(id) ON DELETE CASCADE,
    provedor            VARCHAR(40) NOT NULL,
    referencia_externa VARCHAR(180) UNIQUE,
    status              VARCHAR(20) NOT NULL
                        CHECK (status IN ('pendente','indisponivel','aprovado','falhou','expirado')),
    url_checkout        TEXT,
    chave_idempotencia  VARCHAR(64) NOT NULL UNIQUE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.evento_operacional (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo        VARCHAR(60) NOT NULL,
    entidade    VARCHAR(60) NOT NULL,
    entidade_id BIGINT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    status      VARCHAR(20) NOT NULL DEFAULT 'pendente'
                CHECK (status IN ('pendente','processando','enviado','falhou')),
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_evento_operacional_pendente
    ON public.evento_operacional (status, criado_em);

CREATE TABLE public.webhook_pagamento_evento (
    event_id        VARCHAR(180) PRIMARY KEY,
    tipo            VARCHAR(60) NOT NULL,
    processado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON public.contratacao
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

CREATE TRIGGER trg_atualiza_timestamp
    BEFORE UPDATE ON public.checkout_session
    FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();

INSERT INTO public.plano_assinatura
    (slug, nome, descricao, preco_mensal, moeda, limite_usuarios, limite_pessoas,
     limite_armazenamento_mb, recursos, ordem_comercial, ativo)
VALUES
    ('essencial', 'Essencial', 'Base organizada para iniciar a operacao eleitoral.',
     299.00, 'BRL', 5, 10000, 2048,
     '{"cadastro": true, "agenda": true, "demandas": true}'::jsonb, 10, TRUE),
    ('profissional', 'Profissional', 'Inteligencia territorial e gestao para equipes em crescimento.',
     699.00, 'BRL', 15, 50000, 10240,
     '{"cadastro": true, "agenda": true, "demandas": true, "territorios": true, "metas": true}'::jsonb,
     20, TRUE),
    ('operacao', 'Operacao', 'Operacao completa para campanhas de maior escala.',
     1499.00, 'BRL', 50, 200000, 51200,
     '{"cadastro": true, "agenda": true, "demandas": true, "territorios": true, "metas": true, "modo_eleicao": true}'::jsonb,
     30, TRUE),
    ('enterprise', 'Enterprise', 'Limites e integracoes definidos conforme a operacao.',
     0.00, 'BRL', NULL, NULL, NULL,
     '{"todos_recursos": true, "suporte_dedicado": true}'::jsonb, 40, TRUE)
ON CONFLICT (nome) DO UPDATE SET
    slug = EXCLUDED.slug,
    descricao = EXCLUDED.descricao,
    preco_mensal = EXCLUDED.preco_mensal,
    limite_usuarios = EXCLUDED.limite_usuarios,
    limite_pessoas = EXCLUDED.limite_pessoas,
    limite_armazenamento_mb = EXCLUDED.limite_armazenamento_mb,
    recursos = EXCLUDED.recursos,
    ordem_comercial = EXCLUDED.ordem_comercial,
    ativo = EXCLUDED.ativo,
    atualizado_em = now();

COMMIT;
