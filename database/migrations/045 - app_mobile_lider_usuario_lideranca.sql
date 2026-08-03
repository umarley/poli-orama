-- App mobile de lideres/coordenadores (React Native - app_mobile_lider).
-- Vincula contas de usuario a pessoa/lideranca operacional e prepara o cadastro
-- de eleitores/pessoas no campo seguindo o fluxo web existente.
--
-- Fluxo de cadastro via app mobile (sem tabelas paralelas):
--   1. cadastro.pessoa          — origem_cadastro = 'lider_mobile', criado_por = usuario do app
--   2. cadastro.endereco        — latitude/longitude capturadas pelo GPS do dispositivo
--   3. cadastro.pessoa_endereco — vinculo tipo 'residencial' (endereco principal da pessoa)
--   4. arquivo.arquivo          — metadados do upload no SeaweedFS (mime_type, caminho, etc.)
--   5. arquivo.anexo            — entidade_tipo = 'pessoa', entidade_id = pessoa.id,
--                                 tipo_anexo = 'foto'
--   6. cadastro.indicacao       — pessoa_indicante_id = auth.usuario.pessoa_id do lider logado
--   7. cadastro.hierarquia_lideranca + eleicao.campanha_liderado — origem = 'lider_mobile'

BEGIN;

-- =============================================================================
-- 1. auth.usuario: vinculo operacional com lideranca/pessoa
-- =============================================================================

