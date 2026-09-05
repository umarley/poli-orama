import hmac
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import AuthRepository
from app.auth.security import (
    decode_access_token,
    is_api_key_token,
    session_is_inactive,
    token_digest,
)
from app.core.config import get_settings
from app.core.database import get_session
from app.core.errors import (
    AuthenticationError,
    AuthorizationError,
    PasswordChangeRequiredError,
    TenantInactiveError,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_PASSWORD_CHANGE_ALLOWED_PATH_SUFFIXES = (
    "/auth/change-password",
    "/auth/logout",
    "/auth/me",
)
_API_KEY_ALLOWED_PATH_SUFFIXES = ("/cadastro/pessoas",)
_INTEGRATION_PERMISSIONS = frozenset({"cadastro.criar"})


@dataclass(frozen=True, slots=True)
class RequestActor:
    tenant_id: int
    user_id: int
    session_id: int
    profiles: tuple[str, ...]
    permissions: frozenset[str]
    token: str
    pessoa_id: int | None = None
    lideranca_id: int | None = None
    habilitado_app_lider: bool = False
    login_origin: str = "web"

    @property
    def role(self) -> str:
        return self.profiles[0] if self.profiles else "usuario"

    @property
    def is_mobile_leader_session(self) -> bool:
        return self.login_origin == "app_lider"

    @property
    def is_integration_session(self) -> bool:
        return self.login_origin == "integracao"


@dataclass(frozen=True, slots=True)
class TerritorialAccess:
    unrestricted: bool
    scopes: frozenset[tuple[str, int | None, bool]]

    def can_access(
        self, scope_type: str, scope_id: int | None, *, administer: bool = False
    ) -> bool:
        if self.unrestricted:
            return True
        for current_type, current_id, can_administer in self.scopes:
            if current_type == "global" and (not administer or can_administer):
                return True
            if (
                current_type == scope_type
                and current_id == scope_id
                and (not administer or can_administer)
            ):
                return True
        return False


def _is_api_key_allowed_path(request: Request) -> bool:
    if request.method != "POST":
        return False
    path = request.url.path.rstrip("/")
    return any(path.endswith(suffix) for suffix in _API_KEY_ALLOWED_PATH_SUFFIXES)


async def _authenticate_api_key(
    request: Request,
    repository: AuthRepository,
    token: str,
) -> RequestActor:
    if not _is_api_key_allowed_path(request):
        raise AuthorizationError(
            "Token de integracao autorizado apenas para cadastro de pessoas."
        )
    api_key = await repository.get_active_api_key_by_hash(token_digest(token))
    if api_key is None or not hmac.compare_digest(api_key.token_api, token_digest(token)):
        raise AuthenticationError("Token de integracao invalido ou revogado.")

    await repository.set_tenant_context(api_key.tenant_id)
    tenant = await repository.resolve_tenant_for_login_by_id(api_key.tenant_id)
    if tenant is None:
        raise AuthenticationError("Tenant da chave de integracao nao foi encontrado.")
    if tenant.status not in {"ativo", "trial"}:
        raise TenantInactiveError(tenant.status)

    settings = get_settings()
    now = datetime.now(UTC)
    if (
        api_key.ultimo_uso_em is None
        or api_key.ultimo_uso_em + timedelta(seconds=settings.session_touch_interval_seconds)
        <= now
    ):
        await repository.touch_api_key(api_key, now)
        await repository.commit()
        await repository.set_tenant_context(api_key.tenant_id)

    return RequestActor(
        tenant_id=api_key.tenant_id,
        user_id=api_key.criado_por,
        session_id=0,
        profiles=("integracao",),
        permissions=_INTEGRATION_PERMISSIONS,
        token=token,
        login_origin="integracao",
    )


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> RequestActor:
    if not token:
        raise AuthenticationError()
    if is_api_key_token(token):
        return await _authenticate_api_key(request, AuthRepository(session), token)
    settings = get_settings()
    claims = decode_access_token(token, settings)
    repository = AuthRepository(session)
    tenant_id = int(claims["tenant_id"])
    user_id = int(claims["sub"])
    session_id = int(claims["sid"])
    login_origin = str(claims["origem_login"])

    await repository.set_tenant_context(tenant_id)
    tenant = await repository.resolve_tenant_for_login_by_id(tenant_id)
    if tenant is None:
        raise AuthenticationError("Tenant da sessao nao foi encontrado.")
    user = await repository.get_user(tenant_id, user_id)
    user_session = await repository.get_session(session_id)
    now = datetime.now(UTC)
    if (
        user is None
        or user.status != "ativo"
        or user_session is None
        or user_session.usuario_id != user_id
        or user_session.tenant_id != tenant_id
        or user_session.origem_login != login_origin
        or user_session.revogada_em is not None
        or user_session.expira_em <= now
        or not hmac.compare_digest(user_session.token_hash, token_digest(token))
    ):
        raise AuthenticationError("Sessao invalida ou revogada.")
    if session_is_inactive(user_session.ultimo_uso_em, now, settings):
        await repository.revoke_session(user_session)
        await repository.commit()
        raise AuthenticationError("Sessao expirada por inatividade.")
    if (
        user_session.ultimo_uso_em + timedelta(seconds=settings.session_touch_interval_seconds)
        <= now
    ):
        await repository.touch_session(user_session, now)
        await repository.commit()
        await repository.set_tenant_context(tenant_id)

    if user.deve_alterar_senha:
        path = request.url.path.rstrip("/")
        if not any(path.endswith(suffix) for suffix in _PASSWORD_CHANGE_ALLOWED_PATH_SUFFIXES):
            raise PasswordChangeRequiredError()

    profiles = tuple(profile.codigo for profile in await repository.profiles_for_user(user_id))
    if tenant.status not in {"ativo", "trial"} and "gestor_saas" not in profiles:
        raise TenantInactiveError(tenant.status)
    permissions = frozenset(
        permission.codigo for permission in await repository.permissions_for_user(user_id)
    )
    return RequestActor(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        profiles=profiles,
        permissions=permissions,
        token=token,
        pessoa_id=user.pessoa_id,
        lideranca_id=user.lideranca_id,
        habilitado_app_lider=user.habilitado_app_lider,
        login_origin=login_origin,
    )


async def get_db_session(
    _: Annotated[RequestActor, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[AsyncSession]:
    """Entrega a sessao depois de validar o JWT e definir o tenant para o RLS."""
    yield session


async def get_territorial_access(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TerritorialAccess:
    if {"gestor", "gestor_saas"} & set(actor.profiles):
        return TerritorialAccess(unrestricted=True, scopes=frozenset())
    policies = await AuthRepository(session).territorial_access_for_user(
        actor.tenant_id, actor.user_id
    )
    scope_fields = {
        "estado": "codigo_uf_ibge",
        "municipio": "codigo_municipio_ibge",
        "bairro": "bairro_id",
        "zona_eleitoral": "zona_eleitoral_id",
        "secao_eleitoral": "secao_eleitoral_id",
        "territorio": "territorio_id",
    }
    return TerritorialAccess(
        unrestricted=False,
        scopes=frozenset(
            (
                policy.tipo_escopo,
                (
                    getattr(policy, scope_fields[policy.tipo_escopo])
                    if policy.tipo_escopo in scope_fields
                    else None
                ),
                policy.pode_administrar,
            )
            for policy in policies
        ),
    )


def require_permission(module: str, action: str) -> Callable[..., Awaitable[RequestActor]]:
    permission_code = f"{module}.{action}"

    async def dependency(
        actor: Annotated[RequestActor, Depends(get_current_user)],
    ) -> RequestActor:
        if permission_code not in actor.permissions:
            raise AuthorizationError(f"Permissao obrigatoria: {permission_code}.")
        return actor

    return dependency


def require_any_profile(*profiles: str) -> Callable[..., Awaitable[RequestActor]]:
    allowed = frozenset(profiles)

    async def dependency(
        actor: Annotated[RequestActor, Depends(get_current_user)],
    ) -> RequestActor:
        if not allowed.intersection(actor.profiles):
            raise AuthorizationError(
                f"Perfil obrigatorio: {', '.join(sorted(allowed))}."
            )
        return actor

    return dependency


async def require_tenant_admin(
    actor: Annotated[RequestActor, Depends(get_current_user)],
) -> RequestActor:
    if "configuracoes.administrar" not in actor.permissions:
        raise AuthorizationError()
    return actor


async def require_saas_admin(
    actor: Annotated[RequestActor, Depends(get_current_user)],
) -> int:
    if "gestor_saas" not in actor.profiles:
        raise AuthorizationError("Apenas gestores SaaS podem administrar tenants.")
    return actor.user_id
