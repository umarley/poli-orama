import argparse
import asyncio
import getpass

from app.audit.service import AuditService
from app.auth.repository import AuthRepository
from app.auth.schemas import UserCreate
from app.auth.security import hash_password, validate_password_policy
from app.core.config import get_settings
from app.core.database import async_session_factory, dispose_database
from app.core.errors import AppError


async def bootstrap_admin(
    *, tenant_slug: str, name: str, email: str, password: str, profile_code: str
) -> int:
    settings = get_settings()
    validate_password_policy(password, settings)
    async with async_session_factory() as session:
        repository = AuthRepository(session)
        tenant = await repository.resolve_tenant_for_login(tenant_slug)
        if tenant is None:
            raise RuntimeError(f"Tenant '{tenant_slug}' nao encontrado.")
        if await repository.get_user_by_email(tenant.id, email):
            raise RuntimeError("Ja existe um usuario com este e-mail no tenant.")
        profiles = await repository.available_profiles(tenant.id)
        profile = next(
            (candidate for candidate in profiles if candidate.codigo == profile_code),
            None,
        )
        if profile is None:
            raise RuntimeError(f"Perfil '{profile_code}' nao encontrado. Aplique a migration 003.")
        user = await repository.create_user(
            tenant.id,
            UserCreate(
                nome=name,
                email=email,
                senha=password,
                perfil_ids=[profile.id],
            ),
            hash_password(password),
        )
        await AuditService(session).record(
            action="criar",
            tenant_id=tenant.id,
            user_id=user.id,
            schema_name="auth",
            table_name="usuario",
            record_id=user.id,
            after={"bootstrap": True, "perfil": profile.codigo},
        )
        await repository.commit()
        return user.id


async def _run_and_dispose(**kwargs: str) -> int:
    try:
        return await bootstrap_admin(**kwargs)
    finally:
        await dispose_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria o primeiro gestor de um tenant.")
    parser.add_argument("--tenant-slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--profile",
        choices=("gestor", "gestor_saas"),
        default="gestor",
    )
    args = parser.parse_args()
    password = getpass.getpass("Senha inicial: ")
    confirmation = getpass.getpass("Confirme a senha: ")
    if password != confirmation:
        parser.error("As senhas nao conferem.")
    try:
        user_id = asyncio.run(
            _run_and_dispose(
                tenant_slug=args.tenant_slug,
                name=args.name,
                email=args.email,
                password=password,
                profile_code=args.profile,
            )
        )
    except AppError as exc:
        parser.error(exc.message)
    except RuntimeError as exc:
        parser.error(str(exc))
    print(f"Gestor criado com id={user_id}.")


if __name__ == "__main__":
    main()
