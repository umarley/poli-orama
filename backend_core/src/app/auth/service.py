import hmac
from datetime import UTC, datetime
from typing import Any

from app.audit.service import AuditService
from app.auth.access import RequestActor
from app.auth.models import AccessProfile, Permission, User
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    LoginRequest,
    MfaSetupResponse,
    PermissionResponse,
    ProfileResponse,
    ResetPasswordResponse,
    SelfProfileUpdate,
    SessionResponse,
    TenantSwitchRequest,
    TerritorialAccessInput,
    TerritorialAccessResponse,
    TokenResponse,
    UserCreate,
    UserData,
    UserResponse,
    UserUpdate,
)
from app.auth.security import (
    access_token_expiration,
    consume_password_verification_time,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    generate_mfa_secret,
    generate_temporary_password,
    hash_password,
    mfa_provisioning_uri,
    refresh_token_expiration,
    session_is_inactive,
    token_digest,
    validate_password_policy,
    verify_mfa_code,
    verify_password,
)
from app.core.config import Settings
from app.core.errors import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    InvalidMfaCodeError,
    MfaRequiredError,
    ResourceNotFoundError,
    TenantInactiveError,
)
from app.core.pagination import ListParams, Page
from app.tenants.models import Tenant
from app.tenants.schemas import TenantResponse


