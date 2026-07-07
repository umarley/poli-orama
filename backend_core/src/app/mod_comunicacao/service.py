from typing import Any

from app.audit.service import AuditService
from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_comunicacao.repository import ComunicacaoRepository
from app.mod_comunicacao.schemas import CatalogInput, CatalogUpdate, InteracaoInput
from app.mod_territorio.repository import TerritorioRepository


class ComunicacaoService:
    def __init__(self, repository: ComunicacaoRepository) -> None:
        self.repository = repository
        self.territories = TerritorioRepository(repository.session)
        self.audit = AuditService(repository.session)

    async def accessible_ids(
        self, actor: RequestActor, access: TerritorialAccess
    ) -> set[int] | None:
        return await self.territories.accessible_ids(actor.tenant_id, access)

    async def list_catalog(
        self, actor: RequestActor, catalog: str, include_inactive: bool
    ) -> list[dict[str, Any]]:
        return await self.repository.list_catalog(catalog, actor.tenant_id, include_inactive)

    async def create_catalog(
        self, actor: RequestActor, catalog: str, payload: CatalogInput
    ) -> dict[str, Any]:
        item = await self.repository.create_catalog(catalog, actor.tenant_id, payload)
        await self.repository.commit()
        return item

    async def update_catalog(
        self, actor: RequestActor, catalog: str, item_id: int, payload: CatalogUpdate
    ) -> dict[str, Any]:
        item = await self.repository.update_catalog(catalog, actor.tenant_id, item_id, payload)
        if item is None:
            raise ResourceNotFoundError("Catalogo de comunicacao", item_id)
        await self.repository.commit()
        return item

    async def list_person_interactions(
        self, actor: RequestActor, access: TerritorialAccess, person_id: int, limit: int
    ) -> list[dict[str, Any]]:
        accessible = await self.accessible_ids(actor, access)
        if not await self.repository.person_in_scope(actor.tenant_id, person_id, accessible):
            raise AuthorizationError("Pessoa fora do escopo territorial permitido.")
        return await self.repository.list_person_interactions(actor.tenant_id, person_id, limit)

    async def create_person_interaction(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        person_id: int,
        payload: InteracaoInput,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        accessible = await self.accessible_ids(actor, access)
        if not await self.repository.person_in_scope(actor.tenant_id, person_id, accessible):
            raise AuthorizationError("Pessoa fora do escopo territorial permitido.")
        if payload.tipo_interacao_id and not await self.repository.catalog_item_exists(
            "tipos-interacao", actor.tenant_id, payload.tipo_interacao_id
        ):
            raise BusinessRuleError("Tipo de interacao invalido ou inativo.")
        if payload.canal_comunicacao_id and not await self.repository.catalog_item_exists(
            "canais", actor.tenant_id, payload.canal_comunicacao_id
        ):
            raise BusinessRuleError("Canal de comunicacao invalido ou inativo.")
        item = await self.repository.create_interaction(
            actor.tenant_id, actor.user_id, person_id, payload
        )
        await self.audit.record(
            action="criar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="comunicacao",
            table_name="interacao",
            record_id=item["id"],
            after={
                "pessoa_id": person_id,
                "tipo_interacao_id": payload.tipo_interacao_id,
                "canal_comunicacao_id": payload.canal_comunicacao_id,
                "direcao": payload.direcao,
                "assunto": payload.assunto,
                "resultado": payload.resultado,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return item