ALTER TABLE auth.usuario
    ADD COLUMN IF NOT EXISTS lideranca_id BIGINT
        REFERENCES cadastro.lideranca(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS habilitado_app_lider BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ultimo_acesso_app_em TIMESTAMPTZ;

COMMENT ON COLUMN auth.usuario.lideranca_id IS
    'Lideranca operacional vinculada ao usuario para acesso ao app mobile de campo.';
COMMENT ON COLUMN auth.usuario.habilitado_app_lider IS
    'Indica se o usuario pode autenticar no app mobile de lideres/coordenadores.';
COMMENT ON COLUMN auth.usuario.ultimo_acesso_app_em IS
    'Data/hora do ultimo acesso bem-sucedido ao app mobile de lideranca.';

ALTER TABLE auth.usuario
    DROP CONSTRAINT IF EXISTS ck_usuario_app_lider_requer_lideranca;

ALTER TABLE auth.usuario
    ADD CONSTRAINT ck_usuario_app_lider_requer_lideranca
    CHECK (NOT habilitado_app_lider OR lideranca_id IS NOT NULL);

CREATE INDEX IF NOT EXISTS ix_usuario_lideranca
    ON auth.usuario (tenant_id, lideranca_id)
    WHERE lideranca_id IS NOT NULL AND excluido_em IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_lideranca_ativo
    ON auth.usuario (tenant_id, lideranca_id)
    WHERE lideranca_id IS NOT NULL AND excluido_em IS NULL;

-- Sincroniza pessoa_id a partir da lideranca vinculada (usado em cadastro.indicacao).
CREATE OR REPLACE FUNCTION auth.sync_usuario_lideranca_pessoa()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_pessoa_id BIGINT;
BEGIN
    IF NEW.lideranca_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT l.pessoa_id
      INTO v_pessoa_id
      FROM cadastro.lideranca AS l
     WHERE l.id = NEW.lideranca_id
       AND l.tenant_id = NEW.tenant_id
       AND l.ativo = TRUE;

    IF v_pessoa_id IS NULL THEN
        RAISE EXCEPTION
            'lideranca_id % invalida, inativa ou de outro tenant para o usuario %',
            NEW.lideranca_id, NEW.id;
    END IF;

    NEW.pessoa_id := v_pessoa_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_usuario_lideranca_pessoa ON auth.usuario;

CREATE TRIGGER trg_sync_usuario_lideranca_pessoa
    BEFORE INSERT OR UPDATE OF lideranca_id, tenant_id
    ON auth.usuario
    FOR EACH ROW
    EXECUTE FUNCTION auth.sync_usuario_lideranca_pessoa();

-- Backfill: usuarios ja vinculados a pessoa que possui registro de lideranca.
UPDATE auth.usuario AS u
   SET lideranca_id = l.id
  FROM cadastro.lideranca AS l
 WHERE l.pessoa_id = u.pessoa_id
   AND l.tenant_id = u.tenant_id
   AND l.ativo = TRUE
   AND u.lideranca_id IS NULL
   AND u.excluido_em IS NULL;

-- Backfill inverso: pessoa_id ausente, mas lideranca_id informada.
UPDATE auth.usuario AS u
   SET pessoa_id = l.pessoa_id
  FROM cadastro.lideranca AS l
 WHERE l.id = u.lideranca_id
   AND l.tenant_id = u.tenant_id
   AND u.pessoa_id IS NULL
   AND u.excluido_em IS NULL;

-- =============================================================================
-- 2. cadastro.pessoa: origem do cadastro de campo
-- =============================================================================

ALTER TABLE cadastro.pessoa
    ADD COLUMN IF NOT EXISTS origem_cadastro VARCHAR(30),
    ADD COLUMN IF NOT EXISTS cadastrado_por_lideranca_id BIGINT
        REFERENCES cadastro.lideranca(id) ON DELETE SET NULL;

ALTER TABLE cadastro.pessoa
    DROP CONSTRAINT IF EXISTS ck_pessoa_origem_cadastro;

ALTER TABLE cadastro.pessoa
    ADD CONSTRAINT ck_pessoa_origem_cadastro
    CHECK (
        origem_cadastro IS NULL
        OR origem_cadastro IN (
            'manual',
            'cadastro_web',
            'lider_mobile',
            'importacao',
            'call_center',
            'formulario',
            'migracao'
        )
    );

COMMENT ON COLUMN cadastro.pessoa.origem_cadastro IS
    'Canal de origem do cadastro. No app mobile usar lider_mobile e fonte_dado app_lider_mobile.';
COMMENT ON COLUMN cadastro.pessoa.cadastrado_por_lideranca_id IS
    'Lideranca que realizou o cadastro via app mobile (redundante a criado_por para consultas diretas).';

CREATE INDEX IF NOT EXISTS ix_pessoa_cadastrado_por_lideranca
    ON cadastro.pessoa (tenant_id, cadastrado_por_lideranca_id)
    WHERE cadastrado_por_lideranca_id IS NOT NULL AND excluido_em IS NULL;

-- =============================================================================
-- 3. cadastro.indicacao: pessoa_indicante_id recebe a pessoa do lider logado
-- =============================================================================

COMMENT ON COLUMN cadastro.indicacao.pessoa_indicante_id IS
    'Pessoa que indicou o cadastro. No app mobile, preencher com auth.usuario.pessoa_id '
    'do lider/coordenador autenticado (sincronizado via auth.usuario.lideranca_id).';

COMMENT ON COLUMN cadastro.indicacao.origem IS
    'Canal da indicacao. No app mobile usar lider_mobile.';

-- =============================================================================
-- 4. Endereco residencial: GPS do app mobile (fluxo cadastro existente)
-- =============================================================================

COMMENT ON COLUMN cadastro.endereco.latitude IS
    'Latitude WGS84. No app mobile, preenchida com a coordenada GPS capturada no ato do cadastro.';
COMMENT ON COLUMN cadastro.endereco.longitude IS
    'Longitude WGS84. No app mobile, preenchida com a coordenada GPS capturada no ato do cadastro.';

COMMENT ON TABLE cadastro.pessoa_endereco IS
    'Associacao pessoa x endereco. No app mobile, vincular endereco GPS com tipo residencial.';

-- =============================================================================
-- 5. Foto: SeaweedFS -> arquivo.arquivo -> arquivo.anexo (tipo foto, entidade pessoa)
-- =============================================================================

COMMENT ON TABLE arquivo.arquivo IS
    'Registro logico de arquivo no storage. No app mobile, persistir mime_type, caminho SeaweedFS '
    'e demais metadados apos upload da foto da pessoa cadastrada.';
COMMENT ON TABLE arquivo.anexo IS
    'Vinculo polimorfico de arquivo a entidades. No app mobile, associar foto da pessoa com '
    'entidade_tipo = pessoa, entidade_id = cadastro.pessoa.id e tipo_anexo codigo foto.';

-- =============================================================================
-- 6. cadastro.hierarquia_lideranca: origem do vinculo (Eleitores/Liderados)
-- =============================================================================

ALTER TABLE cadastro.hierarquia_lideranca
    ADD COLUMN IF NOT EXISTS origem VARCHAR(30) NOT NULL DEFAULT 'manual';

ALTER TABLE cadastro.hierarquia_lideranca
    DROP CONSTRAINT IF EXISTS ck_hierarquia_lideranca_origem;

ALTER TABLE cadastro.hierarquia_lideranca
    ADD CONSTRAINT ck_hierarquia_lideranca_origem
    CHECK (origem IN (
        'migracao',
        'lider_mobile',
        'cadastro_web',
        'importacao',
        'call_center',
        'manual'
    ));

COMMENT ON COLUMN cadastro.hierarquia_lideranca.origem IS
    'Origem do vinculo exibido em Eleitores/Liderados. No app mobile usar lider_mobile.';

UPDATE cadastro.hierarquia_lideranca
   SET origem = 'migracao'
 WHERE origem = 'manual'
   AND criado_em < now() - INTERVAL '1 day';

-- =============================================================================
-- 7. Fonte de dados ETL para cadastros do app mobile
-- =============================================================================

ALTER TABLE etl.fonte_dado
    DROP CONSTRAINT IF EXISTS fonte_dado_tipo_check;

ALTER TABLE etl.fonte_dado
    ADD CONSTRAINT fonte_dado_tipo_check
    CHECK (tipo IN (
        'gesped', 'tse', 'ibge', 'planilha', 'formulario',
        'api', 'manual', 'aplicativo', 'outro'
    ));

INSERT INTO etl.fonte_dado (tenant_id, codigo, nome, tipo, descricao)
VALUES (
    NULL,
    'app_lider_mobile',
    'App mobile de lideranca',
    'aplicativo',
    'Cadastro de eleitores/pessoas via app React Native de lideres e coordenadores'
)
ON CONFLICT (codigo) WHERE tenant_id IS NULL DO UPDATE
SET nome = EXCLUDED.nome,
    tipo = EXCLUDED.tipo,
    descricao = EXCLUDED.descricao,
    ativo = TRUE;

COMMIT;
