from ipaddress import ip_address
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    get_current_user,
    get_db_session,
    require_permission,
)
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MfaCodeRequest,
    MfaDisableRequest,
    MfaSetupRequest,
    MfaSetupResponse,
    ProfileResponse,
    RefreshRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SelfProfileUpdate,
    SessionResponse,
    TenantSwitchRequest,
    TerritorialAccessReplace,
    TerritorialAccessResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.auth.service import AuthService
from app.core.config import get_settings
from app.core.database import get_session
from app.core.pagination import ListParams, Page, list_params

router = APIRouter()


def get_public_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    return AuthService(AuthRepository(session), get_settings())


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(AuthRepository(session), get_settings())


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["Autenticacao"],
    summary="Autentica usuario e cria sessao",
)
async def login(
    payload: LoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_public_auth_service)],
) -> TokenResponse:
    return await service.login(
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/auth/login/mobile",
    response_model=TokenResponse,
    tags=["Autenticacao"],
    summary="Autentica lider/coordenador no app mobile",
)
async def login_mobile(
    payload: LoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_public_auth_service)],
) -> TokenResponse:
    mobile_payload = payload.model_copy(update={"app_lider": True})
    return await service.login(
        mobile_payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    tags=["Autenticacao"],
    summary="Rotaciona tokens de uma sessao valida",
)
async def refresh(
    payload: RefreshRequest,
    service: Annotated[AuthService, Depends(get_public_auth_service)],
) -> TokenResponse:
    return await service.refresh(payload.refresh_token)


@router.post(
    "/auth/switch-tenant",
    response_model=TokenResponse,
    tags=["Autenticacao"],
    summary="Troca o tenant de suporte do gestor SaaS",
)
async def switch_tenant(
    payload: TenantSwitchRequest,
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await service.switch_tenant(
        actor,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Autenticacao"],
    summary="Revoga a sessao atual",
)
async def logout(
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.logout(
        actor,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/auth/me",
    response_model=UserResponse,
    tags=["Autenticacao"],
    summary="Retorna identidade e permissoes efetivas",
)
async def me(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    return await service.me(actor)


@router.patch(
    "/auth/me",
    response_model=UserResponse,
    tags=["Autenticacao"],
    summary="Atualiza dados pessoais do usuario atual",
)
async def update_me(
    payload: SelfProfileUpdate,
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    return await service.update_me(
        actor,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/auth/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Autenticacao"],
    summary="Altera a senha do usuario atual",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.change_password(
        actor,
        payload.senha_atual,
        payload.nova_senha,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/mfa/setup",
    response_model=MfaSetupResponse,
    tags=["Autenticacao"],
    summary="Inicia configuracao TOTP para gestor",
)
async def setup_mfa(
    payload: MfaSetupRequest,
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MfaSetupResponse:
    return await service.setup_mfa(
        actor,
        payload.senha,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/auth/mfa/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Autenticacao"],
    summary="Confirma e habilita TOTP",
)
async def confirm_mfa(
    payload: MfaCodeRequest,
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.confirm_mfa(
        actor,
        payload.codigo,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/mfa/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Autenticacao"],
    summary="Desabilita TOTP do gestor",
)
async def disable_mfa(
    payload: MfaDisableRequest,
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.disable_mfa(
        actor,
        payload.senha,
        payload.codigo,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/auth/sessions",
    response_model=list[SessionResponse],
    tags=["Autenticacao"],
    summary="Lista historico de sessoes do usuario",
)
async def list_sessions(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> list[SessionResponse]:
    return await service.list_sessions(actor)


@router.delete(
    "/auth/sessions/{session_id}",
    tags=["Autenticacao"],
    summary="Revoga uma sessao do usuario",
)
async def revoke_session(
    request: Request,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    session_id: int = Path(ge=1),
) -> dict[str, bool]:
    current = await service.revoke_user_session(
        actor,
        session_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return {"current_session": current}


@router.get(
    "/users",
    response_model=Page[UserResponse],
    tags=["Usuarios"],
    summary="Lista usuarios do tenant",
)
async def list_users(
    params: Annotated[ListParams, Depends(list_params)],
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "visualizar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_status: str | None = Query(
        default=None, alias="status", pattern=r"^(ativo|inativo|bloqueado|pendente)$"
    ),
) -> Page[UserResponse]:
    return await service.list_users(actor, params, user_status)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Usuarios"],
    summary="Cria usuario e associa perfis",
)
async def create_user(
    payload: UserCreate,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "criar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    return await service.create_user(
        actor,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/users/profiles",
    response_model=list[ProfileResponse],
    tags=["Usuarios"],
    summary="Lista perfis disponiveis",
)
async def list_profiles(
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "visualizar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> list[ProfileResponse]:
    return await service.list_profiles(actor)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    tags=["Usuarios"],
    summary="Busca usuario do tenant",
)
async def get_user(
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "visualizar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: int = Path(ge=1),
) -> UserResponse:
    return await service.get_user(actor, user_id)


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    tags=["Usuarios"],
    summary="Atualiza usuario e perfis",
)
async def update_user(
    payload: UserUpdate,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "editar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: int = Path(ge=1),
) -> UserResponse:
    return await service.update_user(
        actor,
        user_id,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/users/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
    tags=["Usuarios"],
    summary="Emite senha temporaria e revoga sessoes",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "administrar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: int = Path(ge=1),
) -> ResetPasswordResponse:
    return await service.reset_password(
        actor,
        user_id,
        payload.senha_temporaria,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/users/{user_id}/territorial-access",
    response_model=list[TerritorialAccessResponse],
    tags=["Usuarios"],
    summary="Lista acessos territoriais do usuario",
)
async def get_territorial_access(
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "visualizar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: int = Path(ge=1),
) -> list[TerritorialAccessResponse]:
    return await service.get_territorial_access(actor, user_id)


@router.put(
    "/users/{user_id}/territorial-access",
    response_model=list[TerritorialAccessResponse],
    tags=["Usuarios"],
    summary="Substitui acessos territoriais do usuario",
)
async def replace_territorial_access(
    payload: TerritorialAccessReplace,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "administrar"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: int = Path(ge=1),
) -> list[TerritorialAccessResponse]:
    return await service.replace_territorial_access(
        actor,
        user_id,
        payload.acessos,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Usuarios"],
    summary="Exclui logicamente um usuario e revoga suas sessoes",
)
async def delete_user(
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("usuarios", "excluir"))],
    service: Annotated[AuthService, Depends(get_auth_service)],
    user_id: int = Path(ge=1),
) -> Response:
    await service.delete_user(
        actor,
        user_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    candidate = request.client.host.split("%", 1)[0]
    try:
        return str(ip_address(candidate))
    except ValueError:
        return None
