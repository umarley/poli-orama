from app.audit.service import AuditService
from app.auth.models import ApiKey
from app.auth.repository import AuthRepository
from app.auth.schemas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from app.auth.security import generate_api_key, token_digest
from app.core.errors import BusinessRuleError, ResourceNotFoundError
from app.core.pagination import ListParams, Page
from app.tenants.models import Tenant


class ApiKeyService:
    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository
        self.audit = AuditService(repository.session)

    async def list(
        self, params: ListParams, tenant_id: int | None = None
    ) -> Page[ApiKeyResponse]:
        rows, total = await self.repository.list_api_keys(params, tenant_id)
        items = [_to_response(api_key, tenant) for api_key, tenant in rows]
        return Page[ApiKeyResponse].create(items, total, params)

    async def create(
        self,
        payload: ApiKeyCreate,
        created_by: int,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ApiKeyCreatedResponse:
        tenant = await self.repository.resolve_tenant_for_login_by_id(payload.tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", payload.tenant_id)
        if tenant.status not in {"ativo", "trial"}:
            raise BusinessRuleError(
                "So e possivel emitir chave para tenant ativo ou em trial.",
                code="tenant_inactive",
                details={"tenant_status": tenant.status},
            )
        plaintext = generate_api_key()
        api_key = await self.repository.create_api_key(
            tenant_id=payload.tenant_id,
            nome=payload.nome,
            token_hash=token_digest(plaintext),
            token_prefix=plaintext[:12],
            created_by=created_by,
        )
        await self.audit.record(
            action="criar",
            tenant_id=tenant.id,
            user_id=created_by,
            schema_name="auth",
            table_name="api_key",
            record_id=api_key.id,
            after={"nome": api_key.nome, "token_prefix": api_key.token_prefix},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        response = _to_response(api_key, tenant)
        return ApiKeyCreatedResponse(**response.model_dump(), token=plaintext)

    async def revoke(
        self,
        api_key_id: int,
        actor_id: int,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ApiKeyResponse:
        api_key = await self.repository.get_api_key(api_key_id)
        if api_key is None:
            raise ResourceNotFoundError("Chave de integracao", api_key_id)
        tenant = await self.repository.resolve_tenant_for_login_by_id(api_key.tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", api_key.tenant_id)
        if api_key.revogada_em is not None:
            raise BusinessRuleError(
                "Esta chave de integracao ja foi revogada.",
                code="api_key_already_revoked",
            )
        before = {"ativo": api_key.ativo, "revogada_em": None}
        await self.repository.revoke_api_key(api_key)
        await self.audit.record(
            action="editar",
            tenant_id=api_key.tenant_id,
            user_id=actor_id,
            schema_name="auth",
            table_name="api_key",
            record_id=api_key.id,
            before=before,
            after={"ativo": False, "revogada_em": api_key.revogada_em.isoformat()},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return _to_response(api_key, tenant)


def _to_response(api_key: ApiKey, tenant: Tenant) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=api_key.id,
        uuid_publico=api_key.uuid_publico,
        tenant_id=api_key.tenant_id,
        tenant_nome=tenant.nome,
        tenant_slug=tenant.slug,
        nome=api_key.nome,
        token_prefix=api_key.token_prefix,
        ativo=api_key.ativo,
        ultimo_uso_em=api_key.ultimo_uso_em,
        revogada_em=api_key.revogada_em,
        criado_por=api_key.criado_por,
        criado_em=api_key.criado_em,
        atualizado_em=api_key.atualizado_em,
    )
