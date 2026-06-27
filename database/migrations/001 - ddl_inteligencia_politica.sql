-- =====================================================================================
-- PLATAFORMA SaaS DE INTELIGENCIA POLITICA
-- DDL COMPLETO - PostgreSQL 14+ (recomendado 16+)
-- =====================================================================================
-- Convencoes:
--   * Nomenclatura em portugues, snake_case, sem acentos.
--   * Chaves primarias substitutas: BIGINT GENERATED ALWAYS AS IDENTITY.
--   * Identificadores publicos/externos: UUID (coluna uuid_publico).
--   * Multitenancy: estrategia RLS (Row-Level Security) com coluna tenant_id em
--     todas as tabelas privadas de cada politico/candidato assinante.
--   * Auditoria padrao: criado_em, atualizado_em, criado_por, atualizado_por,
--     excluido_em (soft delete logico) nas tabelas operacionais.
--   * Tabelas globais (schemas public/global) NAO possuem tenant_id.
--   * PostGIS habilitado para georreferenciamento (geography/geometry).
-- =====================================================================================

-- =====================================================================================
-- 0. CRIACAO DO BANCO DE DADOS
-- =====================================================================================
-- OBS: CREATE DATABASE nao pode ser executado dentro de uma transacao/bloco.
-- Execute as duas linhas abaixo isoladamente (fora de transacao) se necessario.
-- Comente caso o banco ja exista ou seja gerenciado pela infraestrutura.

-- CREATE DATABASE inteligencia_politica
--     WITH ENCODING = 'UTF8'
--     LC_COLLATE = 'pt_BR.UTF-8'
--     LC_CTYPE = 'pt_BR.UTF-8'
--     TEMPLATE = template0;

-- \connect inteligencia_politica

-- =====================================================================================
-- 1. EXTENSOES
-- =====================================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid(), hashing
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- geracao de UUID alternativa
CREATE EXTENSION IF NOT EXISTS "citext";        -- texto case-insensitive (emails)
CREATE EXTENSION IF NOT EXISTS "unaccent";      -- busca sem acento
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- busca fuzzy / similaridade
CREATE EXTENSION IF NOT EXISTS "postgis";       -- georreferenciamento

-- =====================================================================================
-- 2. SCHEMAS
-- =====================================================================================
CREATE SCHEMA IF NOT EXISTS global;        -- dados compartilhados (UF, municipio, TSE, IBGE)
CREATE SCHEMA IF NOT EXISTS auth;          -- usuarios, perfis, permissoes, sessoes
CREATE SCHEMA IF NOT EXISTS cadastro;      -- pessoas, contatos, enderecos, lideranca, comunidade
CREATE SCHEMA IF NOT EXISTS territorio;    -- territorios, georreferenciamento, vinculos territoriais
CREATE SCHEMA IF NOT EXISTS agenda;        -- eventos, convites, presencas, pautas
CREATE SCHEMA IF NOT EXISTS demanda;       -- demandas, atendimentos, movimentacoes
CREATE SCHEMA IF NOT EXISTS meta;          -- metas de votos, acompanhamento, alertas, ranking
CREATE SCHEMA IF NOT EXISTS comunicacao;   -- interacoes, redes sociais, mensagens, campanhas
CREATE SCHEMA IF NOT EXISTS eleicao;       -- eleicoes, campanhas e operacao do dia da votacao
CREATE SCHEMA IF NOT EXISTS arquivo;       -- arquivos, anexos, documentos extraidos
CREATE SCHEMA IF NOT EXISTS etl;           -- importacoes, fontes externas, staging, jobs
CREATE SCHEMA IF NOT EXISTS dw;            -- analytics, fatos, dimensoes, indicadores
CREATE SCHEMA IF NOT EXISTS auditoria;     -- trilha de auditoria, logs de exportacao

COMMENT ON SCHEMA global IS 'Dados compartilhados entre todos os tenants: UF, municipios, bairros, zonas, secoes, locais de votacao, datas comemorativas e bases TSE/IBGE.';
COMMENT ON SCHEMA auth IS 'Autenticacao, autorizacao e seguranca: usuarios, perfis, permissoes, sessoes e politicas de acesso territorial.';
COMMENT ON SCHEMA cadastro IS 'Cadastro central: pessoas, documentos, contatos, enderecos, vinculos, liderancas, comunidades, tags e nucleos familiares.';
COMMENT ON SCHEMA territorio IS 'Estrutura territorial operacional e georreferenciamento.';
COMMENT ON SCHEMA agenda IS 'Agenda politica: eventos, convites, presencas e pautas.';
COMMENT ON SCHEMA demanda IS 'Demandas, pedidos, atendimentos e movimentacoes.';
COMMENT ON SCHEMA meta IS 'Metas de votos, acompanhamento, alertas de risco e ranking de liderancas.';
COMMENT ON SCHEMA comunicacao IS 'Comunicacao e relacionamento: interacoes, redes sociais, mensagens e campanhas.';
COMMENT ON SCHEMA eleicao IS 'Eleicoes, campanhas eleitorais e acompanhamento operacional do dia da votacao.';
COMMENT ON SCHEMA arquivo IS 'Arquivos, anexos, fotos e documentos extraidos.';
COMMENT ON SCHEMA etl IS 'Importacao, fontes externas, staging, qualidade e jobs de processamento.';
COMMENT ON SCHEMA dw IS 'Data Warehouse / analytics: fatos, dimensoes, indicadores e relatorios.';
COMMENT ON SCHEMA auditoria IS 'Trilha de auditoria de acoes sensiveis e exportacoes (LGPD).';

-- =====================================================================================
-- 3. ROLE DE APLICACAO E FUNCOES DE APOIO AO RLS
-- =====================================================================================
-- A aplicacao (FastAPI) conecta com uma role SEM privilegio BYPASSRLS.
-- A cada requisicao, executa: SET LOCAL app.current_tenant_id = '<id>';

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_inteligencia') THEN
        CREATE ROLE app_inteligencia LOGIN PASSWORD 'troque_esta_senha';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA global, auth, cadastro, territorio, agenda, demanda,
    meta, comunicacao, eleicao, arquivo, etl, dw, auditoria TO app_inteligencia;

-- Funcao que recupera o tenant corrente da variavel de sessao definida pela aplicacao.
-- Retorna NULL quando nao definida (uso administrativo / ETL).
CREATE OR REPLACE FUNCTION global.tenant_atual()
RETURNS BIGINT
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_valor TEXT;
BEGIN
    v_valor := current_setting('app.current_tenant_id', TRUE);
    IF v_valor IS NULL OR v_valor = '' THEN
        RETURN NULL;
    END IF;
    RETURN v_valor::BIGINT;
END;
$$;

COMMENT ON FUNCTION global.tenant_atual() IS 'Retorna o tenant_id corrente definido por SET LOCAL app.current_tenant_id pela aplicacao. Base para as politicas RLS.';

-- Funcao de trigger para manter a coluna atualizado_em.
CREATE OR REPLACE FUNCTION global.fn_atualiza_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.atualizado_em := now();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION global.fn_atualiza_timestamp() IS 'Atualiza automaticamente a coluna atualizado_em em operacoes de UPDATE.';

-- Funcao de trigger que preenche tenant_id automaticamente em INSERT, quando ausente.
CREATE OR REPLACE FUNCTION global.fn_preenche_tenant()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.tenant_id IS NULL THEN
        NEW.tenant_id := global.tenant_atual();
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION global.fn_preenche_tenant() IS 'Preenche automaticamente tenant_id no INSERT com o tenant corrente da sessao quando omitido.';

-- =====================================================================================
-- 4. SCHEMA public - GESTAO DO SaaS (TENANTS E PLANOS)
-- =====================================================================================

-- 4.1 plano_assinatura -----------------------------------------------------------------
CREATE TABLE public.plano_assinatura (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid(),
    nome                VARCHAR(120) NOT NULL,
    descricao           TEXT,
    preco_mensal        NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (preco_mensal >= 0),
    moeda               CHAR(3) NOT NULL DEFAULT 'BRL',
    limite_usuarios     INTEGER CHECK (limite_usuarios IS NULL OR limite_usuarios > 0),
    limite_pessoas      INTEGER CHECK (limite_pessoas IS NULL OR limite_pessoas > 0),
    limite_armazenamento_mb INTEGER CHECK (limite_armazenamento_mb IS NULL OR limite_armazenamento_mb > 0),
    recursos            JSONB NOT NULL DEFAULT '{}'::jsonb,
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_plano_assinatura_nome UNIQUE (nome),
    CONSTRAINT uq_plano_assinatura_uuid UNIQUE (uuid_publico)
);
COMMENT ON TABLE public.plano_assinatura IS 'Planos comerciais do SaaS, limites, recursos habilitados e regras de cobranca.';

-- 4.2 tenant ---------------------------------------------------------------------------
CREATE TABLE public.tenant (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid(),
    nome                VARCHAR(180) NOT NULL,
    slug                VARCHAR(80) NOT NULL,
    documento           VARCHAR(20),                 -- CNPJ/CPF do contratante
    tem_mandato         BOOLEAN NOT NULL DEFAULT FALSE,
    plano_assinatura_id BIGINT REFERENCES public.plano_assinatura(id),
    data_inicio_contrato DATE,
    data_fim_contrato   DATE,
    status              VARCHAR(20) NOT NULL DEFAULT 'ativo'
                        CHECK (status IN ('ativo','suspenso','cancelado','trial','inadimplente')),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em         TIMESTAMPTZ,
    CONSTRAINT uq_tenant_slug UNIQUE (slug),
    CONSTRAINT uq_tenant_uuid UNIQUE (uuid_publico)
);
COMMENT ON TABLE public.tenant IS 'Politico ou candidato assinante da plataforma. Unidade principal de isolamento dos dados.';

-- 4.3 tenant_configuracao --------------------------------------------------------------
CREATE TABLE public.tenant_configuracao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome_publico        VARCHAR(180),
    cor_primaria        VARCHAR(9),
    logo_url            TEXT,
    fuso_horario        VARCHAR(60) NOT NULL DEFAULT 'America/Sao_Paulo',
    percentual_alerta_meta NUMERIC(5,2) NOT NULL DEFAULT 70.00
                        CHECK (percentual_alerta_meta BETWEEN 0 AND 100),
    integracoes         JSONB NOT NULL DEFAULT '{}'::jsonb,
    preferencias        JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenant_configuracao_tenant UNIQUE (tenant_id)
);
COMMENT ON TABLE public.tenant_configuracao IS 'Configuracoes especificas de cada tenant: nome publico, preferencias, integracoes e parametros operacionais.';

-- =====================================================================================
-- 5. SCHEMA global - DADOS COMPARTILHADOS (TSE / IBGE / REFERENCIA)
-- =====================================================================================

-- 5.1 estado ---------------------------------------------------------------------------
CREATE TABLE global.estado (
    id              SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_ibge     SMALLINT NOT NULL,
    uf              CHAR(2) NOT NULL,
    nome            VARCHAR(60) NOT NULL,
    regiao          VARCHAR(20),
    CONSTRAINT uq_estado_uf UNIQUE (uf),
    CONSTRAINT uq_estado_codigo_ibge UNIQUE (codigo_ibge)
);
COMMENT ON TABLE global.estado IS 'Unidades federativas brasileiras (UF) com codigo IBGE.';

-- 5.2 municipio ------------------------------------------------------------------------
CREATE TABLE global.municipio (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estado_id       SMALLINT NOT NULL REFERENCES global.estado(id),
    codigo_ibge     INTEGER NOT NULL,
    codigo_tse      INTEGER,
    nome            VARCHAR(120) NOT NULL,
    latitude        NUMERIC(10,7),
    longitude       NUMERIC(10,7),
    geom            geography(Point, 4326),
    data_aniversario DATE,                 -- aniversario do municipio (relacionamento)
    CONSTRAINT uq_municipio_codigo_ibge UNIQUE (codigo_ibge),
    CONSTRAINT uq_municipio_codigo_tse UNIQUE (codigo_tse)
);
COMMENT ON TABLE global.municipio IS 'Cadastro oficial de municipios, integrado com codigo IBGE e codigo TSE.';

-- 5.3 bairro ---------------------------------------------------------------------------
CREATE TABLE global.bairro (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    municipio_id    INTEGER NOT NULL REFERENCES global.municipio(id),
    nome            VARCHAR(150) NOT NULL,
    origem          VARCHAR(20) NOT NULL DEFAULT 'oficial'
                    CHECK (origem IN ('oficial','manual','importado')),
    CONSTRAINT uq_bairro_municipio_nome UNIQUE (municipio_id, nome)
);
COMMENT ON TABLE global.bairro IS 'Bairros por municipio. Pode ter origem oficial ou cadastro manual da campanha.';

-- 5.4 zona_eleitoral -------------------------------------------------------------------
CREATE TABLE global.zona_eleitoral (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estado_id       SMALLINT NOT NULL REFERENCES global.estado(id),
    municipio_id    INTEGER REFERENCES global.municipio(id),
    numero_zona     SMALLINT NOT NULL,
    descricao       VARCHAR(150),
    CONSTRAINT uq_zona_eleitoral UNIQUE (estado_id, numero_zona)
);
COMMENT ON TABLE global.zona_eleitoral IS 'Zona eleitoral oficial do TSE, vinculada a UF e municipio.';

-- 5.5 local_votacao --------------------------------------------------------------------
CREATE TABLE global.local_votacao (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    municipio_id    INTEGER NOT NULL REFERENCES global.municipio(id),
    zona_eleitoral_id INTEGER REFERENCES global.zona_eleitoral(id),
    bairro_id       INTEGER REFERENCES global.bairro(id),
    codigo_local    INTEGER,
    nome            VARCHAR(180) NOT NULL,
    logradouro      VARCHAR(180),
    numero          VARCHAR(20),
    complemento     VARCHAR(120),
    cep             VARCHAR(9),
    latitude        NUMERIC(10,7),
    longitude       NUMERIC(10,7),
    geom            geography(Point, 4326),
    situacao        VARCHAR(20) NOT NULL DEFAULT 'ativo'
                    CHECK (situacao IN ('ativo','inativo','desativado')),
    CONSTRAINT uq_local_votacao UNIQUE (municipio_id, zona_eleitoral_id, codigo_local)
);
COMMENT ON TABLE global.local_votacao IS 'Local oficial de votacao com endereco, georreferencia e situacao cadastral.';

