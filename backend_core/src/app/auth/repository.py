from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError

from app.auth.models import (
    AccessProfile,
    Permission,
    ProfilePermission,
    TerritorialAccessPolicy,
    User,
    UserProfile,
    UserSession,
)
from app.auth.schemas import TerritorialAccessInput, UserCreate, UserUpdate
from app.core.errors import BusinessRuleError
from app.core.pagination import ListParams, SortDirection
from app.core.repository import BaseRepository
from app.tenants.models import Tenant


class AuthRepository(BaseRepository[User]):
    sortable_columns = {
        "id": User.id,
        "nome": User.nome,
        "email": User.email,
        "status": User.status,
        "criado_em": User.criado_em,
    }

    async def resolve_tenant_for_login(self, slug: str) -> Tenant | None:
        tenant: Tenant | None = await self.session.scalar(
            select(Tenant).where(Tenant.slug == slug, Tenant.excluido_em.is_(None))
        )
        if tenant is not None:
            await self.set_tenant_context(tenant.id)
        return tenant

    async def resolve_tenant_for_login_by_id(self, tenant_id: int) -> Tenant | None:
        tenant: Tenant | None = await self.session.scalar(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.excluido_em.is_(None))
        )
        return tenant

    async def set_tenant_context(self, tenant_id: int) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

    async def get_user_by_email(self, tenant_id: int, email: str) -> User | None:
        user: User | None = await self.session.scalar(
            select(User).where(
                User.tenant_id == tenant_id,
                func.lower(User.email) == email.lower(),
                User.excluido_em.is_(None),
            )
        )
        return user

    async def get_user(self, tenant_id: int, user_id: int) -> User | None:
        user: User | None = await self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.excluido_em.is_(None),
            )
        )
        return user

    async def list_users(
        self, tenant_id: int, params: ListParams, status: str | None
    ) -> tuple[list[User], int]:
        order_column = self.sortable_columns.get(params.order_by)
        if order_column is None:
            raise BusinessRuleError(
                "Campo de ordenacao nao permitido.",
                code="invalid_order_field",
                details={"allowed": sorted(self.sortable_columns)},
            )
        statement = select(User).where(User.tenant_id == tenant_id, User.excluido_em.is_(None))
        if status:
            statement = statement.where(User.status == status)
        if params.query:
            term = f"%{params.query}%"
            statement = statement.where(or_(User.nome.ilike(term), User.email.ilike(term)))
        total = int(
            (await self.session.scalar(select(func.count()).select_from(statement.subquery()))) or 0
        )
        order = (
            order_column.desc() if params.direction == SortDirection.DESC else order_column.asc()
        )
        users = await self.session.scalars(
            statement.order_by(order).offset(params.offset).limit(params.page_size)
        )
        return list(users.all()), total

    async def profiles_for_user(self, user_id: int) -> list[AccessProfile]:
        profiles = await self.session.scalars(
            select(AccessProfile)
            .join(UserProfile, UserProfile.perfil_acesso_id == AccessProfile.id)
            .where(UserProfile.usuario_id == user_id)
            .order_by(AccessProfile.nivel, AccessProfile.codigo)
        )
        return list(profiles.all())

    async def permissions_for_user(self, user_id: int) -> list[Permission]:
        permissions = await self.session.scalars(
            select(Permission)
            .join(ProfilePermission, ProfilePermission.permissao_id == Permission.id)
            .join(
                UserProfile,
                UserProfile.perfil_acesso_id == ProfilePermission.perfil_acesso_id,
            )
            .where(UserProfile.usuario_id == user_id)
            .distinct()
            .order_by(Permission.codigo)
        )
        return list(permissions.all())

    async def permissions_for_profile(self, profile_id: int) -> list[Permission]:
        permissions = await self.session.scalars(
            select(Permission)
            .join(ProfilePermission, ProfilePermission.permissao_id == Permission.id)
            .where(ProfilePermission.perfil_acesso_id == profile_id)
            .order_by(Permission.modulo, Permission.acao)
        )
        return list(permissions.all())

    async def territorial_access_for_user(
        self, tenant_id: int, user_id: int
    ) -> list[TerritorialAccessPolicy]:
        policies = await self.session.scalars(
            select(TerritorialAccessPolicy)
            .where(
                TerritorialAccessPolicy.tenant_id == tenant_id,
                TerritorialAccessPolicy.usuario_id == user_id,
            )
            .order_by(
                TerritorialAccessPolicy.tipo_escopo,
                TerritorialAccessPolicy.id,
            )
        )
        return list(policies.all())

    async def replace_territorial_access(
        self,
        tenant_id: int,
        user_id: int,
        accesses: list[TerritorialAccessInput],
    ) -> list[TerritorialAccessPolicy]:
        for access in accesses:
            await self._validate_territorial_reference(tenant_id, access)
        await self.session.execute(
            delete(TerritorialAccessPolicy).where(
                TerritorialAccessPolicy.tenant_id == tenant_id,
                TerritorialAccessPolicy.usuario_id == user_id,
            )
        )
        now = datetime.now(UTC)
        policies = [
            TerritorialAccessPolicy(
                tenant_id=tenant_id,
                usuario_id=user_id,
                criado_em=now,
                **access.model_dump(),
            )
            for access in accesses
        ]
        self.session.add_all(policies)
        await self.session.flush()
        return policies

    async def _validate_territorial_reference(
        self, tenant_id: int, access: TerritorialAccessInput
    ) -> None:
        references = {
            "estado": ("global.estado", "codigo_uf_ibge", "codigo_ibge"),
            "municipio": ("global.municipio", "codigo_municipio_ibge", "codigo_ibge"),
            "bairro": ("global.bairro", "bairro_id"),
            "zona_eleitoral": ("global.zona_eleitoral", "zona_eleitoral_id"),
            "secao_eleitoral": ("global.secao_eleitoral", "secao_eleitoral_id"),
            "territorio": ("territorio.territorio", "territorio_id"),
        }
        reference = references.get(access.tipo_escopo)
        if reference is None:
            return
        table_name, field_name, *column_name = reference
        identifier = getattr(access, field_name)
        id_column = column_name[0] if column_name else "id"
        tenant_filter = " AND tenant_id = :tenant_id" if access.tipo_escopo == "territorio" else ""
        found = await self.session.scalar(
            text(f"SELECT {id_column} FROM {table_name} WHERE {id_column} = :id{tenant_filter}"),
            {"id": identifier, "tenant_id": tenant_id},
        )
        if found is None:
            raise BusinessRuleError(
                "Referencia territorial nao encontrada no escopo do tenant.",
                code="invalid_territorial_scope",
                details={"tipo_escopo": access.tipo_escopo, "id": identifier},
            )

    async def available_profiles(
        self, tenant_id: int, profile_ids: list[int] | None = None
    ) -> list[AccessProfile]:
        statement = select(AccessProfile).where(
            or_(AccessProfile.tenant_id.is_(None), AccessProfile.tenant_id == tenant_id)
        )
        if profile_ids is not None:
            statement = statement.where(AccessProfile.id.in_(profile_ids))
        profiles = await self.session.scalars(statement.order_by(AccessProfile.nivel))
        return list(profiles.all())

    async def support_user_for_tenant(
        self, source: User, tenant_id: int
    ) -> User:
        root_id = source.usuario_plataforma_id or source.id
        existing: User | None = await self.session.scalar(
            select(User).where(
                User.tenant_id == tenant_id,
                or_(User.id == root_id, User.usuario_plataforma_id == root_id),
                User.excluido_em.is_(None),
            )
        )
        if existing is not None:
            return existing
        support_profile: AccessProfile | None = await self.session.scalar(
            select(AccessProfile).where(
                AccessProfile.codigo == "gestor_saas",
                AccessProfile.tenant_id.is_(None),
            )
        )
        if support_profile is None:
            raise BusinessRuleError("Perfil gestor_saas nao configurado.")
        email = source.email
        email_in_use = await self.session.scalar(
            select(User.id).where(
                User.tenant_id == tenant_id,
                func.lower(User.email) == email.lower(),
                User.excluido_em.is_(None),
            )
        )
        if email_in_use is not None:
            local, separator, domain = email.partition("@")
            if separator:
                suffix = f"+saas-{root_id}"
                local = local[: 253 - len(domain) - len(suffix)]
                email = f"{local}{suffix}@{domain}"
            else:
                email = f"saas-{root_id}@suporte.plataforma.local"
        now = datetime.now(UTC)
        user = User(
            uuid_publico=uuid4(),
            tenant_id=tenant_id,
            usuario_plataforma_id=root_id,
            pessoa_id=None,
            nome=source.nome,
            email=email,
            hash_senha=source.hash_senha,
            telefone=source.telefone,
            mfa_habilitado=source.mfa_habilitado,
            mfa_segredo=source.mfa_segredo,
            status="ativo",
            tentativas_login=0,
            senha_alterada_em=source.senha_alterada_em,
            deve_alterar_senha=False,
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(user)
        await self.session.flush()
        self.session.add(
            UserProfile(
                usuario_id=user.id,
                perfil_acesso_id=support_profile.id,
                tenant_id=tenant_id,
                atribuido_em=now,
            )
        )
        await self.session.flush()
        return user

    async def create_user(self, tenant_id: int, payload: UserCreate, password_hash: str) -> User:
        now = datetime.now(UTC)
        user = User(
            uuid_publico=uuid4(),
            tenant_id=tenant_id,
            pessoa_id=payload.pessoa_id,
            nome=payload.nome,
            email=payload.email,
            hash_senha=password_hash,
            telefone=payload.telefone,
            mfa_habilitado=False,
            status="ativo",
            tentativas_login=0,
            senha_alterada_em=now,
            deve_alterar_senha=False,
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(user)
        await self.session.flush()
        await self.replace_profiles(user.id, tenant_id, payload.perfil_ids)
        return user

    async def update_user(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True, exclude={"perfil_ids"})
        for field, value in data.items():
            setattr(user, field, value)
        user.atualizado_em = datetime.now(UTC)
        if payload.perfil_ids is not None:
            await self.replace_profiles(user.id, user.tenant_id, payload.perfil_ids)
        await self.session.flush()
        return user

    async def delete_user(self, user: User) -> None:
        now = datetime.now(UTC)
        user.status = "inativo"
        user.excluido_em = now
        user.atualizado_em = now
        await self.revoke_all_user_sessions(user.id)
        await self.session.flush()

    async def replace_profiles(self, user_id: int, tenant_id: int, profile_ids: list[int]) -> None:
        unique_ids = sorted(set(profile_ids))
        profiles = await self.available_profiles(tenant_id, unique_ids)
        if len(profiles) != len(unique_ids):
            raise BusinessRuleError(
                "Um ou mais perfis nao pertencem ao tenant.",
                code="invalid_access_profile",
            )
        await self.session.execute(delete(UserProfile).where(UserProfile.usuario_id == user_id))
        now = datetime.now(UTC)
        self.session.add_all(
            [
                UserProfile(
                    usuario_id=user_id,
                    perfil_acesso_id=profile_id,
                    tenant_id=tenant_id,
                    atribuido_em=now,
                )
                for profile_id in unique_ids
            ]
        )
        await self.session.flush()

    async def create_session(
        self,
        *,
        tenant_id: int,
        user_id: int,
        expires_at: datetime,
        device: str | None,
        user_agent: str | None,
        ip_address: str | None,
    ) -> UserSession:
        session = UserSession(
            tenant_id=tenant_id,
            usuario_id=user_id,
            token_hash=f"pending:{uuid4()}",
            dispositivo=device,
            user_agent=user_agent,
            ip_origem=ip_address,
            criado_em=datetime.now(UTC),
            ultimo_uso_em=datetime.now(UTC),
            expira_em=expires_at,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def rotate_session_tokens(
        self,
        session: UserSession,
        *,
        access_token_hash: str,
        refresh_token_hash: str,
    ) -> None:
        session.token_hash = access_token_hash
        session.refresh_token_hash = refresh_token_hash
        await self.session.flush()

    async def get_session(self, session_id: int) -> UserSession | None:
        return await self.session.get(UserSession, session_id)

    async def revoke_session(self, session: UserSession) -> None:
        session.revogada_em = datetime.now(UTC)
        await self.session.flush()

    async def list_user_sessions(
        self, tenant_id: int, user_id: int, *, limit: int = 100
    ) -> list[UserSession]:
        sessions = await self.session.scalars(
            select(UserSession)
            .where(
                UserSession.tenant_id == tenant_id,
                UserSession.usuario_id == user_id,
            )
            .order_by(UserSession.criado_em.desc())
            .limit(limit)
        )
        return list(sessions.all())

    async def get_user_session(
        self, tenant_id: int, user_id: int, session_id: int
    ) -> UserSession | None:
        user_session: UserSession | None = await self.session.scalar(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.tenant_id == tenant_id,
                UserSession.usuario_id == user_id,
            )
        )
        return user_session

    async def revoke_other_user_sessions(self, user_id: int, current_session_id: int) -> None:
        await self.session.execute(
            update(UserSession)
            .where(
                UserSession.usuario_id == user_id,
                UserSession.id != current_session_id,
                UserSession.revogada_em.is_(None),
            )
            .values(revogada_em=datetime.now(UTC))
        )

    async def touch_session(self, session: UserSession, now: datetime) -> None:
        session.ultimo_uso_em = now
        await self.session.flush()

    async def revoke_all_user_sessions(self, user_id: int) -> None:
        await self.session.execute(
            update(UserSession)
            .where(UserSession.usuario_id == user_id, UserSession.revogada_em.is_(None))
            .values(revogada_em=datetime.now(UTC))
        )

    async def register_login_success(self, user: User) -> None:
        user.ultimo_login_em = datetime.now(UTC)
        user.tentativas_login = 0
        await self.session.flush()

    async def register_login_failure(self, user: User) -> None:
        user.tentativas_login = min(user.tentativas_login + 1, 32767)
        if user.tentativas_login >= 5:
            user.status = "bloqueado"
        await self.session.flush()

    async def set_password(self, user: User, password_hash: str, *, must_change: bool) -> None:
        user.hash_senha = password_hash
        user.senha_alterada_em = datetime.now(UTC)
        user.deve_alterar_senha = must_change
        user.tentativas_login = 0
        if user.status == "bloqueado":
            user.status = "ativo"
        user.atualizado_em = datetime.now(UTC)
        await self.revoke_all_user_sessions(user.id)
        await self.session.flush()

    async def set_mfa_secret(self, user: User, encrypted_secret: str) -> None:
        user.mfa_segredo = encrypted_secret
        user.mfa_habilitado = False
        user.atualizado_em = datetime.now(UTC)
        await self.session.flush()

    async def enable_mfa(self, user: User) -> None:
        user.mfa_habilitado = True
        user.atualizado_em = datetime.now(UTC)
        await self.session.flush()

    async def disable_mfa(self, user: User) -> None:
        user.mfa_habilitado = False
        user.mfa_segredo = None
        user.atualizado_em = datetime.now(UTC)
        await self.session.flush()

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if "uq_usuario_email_tenant" in str(exc.orig):
                raise BusinessRuleError(
                    "Ja existe um usuario com este e-mail no tenant.",
                    code="user_email_already_exists",
                ) from exc
            raise
