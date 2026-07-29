-- Bootstrap idempotente do primeiro Gestor SaaS.
--
-- Execute com uma role PostgreSQL que possa inserir em public/auth e contornar
-- as politicas RLS (por exemplo, postgres), depois de aplicar as migrations.
--
-- Credenciais iniciais:
--   tenant: vurix-admin
--   e-mail: admin@vurix.local
--   senha:  TroqueAgora#2026
--
-- O sistema exigira a troca da senha no primeiro acesso.

BEGIN;

DO $bootstrap$
DECLARE
    v_tenant_id BIGINT;
    v_perfil_id BIGINT;
    v_usuario_id BIGINT;
BEGIN
    INSERT INTO public.tenant (
        nome,
        slug,
        status,
        tem_mandato
    )
    VALUES (
        'Administração Vurix',
        'vurix-admin',
        'ativo',
        FALSE
    )
    ON CONFLICT (slug) DO UPDATE
       SET excluido_em = NULL
    RETURNING id INTO v_tenant_id;

    INSERT INTO public.tenant_configuracao (
        tenant_id,
        nome_publico,
        fuso_horario
    )
    VALUES (
        v_tenant_id,
        'Administração Vurix',
        'America/Sao_Paulo'
    )
    ON CONFLICT (tenant_id) DO NOTHING;

    -- auth.usuario e auth.usuario_perfil possuem RLS por tenant.
    PERFORM set_config('app.current_tenant_id', v_tenant_id::TEXT, TRUE);

    SELECT id
      INTO v_perfil_id
      FROM auth.perfil_acesso
     WHERE tenant_id IS NULL
       AND codigo = 'gestor_saas';

    IF v_perfil_id IS NULL THEN
        RAISE EXCEPTION
            'Perfil gestor_saas não encontrado. Aplique a migration 003.';
    END IF;

    INSERT INTO auth.usuario (
        tenant_id,
        nome,
        email,
        hash_senha,
        mfa_habilitado,
        status,
        tentativas_login,
        senha_alterada_em,
        deve_alterar_senha
    )
    VALUES (
        v_tenant_id,
        'Administrador SaaS',
        'admin@vurix.local',
        '$argon2id$v=19$m=65536,t=3,p=4$k9GbqcL7ytGJxJ2e1ooVrg$ihtXonLIXu9E7OrIXsDFUNMof/jfaZVbbVcibXZVddM',
        FALSE,
        'ativo',
        0,
        now(),
        TRUE
    )
    ON CONFLICT (tenant_id, email) DO UPDATE
       SET nome = EXCLUDED.nome,
           status = 'ativo',
           tentativas_login = 0,
           excluido_em = NULL
    RETURNING id INTO v_usuario_id;

    INSERT INTO auth.usuario_perfil (
        usuario_id,
        perfil_acesso_id,
        tenant_id
    )
    VALUES (
        v_usuario_id,
        v_perfil_id,
        v_tenant_id
    )
    ON CONFLICT (usuario_id, perfil_acesso_id) DO NOTHING;

    RAISE NOTICE
        'Gestor SaaS pronto: tenant=%, usuario_id=%, email=%',
        'vurix-admin',
        v_usuario_id,
        'admin@vurix.local';
END;
$bootstrap$;

COMMIT;