-- 5.6 secao_eleitoral ------------------------------------------------------------------
CREATE TABLE global.secao_eleitoral (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    zona_eleitoral_id INTEGER NOT NULL REFERENCES global.zona_eleitoral(id),
    local_votacao_id INTEGER REFERENCES global.local_votacao(id),
    numero_secao    SMALLINT NOT NULL,
    agregada_em     SMALLINT,             -- secao agregadora, quando houver
    CONSTRAINT uq_secao_eleitoral UNIQUE (zona_eleitoral_id, numero_secao)
);
COMMENT ON TABLE global.secao_eleitoral IS 'Secao eleitoral oficial, vinculada a zona eleitoral e local de votacao.';

-- 5.7 categoria_data_comemorativa ------------------------------------------------------
CREATE TABLE global.categoria_data_comemorativa (
    id              SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR(80) NOT NULL,
    descricao       VARCHAR(255),
    CONSTRAINT uq_categoria_data_comemorativa_nome UNIQUE (nome)
);
COMMENT ON TABLE global.categoria_data_comemorativa IS 'Classifica datas comemorativas: aniversario municipal, religiosa, civica, cultural ou comunitaria.';

-- 5.8 data_comemorativa ----------------------------------------------------------------
CREATE TABLE global.data_comemorativa (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    categoria_id    SMALLINT REFERENCES global.categoria_data_comemorativa(id),
    nome            VARCHAR(180) NOT NULL,
    descricao       TEXT,
    dia             SMALLINT CHECK (dia BETWEEN 1 AND 31),
    mes             SMALLINT CHECK (mes BETWEEN 1 AND 12),
    data_movel      BOOLEAN NOT NULL DEFAULT FALSE,   -- datas como Pascoa
    ambito          VARCHAR(20) NOT NULL DEFAULT 'nacional'
                    CHECK (ambito IN ('nacional','estadual','municipal','regional','setorial')),
    estado_id       SMALLINT REFERENCES global.estado(id),
    municipio_id    INTEGER REFERENCES global.municipio(id),
    ativo           BOOLEAN NOT NULL DEFAULT TRUE
);
COMMENT ON TABLE global.data_comemorativa IS 'Datas civicas, religiosas, municipais, culturais e setoriais para relacionamento politico e alertas.';

CREATE INDEX ix_data_comemorativa_dia_mes ON global.data_comemorativa (mes, dia);

-- =====================================================================================
-- 6. SCHEMA auth - AUTENTICACAO, AUTORIZACAO E SEGURANCA
-- =====================================================================================

-- 6.1 usuario --------------------------------------------------------------------------
CREATE TABLE auth.usuario (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id           BIGINT,                          -- FK adicionada apos cadastro.pessoa
    nome                VARCHAR(180) NOT NULL,
    email               CITEXT NOT NULL,
    hash_senha          TEXT NOT NULL,
    telefone            VARCHAR(20),
    mfa_habilitado      BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_segredo         TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'ativo'
                        CHECK (status IN ('ativo','inativo','bloqueado','pendente')),
    ultimo_login_em     TIMESTAMPTZ,
    tentativas_login    SMALLINT NOT NULL DEFAULT 0,
    senha_alterada_em   TIMESTAMPTZ,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em         TIMESTAMPTZ,
    CONSTRAINT uq_usuario_email_tenant UNIQUE (tenant_id, email),
    CONSTRAINT uq_usuario_uuid UNIQUE (uuid_publico)
);
COMMENT ON TABLE auth.usuario IS 'Conta de acesso ao sistema, vinculada a um tenant e opcionalmente a uma pessoa cadastrada.';

-- 6.2 perfil_acesso --------------------------------------------------------------------
CREATE TABLE auth.perfil_acesso (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL = perfil global do sistema
    nome            VARCHAR(80) NOT NULL,
    codigo          VARCHAR(50) NOT NULL,
    descricao       VARCHAR(255),
    nivel           SMALLINT NOT NULL DEFAULT 5,        -- 1=gestor ... 9=restrito
    sistema         BOOLEAN NOT NULL DEFAULT FALSE,     -- perfil padrao nao editavel
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_perfil_acesso_codigo UNIQUE (tenant_id, codigo)
);
COMMENT ON TABLE auth.perfil_acesso IS 'Papel de acesso: gestor, coordenador territorial, lider, telefonista, atendimento, RH, administrativo.';

-- 6.3 permissao ------------------------------------------------------------------------
CREATE TABLE auth.permissao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo          VARCHAR(100) NOT NULL,
    modulo          VARCHAR(60) NOT NULL,
    acao            VARCHAR(30) NOT NULL
                    CHECK (acao IN ('visualizar','criar','editar','excluir','exportar','aprovar','administrar')),
    descricao       VARCHAR(255),
    CONSTRAINT uq_permissao_codigo UNIQUE (codigo)
);
COMMENT ON TABLE auth.permissao IS 'Permissao granular sobre modulos, acoes, tipos de dados e exportacoes.';

-- 6.4 perfil_permissao (N:N) -----------------------------------------------------------
CREATE TABLE auth.perfil_permissao (
    perfil_acesso_id BIGINT NOT NULL REFERENCES auth.perfil_acesso(id) ON DELETE CASCADE,
    permissao_id     BIGINT NOT NULL REFERENCES auth.permissao(id) ON DELETE CASCADE,
    concedida_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_perfil_permissao PRIMARY KEY (perfil_acesso_id, permissao_id)
);
COMMENT ON TABLE auth.perfil_permissao IS 'Associacao entre perfis de acesso e permissoes.';

-- 6.5 usuario_perfil (N:N) -------------------------------------------------------------
CREATE TABLE auth.usuario_perfil (
    usuario_id       BIGINT NOT NULL REFERENCES auth.usuario(id) ON DELETE CASCADE,
    perfil_acesso_id BIGINT NOT NULL REFERENCES auth.perfil_acesso(id) ON DELETE CASCADE,
    tenant_id        BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    atribuido_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_usuario_perfil PRIMARY KEY (usuario_id, perfil_acesso_id)
);
COMMENT ON TABLE auth.usuario_perfil IS 'Associacao entre usuarios e perfis, permitindo mais de um papel por usuario.';

