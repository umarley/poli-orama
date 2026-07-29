"""Regras de negocio do dominio de territorio."""

from __future__ import annotations

from typing import Any

from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_territorio.repository import TerritorioRepository
from app.mod_territorio.schemas import (
    BairroCreate,
    GeocodificacaoInput,
    LiderancaTerritorioInput,
    PessoaTerritorioInput,
    TerritorioCreate,
    TerritorioTreeNode,
    TerritorioUpdate,
    TipoTerritorioCreate,
    TipoTerritorioUpdate,
)


class TerritorioService:
    def __init__(self, repository: TerritorioRepository) -> None:
        self.repository = repository

    async def accessible_ids(
        self, actor: RequestActor, access: TerritorialAccess
    ) -> set[int] | None:
        return await self.repository.accessible_ids(actor.tenant_id, access)

    async def create_neighborhood(self, payload: BairroCreate) -> dict[str, Any]:
        if not await self.repository.reference_exists(
            "municipio", payload.codigo_municipio_ibge
        ):
            raise ResourceNotFoundError("Municipio", payload.codigo_municipio_ibge)
        item = await self.repository.create_neighborhood(payload)
        await self.repository.commit()
        return item

    async def list_territories(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        *,
        include_inactive: bool = False,
        type_id: int | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        ids = await self.accessible_ids(actor, access)
        return await self.repository.list_territories(
            actor.tenant_id,
            include_inactive=include_inactive,
            type_id=type_id,
            query=query,
            accessible_ids=ids,
        )

    async def create_type(
        self, actor: RequestActor, payload: TipoTerritorioCreate
    ) -> dict[str, Any]:
        item = await self.repository.create_type(actor.tenant_id, payload)
        await self.repository.commit()
        return item

    async def update_type(
        self, actor: RequestActor, type_id: int, payload: TipoTerritorioUpdate
    ) -> dict[str, Any]:
        current = await self.repository.get_type(actor.tenant_id, type_id)
        if current is None:
            raise ResourceNotFoundError("Tipo de territorio", type_id)
        if current["tenant_id"] is None:
            raise BusinessRuleError("Tipos globais do sistema nao podem ser alterados.")
        item = await self.repository.update_type(actor.tenant_id, type_id, payload)
        await self.repository.commit()
        assert item is not None
        return item

    async def validate_payload_references(
        self, actor: RequestActor, payload: TerritorioCreate | TerritorioUpdate
    ) -> None:
        type_id = payload.tipo_territorio_id
        if type_id and await self.repository.get_type(actor.tenant_id, type_id) is None:
            raise ResourceNotFoundError("Tipo de territorio", type_id)
        references = {
            "estado": payload.codigo_uf_ibge,
            "municipio": payload.codigo_municipio_ibge,
            "bairro": payload.bairro_id,
            "zona_eleitoral": payload.zona_eleitoral_id,
            "secao_eleitoral": payload.secao_eleitoral_id,
        }
        for table, identifier in references.items():
            if identifier and not await self.repository.reference_exists(table, identifier):
                raise ResourceNotFoundError(table.replace("_", " ").title(), identifier)

    async def ensure_access(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        territory_id: int,
        *,
        administer: bool,
    ) -> dict[str, Any]:
        territory = await self.repository.get_territory(actor.tenant_id, territory_id)
        if territory is None:
            raise ResourceNotFoundError("Territorio", territory_id)
        ids = await self.accessible_ids(actor, access)
        if ids is not None and territory_id not in ids:
            raise AuthorizationError("Territorio fora do escopo permitido.")
        if administer and not access.unrestricted:
            administrative_access = TerritorialAccess(
                unrestricted=False,
                scopes=frozenset(
                    scope for scope in access.scopes if scope[2]
                ),
            )
            administrative_ids = await self.repository.accessible_ids(
                actor.tenant_id, administrative_access
            )
            if administrative_ids is not None and territory_id not in administrative_ids:
                raise AuthorizationError("Administracao territorial nao permitida.")
        return territory

    async def create_territory(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        payload: TerritorioCreate,
    ) -> dict[str, Any]:
        await self.validate_payload_references(actor, payload)
        if payload.territorio_pai_id:
            await self.ensure_access(
                actor, access, payload.territorio_pai_id, administer=True
            )
        elif not access.unrestricted:
            raise AuthorizationError("Apenas gestores podem criar territorios raiz.")
        item = await self.repository.create_territory(actor.tenant_id, payload)
        await self.repository.commit()
        return item

    async def update_territory(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        territory_id: int,
        payload: TerritorioUpdate,
    ) -> dict[str, Any]:
        await self.ensure_access(actor, access, territory_id, administer=True)
        await self.validate_payload_references(actor, payload)
        if payload.territorio_pai_id is not None:
            await self.ensure_access(
                actor, access, payload.territorio_pai_id, administer=True
            )
            if await self.repository.would_create_cycle(
                actor.tenant_id, territory_id, payload.territorio_pai_id
            ):
                raise BusinessRuleError(
                    "A hierarquia territorial nao pode conter ciclos.",
                    code="territory_hierarchy_cycle",
                )
        item = await self.repository.update_territory(
            actor.tenant_id, territory_id, payload
        )
        if item is None:
            raise ResourceNotFoundError("Territorio", territory_id)
        await self.repository.commit()
        return item

    async def tree(
        self, actor: RequestActor, access: TerritorialAccess
    ) -> list[TerritorioTreeNode]:
        rows = await self.list_territories(actor, access, include_inactive=False)
        allowed_fields = set(TerritorioTreeNode.model_fields)
        nodes = {
            row["id"]: TerritorioTreeNode.model_validate(
                {
                    **{key: value for key, value in row.items() if key in allowed_fields},
                    "filhos": [],
                }
            )
            for row in rows
        }
        roots: list[TerritorioTreeNode] = []
        for row in rows:
            node = nodes[row["id"]]
            parent = nodes.get(row["territorio_pai_id"])
            if parent:
                parent.filhos.append(node)
            else:
                roots.append(node)
        return roots

    async def link_person(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        territory_id: int,
        payload: PessoaTerritorioInput,
    ) -> dict[str, Any]:
        await self.ensure_access(actor, access, territory_id, administer=True)
        if not await self.repository.entity_exists("pessoa", actor.tenant_id, payload.pessoa_id):
            raise ResourceNotFoundError("Pessoa", payload.pessoa_id)
        item = await self.repository.link_person(actor.tenant_id, territory_id, payload)
        await self.repository.commit()
        return item

    async def list_person_links(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        person_id: int,
    ) -> list[dict[str, Any]]:
        if not await self.repository.entity_exists("pessoa", actor.tenant_id, person_id):
            raise ResourceNotFoundError("Pessoa", person_id)
        ids = await self.accessible_ids(actor, access)
        return await self.repository.list_person_links(actor.tenant_id, person_id, ids)

    async def unlink_person(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        link_id: int,
    ) -> None:
        item = await self.repository.person_link(actor.tenant_id, link_id)
        if item is None:
            raise ResourceNotFoundError("Vinculo territorial da pessoa", link_id)
        await self.ensure_access(actor, access, item["territorio_id"], administer=True)
        await self.repository.unlink_person(actor.tenant_id, link_id)
        await self.repository.commit()

    async def link_leadership(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        territory_id: int,
        payload: LiderancaTerritorioInput,
    ) -> dict[str, Any]:
        await self.ensure_access(actor, access, territory_id, administer=True)
        if not await self.repository.entity_exists(
            "lideranca", actor.tenant_id, payload.lideranca_id
        ):
            raise ResourceNotFoundError("Lideranca", payload.lideranca_id)
        item = await self.repository.link_leadership(actor.tenant_id, territory_id, payload)
        await self.repository.commit()
        return item

    async def create_geocoding(
        self, actor: RequestActor, payload: GeocodificacaoInput
    ) -> dict[str, Any]:
        item = await self.repository.create_geocoding(actor.tenant_id, payload)
        await self.repository.commit()
        return item