class AuthService:
    def __init__(self, repository: AuthRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self.audit = AuditService(repository.session)

    async def login(
        self,
        payload: LoginRequest,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        tenant = await self.repository.resolve_tenant_for_login(payload.tenant_slug)
        if tenant is None:
            consume_password_verification_time(payload.senha)
            raise AuthenticationError("Credenciais invalidas.")
        if tenant.status not in {"ativo", "trial"}:
            consume_password_verification_time(payload.senha)
            raise AuthenticationError("Credenciais invalidas.")

        user = await self.repository.get_user_by_email(tenant.id, payload.email)
        if user is None:
            consume_password_verification_time(payload.senha)
            await self.audit.record(
                action="login",
                tenant_id=tenant.id,
                user_id=None,
                schema_name="auth",
                table_name="usuario",
                after={"resultado": "falha"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.repository.commit()
            raise AuthenticationError("Credenciais invalidas.")
        if user.usuario_plataforma_id is not None:
            consume_password_verification_time(payload.senha)
            raise AuthenticationError("Credenciais invalidas.")
        if not verify_password(payload.senha, user.hash_senha):
            await self.repository.register_login_failure(user)
            await self.audit.record(
                action="login",
                tenant_id=tenant.id,
                user_id=user.id,
                schema_name="auth",
                table_name="usuario",
                record_id=user.id,
                after={"resultado": "falha"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.repository.commit()
            raise AuthenticationError("Credenciais invalidas.")
        if user.status != "ativo":
            raise AuthenticationError("Usuario inativo ou bloqueado.")

        if payload.app_lider:
            if not user.habilitado_app_lider:
                raise AuthenticationError(
                    "Usuario nao habilitado para o app mobile de lideranca."
                )
            if user.lideranca_id is None:
                raise AuthenticationError(
                    "Usuario sem lideranca vinculada para o app mobile."
                )

        profiles = await self.repository.profiles_for_user(user.id)
        if user.mfa_habilitado:
            if payload.codigo_mfa is None:
                raise MfaRequiredError()
            if user.mfa_segredo is None or not verify_mfa_code(
                decrypt_mfa_secret(user.mfa_segredo, self.settings),
                payload.codigo_mfa,
            ):
                await self.audit.record(
                    action="login",
                    tenant_id=tenant.id,
                    user_id=user.id,
                    schema_name="auth",
                    table_name="usuario",
                    record_id=user.id,
                    after={"resultado": "falha_mfa"},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                await self.repository.commit()
                raise InvalidMfaCodeError()
        permissions = await self.repository.permissions_for_user(user.id)
        access_expires_at = access_token_expiration(self.settings)
        session_expires_at = refresh_token_expiration(self.settings)
        user_session = await self.repository.create_session(
            tenant_id=tenant.id,
            user_id=user.id,
            login_origin="app_lider" if payload.app_lider else "web",
            expires_at=session_expires_at,
            device=payload.dispositivo,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        token = create_access_token(
            settings=self.settings,
            user_id=user.id,
            tenant_id=tenant.id,
            session_id=user_session.id,
            profiles=[profile.codigo for profile in profiles],
            permissions=[permission.codigo for permission in permissions],
            login_origin=user_session.origem_login,
            expires_at=access_expires_at,
        )
        refresh_token = create_refresh_token(
            settings=self.settings,
            user_id=user.id,
            tenant_id=tenant.id,
            session_id=user_session.id,
            login_origin=user_session.origem_login,
            expires_at=session_expires_at,
        )
        user_session.token_hash = token_digest(token)
        user_session.refresh_token_hash = token_digest(refresh_token)
        if payload.app_lider:
            await self.repository.register_mobile_app_access(user)
        else:
            await self.repository.register_login_success(user)
        await self.audit.record(
            action="login",
            tenant_id=tenant.id,
            user_id=user.id,
            schema_name="auth",
            table_name="sessao_usuario",
            record_id=user_session.id,
            after={"resultado": "sucesso"},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_minutes * 60,
            usuario=_user_response(user, profiles, permissions, tenant),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        claims = decode_refresh_token(refresh_token, self.settings)
        tenant_id = int(claims["tenant_id"])
        user_id = int(claims["sub"])
        session_id = int(claims["sid"])
        login_origin = str(claims["origem_login"])
        await self.repository.set_tenant_context(tenant_id)
        tenant = await self.repository.resolve_tenant_for_login_by_id(tenant_id)
        if tenant is None:
            raise AuthenticationError("Sessao invalida ou revogada.")
        user = await self.repository.get_user(tenant_id, user_id)
        user_session = await self.repository.get_session(session_id)
        if (
            user is None
            or user.status != "ativo"
            or user_session is None
            or user_session.usuario_id != user_id
            or user_session.tenant_id != tenant_id
            or user_session.origem_login != login_origin
            or user_session.revogada_em is not None
            or user_session.expira_em <= datetime.now(UTC)
            or user_session.refresh_token_hash is None
            or not hmac.compare_digest(user_session.refresh_token_hash, token_digest(refresh_token))
        ):
            raise AuthenticationError("Sessao invalida ou revogada.")
        now = datetime.now(UTC)
        if session_is_inactive(user_session.ultimo_uso_em, now, self.settings):
            await self.repository.revoke_session(user_session)
            await self.repository.commit()
            raise AuthenticationError("Sessao expirada por inatividade.")

        profiles = await self.repository.profiles_for_user(user_id)
        if tenant.status not in {"ativo", "trial"} and not any(
            profile.codigo == "gestor_saas" for profile in profiles
        ):
            raise TenantInactiveError(tenant.status)
        permissions = await self.repository.permissions_for_user(user_id)
        access_expires_at = access_token_expiration(self.settings)
        access_token = create_access_token(
            settings=self.settings,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            profiles=[profile.codigo for profile in profiles],
            permissions=[permission.codigo for permission in permissions],
            login_origin=user_session.origem_login,
            expires_at=access_expires_at,
        )
        rotated_refresh_token = create_refresh_token(
            settings=self.settings,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            login_origin=user_session.origem_login,
            expires_at=user_session.expira_em,
        )
        await self.repository.rotate_session_tokens(
            user_session,
            access_token_hash=token_digest(access_token),
            refresh_token_hash=token_digest(rotated_refresh_token),
        )
        await self.repository.touch_session(user_session, now)
        await self.repository.commit()
        return TokenResponse(
            access_token=access_token,
            refresh_token=rotated_refresh_token,
            expires_in=self.settings.access_token_minutes * 60,
            usuario=await self._response(user, tenant),
        )

    async def setup_mfa(
        self,
        actor: RequestActor,
        password: str,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> MfaSetupResponse:
        self._require_manager_profile(actor)
        user = await self._get_user(actor.tenant_id, actor.user_id)
        if not verify_password(password, user.hash_senha):
            raise BusinessRuleError("Senha atual incorreta.", code="current_password_invalid")
        secret = generate_mfa_secret()
        await self.repository.set_mfa_secret(user, encrypt_mfa_secret(secret, self.settings))
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            after={"mfa_configuracao_iniciada": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return MfaSetupResponse(
            segredo=secret,
            uri_configuracao=mfa_provisioning_uri(secret, user.email, self.settings),
        )

    async def confirm_mfa(
        self,
        actor: RequestActor,
        code: str,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        self._require_manager_profile(actor)
        user = await self._get_user(actor.tenant_id, actor.user_id)
        if user.mfa_segredo is None or not verify_mfa_code(
            decrypt_mfa_secret(user.mfa_segredo, self.settings), code
        ):
            raise InvalidMfaCodeError()
        await self.repository.enable_mfa(user)
        await self.repository.revoke_other_user_sessions(user.id, actor.session_id)
        await self.audit.record(
            action="confirmar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            after={"mfa_habilitado": True, "outras_sessoes_revogadas": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()

    async def disable_mfa(
        self,
        actor: RequestActor,
        password: str,
        code: str,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        self._require_manager_profile(actor)
        user = await self._get_user(actor.tenant_id, actor.user_id)
        if not verify_password(password, user.hash_senha):
            raise BusinessRuleError("Senha atual incorreta.", code="current_password_invalid")
        if (
            not user.mfa_habilitado
            or user.mfa_segredo is None
            or not verify_mfa_code(decrypt_mfa_secret(user.mfa_segredo, self.settings), code)
        ):
            raise InvalidMfaCodeError()
        await self.repository.disable_mfa(user)
        await self.repository.revoke_other_user_sessions(user.id, actor.session_id)
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            after={"mfa_habilitado": False, "outras_sessoes_revogadas": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()

    async def list_sessions(self, actor: RequestActor) -> list[SessionResponse]:
        now = datetime.now(UTC)
        return [
            SessionResponse(
                id=session.id,
                origem_login=session.origem_login,
                dispositivo=session.dispositivo,
                user_agent=session.user_agent,
                ip_origem=str(session.ip_origem) if session.ip_origem else None,
                criado_em=session.criado_em,
                ultimo_uso_em=session.ultimo_uso_em,
                expira_em=session.expira_em,
                revogada_em=session.revogada_em,
                atual=session.id == actor.session_id,
                status=(
                    "revogada"
                    if session.revogada_em
                    else "expirada"
                    if session.expira_em <= now
                    else "expirada_inatividade"
                    if session_is_inactive(session.ultimo_uso_em, now, self.settings)
                    else "ativa"
                ),
            )
            for session in await self.repository.list_user_sessions(actor.tenant_id, actor.user_id)
        ]

    async def revoke_user_session(
        self,
        actor: RequestActor,
        session_id: int,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> bool:
        user_session = await self.repository.get_user_session(
            actor.tenant_id, actor.user_id, session_id
        )
        if user_session is None:
            raise ResourceNotFoundError("Sessao", session_id)
        if user_session.revogada_em is None:
            await self.repository.revoke_session(user_session)
        await self.audit.record(
            action="logout",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="sessao_usuario",
            record_id=session_id,
            after={"revogada_manualmente": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return session_id == actor.session_id

    async def logout(
        self,
        actor: RequestActor,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        user_session = await self.repository.get_session(actor.session_id)
        if user_session is not None and user_session.revogada_em is None:
            await self.repository.revoke_session(user_session)
        await self.audit.record(
            action="logout",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="sessao_usuario",
            record_id=actor.session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()

    async def me(self, actor: RequestActor) -> UserResponse:
        user = await self._get_user(actor.tenant_id, actor.user_id)
        return await self._response(user)

    async def update_me(
        self,
        actor: RequestActor,
        payload: SelfProfileUpdate,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> UserResponse:
        user = await self._get_user(actor.tenant_id, actor.user_id)
        before = _user_snapshot(user, await self.repository.profiles_for_user(user.id))
        update = UserUpdate(**payload.model_dump(exclude_unset=True))
        await self.repository.update_user(user, update)
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            before=before,
            after=_user_snapshot(user, await self.repository.profiles_for_user(user.id)),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return await self._response(user)

    async def list_users(
        self, actor: RequestActor, params: ListParams, status: str | None
    ) -> Page[UserResponse]:
        users, total = await self.repository.list_users(actor.tenant_id, params, status)
        tenant = await self._get_tenant(actor.tenant_id)
        return Page[UserResponse].create(
            [await self._response(user, tenant) for user in users], total, params
        )

    async def get_user(self, actor: RequestActor, user_id: int) -> UserResponse:
        return await self._response(await self._get_manageable_user(actor, user_id))

    async def create_user(
        self,
        actor: RequestActor,
        payload: UserCreate,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> UserResponse:
        await self._validate_profile_assignment(actor, payload.perfil_ids)
        validate_password_policy(payload.senha, self.settings)
        user = await self.repository.create_user(
            actor.tenant_id, payload, hash_password(payload.senha)
        )
        profiles = await self.repository.profiles_for_user(user.id)
        await self.audit.record(
            action="criar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            after=_user_snapshot(user, profiles),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return await self._response(user)

    async def update_user(
        self,
        actor: RequestActor,
        user_id: int,
        payload: UserUpdate,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> UserResponse:
        if payload.perfil_ids is not None:
            await self._validate_profile_assignment(actor, payload.perfil_ids)
        user = await self._get_manageable_user(actor, user_id)
        before_profiles = await self.repository.profiles_for_user(user.id)
        before = _user_snapshot(user, before_profiles)
        await self.repository.update_user(user, payload)
        if payload.status is not None and payload.status != "ativo":
            await self.repository.revoke_all_user_sessions(user.id)
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            before=before,
            after=_user_snapshot(user, await self.repository.profiles_for_user(user.id)),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return await self._response(user)

    async def reset_password(
        self,
        actor: RequestActor,
        user_id: int,
        supplied_password: str | None,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> ResetPasswordResponse:
        user = await self._get_manageable_user(actor, user_id)
        temporary_password = supplied_password or generate_temporary_password()
        validate_password_policy(temporary_password, self.settings)
        await self.repository.set_password(
            user, hash_password(temporary_password), must_change=True
        )
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            after={"senha_redefinida": True, "sessoes_revogadas": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return ResetPasswordResponse(usuario_id=user.id, senha_temporaria=temporary_password)

    async def delete_user(
        self,
        actor: RequestActor,
        user_id: int,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        if user_id == actor.user_id:
            raise BusinessRuleError(
                "O usuario nao pode excluir a propria conta.",
                code="cannot_delete_current_user",
            )
        user = await self._get_manageable_user(actor, user_id)
        before = _user_snapshot(user)
        await self.repository.delete_user(user)
        await self.audit.record(
            action="excluir",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            before=before,
            after=_user_snapshot(user),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()

    async def change_password(
        self,
        actor: RequestActor,
        current_password: str,
        new_password: str,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        user = await self._get_user(actor.tenant_id, actor.user_id)
        if not verify_password(current_password, user.hash_senha):
            raise BusinessRuleError("Senha atual incorreta.", code="current_password_invalid")
        validate_password_policy(new_password, self.settings)
        await self.repository.set_password(
            user,
            hash_password(new_password),
            must_change=False,
            keep_session_id=actor.session_id,
        )
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            after={"senha_alterada": True, "sessoes_revogadas": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()

    async def list_profiles(self, actor: RequestActor) -> list[ProfileResponse]:
        responses: list[ProfileResponse] = []
        for profile in await self.repository.available_profiles(actor.tenant_id):
            if profile.codigo == "gestor_saas":
                continue
            response = ProfileResponse.model_validate(profile)
            response.permissoes = [
                PermissionResponse.model_validate(permission)
                for permission in await self.repository.permissions_for_profile(profile.id)
            ]
            responses.append(response)
        return responses

    async def switch_tenant(
        self,
        actor: RequestActor,
        payload: TenantSwitchRequest,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        if "gestor_saas" not in actor.profiles:
            raise AuthorizationError("Apenas gestores SaaS podem trocar de tenant.")
        source = await self._get_user(actor.tenant_id, actor.user_id)
        tenant = await self._get_tenant(payload.tenant_id)
        current_session = await self.repository.get_session(actor.session_id)
        if current_session is not None:
            await self.repository.revoke_session(current_session)
        await self.repository.set_tenant_context(tenant.id)
        user = await self.repository.support_user_for_tenant(source, tenant.id)
        profiles = await self.repository.profiles_for_user(user.id)
        permissions = await self.repository.permissions_for_user(user.id)
        access_expires_at = access_token_expiration(self.settings)
        session_expires_at = refresh_token_expiration(self.settings)
        user_session = await self.repository.create_session(
            tenant_id=tenant.id,
            user_id=user.id,
            login_origin=actor.login_origin,
            expires_at=session_expires_at,
            device=payload.dispositivo,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        token = create_access_token(
            settings=self.settings,
            user_id=user.id,
            tenant_id=tenant.id,
            session_id=user_session.id,
            profiles=[profile.codigo for profile in profiles],
            permissions=[permission.codigo for permission in permissions],
            login_origin=user_session.origem_login,
            expires_at=access_expires_at,
        )
        refresh_token = create_refresh_token(
            settings=self.settings,
            user_id=user.id,
            tenant_id=tenant.id,
            session_id=user_session.id,
            login_origin=user_session.origem_login,
            expires_at=session_expires_at,
        )
        user_session.token_hash = token_digest(token)
        user_session.refresh_token_hash = token_digest(refresh_token)
        await self.repository.commit()
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_minutes * 60,
            usuario=_user_response(user, profiles, permissions, tenant),
        )

    async def _validate_profile_assignment(
        self, actor: RequestActor, profile_ids: list[int]
    ) -> None:
        profiles = await self.repository.available_profiles(actor.tenant_id, profile_ids)
        if any(profile.codigo == "gestor_saas" for profile in profiles):
            raise AuthorizationError(
                "O perfil gestor_saas pertence a identidade global da plataforma e nao pode "
                "ser atribuido a usuarios de tenants."
            )

    async def get_territorial_access(
        self, actor: RequestActor, user_id: int
    ) -> list[TerritorialAccessResponse]:
        await self._get_manageable_user(actor, user_id)
        return [
            TerritorialAccessResponse.model_validate(policy)
            for policy in await self.repository.territorial_access_for_user(
                actor.tenant_id, user_id
            )
        ]

    async def replace_territorial_access(
        self,
        actor: RequestActor,
        user_id: int,
        accesses: list[TerritorialAccessInput],
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> list[TerritorialAccessResponse]:
        await self._get_manageable_user(actor, user_id)
        before = [
            TerritorialAccessResponse.model_validate(item).model_dump(mode="json")
            for item in await self.repository.territorial_access_for_user(actor.tenant_id, user_id)
        ]
        policies = await self.repository.replace_territorial_access(
            actor.tenant_id, user_id, accesses
        )
        after = [
            TerritorialAccessResponse.model_validate(item).model_dump(mode="json")
            for item in policies
        ]
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="auth",
            table_name="politica_acesso_territorial",
            record_id=user_id,
            before={"acessos": before},
            after={"acessos": after},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return [TerritorialAccessResponse.model_validate(item) for item in policies]

    async def _get_user(self, tenant_id: int, user_id: int) -> User:
        user = await self.repository.get_user(tenant_id, user_id)
        if user is None:
            raise ResourceNotFoundError("Usuario", user_id)
        return user

    async def _get_manageable_user(self, actor: RequestActor, user_id: int) -> User:
        user = await self._get_user(actor.tenant_id, user_id)
        if user.usuario_plataforma_id is not None and "gestor_saas" not in actor.profiles:
            raise ResourceNotFoundError("Usuario", user_id)
        return user

    @staticmethod
    def _require_manager_profile(actor: RequestActor) -> None:
        if not {"gestor", "gestor_saas"} & set(actor.profiles):
            raise AuthorizationError("MFA opcional esta disponivel apenas para gestores.")

    async def _get_tenant(self, tenant_id: int) -> Tenant:
        tenant = await self.repository.resolve_tenant_for_login_by_id(tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", tenant_id)
        return tenant

    async def _response(self, user: User, tenant: Tenant | None = None) -> UserResponse:
        profiles = await self.repository.profiles_for_user(user.id)
        permissions = await self.repository.permissions_for_user(user.id)
        response = _user_response(
            user,
            profiles,
            permissions,
            tenant or await self._get_tenant(user.tenant_id),
        )
        response.acessos_territoriais = [
            TerritorialAccessResponse.model_validate(policy)
            for policy in await self.repository.territorial_access_for_user(user.tenant_id, user.id)
        ]
        return response


def _user_response(
    user: User,
    profiles: list[AccessProfile],
    permissions: list[Permission],
    tenant: Tenant,
) -> UserResponse:
    user_data = UserData.model_validate(user)
    return UserResponse(
        **user_data.model_dump(),
        tenant=TenantResponse.model_validate(tenant),
        perfis=[ProfileResponse.model_validate(profile) for profile in profiles],
        permissoes=[permission.codigo for permission in permissions],
    )


def _user_snapshot(user: User, profiles: list[AccessProfile] | None = None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "nome": user.nome,
        "email": user.email,
        "telefone": user.telefone,
        "pessoa_id": user.pessoa_id,
        "lideranca_id": user.lideranca_id,
        "habilitado_app_lider": user.habilitado_app_lider,
        "status": user.status,
        "deve_alterar_senha": user.deve_alterar_senha,
    }
    if profiles is not None:
        snapshot["perfis"] = [profile.codigo for profile in profiles]
    return snapshot
