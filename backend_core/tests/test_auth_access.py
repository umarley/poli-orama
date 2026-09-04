import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.access import RequestActor, get_territorial_access, require_permission
from app.auth.repository import AuthRepository
from app.auth.schemas import UserCreate
from app.auth.service import AuthService
from app.core.config import Settings
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.core.pagination import ListParams


def make_actor(*permissions: str) -> RequestActor:
    return RequestActor(
        tenant_id=1,
        user_id=2,
        session_id=3,
        profiles=("gestor",),
        permissions=frozenset(permissions),
        token="token",
    )


def test_permission_dependency_accepts_effective_permission() -> None:
    dependency = require_permission("usuarios", "editar")

    actor = asyncio.run(dependency(make_actor("usuarios.editar")))

    assert actor.user_id == 2


def test_permission_dependency_rejects_missing_permission() -> None:
    dependency = require_permission("usuarios", "editar")

    with pytest.raises(AuthorizationError):
        asyncio.run(dependency(make_actor("usuarios.visualizar")))


def test_web_actor_with_multiple_profiles_keeps_unrestricted_access() -> None:
    actor = RequestActor(
        tenant_id=2,
        user_id=8,
        session_id=30,
        profiles=("lider", "telefonista", "gestor", "administrativo_rh"),
        permissions=frozenset({"cadastro.visualizar"}),
        token="token",
        habilitado_app_lider=True,
        lideranca_id=5,
        login_origin="web",
    )

    access = asyncio.run(get_territorial_access(actor, None))

    assert access.unrestricted is True
    assert actor.is_mobile_leader_session is False


def saas_actor(*profiles: str) -> RequestActor:
    return RequestActor(
        tenant_id=20,
        user_id=30,
        session_id=40,
        profiles=profiles,
        permissions=frozenset(),
        token="token",
    )


def auth_service(repository: Mock) -> AuthService:
    repository.session = Mock()
    return AuthService(repository, Mock(spec=Settings))


@pytest.mark.asyncio
async def test_tenant_user_cannot_list_gestor_saas_profile() -> None:
    repository = Mock()
    repository.available_profiles = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=1,
                nome="Gestor SaaS",
                codigo="gestor_saas",
                descricao="Plataforma",
                nivel=0,
            ),
            SimpleNamespace(
                id=2,
                nome="Gestor",
                codigo="gestor",
                descricao="Tenant",
                nivel=1,
            ),
        ]
    )
    repository.permissions_for_profile = AsyncMock(return_value=[])

    profiles = await auth_service(repository).list_profiles(saas_actor("gestor"))

    assert [profile.codigo for profile in profiles] == ["gestor"]


@pytest.mark.asyncio
@pytest.mark.parametrize("requester_profile", ["gestor", "gestor_saas"])
async def test_gestor_saas_profile_cannot_be_assigned_to_tenant_user(
    requester_profile: str,
) -> None:
    repository = Mock()
    repository.available_profiles = AsyncMock(
        return_value=[SimpleNamespace(id=1, codigo="gestor_saas")]
    )

    with pytest.raises(AuthorizationError):
        await auth_service(repository)._validate_profile_assignment(
            saas_actor(requester_profile), [1]
        )


@pytest.mark.asyncio
async def test_tenant_user_cannot_open_platform_context_user() -> None:
    repository = Mock()
    repository.get_user = AsyncMock(
        return_value=SimpleNamespace(id=99, usuario_plataforma_id=1)
    )

    with pytest.raises(ResourceNotFoundError):
        await auth_service(repository).get_user(saas_actor("gestor"), 99)


@pytest.mark.asyncio
async def test_platform_context_users_are_excluded_from_tenant_user_list() -> None:
    scalar_result = Mock()
    scalar_result.all.return_value = []
    session = Mock()
    session.scalar = AsyncMock(return_value=0)
    session.scalars = AsyncMock(return_value=scalar_result)
    repository = AuthRepository(session)

    await repository.list_users(20, ListParams(), None)

    count_statement = str(session.scalar.await_args.args[0])
    list_statement = str(session.scalars.await_args.args[0])
    assert "usuario_plataforma_id IS NULL" in count_statement
    assert "usuario_plataforma_id IS NULL" in list_statement


@pytest.mark.asyncio
async def test_platform_context_user_derives_global_saas_profile_without_assignment() -> None:
    profile = SimpleNamespace(id=1, codigo="gestor_saas")
    session = Mock()
    session.get = AsyncMock(
        return_value=SimpleNamespace(id=99, usuario_plataforma_id=1)
    )
    session.scalar = AsyncMock(return_value=profile)
    repository = AuthRepository(session)

    profiles = await repository.profiles_for_user(99)

    assert profiles == [profile]
    session.scalars.assert_not_called()


def _user_create() -> UserCreate:
    return UserCreate(
        nome="Amanda Caroline",
        email="amandazanin90@gmail.com",
        senha="SenhaForte1!",
        perfil_ids=[1],
        lideranca_id=516,
        habilitado_app_lider=True,
    )


@pytest.mark.asyncio
async def test_create_user_rejects_existing_email() -> None:
    session = Mock()
    session.scalar = AsyncMock(return_value=SimpleNamespace(id=9, excluido_em=None))
    repository = AuthRepository(session)

    with pytest.raises(BusinessRuleError) as error:
        await repository.create_user(2, _user_create(), "hash")

    assert error.value.code == "user_email_already_exists"
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_rejects_deleted_email() -> None:
    session = Mock()
    session.scalar = AsyncMock(
        return_value=SimpleNamespace(id=9, excluido_em=datetime.now(UTC))
    )
    repository = AuthRepository(session)

    with pytest.raises(BusinessRuleError) as error:
        await repository.create_user(2, _user_create(), "hash")

    assert error.value.code == "user_email_already_exists"
    assert "excluido" in error.value.message.lower()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_translates_duplicate_email_integrity_error() -> None:
    session = Mock()
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock(
        side_effect=IntegrityError(
            "INSERT INTO auth.usuario",
            {},
            Exception(
                'duplicate key value violates unique constraint "uq_usuario_email_tenant"'
            ),
        )
    )
    session.rollback = AsyncMock()
    repository = AuthRepository(session)

    with pytest.raises(BusinessRuleError) as error:
        await repository.create_user(2, _user_create(), "hash")

    assert error.value.code == "user_email_already_exists"
    session.rollback.assert_awaited_once()