-- 6.6 sessao_usuario -------------------------------------------------------------------
CREATE TABLE auth.sessao_usuario (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    usuario_id      BIGINT NOT NULL REFERENCES auth.usuario(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL,
    refresh_token_hash TEXT,
    dispositivo     VARCHAR(180),
    user_agent      TEXT,
    ip_origem       INET,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_em       TIMESTAMPTZ NOT NULL,
    revogada_em     TIMESTAMPTZ,
    CONSTRAINT uq_sessao_token UNIQUE (token_hash)
);
COMMENT ON TABLE auth.sessao_usuario IS 'Sessoes ativas, tokens, dispositivos, IPs e datas de expiracao.';

CREATE INDEX ix_sessao_usuario_usuario ON auth.sessao_usuario (usuario_id);

-- 6.7 politica_acesso_territorial ------------------------------------------------------
CREATE TABLE auth.politica_acesso_territorial (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    usuario_id      BIGINT NOT NULL REFERENCES auth.usuario(id) ON DELETE CASCADE,
    tipo_escopo     VARCHAR(30) NOT NULL
                    CHECK (tipo_escopo IN ('estado','municipio','bairro','zona_eleitoral','secao_eleitoral','territorio','global')),
    estado_id       SMALLINT REFERENCES global.estado(id),
    municipio_id    INTEGER REFERENCES global.municipio(id),
    bairro_id       INTEGER REFERENCES global.bairro(id),
    zona_eleitoral_id INTEGER REFERENCES global.zona_eleitoral(id),
    secao_eleitoral_id BIGINT REFERENCES global.secao_eleitoral(id),
    territorio_id   BIGINT,                  -- FK adicionada apos territorio.territorio
    pode_administrar BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE auth.politica_acesso_territorial IS 'Define quais territorios/regioes/cidades/bairros/zonas/secoes um usuario pode visualizar ou administrar.';

CREATE INDEX ix_politica_acesso_usuario ON auth.politica_acesso_territorial (usuario_id);

-- =====================================================================================
-- 7. SCHEMA cadastro - CADASTRO CENTRAL
-- =====================================================================================

-- 7.1 Tabelas de dominio/referencia (por tenant, permitem personalizacao) --------------
CREATE TABLE cadastro.profissao (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL = catalogo global
    nome        VARCHAR(120) NOT NULL,
    cbo         VARCHAR(10),
    CONSTRAINT uq_profissao_nome UNIQUE (tenant_id, nome)
);
COMMENT ON TABLE cadastro.profissao IS 'Cadastro padronizado de profissoes para segmentacao e relatorios.';

CREATE TABLE cadastro.escolaridade (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome        VARCHAR(80) NOT NULL,
    ordem       SMALLINT,
    CONSTRAINT uq_escolaridade_nome UNIQUE (nome)
);
COMMENT ON TABLE cadastro.escolaridade IS 'Niveis de escolaridade padronizados.';

CREATE TABLE cadastro.religiao (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome        VARCHAR(80) NOT NULL,
    CONSTRAINT uq_religiao_nome UNIQUE (nome)
);
COMMENT ON TABLE cadastro.religiao IS 'Religioes ou denominacoes (coleta condicionada a base legal adequada - LGPD).';

CREATE TABLE cadastro.partido (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sigla       VARCHAR(20) NOT NULL,
    nome        VARCHAR(120) NOT NULL,
    numero      SMALLINT,
    CONSTRAINT uq_partido_sigla UNIQUE (sigla)
);
COMMENT ON TABLE cadastro.partido IS 'Partidos politicos para vinculos, historico ou relacionamento institucional.';

CREATE TABLE cadastro.pessoa_tipo (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(40) NOT NULL,
    nome        VARCHAR(80) NOT NULL,
    descricao   VARCHAR(255),
    CONSTRAINT uq_pessoa_tipo_codigo UNIQUE (codigo)
);
COMMENT ON TABLE cadastro.pessoa_tipo IS 'Classificacao de pessoa: eleitor, apoiador, lider, coordenador, liderado, telefonista, contato institucional, voluntario.';

-- 7.2 pessoa ---------------------------------------------------------------------------
CREATE TABLE cadastro.pessoa (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome_completo       VARCHAR(180) NOT NULL,
    nome_social         VARCHAR(180),
    apelido             VARCHAR(120),
    sexo                CHAR(1) CHECK (sexo IN ('M','F','O','N')),
    data_nascimento     DATE,
    estado_civil        VARCHAR(30),
    escolaridade_id     SMALLINT REFERENCES cadastro.escolaridade(id),
    profissao_id        INTEGER REFERENCES cadastro.profissao(id),
    religiao_id         SMALLINT REFERENCES cadastro.religiao(id),
    foto_arquivo_id     BIGINT,                       -- FK adicionada apos arquivo.arquivo
    nivel_engajamento   SMALLINT CHECK (nivel_engajamento BETWEEN 0 AND 10),
    score_confiabilidade NUMERIC(5,2) CHECK (score_confiabilidade BETWEEN 0 AND 100),
    completude_cadastral NUMERIC(5,2) CHECK (completude_cadastral BETWEEN 0 AND 100),
    fonte_dado_id       BIGINT,                       -- FK adicionada apos etl.fonte_dado
    observacoes         TEXT,
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    criado_por          BIGINT REFERENCES auth.usuario(id),
    atualizado_por      BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em         TIMESTAMPTZ,
    CONSTRAINT uq_pessoa_uuid UNIQUE (uuid_publico)
);
COMMENT ON TABLE cadastro.pessoa IS 'Entidade central: eleitor, apoiador, lider, coordenador, contato institucional ou integrante de equipe.';

CREATE INDEX ix_pessoa_tenant ON cadastro.pessoa (tenant_id);
CREATE INDEX ix_pessoa_nome_trgm ON cadastro.pessoa USING gin (nome_completo gin_trgm_ops);
CREATE INDEX ix_pessoa_data_nascimento ON cadastro.pessoa (tenant_id, (EXTRACT(MONTH FROM data_nascimento)), (EXTRACT(DAY FROM data_nascimento)));

-- FK pendente de auth.usuario -> cadastro.pessoa
ALTER TABLE auth.usuario
    ADD CONSTRAINT fk_usuario_pessoa FOREIGN KEY (pessoa_id)
    REFERENCES cadastro.pessoa(id) ON DELETE SET NULL;

-- 7.3 pessoa_documento -----------------------------------------------------------------
CREATE TABLE cadastro.pessoa_documento (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    tipo_documento  VARCHAR(20) NOT NULL
                    CHECK (tipo_documento IN ('cpf','rg','titulo_eleitor','cnh','passaporte','outro')),
    numero          VARCHAR(40) NOT NULL,
    orgao_emissor   VARCHAR(40),
    uf_emissor      CHAR(2),
    data_emissao    DATE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_pessoa_documento UNIQUE (tenant_id, tipo_documento, numero)
);
COMMENT ON TABLE cadastro.pessoa_documento IS 'Documentos pessoais: CPF, RG, titulo de eleitor e outros identificadores.';

CREATE INDEX ix_pessoa_documento_pessoa ON cadastro.pessoa_documento (pessoa_id);

-- 7.4 pessoa_contato -------------------------------------------------------------------
CREATE TABLE cadastro.pessoa_contato (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    tipo_contato    VARCHAR(20) NOT NULL
                    CHECK (tipo_contato IN ('telefone','celular','whatsapp','email','outro')),
    valor           VARCHAR(180) NOT NULL,
    principal       BOOLEAN NOT NULL DEFAULT FALSE,
    verificado      BOOLEAN NOT NULL DEFAULT FALSE,
    observacao      VARCHAR(255),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE cadastro.pessoa_contato IS 'Telefones, WhatsApp, e-mails e outros canais de contato da pessoa.';

CREATE INDEX ix_pessoa_contato_pessoa ON cadastro.pessoa_contato (pessoa_id);
CREATE INDEX ix_pessoa_contato_valor ON cadastro.pessoa_contato (tenant_id, valor);

-- 7.5 pessoa_rede_social ---------------------------------------------------------------
CREATE TABLE cadastro.pessoa_rede_social (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    rede            VARCHAR(30) NOT NULL
                    CHECK (rede IN ('instagram','facebook','tiktok','x','youtube','linkedin','outro')),
    usuario_perfil  VARCHAR(120),
    url             TEXT,
    seguidores      INTEGER,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE cadastro.pessoa_rede_social IS 'Perfis sociais associados a pessoa: Instagram, Facebook, TikTok, X e outros.';

-- 7.6 endereco -------------------------------------------------------------------------
CREATE TABLE cadastro.endereco (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    municipio_id    INTEGER REFERENCES global.municipio(id),
    bairro_id       INTEGER REFERENCES global.bairro(id),
    bairro_texto    VARCHAR(150),               -- quando bairro nao catalogado
    logradouro      VARCHAR(180),
    numero          VARCHAR(20),
    complemento     VARCHAR(120),
    cep             VARCHAR(9),
    ponto_referencia VARCHAR(180),
    latitude        NUMERIC(10,7),
    longitude       NUMERIC(10,7),
    geom            geography(Point, 4326),
    geocodificado   BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE cadastro.endereco IS 'Endereco estruturado com logradouro, numero, complemento, bairro, cidade, CEP e georreferencia.';

CREATE INDEX ix_endereco_geom ON cadastro.endereco USING gist (geom);
CREATE INDEX ix_endereco_municipio ON cadastro.endereco (municipio_id);

-- 7.7 pessoa_endereco (N:N) ------------------------------------------------------------
CREATE TABLE cadastro.pessoa_endereco (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    endereco_id     BIGINT NOT NULL REFERENCES cadastro.endereco(id) ON DELETE CASCADE,
    tipo            VARCHAR(20) NOT NULL DEFAULT 'residencial'
                    CHECK (tipo IN ('residencial','eleitoral','comercial','temporario','outro')),
    principal       BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_pessoa_endereco UNIQUE (pessoa_id, endereco_id, tipo)
);
COMMENT ON TABLE cadastro.pessoa_endereco IS 'Associacao entre pessoa e endereco (residencial, eleitoral, comercial ou temporario).';

-- 7.8 pessoa_pessoa_tipo (N:N) ---------------------------------------------------------
CREATE TABLE cadastro.pessoa_pessoa_tipo (
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    pessoa_tipo_id  SMALLINT NOT NULL REFERENCES cadastro.pessoa_tipo(id),
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_pessoa_pessoa_tipo PRIMARY KEY (pessoa_id, pessoa_tipo_id)
);
COMMENT ON TABLE cadastro.pessoa_pessoa_tipo IS 'Associacao pessoa x tipos, permitindo que a mesma pessoa seja lider e eleitor, por exemplo.';

-- 7.9 eleitor (extensao 1:1 de pessoa) -------------------------------------------------
CREATE TABLE cadastro.eleitor (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    titulo_eleitor  VARCHAR(20),
    zona_eleitoral_id INTEGER REFERENCES global.zona_eleitoral(id),
    secao_eleitoral_id BIGINT REFERENCES global.secao_eleitoral(id),
    local_votacao_id INTEGER REFERENCES global.local_votacao(id),
    municipio_voto_id INTEGER REFERENCES global.municipio(id),
    situacao_titulo VARCHAR(30) DEFAULT 'regular'
                    CHECK (situacao_titulo IN ('regular','suspenso','cancelado','desconhecido')),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_eleitor_pessoa UNIQUE (pessoa_id)
);
COMMENT ON TABLE cadastro.eleitor IS 'Extensao da pessoa com dados eleitorais: titulo, zona, secao e local de votacao.';

CREATE INDEX ix_eleitor_zona_secao ON cadastro.eleitor (tenant_id, zona_eleitoral_id, secao_eleitoral_id);

-- 7.10 lideranca -----------------------------------------------------------------------
CREATE TABLE cadastro.lideranca (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id           BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    tipo_lideranca      VARCHAR(40) NOT NULL DEFAULT 'lider'
                        CHECK (tipo_lideranca IN ('coordenador_geral','coordenador_territorial','lider','sublider')),
    coordenador_id      BIGINT REFERENCES cadastro.lideranca(id),  -- auto-relacionamento hierarquico
    meta_votos          INTEGER CHECK (meta_votos IS NULL OR meta_votos >= 0),
    apelido_campanha    VARCHAR(120),
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lideranca_pessoa UNIQUE (pessoa_id)
);
COMMENT ON TABLE cadastro.lideranca IS 'Papel operacional de lideranca: tipo de lider, coordenador responsavel, equipe, meta associada.';

CREATE INDEX ix_lideranca_coordenador ON cadastro.lideranca (coordenador_id);

-- 7.11 hierarquia_lideranca ------------------------------------------------------------
CREATE TABLE cadastro.hierarquia_lideranca (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    lideranca_superior_id BIGINT NOT NULL REFERENCES cadastro.lideranca(id) ON DELETE CASCADE,
    pessoa_subordinada_id BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    papel_subordinado VARCHAR(30) NOT NULL DEFAULT 'liderado'
                    CHECK (papel_subordinado IN ('lider','liderado','apoiador','eleitor')),
    data_inicio     DATE NOT NULL DEFAULT CURRENT_DATE,
    data_fim        DATE,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_hierarquia_lideranca UNIQUE (lideranca_superior_id, pessoa_subordinada_id, data_inicio)
);
COMMENT ON TABLE cadastro.hierarquia_lideranca IS 'Relacoes entre coordenador geral, coordenador territorial, lider, liderado e apoiador.';

CREATE INDEX ix_hierarquia_pessoa_sub ON cadastro.hierarquia_lideranca (pessoa_subordinada_id);

-- 7.12 indicacao -----------------------------------------------------------------------
CREATE TABLE cadastro.indicacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_indicada_id BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    pessoa_indicante_id BIGINT REFERENCES cadastro.pessoa(id) ON DELETE SET NULL,
    origem          VARCHAR(60),
    contexto        VARCHAR(255),
    data_indicacao  DATE NOT NULL DEFAULT CURRENT_DATE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE cadastro.indicacao IS 'Registra quem indicou quem, origem da indicacao, data e contexto.';

-- 7.13 relacionamento_pessoa -----------------------------------------------------------
CREATE TABLE cadastro.relacionamento_pessoa (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_origem_id BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    pessoa_destino_id BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    tipo_relacao    VARCHAR(40) NOT NULL
                    CHECK (tipo_relacao IN ('familiar','lideranca','amizade','apoio_politico','contato_institucional','comunitario','outro')),
    descricao       VARCHAR(255),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_relacionamento_distinto CHECK (pessoa_origem_id <> pessoa_destino_id)
);
COMMENT ON TABLE cadastro.relacionamento_pessoa IS 'Relacoes entre pessoas: familiar, lideranca, amizade, apoio politico, institucional ou comunitario.';

-- 7.14 nucleo_familiar -----------------------------------------------------------------
CREATE TABLE cadastro.nucleo_familiar (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome            VARCHAR(150),
    pessoa_referencia_id BIGINT REFERENCES cadastro.pessoa(id) ON DELETE SET NULL,
    endereco_id     BIGINT REFERENCES cadastro.endereco(id),
    quantidade_membros SMALLINT,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE cadastro.nucleo_familiar IS 'Grupo familiar usado para mobilizacao, metas e analise territorial.';

-- 7.15 pessoa_nucleo_familiar (N:N) ----------------------------------------------------
CREATE TABLE cadastro.pessoa_nucleo_familiar (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    nucleo_familiar_id BIGINT NOT NULL REFERENCES cadastro.nucleo_familiar(id) ON DELETE CASCADE,
    parentesco      VARCHAR(40),
    responsavel     BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_pessoa_nucleo UNIQUE (pessoa_id, nucleo_familiar_id)
);
COMMENT ON TABLE cadastro.pessoa_nucleo_familiar IS 'Associacao pessoa x nucleo familiar, permitindo multiplos vinculos quando necessario.';

-- 7.16 comunidade ----------------------------------------------------------------------
CREATE TABLE cadastro.comunidade (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome            VARCHAR(150) NOT NULL,
    tipo            VARCHAR(40)
                    CHECK (tipo IN ('religiosa','profissional','territorial','politica','social','esportiva','cultural','outra')),
    descricao       TEXT,
    lider_responsavel_id BIGINT REFERENCES cadastro.lideranca(id),
    municipio_id    INTEGER REFERENCES global.municipio(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_comunidade_nome UNIQUE (tenant_id, nome)
);
COMMENT ON TABLE cadastro.comunidade IS 'Grupo social, religioso, profissional, territorial ou politico ao qual pessoas podem pertencer.';

-- 7.17 pessoa_comunidade (N:N) ---------------------------------------------------------
CREATE TABLE cadastro.pessoa_comunidade (
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    comunidade_id   BIGINT NOT NULL REFERENCES cadastro.comunidade(id) ON DELETE CASCADE,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    papel           VARCHAR(40),
    desde           DATE DEFAULT CURRENT_DATE,
    CONSTRAINT pk_pessoa_comunidade PRIMARY KEY (pessoa_id, comunidade_id)
);
COMMENT ON TABLE cadastro.pessoa_comunidade IS 'Associacao entre pessoas e comunidades.';

-- 7.18 tag -----------------------------------------------------------------------------
CREATE TABLE cadastro.tag (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome            VARCHAR(80) NOT NULL,
    cor             VARCHAR(9),
    categoria       VARCHAR(40),
    descricao       VARCHAR(255),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tag_nome UNIQUE (tenant_id, nome)
);
COMMENT ON TABLE cadastro.tag IS 'Marcador de segmentacao: META 30, META 100, evangelico, juventude, saude, bairro especifico ou grupo estrategico.';

-- 7.19 pessoa_tag (N:N) ----------------------------------------------------------------
CREATE TABLE cadastro.pessoa_tag (
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    tag_id          BIGINT NOT NULL REFERENCES cadastro.tag(id) ON DELETE CASCADE,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    atribuido_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_pessoa_tag PRIMARY KEY (pessoa_id, tag_id)
);
COMMENT ON TABLE cadastro.pessoa_tag IS 'Associacao entre pessoas e tags.';

-- 7.20 pessoa_complemento_politico (1:1) -----------------------------------------------
CREATE TABLE cadastro.pessoa_complemento_politico (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    vinculo_politico VARCHAR(120),
    partido_id      SMALLINT REFERENCES cadastro.partido(id),
    cargo_funcao    VARCHAR(120),
    temas_interesse JSONB NOT NULL DEFAULT '[]'::jsonb,
    nivel_engajamento SMALLINT CHECK (nivel_engajamento BETWEEN 0 AND 10),
    observacoes     TEXT,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_complemento_politico_pessoa UNIQUE (pessoa_id)
);
COMMENT ON TABLE cadastro.pessoa_complemento_politico IS 'Informacoes politicas e de engajamento: vinculo, partido, cargo, funcao, temas de interesse e nivel de engajamento.';

-- 7.21 validacao_cadastro --------------------------------------------------------------
CREATE TABLE cadastro.validacao_cadastro (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    motivo          VARCHAR(40) NOT NULL
                    CHECK (motivo IN ('incompleto','duplicado','sem_lider','dados_invalidos','revisao_periodica','outro')),
    status          VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','aprovado','rejeitado','em_revisao')),
    observacao      TEXT,
    revisado_por    BIGINT REFERENCES auth.usuario(id),
    revisado_em     TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE cadastro.validacao_cadastro IS 'Controla revisao, aprovacao, rejeicao ou pendencias de cadastros incompletos, duplicados ou sem lider.';

CREATE INDEX ix_validacao_cadastro_status ON cadastro.validacao_cadastro (tenant_id, status);

-- 7.22 suspeita_duplicidade ------------------------------------------------------------
CREATE TABLE cadastro.suspeita_duplicidade (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    pessoa_duplicada_id BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    criterio        VARCHAR(40) NOT NULL
                    CHECK (criterio IN ('cpf','telefone','email','titulo_eleitor','nome_data_nascimento','fuzzy')),
    score_similaridade NUMERIC(5,2) CHECK (score_similaridade BETWEEN 0 AND 100),
    status          VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','confirmada','descartada','mesclada')),
    resolvido_por   BIGINT REFERENCES auth.usuario(id),
    resolvido_em    TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_duplicidade_distinta CHECK (pessoa_id <> pessoa_duplicada_id)
);
COMMENT ON TABLE cadastro.suspeita_duplicidade IS 'Possiveis duplicidades por CPF, telefone, e-mail, titulo de eleitor, nome e data de nascimento.';

CREATE INDEX ix_suspeita_duplicidade_status ON cadastro.suspeita_duplicidade (tenant_id, status);

-- =====================================================================================
-- 8. SCHEMA territorio - ESTRUTURA TERRITORIAL E GEORREFERENCIAMENTO
-- =====================================================================================

-- 8.1 tipo_territorio ------------------------------------------------------------------
CREATE TABLE territorio.tipo_territorio (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(40) NOT NULL,
    nome        VARCHAR(80) NOT NULL,
    descricao   VARCHAR(255),
    CONSTRAINT uq_tipo_territorio_codigo UNIQUE (codigo)
);
COMMENT ON TABLE territorio.tipo_territorio IS 'Classifica territorios: estado, municipio, bairro, zona, secao, microrregiao, comunidade ou area personalizada.';

-- 8.2 territorio -----------------------------------------------------------------------
CREATE TABLE territorio.territorio (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    tipo_territorio_id SMALLINT NOT NULL REFERENCES territorio.tipo_territorio(id),
    nome            VARCHAR(150) NOT NULL,
    estado_id       SMALLINT REFERENCES global.estado(id),
    municipio_id    INTEGER REFERENCES global.municipio(id),
    bairro_id       INTEGER REFERENCES global.bairro(id),
    zona_eleitoral_id INTEGER REFERENCES global.zona_eleitoral(id),
    secao_eleitoral_id BIGINT REFERENCES global.secao_eleitoral(id),
    geom            geography(MultiPolygon, 4326),
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE territorio.territorio IS 'Unidade territorial operacional: regiao, microrregiao, cidade, bairro, zona, secao ou area customizada.';

CREATE INDEX ix_territorio_tenant ON territorio.territorio (tenant_id);
CREATE INDEX ix_territorio_geom ON territorio.territorio USING gist (geom);

-- FK pendente de auth.politica_acesso_territorial -> territorio.territorio
ALTER TABLE auth.politica_acesso_territorial
    ADD CONSTRAINT fk_politica_territorio FOREIGN KEY (territorio_id)
    REFERENCES territorio.territorio(id) ON DELETE CASCADE;

-- 8.3 territorio_hierarquia ------------------------------------------------------------
CREATE TABLE territorio.territorio_hierarquia (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    territorio_pai_id BIGINT NOT NULL REFERENCES territorio.territorio(id) ON DELETE CASCADE,
    territorio_filho_id BIGINT NOT NULL REFERENCES territorio.territorio(id) ON DELETE CASCADE,
    CONSTRAINT uq_territorio_hierarquia UNIQUE (territorio_pai_id, territorio_filho_id),
    CONSTRAINT ck_territorio_hierarquia_distinto CHECK (territorio_pai_id <> territorio_filho_id)
);
COMMENT ON TABLE territorio.territorio_hierarquia IS 'Relacao pai-filho entre territorios, formando a arvore territorial.';

-- 8.4 pessoa_territorio (N:N) ----------------------------------------------------------
CREATE TABLE territorio.pessoa_territorio (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    territorio_id   BIGINT NOT NULL REFERENCES territorio.territorio(id) ON DELETE CASCADE,
    vinculo         VARCHAR(20) NOT NULL DEFAULT 'moradia'
                    CHECK (vinculo IN ('moradia','atuacao','votacao','responsabilidade')),
    CONSTRAINT uq_pessoa_territorio UNIQUE (pessoa_id, territorio_id, vinculo)
);
COMMENT ON TABLE territorio.pessoa_territorio IS 'Associa pessoas a territorios de moradia, atuacao, votacao ou responsabilidade.';

-- 8.5 lideranca_territorio (N:N) -------------------------------------------------------
CREATE TABLE territorio.lideranca_territorio (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    lideranca_id    BIGINT NOT NULL REFERENCES cadastro.lideranca(id) ON DELETE CASCADE,
    territorio_id   BIGINT NOT NULL REFERENCES territorio.territorio(id) ON DELETE CASCADE,
    responsabilidade VARCHAR(20) NOT NULL DEFAULT 'principal'
                    CHECK (responsabilidade IN ('principal','apoio','compartilhada')),
    CONSTRAINT uq_lideranca_territorio UNIQUE (lideranca_id, territorio_id)
);
COMMENT ON TABLE territorio.lideranca_territorio IS 'Territorios sob responsabilidade de lideres ou coordenadores.';

-- 8.6 geocodificacao -------------------------------------------------------------------
CREATE TABLE territorio.geocodificacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    entidade_tipo   VARCHAR(30) NOT NULL
                    CHECK (entidade_tipo IN ('endereco','evento','demanda','local_votacao','pessoa')),
    entidade_id     BIGINT NOT NULL,
    endereco_texto  TEXT,
    latitude        NUMERIC(10,7),
    longitude       NUMERIC(10,7),
    geom            geography(Point, 4326),
    precisao        VARCHAR(30)
                    CHECK (precisao IN ('exata','aproximada','centroide','interpolada','falha')),
    provedor        VARCHAR(40),
    status          VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','sucesso','falha','revisar')),
    processado_em   TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE territorio.geocodificacao IS 'Resultados de geocodificacao de enderecos, eventos e demandas, com precisao, provedor e status.';

CREATE INDEX ix_geocodificacao_entidade ON territorio.geocodificacao (tenant_id, entidade_tipo, entidade_id);

-- 8.7 area_mapa ------------------------------------------------------------------------
CREATE TABLE territorio.area_mapa (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome            VARCHAR(150) NOT NULL,
    descricao       TEXT,
    geom            geography(MultiPolygon, 4326) NOT NULL,
    cor             VARCHAR(9),
    criado_por      BIGINT REFERENCES auth.usuario(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE territorio.area_mapa IS 'Poligonos ou areas geograficas customizadas usadas em mapas, filtros e dashboards.';

CREATE INDEX ix_area_mapa_geom ON territorio.area_mapa USING gist (geom);

-- =====================================================================================
-- 9. SCHEMA agenda - AGENDA E EVENTOS
-- =====================================================================================

-- 9.1 tipo_evento ----------------------------------------------------------------------
CREATE TABLE agenda.tipo_evento (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL = catalogo padrao
    codigo      VARCHAR(40) NOT NULL,
    nome        VARCHAR(80) NOT NULL,
    CONSTRAINT uq_tipo_evento_codigo UNIQUE (tenant_id, codigo)
);
COMMENT ON TABLE agenda.tipo_evento IS 'Classifica eventos: politico, religioso, comunitario, partidario, institucional ou cultural.';

-- 9.2 status_evento --------------------------------------------------------------------
CREATE TABLE agenda.status_evento (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    CONSTRAINT uq_status_evento_codigo UNIQUE (codigo)
);
COMMENT ON TABLE agenda.status_evento IS 'Situacao do evento: planejado, confirmado, realizado, cancelado ou remarcado.';

-- 9.3 evento ---------------------------------------------------------------------------
CREATE TABLE agenda.evento (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    tipo_evento_id      SMALLINT REFERENCES agenda.tipo_evento(id),
    status_evento_id    SMALLINT REFERENCES agenda.status_evento(id),
    titulo              VARCHAR(180) NOT NULL,
    descricao           TEXT,
    data_inicio         TIMESTAMPTZ NOT NULL,
    data_fim            TIMESTAMPTZ,
    local_nome          VARCHAR(180),
    endereco_id         BIGINT REFERENCES cadastro.endereco(id),
    municipio_id        INTEGER REFERENCES global.municipio(id),
    bairro_id           INTEGER REFERENCES global.bairro(id),
    zona_eleitoral_id   INTEGER REFERENCES global.zona_eleitoral(id),
    territorio_id       BIGINT REFERENCES territorio.territorio(id),
    latitude            NUMERIC(10,7),
    longitude           NUMERIC(10,7),
    geom                geography(Point, 4326),
    responsavel_pessoa_id BIGINT REFERENCES cadastro.pessoa(id),
    origem_convite      VARCHAR(120),
    pessoa_indicou_id   BIGINT REFERENCES cadastro.pessoa(id),
    presenca_parlamentar BOOLEAN NOT NULL DEFAULT FALSE,
    presenca_representante BOOLEAN NOT NULL DEFAULT FALSE,
    numero_presentes    INTEGER CHECK (numero_presentes IS NULL OR numero_presentes >= 0),
    criado_por          BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em         TIMESTAMPTZ,
    CONSTRAINT uq_evento_uuid UNIQUE (uuid_publico),
    CONSTRAINT ck_evento_datas CHECK (data_fim IS NULL OR data_fim >= data_inicio)
);
COMMENT ON TABLE agenda.evento IS 'Compromisso, reuniao, agenda politica, evento comunitario, religioso, partidario, institucional ou cultural.';

CREATE INDEX ix_evento_tenant_data ON agenda.evento (tenant_id, data_inicio);
CREATE INDEX ix_evento_territorio ON agenda.evento (territorio_id);
CREATE INDEX ix_evento_geom ON agenda.evento USING gist (geom);

-- 9.4 evento_participante (N:N) --------------------------------------------------------
CREATE TABLE agenda.evento_participante (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    evento_id       BIGINT NOT NULL REFERENCES agenda.evento(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    papel           VARCHAR(40),
    presente        BOOLEAN,
    observacao      VARCHAR(255),
    CONSTRAINT uq_evento_participante UNIQUE (evento_id, pessoa_id)
);
COMMENT ON TABLE agenda.evento_participante IS 'Pessoas participantes do evento, incluindo presenca, papel e observacoes.';

-- 9.5 evento_lideranca (N:N) -----------------------------------------------------------
CREATE TABLE agenda.evento_lideranca (
    evento_id       BIGINT NOT NULL REFERENCES agenda.evento(id) ON DELETE CASCADE,
    lideranca_id    BIGINT NOT NULL REFERENCES cadastro.lideranca(id) ON DELETE CASCADE,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    papel           VARCHAR(40),
    CONSTRAINT pk_evento_lideranca PRIMARY KEY (evento_id, lideranca_id)
);
COMMENT ON TABLE agenda.evento_lideranca IS 'Lideres ou coordenadores envolvidos em determinado evento.';

-- 9.6 convite --------------------------------------------------------------------------
CREATE TABLE agenda.convite (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    evento_id       BIGINT REFERENCES agenda.evento(id) ON DELETE CASCADE,
    direcao         VARCHAR(20) NOT NULL DEFAULT 'recebido'
                    CHECK (direcao IN ('recebido','emitido')),
    origem          VARCHAR(120),
    pessoa_indicou_id BIGINT REFERENCES cadastro.pessoa(id),
    arquivo_id      BIGINT,                  -- FK adicionada apos arquivo.arquivo
    status          VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','aceito','recusado','confirmado')),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE agenda.convite IS 'Convite recebido ou emitido para evento, com origem, indicacao, arquivo anexado e status.';

-- 9.7 pauta_evento ---------------------------------------------------------------------
CREATE TABLE agenda.pauta_evento (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    evento_id       BIGINT NOT NULL REFERENCES agenda.evento(id) ON DELETE CASCADE,
    titulo          VARCHAR(180) NOT NULL,
    descricao       TEXT,
    encaminhamento  TEXT,
    ordem           SMALLINT,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE agenda.pauta_evento IS 'Pautas discutidas no evento, temas tratados e encaminhamentos.';

-- 9.8 presenca_evento ------------------------------------------------------------------
CREATE TABLE agenda.presenca_evento (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    evento_id       BIGINT NOT NULL REFERENCES agenda.evento(id) ON DELETE CASCADE,
    presenca_parlamentar BOOLEAN NOT NULL DEFAULT FALSE,
    presenca_representante BOOLEAN NOT NULL DEFAULT FALSE,
    nome_representante VARCHAR(180),
    numero_lideres_presentes INTEGER,
    numero_convidados   INTEGER,
    numero_estimado_presentes INTEGER,
    observacao      TEXT,
    registrado_por  BIGINT REFERENCES auth.usuario(id),
    registrado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_presenca_evento UNIQUE (evento_id)
);
COMMENT ON TABLE agenda.presenca_evento IS 'Registro detalhado de presenca do parlamentar, representante, lideres, convidados e numero estimado de presentes.';

-- =====================================================================================
-- 10. SCHEMA demanda - DEMANDAS, PEDIDOS E ATENDIMENTOS
-- =====================================================================================

-- 10.1 categoria_demanda ---------------------------------------------------------------
CREATE TABLE demanda.categoria_demanda (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL = catalogo padrao
    codigo      VARCHAR(40) NOT NULL,
    nome        VARCHAR(80) NOT NULL,
    CONSTRAINT uq_categoria_demanda_codigo UNIQUE (tenant_id, codigo)
);
COMMENT ON TABLE demanda.categoria_demanda IS 'Classifica demandas: saude, educacao, infraestrutura, emprego, seguranca, assistencia social, transporte ou habitacao.';

-- 10.2 status_demanda ------------------------------------------------------------------
CREATE TABLE demanda.status_demanda (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    ordem       SMALLINT,
    final       BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_status_demanda_codigo UNIQUE (codigo)
);
COMMENT ON TABLE demanda.status_demanda IS 'Situacao da demanda: pendente, em andamento, concluida, cancelada, nao atendida ou parcialmente atendida.';

-- 10.3 prioridade_demanda --------------------------------------------------------------
CREATE TABLE demanda.prioridade_demanda (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(20) NOT NULL,
    nome        VARCHAR(40) NOT NULL,
    peso        SMALLINT,
    CONSTRAINT uq_prioridade_demanda_codigo UNIQUE (codigo)
);
COMMENT ON TABLE demanda.prioridade_demanda IS 'Grau de prioridade operacional ou estrategica da demanda.';

-- 10.4 origem_demanda ------------------------------------------------------------------
CREATE TABLE demanda.origem_demanda (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    CONSTRAINT uq_origem_demanda_codigo UNIQUE (codigo)
);
COMMENT ON TABLE demanda.origem_demanda IS 'Origem da demanda: evento, ligacao, WhatsApp, cadastro manual, lider, comunidade ou importacao.';

-- 10.5 resultado_atendimento -----------------------------------------------------------
CREATE TABLE demanda.resultado_atendimento (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    CONSTRAINT uq_resultado_atendimento_codigo UNIQUE (codigo)
);
COMMENT ON TABLE demanda.resultado_atendimento IS 'Resultado do atendimento: solucionado, parcialmente atendido ou nao atendido.';

-- 10.6 demanda -------------------------------------------------------------------------
CREATE TABLE demanda.demanda (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    protocolo           VARCHAR(30),
    categoria_demanda_id SMALLINT REFERENCES demanda.categoria_demanda(id),
    prioridade_demanda_id SMALLINT REFERENCES demanda.prioridade_demanda(id),
    status_demanda_id   SMALLINT NOT NULL REFERENCES demanda.status_demanda(id),
    origem_demanda_id   SMALLINT REFERENCES demanda.origem_demanda(id),
    titulo              VARCHAR(180),
    descricao           TEXT NOT NULL,
    pessoa_solicitante_id BIGINT REFERENCES cadastro.pessoa(id),
    lideranca_indicacao_id BIGINT REFERENCES cadastro.lideranca(id),
    evento_id           BIGINT REFERENCES agenda.evento(id),
    territorio_id       BIGINT REFERENCES territorio.territorio(id),
    municipio_id        INTEGER REFERENCES global.municipio(id),
    bairro_id           INTEGER REFERENCES global.bairro(id),
    latitude            NUMERIC(10,7),
    longitude           NUMERIC(10,7),
    geom                geography(Point, 4326),
    data_solicitacao    DATE NOT NULL DEFAULT CURRENT_DATE,
    prazo               DATE,
    classificacao_automatica BOOLEAN NOT NULL DEFAULT FALSE,
    criado_por          BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em         TIMESTAMPTZ,
    CONSTRAINT uq_demanda_uuid UNIQUE (uuid_publico)
);
COMMENT ON TABLE demanda.demanda IS 'Solicitacao, pedido ou necessidade registrada por pessoa, lideranca, comunidade ou evento.';

CREATE INDEX ix_demanda_tenant_status ON demanda.demanda (tenant_id, status_demanda_id);
CREATE INDEX ix_demanda_categoria ON demanda.demanda (categoria_demanda_id);
CREATE INDEX ix_demanda_territorio ON demanda.demanda (territorio_id);
CREATE INDEX ix_demanda_geom ON demanda.demanda USING gist (geom);

-- 10.7 responsavel_atendimento ---------------------------------------------------------
CREATE TABLE demanda.responsavel_atendimento (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome        VARCHAR(150) NOT NULL,
    tipo        VARCHAR(20) NOT NULL DEFAULT 'usuario'
                CHECK (tipo IN ('usuario','pessoa','setor','area')),
    usuario_id  BIGINT REFERENCES auth.usuario(id),
    pessoa_id   BIGINT REFERENCES cadastro.pessoa(id),
    area        VARCHAR(120),
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE demanda.responsavel_atendimento IS 'Pessoa, usuario, setor ou area responsavel pelo atendimento de uma demanda.';

-- 10.8 atendimento ---------------------------------------------------------------------
CREATE TABLE demanda.atendimento (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    demanda_id          BIGINT NOT NULL REFERENCES demanda.demanda(id) ON DELETE CASCADE,
    responsavel_atendimento_id BIGINT REFERENCES demanda.responsavel_atendimento(id),
    resultado_atendimento_id SMALLINT REFERENCES demanda.resultado_atendimento(id),
    descricao           TEXT,
    prazo               DATE,
    data_execucao       DATE,
    tempo_atendimento_horas NUMERIC(10,2),
    criado_por          BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE demanda.atendimento IS 'Acao de atendimento vinculada a uma demanda, com responsavel, prazo, resultado e data de execucao.';

CREATE INDEX ix_atendimento_demanda ON demanda.atendimento (demanda_id);

-- 10.9 movimentacao_demanda ------------------------------------------------------------
CREATE TABLE demanda.movimentacao_demanda (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    demanda_id          BIGINT NOT NULL REFERENCES demanda.demanda(id) ON DELETE CASCADE,
    status_anterior_id  SMALLINT REFERENCES demanda.status_demanda(id),
    status_novo_id      SMALLINT REFERENCES demanda.status_demanda(id),
    responsavel_anterior_id BIGINT REFERENCES demanda.responsavel_atendimento(id),
    responsavel_novo_id BIGINT REFERENCES demanda.responsavel_atendimento(id),
    observacao          TEXT,
    usuario_id          BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE demanda.movimentacao_demanda IS 'Historico de mudancas de status, responsaveis, prazos, observacoes e encaminhamentos da demanda.';

CREATE INDEX ix_movimentacao_demanda ON demanda.movimentacao_demanda (demanda_id);

-- =====================================================================================
-- 11. SCHEMA meta - METAS DE VOTOS E ESTRUTURA DE ACOMPANHAMENTO
-- =====================================================================================

-- 11.1 tipo_meta_voto ------------------------------------------------------------------
CREATE TABLE meta.tipo_meta_voto (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    CONSTRAINT uq_tipo_meta_voto_codigo UNIQUE (codigo)
);
COMMENT ON TABLE meta.tipo_meta_voto IS 'Classifica a meta: global, territorial, por lider, por equipe, por comunidade ou por nucleo familiar.';

-- 11.2 periodo_meta --------------------------------------------------------------------
CREATE TABLE meta.periodo_meta (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome        VARCHAR(120) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim    DATE NOT NULL,
    ciclo       VARCHAR(30),
    eleicao_id  BIGINT,                      -- FK adicionada apos eleicao.eleicao
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_periodo_meta_datas CHECK (data_fim >= data_inicio)
);
COMMENT ON TABLE meta.periodo_meta IS 'Periodo de validade da meta, com inicio, fim, ciclo e eleicao relacionada.';

-- 11.3 meta_voto -----------------------------------------------------------------------
CREATE TABLE meta.meta_voto (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    tipo_meta_voto_id   SMALLINT NOT NULL REFERENCES meta.tipo_meta_voto(id),
    periodo_meta_id     BIGINT REFERENCES meta.periodo_meta(id),
    titulo              VARCHAR(150),
    quantidade_meta     INTEGER NOT NULL CHECK (quantidade_meta >= 0),
    lideranca_id        BIGINT REFERENCES cadastro.lideranca(id),
    coordenador_id      BIGINT REFERENCES cadastro.lideranca(id),
    territorio_id       BIGINT REFERENCES territorio.territorio(id),
    municipio_id        INTEGER REFERENCES global.municipio(id),
    bairro_id           INTEGER REFERENCES global.bairro(id),
    zona_eleitoral_id   INTEGER REFERENCES global.zona_eleitoral(id),
    secao_eleitoral_id  BIGINT REFERENCES global.secao_eleitoral(id),
    comunidade_id       BIGINT REFERENCES cadastro.comunidade(id),
    nucleo_familiar_id  BIGINT REFERENCES cadastro.nucleo_familiar(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'ativa'
                        CHECK (status IN ('ativa','concluida','cancelada','em_risco','suspensa')),
    criado_por          BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE meta.meta_voto IS 'Meta de votos para lider, equipe, territorio, comunidade, nucleo familiar ou campanha inteira.';

CREATE INDEX ix_meta_voto_lideranca ON meta.meta_voto (tenant_id, lideranca_id);
CREATE INDEX ix_meta_voto_territorio ON meta.meta_voto (territorio_id);

-- 11.4 meta_voto_alvo ------------------------------------------------------------------
CREATE TABLE meta.meta_voto_alvo (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    meta_voto_id    BIGINT NOT NULL REFERENCES meta.meta_voto(id) ON DELETE CASCADE,
    tipo_alvo       VARCHAR(30) NOT NULL
                    CHECK (tipo_alvo IN ('lideranca','territorio','equipe','comunidade','nucleo_familiar','pessoa')),
    alvo_id         BIGINT NOT NULL,
    quantidade_atribuida INTEGER CHECK (quantidade_atribuida IS NULL OR quantidade_atribuida >= 0),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE meta.meta_voto_alvo IS 'Aponta o alvo da meta de forma flexivel: lideranca, territorio, equipe, comunidade, nucleo familiar ou pessoa.';

CREATE INDEX ix_meta_voto_alvo ON meta.meta_voto_alvo (tenant_id, tipo_alvo, alvo_id);

-- 11.5 acompanhamento_meta -------------------------------------------------------------
CREATE TABLE meta.acompanhamento_meta (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    meta_voto_id        BIGINT NOT NULL REFERENCES meta.meta_voto(id) ON DELETE CASCADE,
    data_referencia     DATE NOT NULL DEFAULT CURRENT_DATE,
    quantidade_projetada INTEGER CHECK (quantidade_projetada IS NULL OR quantidade_projetada >= 0),
    quantidade_confirmada INTEGER CHECK (quantidade_confirmada IS NULL OR quantidade_confirmada >= 0),
    quantidade_eleitores_vinculados INTEGER,
    percentual_atingido NUMERIC(5,2) CHECK (percentual_atingido IS NULL OR percentual_atingido >= 0),
    situacao_risco      VARCHAR(20) NOT NULL DEFAULT 'normal'
                        CHECK (situacao_risco IN ('normal','atencao','risco','critico')),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_acompanhamento_meta UNIQUE (meta_voto_id, data_referencia)
);
COMMENT ON TABLE meta.acompanhamento_meta IS 'Historico de evolucao da meta: projecao, confirmacao, percentual atingido e situacao de risco.';

-- 11.6 alerta_meta ---------------------------------------------------------------------
CREATE TABLE meta.alerta_meta (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    meta_voto_id    BIGINT NOT NULL REFERENCES meta.meta_voto(id) ON DELETE CASCADE,
    tipo_alerta     VARCHAR(30) NOT NULL DEFAULT 'meta_abaixo_esperado'
                    CHECK (tipo_alerta IN ('meta_abaixo_esperado','meta_estagnada','prazo_proximo','outro')),
    percentual_referencia NUMERIC(5,2),
    mensagem        VARCHAR(255),
    severidade      VARCHAR(20) NOT NULL DEFAULT 'media'
                    CHECK (severidade IN ('baixa','media','alta','critica')),
    resolvido       BOOLEAN NOT NULL DEFAULT FALSE,
    gerado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolvido_em    TIMESTAMPTZ
);
COMMENT ON TABLE meta.alerta_meta IS 'Alertas para metas abaixo do esperado, por exemplo abaixo de 70% do previsto.';

CREATE INDEX ix_alerta_meta_aberto ON meta.alerta_meta (tenant_id, resolvido);

-- 11.7 ranking_lideranca ---------------------------------------------------------------
CREATE TABLE meta.ranking_lideranca (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    lideranca_id        BIGINT NOT NULL REFERENCES cadastro.lideranca(id) ON DELETE CASCADE,
    data_referencia     DATE NOT NULL DEFAULT CURRENT_DATE,
    posicao             INTEGER,
    total_cadastros     INTEGER NOT NULL DEFAULT 0,
    total_confirmacoes  INTEGER NOT NULL DEFAULT 0,
    total_eventos       INTEGER NOT NULL DEFAULT 0,
    total_demandas      INTEGER NOT NULL DEFAULT 0,
    percentual_meta     NUMERIC(5,2),
    pontuacao           NUMERIC(12,2),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_ranking_lideranca UNIQUE (lideranca_id, data_referencia)
);
COMMENT ON TABLE meta.ranking_lideranca IS 'Ranking calculado de lideres por desempenho: cadastros, confirmacoes, eventos, demandas e atingimento de metas.';

-- =====================================================================================
-- 12. SCHEMA comunicacao - COMUNICACAO, REDES SOCIAIS E RELACIONAMENTO
-- =====================================================================================

-- 12.1 canal_comunicacao ---------------------------------------------------------------
CREATE TABLE comunicacao.canal_comunicacao (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    CONSTRAINT uq_canal_comunicacao_codigo UNIQUE (codigo)
);
COMMENT ON TABLE comunicacao.canal_comunicacao IS 'Canal usado na comunicacao: WhatsApp, telefone, e-mail, Instagram, SMS ou presencial.';

-- 12.2 tipo_interacao ------------------------------------------------------------------
CREATE TABLE comunicacao.tipo_interacao (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    CONSTRAINT uq_tipo_interacao_codigo UNIQUE (codigo)
);
COMMENT ON TABLE comunicacao.tipo_interacao IS 'Classifica interacoes por canal e finalidade.';

-- 12.3 interacao -----------------------------------------------------------------------
CREATE TABLE comunicacao.interacao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id           BIGINT REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    tipo_interacao_id   SMALLINT REFERENCES comunicacao.tipo_interacao(id),
    canal_comunicacao_id SMALLINT REFERENCES comunicacao.canal_comunicacao(id),
    lideranca_id        BIGINT REFERENCES cadastro.lideranca(id),
    demanda_id          BIGINT REFERENCES demanda.demanda(id),
    evento_id           BIGINT REFERENCES agenda.evento(id),
    direcao             VARCHAR(10) NOT NULL DEFAULT 'saida'
                        CHECK (direcao IN ('entrada','saida')),
    assunto             VARCHAR(180),
    conteudo            TEXT,
    resultado           VARCHAR(120),
    data_interacao      TIMESTAMPTZ NOT NULL DEFAULT now(),
    registrado_por      BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE comunicacao.interacao IS 'Contato com pessoa: ligacao, WhatsApp, visita, reuniao, mensagem, e-mail ou atendimento presencial.';

CREATE INDEX ix_interacao_pessoa ON comunicacao.interacao (pessoa_id);
CREATE INDEX ix_interacao_tenant_data ON comunicacao.interacao (tenant_id, data_interacao);

-- 12.4 campanha_comunicacao ------------------------------------------------------------
CREATE TABLE comunicacao.campanha_comunicacao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome                VARCHAR(150) NOT NULL,
    descricao           TEXT,
    canal_comunicacao_id SMALLINT REFERENCES comunicacao.canal_comunicacao(id),
    publico_alvo        JSONB NOT NULL DEFAULT '{}'::jsonb,  -- filtros: aniversariantes, lideres, comunidades, territorios
    data_agendada       TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'rascunho'
                        CHECK (status IN ('rascunho','agendada','enviando','concluida','cancelada')),
    criado_por          BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE comunicacao.campanha_comunicacao IS 'Acao de comunicacao segmentada para publicos: aniversariantes, lideres, comunidades ou territorios.';

-- 12.5 mensagem_comunicacao ------------------------------------------------------------
CREATE TABLE comunicacao.mensagem_comunicacao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_comunicacao_id BIGINT REFERENCES comunicacao.campanha_comunicacao(id) ON DELETE CASCADE,
    pessoa_id           BIGINT REFERENCES cadastro.pessoa(id),
    canal_comunicacao_id SMALLINT REFERENCES comunicacao.canal_comunicacao(id),
    destinatario        VARCHAR(180),
    conteudo            TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'pendente'
                        CHECK (status IN ('pendente','enviada','entregue','lida','falha')),
    enviado_em          TIMESTAMPTZ,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE comunicacao.mensagem_comunicacao IS 'Mensagem individual ou em lote enviada ou registrada manualmente.';

CREATE INDEX ix_mensagem_campanha ON comunicacao.mensagem_comunicacao (campanha_comunicacao_id);

-- 12.6 consentimento_comunicacao -------------------------------------------------------
CREATE TABLE comunicacao.consentimento_comunicacao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    pessoa_id           BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    canal_comunicacao_id SMALLINT REFERENCES comunicacao.canal_comunicacao(id),
    base_legal          VARCHAR(60),
    consentido          BOOLEAN NOT NULL DEFAULT TRUE,
    finalidade          VARCHAR(180),
    data_consentimento  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data_opt_out        TIMESTAMPTZ,
    origem              VARCHAR(60),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE comunicacao.consentimento_comunicacao IS 'Consentimento, base legal, preferencia de contato e eventual opt-out (LGPD).';

CREATE INDEX ix_consentimento_pessoa ON comunicacao.consentimento_comunicacao (pessoa_id);

-- 12.7 perfil_social_monitorado --------------------------------------------------------
CREATE TABLE comunicacao.perfil_social_monitorado (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    rede                VARCHAR(30) NOT NULL
                        CHECK (rede IN ('instagram','facebook','tiktok','x','youtube','whatsapp','outro')),
    identificador       VARCHAR(150) NOT NULL,
    url                 TEXT,
    pessoa_id           BIGINT REFERENCES cadastro.pessoa(id),
    lideranca_id        BIGINT REFERENCES cadastro.lideranca(id),
    monitorar           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE comunicacao.perfil_social_monitorado IS 'Perfil de rede social monitorado ou cadastrado, vinculado a pessoa, lideranca, campanha ou organizacao.';

-- 12.8 publicacao_social ---------------------------------------------------------------
CREATE TABLE comunicacao.publicacao_social (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    perfil_social_monitorado_id BIGINT NOT NULL REFERENCES comunicacao.perfil_social_monitorado(id) ON DELETE CASCADE,
    id_externo          VARCHAR(120),
    url                 TEXT,
    conteudo            TEXT,
    tipo_midia          VARCHAR(20),
    publicado_em        TIMESTAMPTZ,
    capturado_em        TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE comunicacao.publicacao_social IS 'Publicacao em rede social capturada ou registrada manualmente para analise de engajamento.';

CREATE INDEX ix_publicacao_perfil ON comunicacao.publicacao_social (perfil_social_monitorado_id);

-- 12.9 engajamento_social --------------------------------------------------------------
CREATE TABLE comunicacao.engajamento_social (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    publicacao_social_id BIGINT REFERENCES comunicacao.publicacao_social(id) ON DELETE CASCADE,
    perfil_social_monitorado_id BIGINT REFERENCES comunicacao.perfil_social_monitorado(id) ON DELETE CASCADE,
    data_referencia     DATE NOT NULL DEFAULT CURRENT_DATE,
    curtidas            INTEGER NOT NULL DEFAULT 0,
    comentarios         INTEGER NOT NULL DEFAULT 0,
    compartilhamentos   INTEGER NOT NULL DEFAULT 0,
    alcance             INTEGER,
    interacoes          INTEGER,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE comunicacao.engajamento_social IS 'Metricas de curtidas, comentarios, compartilhamentos, alcance e interacoes por publicacao ou perfil.';

-- =====================================================================================
-- 13. SCHEMA eleicao - ELEICOES, CAMPANHAS E OPERACAO DO DIA DA VOTACAO
-- =====================================================================================

-- 13.1 eleicao -------------------------------------------------------------------------
CREATE TABLE eleicao.eleicao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL = eleicao de referencia compartilhada
    ano             SMALLINT NOT NULL,
    tipo            VARCHAR(30) NOT NULL
                    CHECK (tipo IN ('municipal','estadual','federal','suplementar','outra')),
    turno           SMALLINT NOT NULL DEFAULT 1 CHECK (turno IN (1,2)),
    data_eleicao    DATE NOT NULL,
    escopo_uf_id    SMALLINT REFERENCES global.estado(id),
    escopo_municipio_id INTEGER REFERENCES global.municipio(id),
    descricao       VARCHAR(180),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE eleicao.eleicao IS 'Cadastro da eleicao de referencia: ano, tipo, turno, data e escopo territorial.';

-- Resolver FK pendente meta.periodo_meta -> eleicao.eleicao
ALTER TABLE meta.periodo_meta
    ADD CONSTRAINT fk_periodo_meta_eleicao FOREIGN KEY (eleicao_id)
    REFERENCES eleicao.eleicao(id) ON DELETE SET NULL;

-- 13.2 campanha_eleicao ----------------------------------------------------------------
CREATE TABLE eleicao.campanha_eleicao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico        UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    eleicao_id          BIGINT NOT NULL REFERENCES eleicao.eleicao(id),
    nome                VARCHAR(180) NOT NULL,
    cargo_pleiteado     VARCHAR(120) NOT NULL,
    ativa               BOOLEAN NOT NULL DEFAULT FALSE,
    data_ativacao       TIMESTAMPTZ,
    data_encerramento   TIMESTAMPTZ,
    criado_por          BIGINT REFERENCES auth.usuario(id),
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_campanha_eleicao_uuid UNIQUE (uuid_publico),
    CONSTRAINT uq_campanha_eleicao_tenant UNIQUE (tenant_id, eleicao_id)
);
COMMENT ON TABLE eleicao.campanha_eleicao IS 'Campanha eleitoral de um politico ou candidato, vinculada ao tenant assinante e a uma eleicao.';

-- 13.3 campanha_configuracao ------------------------------------------------------------
CREATE TABLE eleicao.campanha_configuracao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id BIGINT NOT NULL REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    parametros          JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_campanha_configuracao_campanha UNIQUE (campanha_eleicao_id)
);
COMMENT ON TABLE eleicao.campanha_configuracao IS 'Configuracoes e parametros especificos de uma campanha eleitoral.';

-- 13.4 status_eleitor_eleicao ----------------------------------------------------------
CREATE TABLE eleicao.status_eleitor_eleicao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id BIGINT NOT NULL REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    lideranca_id    BIGINT REFERENCES cadastro.lideranca(id),
    status          VARCHAR(30) NOT NULL DEFAULT 'nao_contatado'
                    CHECK (status IN ('nao_contatado','contatado','confirmado','pendente','precisa_apoio','sem_resposta')),
    zona_eleitoral_id INTEGER REFERENCES global.zona_eleitoral(id),
    secao_eleitoral_id BIGINT REFERENCES global.secao_eleitoral(id),
    local_votacao_id INTEGER REFERENCES global.local_votacao(id),
    atualizado_por  BIGINT REFERENCES auth.usuario(id),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_status_eleitor_eleicao UNIQUE (campanha_eleicao_id, pessoa_id)
);
COMMENT ON TABLE eleicao.status_eleitor_eleicao IS 'Status operacional do eleitor no dia da eleicao: nao contatado, contatado, confirmado, pendente, precisa de apoio ou sem resposta.';

CREATE INDEX ix_status_eleitor_lideranca ON eleicao.status_eleitor_eleicao (tenant_id, lideranca_id, status);

-- 13.5 confirmacao_operacional_voto ----------------------------------------------------
CREATE TABLE eleicao.confirmacao_operacional_voto (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id BIGINT NOT NULL REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    pessoa_id       BIGINT NOT NULL REFERENCES cadastro.pessoa(id) ON DELETE CASCADE,
    informado_por_tipo VARCHAR(20) NOT NULL
                    CHECK (informado_por_tipo IN ('lider','eleitor','equipe')),
    informado_por_usuario_id BIGINT REFERENCES auth.usuario(id),
    confirmado      BOOLEAN NOT NULL DEFAULT FALSE,
    observacao      VARCHAR(255),
    data_confirmacao TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_confirmacao_operacional UNIQUE (campanha_eleicao_id, pessoa_id)
);
COMMENT ON TABLE eleicao.confirmacao_operacional_voto IS 'Registro operacional informado por lider, eleitor ou equipe. NAO representa comprovacao oficial de voto individual (restricao etica/legal).';

-- 13.6 ocorrencia_eleicao --------------------------------------------------------------
CREATE TABLE eleicao.ocorrencia_eleicao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id BIGINT NOT NULL REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    pessoa_id       BIGINT REFERENCES cadastro.pessoa(id),
    lideranca_id    BIGINT REFERENCES cadastro.lideranca(id),
    local_votacao_id INTEGER REFERENCES global.local_votacao(id),
    tipo            VARCHAR(40) NOT NULL
                    CHECK (tipo IN ('transporte','dificuldade_contato','problema_local','solicitacao_apoio','outro')),
    descricao       TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'aberta'
                    CHECK (status IN ('aberta','em_andamento','resolvida','cancelada')),
    registrado_por  BIGINT REFERENCES auth.usuario(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE eleicao.ocorrencia_eleicao IS 'Ocorrencias do dia da eleicao: transporte, dificuldade de contato, problema em local de votacao ou solicitacao de apoio.';

-- 13.7 painel_eleicao_snapshot ---------------------------------------------------------
CREATE TABLE eleicao.painel_eleicao_snapshot (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    campanha_eleicao_id BIGINT NOT NULL REFERENCES eleicao.campanha_eleicao(id) ON DELETE CASCADE,
    capturado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_eleitores INTEGER,
    total_confirmados INTEGER,
    total_pendentes INTEGER,
    total_sem_resposta INTEGER,
    percentual_confirmacao NUMERIC(5,2),
    indicadores     JSONB NOT NULL DEFAULT '{}'::jsonb
);
COMMENT ON TABLE eleicao.painel_eleicao_snapshot IS 'Fotografia periodica dos indicadores do modo eleicao para dashboards em tempo real ou historico.';

CREATE INDEX ix_painel_snapshot_campanha ON eleicao.painel_eleicao_snapshot (campanha_eleicao_id, capturado_em);

-- =====================================================================================
-- 14. SCHEMA arquivo - ARQUIVOS, ANEXOS E DOCUMENTOS
-- =====================================================================================

-- 14.1 tipo_anexo ----------------------------------------------------------------------
CREATE TABLE arquivo.tipo_anexo (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(30) NOT NULL,
    nome        VARCHAR(60) NOT NULL,
    CONSTRAINT uq_tipo_anexo_codigo UNIQUE (codigo)
);
COMMENT ON TABLE arquivo.tipo_anexo IS 'Classifica anexos: foto, convite, pauta, documento pessoal, comprovante, imagem, PDF ou planilha.';

-- 14.2 arquivo -------------------------------------------------------------------------
CREATE TABLE arquivo.arquivo (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uuid_publico    UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome_original   VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255),
    mime_type       VARCHAR(120),
    extensao        VARCHAR(20),
    tamanho_bytes   BIGINT CHECK (tamanho_bytes IS NULL OR tamanho_bytes >= 0),
    hash_sha256     CHAR(64),
    provedor_storage VARCHAR(40) NOT NULL DEFAULT 's3'
                    CHECK (provedor_storage IN ('s3','azure_blob','seaweedfs','gcs','local','outro')),
    bucket          VARCHAR(120),
    caminho         TEXT NOT NULL,
    url_publica     TEXT,
    criado_por      BIGINT REFERENCES auth.usuario(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    excluido_em     TIMESTAMPTZ,
    CONSTRAINT uq_arquivo_uuid UNIQUE (uuid_publico)
);
COMMENT ON TABLE arquivo.arquivo IS 'Registro logico de arquivo armazenado em data lake/storage com nome, tipo, tamanho, hash e localizacao.';

CREATE INDEX ix_arquivo_tenant ON arquivo.arquivo (tenant_id);

-- Resolver FKs pendentes que referenciam arquivo.arquivo
ALTER TABLE cadastro.pessoa
    ADD CONSTRAINT fk_pessoa_foto FOREIGN KEY (foto_arquivo_id)
    REFERENCES arquivo.arquivo(id) ON DELETE SET NULL;

ALTER TABLE agenda.convite
    ADD CONSTRAINT fk_convite_arquivo FOREIGN KEY (arquivo_id)
    REFERENCES arquivo.arquivo(id) ON DELETE SET NULL;

-- 14.3 anexo (polimorfico) -------------------------------------------------------------
CREATE TABLE arquivo.anexo (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    arquivo_id      BIGINT NOT NULL REFERENCES arquivo.arquivo(id) ON DELETE CASCADE,
    tipo_anexo_id   SMALLINT REFERENCES arquivo.tipo_anexo(id),
    entidade_tipo   VARCHAR(30) NOT NULL
                    CHECK (entidade_tipo IN ('pessoa','evento','demanda','interacao','importacao','comunidade','lideranca','convite')),
    entidade_id     BIGINT NOT NULL,
    descricao       VARCHAR(255),
    criado_por      BIGINT REFERENCES auth.usuario(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE arquivo.anexo IS 'Associacao de arquivo a entidades do sistema: pessoa, evento, demanda, comunicacao ou importacao.';

CREATE INDEX ix_anexo_entidade ON arquivo.anexo (tenant_id, entidade_tipo, entidade_id);

-- 14.4 documento_extraido --------------------------------------------------------------
CREATE TABLE arquivo.documento_extraido (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    arquivo_id      BIGINT NOT NULL REFERENCES arquivo.arquivo(id) ON DELETE CASCADE,
    texto_extraido  TEXT,
    metadados       JSONB NOT NULL DEFAULT '{}'::jsonb,
    metodo_extracao VARCHAR(40),
    idioma          VARCHAR(10),
    processado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE arquivo.documento_extraido IS 'Texto ou metadados extraidos de PDFs, imagens, convites, pautas ou documentos enviados.';

-- =====================================================================================
-- 15. SCHEMA etl - IMPORTACAO, FONTES EXTERNAS, STAGING E QUALIDADE DE DADOS
-- =====================================================================================

-- 15.1 fonte_dado ----------------------------------------------------------------------
CREATE TABLE etl.fonte_dado (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(40) NOT NULL,
    nome        VARCHAR(120) NOT NULL,
    tipo        VARCHAR(30) NOT NULL
                CHECK (tipo IN ('gesped','tse','ibge','planilha','formulario','api','manual','outro')),
    descricao   VARCHAR(255),
    CONSTRAINT uq_fonte_dado_codigo UNIQUE (codigo)
);
COMMENT ON TABLE etl.fonte_dado IS 'Origem de dados importados: GESPED, TSE, IBGE, planilhas, formularios, APIs ou cadastro manual.';

-- Resolver FK pendente cadastro.pessoa -> etl.fonte_dado
ALTER TABLE cadastro.pessoa
    ADD CONSTRAINT fk_pessoa_fonte_dado FOREIGN KEY (fonte_dado_id)
    REFERENCES etl.fonte_dado(id) ON DELETE SET NULL;

-- 15.2 importacao ----------------------------------------------------------------------
CREATE TABLE etl.importacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL para cargas globais (TSE/IBGE)
    fonte_dado_id   BIGINT REFERENCES etl.fonte_dado(id),
    descricao       VARCHAR(180),
    tipo_destino    VARCHAR(40),
    status          VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','processando','concluida','falha','parcial','cancelada')),
    total_linhas    INTEGER,
    linhas_validas  INTEGER,
    linhas_erro     INTEGER,
    iniciado_em     TIMESTAMPTZ,
    concluido_em    TIMESTAMPTZ,
    criado_por      BIGINT REFERENCES auth.usuario(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.importacao IS 'Processo de importacao de arquivo, API ou base externa, com status, usuario, origem e periodo.';

-- 15.3 importacao_arquivo --------------------------------------------------------------
CREATE TABLE etl.importacao_arquivo (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    importacao_id   BIGINT NOT NULL REFERENCES etl.importacao(id) ON DELETE CASCADE,
    arquivo_id      BIGINT REFERENCES arquivo.arquivo(id),
    nome_arquivo    VARCHAR(255),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.importacao_arquivo IS 'Arquivos vinculados a uma importacao especifica.';

-- 15.4 importacao_linha ----------------------------------------------------------------
CREATE TABLE etl.importacao_linha (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    importacao_id   BIGINT NOT NULL REFERENCES etl.importacao(id) ON DELETE CASCADE,
    numero_linha    INTEGER,
    conteudo_bruto  JSONB,
    status          VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (status IN ('pendente','processada','erro','aviso','ignorada')),
    mensagem        TEXT,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.importacao_linha IS 'Registro granular de linhas importadas, erros, avisos e status de processamento.';

CREATE INDEX ix_importacao_linha_importacao ON etl.importacao_linha (importacao_id, status);

-- 15.5 erro_importacao -----------------------------------------------------------------
CREATE TABLE etl.erro_importacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    importacao_id   BIGINT NOT NULL REFERENCES etl.importacao(id) ON DELETE CASCADE,
    importacao_linha_id BIGINT REFERENCES etl.importacao_linha(id) ON DELETE CASCADE,
    etapa           VARCHAR(30)
                    CHECK (etapa IN ('leitura','validacao','padronizacao','carga','deduplicacao')),
    campo           VARCHAR(80),
    mensagem        TEXT NOT NULL,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.erro_importacao IS 'Erros encontrados durante leitura, validacao, padronizacao ou carga dos dados.';

-- 15.6 staging_pessoa ------------------------------------------------------------------
CREATE TABLE etl.staging_pessoa (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    importacao_id   BIGINT REFERENCES etl.importacao(id) ON DELETE CASCADE,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome_completo   VARCHAR(180),
    cpf             VARCHAR(20),
    rg              VARCHAR(40),
    titulo_eleitor  VARCHAR(20),
    data_nascimento DATE,
    telefone        VARCHAR(20),
    email           VARCHAR(180),
    endereco        TEXT,
    municipio       VARCHAR(120),
    uf              CHAR(2),
    dados_extras    JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(20) NOT NULL DEFAULT 'novo'
                    CHECK (status IN ('novo','validado','duplicado','carregado','descartado')),
    pessoa_id       BIGINT REFERENCES cadastro.pessoa(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.staging_pessoa IS 'Area temporaria para dados de pessoas antes da validacao, deduplicacao e carga definitiva.';

CREATE INDEX ix_staging_pessoa_importacao ON etl.staging_pessoa (importacao_id, status);

-- 15.7 staging_eleitorado_tse ----------------------------------------------------------
CREATE TABLE etl.staging_eleitorado_tse (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    importacao_id   BIGINT REFERENCES etl.importacao(id) ON DELETE CASCADE,
    ano             SMALLINT,
    uf              CHAR(2),
    codigo_municipio_tse INTEGER,
    nome_municipio  VARCHAR(120),
    numero_zona     SMALLINT,
    numero_secao    SMALLINT,
    genero          VARCHAR(30),
    faixa_etaria    VARCHAR(40),
    grau_instrucao  VARCHAR(60),
    estado_civil    VARCHAR(40),
    quantidade_eleitores INTEGER,
    dados_extras    JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(20) NOT NULL DEFAULT 'novo'
                    CHECK (status IN ('novo','validado','carregado','descartado')),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.staging_eleitorado_tse IS 'Area temporaria para bases TSE antes de normalizar em tabelas globais ou analiticas.';

-- 15.8 job_processamento ---------------------------------------------------------------
CREATE TABLE etl.job_processamento (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    tipo            VARCHAR(40) NOT NULL
                    CHECK (tipo IN ('geocodificacao','deduplicacao','nlp','importacao','relatorio','indicador','outro')),
    referencia      VARCHAR(120),
    status          VARCHAR(20) NOT NULL DEFAULT 'enfileirado'
                    CHECK (status IN ('enfileirado','executando','concluido','falha','cancelado')),
    parametros      JSONB NOT NULL DEFAULT '{}'::jsonb,
    tentativas      SMALLINT NOT NULL DEFAULT 0,
    iniciado_em     TIMESTAMPTZ,
    concluido_em    TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.job_processamento IS 'Jobs assincronos: geocodificacao, deduplicacao, NLP, importacao, relatorio ou calculo de indicadores (Celery/Redis).';

CREATE INDEX ix_job_processamento_status ON etl.job_processamento (status);

-- 15.9 log_processamento ---------------------------------------------------------------
CREATE TABLE etl.log_processamento (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_processamento_id BIGINT REFERENCES etl.job_processamento(id) ON DELETE CASCADE,
    nivel           VARCHAR(10) NOT NULL DEFAULT 'info'
                    CHECK (nivel IN ('debug','info','warn','error','critical')),
    mensagem        TEXT NOT NULL,
    contexto        JSONB,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.log_processamento IS 'Logs tecnicos e operacionais dos jobs de processamento.';

CREATE INDEX ix_log_processamento_job ON etl.log_processamento (job_processamento_id);

-- 15.10 regra_deduplicacao -------------------------------------------------------------
CREATE TABLE etl.regra_deduplicacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL = regra global
    nome            VARCHAR(120) NOT NULL,
    criterio        VARCHAR(40) NOT NULL
                    CHECK (criterio IN ('cpf','telefone','email','titulo_eleitor','nome_data_nascimento','fuzzy')),
    limiar_score    NUMERIC(5,2),
    ativa           BOOLEAN NOT NULL DEFAULT TRUE,
    configuracao    JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.regra_deduplicacao IS 'Criterios configuraveis para identificar duplicidades por CPF, telefone, e-mail, titulo, nome/data de nascimento ou score fuzzy.';

-- 15.11 resultado_deduplicacao ---------------------------------------------------------
CREATE TABLE etl.resultado_deduplicacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    regra_deduplicacao_id BIGINT REFERENCES etl.regra_deduplicacao(id),
    importacao_id   BIGINT REFERENCES etl.importacao(id),
    registro_origem_id BIGINT,
    registro_duplicado_id BIGINT,
    score           NUMERIC(5,2),
    decisao         VARCHAR(20) NOT NULL DEFAULT 'pendente'
                    CHECK (decisao IN ('pendente','duplicado','distinto','mesclar')),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE etl.resultado_deduplicacao IS 'Resultado da aplicacao das regras de deduplicacao sobre registros importados ou cadastrados.';

-- =====================================================================================
-- 16. SCHEMA dw - DATA WAREHOUSE / ANALYTICS
-- =====================================================================================

-- 16.1 perfil_eleitorado_tse (agregado por UF/municipio/zona) --------------------------
CREATE TABLE dw.perfil_eleitorado_tse (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ano             SMALLINT NOT NULL,
    estado_id       SMALLINT REFERENCES global.estado(id),
    municipio_id    INTEGER REFERENCES global.municipio(id),
    zona_eleitoral_id INTEGER REFERENCES global.zona_eleitoral(id),
    genero          VARCHAR(30),
    faixa_etaria    VARCHAR(40),
    grau_instrucao  VARCHAR(60),
    estado_civil    VARCHAR(40),
    raca_cor        VARCHAR(40),
    quantidade_eleitores INTEGER NOT NULL DEFAULT 0,
    carregado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.perfil_eleitorado_tse IS 'Base agregada do TSE com perfil do eleitorado por UF, municipio, zona, genero, faixa etaria, escolaridade, raca/cor e outras dimensoes.';

CREATE INDEX ix_perfil_eleitorado_tse_dim ON dw.perfil_eleitorado_tse (ano, estado_id, municipio_id, zona_eleitoral_id);

-- 16.2 perfil_eleitorado_secao_tse -----------------------------------------------------
CREATE TABLE dw.perfil_eleitorado_secao_tse (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ano             SMALLINT NOT NULL,
    estado_id       SMALLINT REFERENCES global.estado(id),
    municipio_id    INTEGER REFERENCES global.municipio(id),
    zona_eleitoral_id INTEGER REFERENCES global.zona_eleitoral(id),
    secao_eleitoral_id BIGINT REFERENCES global.secao_eleitoral(id),
    local_votacao_id INTEGER REFERENCES global.local_votacao(id),
    genero          VARCHAR(30),
    faixa_etaria    VARCHAR(40),
    grau_instrucao  VARCHAR(60),
    quantidade_eleitores INTEGER NOT NULL DEFAULT 0,
    carregado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.perfil_eleitorado_secao_tse IS 'Base agregada do TSE por secao eleitoral e local de votacao, para analises territoriais e metas.';

CREATE INDEX ix_perfil_eleitorado_secao_dim ON dw.perfil_eleitorado_secao_tse (ano, secao_eleitoral_id);

-- 16.3 indicador -----------------------------------------------------------------------
CREATE TABLE dw.indicador (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      VARCHAR(60) NOT NULL,
    nome        VARCHAR(150) NOT NULL,
    descricao   VARCHAR(255),
    unidade     VARCHAR(30),
    CONSTRAINT uq_indicador_codigo UNIQUE (codigo)
);
COMMENT ON TABLE dw.indicador IS 'Catalogo de indicadores: total de cadastrados, lideres ativos, demandas pendentes, eventos realizados ou metas em risco.';

-- 16.4 indicador_valor -----------------------------------------------------------------
CREATE TABLE dw.indicador_valor (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    indicador_id    SMALLINT NOT NULL REFERENCES dw.indicador(id),
    data_referencia DATE NOT NULL,
    territorio_id   BIGINT REFERENCES territorio.territorio(id),
    lideranca_id    BIGINT REFERENCES cadastro.lideranca(id),
    recorte         JSONB NOT NULL DEFAULT '{}'::jsonb,
    valor           NUMERIC(18,4) NOT NULL,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.indicador_valor IS 'Valor historico de um indicador por data, tenant, territorio, lider ou outro recorte.';

CREATE INDEX ix_indicador_valor_dim ON dw.indicador_valor (tenant_id, indicador_id, data_referencia);

-- 16.5 dashboard_configuracao ----------------------------------------------------------
CREATE TABLE dw.dashboard_configuracao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    nome            VARCHAR(120) NOT NULL,
    perfil_acesso_id BIGINT REFERENCES auth.perfil_acesso(id),
    filtros_padrao  JSONB NOT NULL DEFAULT '{}'::jsonb,
    widgets         JSONB NOT NULL DEFAULT '[]'::jsonb,
    criado_por      BIGINT REFERENCES auth.usuario(id),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.dashboard_configuracao IS 'Configuracao de paineis, filtros padrao, visoes por perfil e widgets habilitados.';

-- 16.6 relatorio -----------------------------------------------------------------------
CREATE TABLE dw.relatorio (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,  -- NULL = relatorio de catalogo
    codigo          VARCHAR(60) NOT NULL,
    nome            VARCHAR(150) NOT NULL,
    descricao       VARCHAR(255),
    tipo            VARCHAR(30)
                    CHECK (tipo IN ('aniversariantes','metas','demandas','agenda','ranking','cadastros','atendimentos','personalizado')),
    formato_saida   VARCHAR(20)
                    CHECK (formato_saida IN ('pdf','excel','dashboard','notificacao')),
    parametros_definicao JSONB NOT NULL DEFAULT '{}'::jsonb,
    automatico      BOOLEAN NOT NULL DEFAULT FALSE,
    agendamento_cron VARCHAR(60),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_relatorio_codigo UNIQUE (tenant_id, codigo)
);
COMMENT ON TABLE dw.relatorio IS 'Definicao de relatorios automaticos ou manuais: aniversariantes, metas, demandas, agenda e ranking de lideres.';

-- 16.7 relatorio_execucao --------------------------------------------------------------
CREATE TABLE dw.relatorio_execucao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    relatorio_id    BIGINT NOT NULL REFERENCES dw.relatorio(id) ON DELETE CASCADE,
    parametros      JSONB NOT NULL DEFAULT '{}'::jsonb,
    arquivo_id      BIGINT REFERENCES arquivo.arquivo(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'gerando'
                    CHECK (status IN ('gerando','concluido','falha')),
    solicitado_por  BIGINT REFERENCES auth.usuario(id),
    iniciado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluido_em    TIMESTAMPTZ
);
COMMENT ON TABLE dw.relatorio_execucao IS 'Historico de geracao de relatorios: parametros usados, arquivo gerado e usuario solicitante.';

-- 16.8 fato_cadastro -------------------------------------------------------------------
CREATE TABLE dw.fato_cadastro (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    data_referencia DATE NOT NULL,
    territorio_id   BIGINT REFERENCES territorio.territorio(id),
    lideranca_id    BIGINT REFERENCES cadastro.lideranca(id),
    fonte_dado_id   BIGINT REFERENCES etl.fonte_dado(id),
    pessoa_tipo_id  SMALLINT REFERENCES cadastro.pessoa_tipo(id),
    total_cadastros INTEGER NOT NULL DEFAULT 0,
    total_novos     INTEGER NOT NULL DEFAULT 0,
    total_atualizados INTEGER NOT NULL DEFAULT 0,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.fato_cadastro IS 'Tabela analitica consolidada sobre evolucao de cadastros por periodo, territorio, origem, lider e perfil.';

CREATE INDEX ix_fato_cadastro_dim ON dw.fato_cadastro (tenant_id, data_referencia, territorio_id);

-- 16.9 fato_demanda --------------------------------------------------------------------
CREATE TABLE dw.fato_demanda (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    data_referencia DATE NOT NULL,
    categoria_demanda_id SMALLINT REFERENCES demanda.categoria_demanda(id),
    status_demanda_id SMALLINT REFERENCES demanda.status_demanda(id),
    territorio_id   BIGINT REFERENCES territorio.territorio(id),
    responsavel_atendimento_id BIGINT REFERENCES demanda.responsavel_atendimento(id),
    total_demandas  INTEGER NOT NULL DEFAULT 0,
    total_concluidas INTEGER NOT NULL DEFAULT 0,
    tempo_medio_atendimento_horas NUMERIC(12,2),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.fato_demanda IS 'Tabela analitica consolidada sobre demandas por categoria, status, territorio, responsavel e tempo de atendimento.';

CREATE INDEX ix_fato_demanda_dim ON dw.fato_demanda (tenant_id, data_referencia, categoria_demanda_id);

-- 16.10 fato_evento --------------------------------------------------------------------
CREATE TABLE dw.fato_evento (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    data_referencia DATE NOT NULL,
    tipo_evento_id  SMALLINT REFERENCES agenda.tipo_evento(id),
    territorio_id   BIGINT REFERENCES territorio.territorio(id),
    total_eventos   INTEGER NOT NULL DEFAULT 0,
    total_presentes INTEGER NOT NULL DEFAULT 0,
    total_demandas_geradas INTEGER NOT NULL DEFAULT 0,
    presenca_parlamentar INTEGER NOT NULL DEFAULT 0,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.fato_evento IS 'Tabela analitica consolidada sobre eventos, presencas, liderancas envolvidas, demandas geradas e territorios.';

-- 16.11 fato_meta_voto -----------------------------------------------------------------
CREATE TABLE dw.fato_meta_voto (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    data_referencia DATE NOT NULL,
    meta_voto_id    BIGINT REFERENCES meta.meta_voto(id),
    lideranca_id    BIGINT REFERENCES cadastro.lideranca(id),
    territorio_id   BIGINT REFERENCES territorio.territorio(id),
    quantidade_meta INTEGER,
    quantidade_projetada INTEGER,
    quantidade_confirmada INTEGER,
    percentual_atingido NUMERIC(5,2),
    em_risco        BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.fato_meta_voto IS 'Tabela analitica consolidada sobre metas, projecoes, confirmacoes, atingimento e risco.';

-- 16.12 fato_interacao -----------------------------------------------------------------
CREATE TABLE dw.fato_interacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    data_referencia DATE NOT NULL,
    canal_comunicacao_id SMALLINT REFERENCES comunicacao.canal_comunicacao(id),
    lideranca_id    BIGINT REFERENCES cadastro.lideranca(id),
    territorio_id   BIGINT REFERENCES territorio.territorio(id),
    total_interacoes INTEGER NOT NULL DEFAULT 0,
    total_com_resultado INTEGER NOT NULL DEFAULT 0,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE dw.fato_interacao IS 'Tabela analitica consolidada sobre contatos, canais, frequencia, resultado e engajamento.';

-- =====================================================================================
-- 17. SCHEMA auditoria - TRILHA DE AUDITORIA E EXPORTACOES (LGPD)
-- =====================================================================================

-- 17.1 log_auditoria -------------------------------------------------------------------
CREATE TABLE auditoria.log_auditoria (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT REFERENCES public.tenant(id) ON DELETE CASCADE,
    usuario_id      BIGINT REFERENCES auth.usuario(id),
    acao            VARCHAR(20) NOT NULL
                    CHECK (acao IN ('criar','editar','excluir','acessar','exportar','login','logout','confirmar')),
    schema_nome     VARCHAR(40),
    tabela          VARCHAR(80),
    registro_id     BIGINT,
    dados_anteriores JSONB,
    dados_novos     JSONB,
    ip_origem       INET,
    user_agent      TEXT,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE auditoria.log_auditoria IS 'Trilha de auditoria para criacao, edicao, exclusao, acesso, exportacao e acoes sensiveis (LGPD).';

CREATE INDEX ix_log_auditoria_tenant_data ON auditoria.log_auditoria (tenant_id, criado_em);
CREATE INDEX ix_log_auditoria_tabela ON auditoria.log_auditoria (tabela, registro_id);

-- 17.2 log_exportacao ------------------------------------------------------------------
CREATE TABLE auditoria.log_exportacao (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES public.tenant(id) ON DELETE CASCADE,
    usuario_id      BIGINT REFERENCES auth.usuario(id),
    entidade        VARCHAR(80),
    filtros         JSONB NOT NULL DEFAULT '{}'::jsonb,
    volume_registros INTEGER,
    formato         VARCHAR(20),
    finalidade      VARCHAR(255),
    arquivo_id      BIGINT REFERENCES arquivo.arquivo(id),
    ip_origem       INET,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE auditoria.log_exportacao IS 'Registro de exportacoes de dados: usuario, filtros, volume exportado e finalidade.';

CREATE INDEX ix_log_exportacao_tenant ON auditoria.log_exportacao (tenant_id, criado_em);

-- =====================================================================================
-- 18. TRIGGERS DE atualizado_em
-- =====================================================================================
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT n.nspname AS schema_nome, c.relname AS tabela
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE c.relkind = 'r'
          AND a.attname = 'atualizado_em'
          AND n.nspname IN ('public','global','auth','cadastro','territorio','agenda',
                            'demanda','meta','comunicacao','eleicao','arquivo','etl','dw','auditoria')
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_atualiza_timestamp BEFORE UPDATE ON %I.%I
             FOR EACH ROW EXECUTE FUNCTION global.fn_atualiza_timestamp();',
            r.schema_nome, r.tabela
        );
    END LOOP;
END;
$$;

-- =====================================================================================
-- 19. ROW-LEVEL SECURITY (RLS) - ISOLAMENTO MULTITENANT
-- =====================================================================================
-- Habilita RLS e cria politica baseada em global.tenant_atual() para TODAS as
-- tabelas que possuem a coluna tenant_id. Tabelas globais nao recebem RLS.
-- Tambem cria trigger fn_preenche_tenant para preencher tenant_id automaticamente.

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT n.nspname AS schema_nome, c.relname AS tabela
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE c.relkind = 'r'
          AND a.attname = 'tenant_id'
          AND a.attnotnull = TRUE                 -- somente tabelas com tenant_id obrigatorio
          AND n.nspname IN ('auth','cadastro','territorio','agenda','demanda','meta',
                            'comunicacao','eleicao','arquivo','dw','auditoria')
    LOOP
        -- Habilita e forca RLS
        EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY;', r.schema_nome, r.tabela);
        EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY;', r.schema_nome, r.tabela);

        -- Politica de isolamento por tenant
        EXECUTE format($f$
            CREATE POLICY pol_isolamento_tenant ON %I.%I
            USING (tenant_id = global.tenant_atual())
            WITH CHECK (tenant_id = global.tenant_atual());
        $f$, r.schema_nome, r.tabela);

        -- Trigger de preenchimento automatico de tenant_id no INSERT
        EXECUTE format(
            'CREATE TRIGGER trg_preenche_tenant BEFORE INSERT ON %I.%I
             FOR EACH ROW EXECUTE FUNCTION global.fn_preenche_tenant();',
            r.schema_nome, r.tabela
        );
    END LOOP;
END;
$$;

-- OBS sobre tabelas com tenant_id OPCIONAL (NULL permitido), usadas tanto como catalogo
-- global quanto por tenant (ex.: auth.perfil_acesso, cadastro.profissao, agenda.tipo_evento,
-- demanda.categoria_demanda, etl.importacao, etl.regra_deduplicacao, eleicao.eleicao,
-- dw.relatorio): nestes casos o RLS NAO e aplicado automaticamente para permitir leitura
-- dos registros globais (tenant_id IS NULL). O filtro por tenant deve ser tratado na
-- camada de aplicacao ou por politica especifica, conforme a regra de negocio adotada.

-- =====================================================================================
-- 20. PRIVILEGIOS PARA A ROLE DE APLICACAO
-- =====================================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA
    public, global, auth, cadastro, territorio, agenda, demanda,
    meta, comunicacao, eleicao, arquivo, etl, dw, auditoria
    TO app_inteligencia;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA
    public, global, auth, cadastro, territorio, agenda, demanda,
    meta, comunicacao, eleicao, arquivo, etl, dw, auditoria
    TO app_inteligencia;

-- Privilegios padrao para objetos criados futuramente
DO $$
DECLARE
    s TEXT;
BEGIN
    FOREACH s IN ARRAY ARRAY['public','global','auth','cadastro','territorio','agenda',
        'demanda','meta','comunicacao','eleicao','arquivo','etl','dw','auditoria']
    LOOP
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_inteligencia;', s);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO app_inteligencia;', s);
    END LOOP;
END;
$$;

-- =====================================================================================
-- 21. DADOS DE REFERENCIA (SEED) ESSENCIAIS
-- =====================================================================================

-- Pessoa tipos
INSERT INTO cadastro.pessoa_tipo (codigo, nome, descricao) VALUES
    ('eleitor','Eleitor','Pessoa eleitora vinculada a campanha'),
    ('apoiador','Apoiador','Pessoa que apoia a campanha'),
    ('lider','Lider','Pessoa com papel de lideranca'),
    ('coordenador','Coordenador','Coordenador territorial ou geral'),
    ('liderado','Liderado','Integrante de equipe vinculado a um lider'),
    ('telefonista','Telefonista','Perfil operacional de atendimento'),
    ('contato_institucional','Contato Institucional','Contato de instituicao ou orgao'),
    ('voluntario','Voluntario','Voluntario da campanha')
ON CONFLICT (codigo) DO NOTHING;

-- Status de evento
INSERT INTO agenda.status_evento (codigo, nome) VALUES
    ('planejado','Planejado'),('confirmado','Confirmado'),('realizado','Realizado'),
    ('cancelado','Cancelado'),('remarcado','Remarcado')
ON CONFLICT (codigo) DO NOTHING;

-- Status de demanda
INSERT INTO demanda.status_demanda (codigo, nome, ordem, final) VALUES
    ('pendente','Pendente',1,FALSE),
    ('em_andamento','Em andamento',2,FALSE),
    ('concluida','Concluida',3,TRUE),
    ('parcialmente_atendida','Parcialmente atendida',4,TRUE),
    ('nao_atendida','Nao atendida',5,TRUE),
    ('cancelada','Cancelada',6,TRUE)
ON CONFLICT (codigo) DO NOTHING;

-- Prioridade de demanda
INSERT INTO demanda.prioridade_demanda (codigo, nome, peso) VALUES
    ('baixa','Baixa',1),('media','Media',2),('alta','Alta',3),('urgente','Urgente',4)
ON CONFLICT (codigo) DO NOTHING;

-- Origem de demanda
INSERT INTO demanda.origem_demanda (codigo, nome) VALUES
    ('evento','Evento'),('ligacao','Ligacao'),('whatsapp','WhatsApp'),
    ('cadastro_manual','Cadastro manual'),('lider','Lider'),('comunidade','Comunidade'),
    ('importacao','Importacao')
ON CONFLICT (codigo) DO NOTHING;

-- Resultado de atendimento
INSERT INTO demanda.resultado_atendimento (codigo, nome) VALUES
    ('solucionado','Solucionado'),('parcialmente_atendido','Parcialmente atendido'),
    ('nao_atendido','Nao atendido')
ON CONFLICT (codigo) DO NOTHING;

-- Tipo de meta
INSERT INTO meta.tipo_meta_voto (codigo, nome) VALUES
    ('global','Global'),('territorial','Territorial'),('lider','Por lider'),
    ('equipe','Por equipe'),('comunidade','Por comunidade'),('nucleo_familiar','Por nucleo familiar')
ON CONFLICT (codigo) DO NOTHING;

-- Canais de comunicacao
INSERT INTO comunicacao.canal_comunicacao (codigo, nome) VALUES
    ('whatsapp','WhatsApp'),('telefone','Telefone'),('email','E-mail'),
    ('instagram','Instagram'),('sms','SMS'),('presencial','Presencial')
ON CONFLICT (codigo) DO NOTHING;

-- Tipos de interacao
INSERT INTO comunicacao.tipo_interacao (codigo, nome) VALUES
    ('ligacao','Ligacao'),('mensagem','Mensagem'),('visita','Visita'),
    ('reuniao','Reuniao'),('email','E-mail'),('atendimento','Atendimento presencial')
ON CONFLICT (codigo) DO NOTHING;

-- Tipos de anexo
INSERT INTO arquivo.tipo_anexo (codigo, nome) VALUES
    ('foto','Foto'),('convite','Convite'),('pauta','Pauta'),
    ('documento_pessoal','Documento pessoal'),('comprovante','Comprovante'),
    ('imagem','Imagem'),('pdf','PDF'),('planilha','Planilha')
ON CONFLICT (codigo) DO NOTHING;

-- Tipos de territorio
INSERT INTO territorio.tipo_territorio (codigo, nome) VALUES
    ('estado','Estado'),('municipio','Municipio'),('bairro','Bairro'),
    ('zona_eleitoral','Zona eleitoral'),('secao_eleitoral','Secao eleitoral'),
    ('microrregiao','Microrregiao'),('comunidade','Comunidade'),('area_personalizada','Area personalizada')
ON CONFLICT (codigo) DO NOTHING;

-- Categorias de data comemorativa
INSERT INTO global.categoria_data_comemorativa (nome, descricao) VALUES
    ('Aniversario municipal','Aniversario de fundacao de municipio'),
    ('Religiosa','Data religiosa'),
    ('Civica','Data civica nacional ou estadual'),
    ('Cultural','Evento cultural local'),
    ('Comunitaria','Data comunitaria ou setorial')
ON CONFLICT (nome) DO NOTHING;

-- =====================================================================================
-- FIM DO DDL
-- =====================================================================================
