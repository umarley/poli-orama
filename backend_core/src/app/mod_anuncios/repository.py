"""Persistencia transacional do modulo Anuncios."""

# ruff: noqa: E501 -- consultas SQL declarativas ficam mais legiveis sem quebras artificiais.

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import ListParams
from app.mod_anuncios.schemas import (
    MaterialCreate,
    MaterialUpdate,
    PlanningCreate,
    PlanningUpdate,
    RouteCreate,
    RoutePointInput,
    RouteUpdate,
    TeamInput,
    TeamUpdate,
)


class AnunciosRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_materials(
        self, tenant_id: int, params: ListParams, include_inactive: bool
    ) -> tuple[list[dict[str, Any]], int]:
        clauses = ["tenant_id=:tenant_id"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if not include_inactive:
            clauses.append("ativo")
        if params.query:
            clauses.append("nome ILIKE :query")
            values["query"] = f"%{params.query}%"
        where = " AND ".join(clauses)
        total = int(
            await self.session.scalar(
                text(f"SELECT count(*) FROM anuncio.material_comunicacao WHERE {where}"), values
            )
            or 0
        )
        result = await self.session.execute(
            text(
                "SELECT id,uuid_publico,tenant_id,nome,descricao,ativo,criado_em,atualizado_em "
                f"FROM anuncio.material_comunicacao WHERE {where} "
                "ORDER BY nome LIMIT :limit OFFSET :offset"
            ),
            {**values, "limit": params.page_size, "offset": params.offset},
        )
        return [dict(row) for row in result.mappings()], total

    async def get_material(self, tenant_id: int, material_id: int) -> dict[str, Any] | None:
        row = (
            (
                await self.session.execute(
                    text(
                        "SELECT id,uuid_publico,tenant_id,nome,descricao,ativo,criado_em,atualizado_em "
                        "FROM anuncio.material_comunicacao WHERE tenant_id=:tenant_id AND id=:id"
                    ),
                    {"tenant_id": tenant_id, "id": material_id},
                )
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    async def create_material(
        self, tenant_id: int, user_id: int, payload: MaterialCreate
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO anuncio.material_comunicacao(tenant_id,nome,descricao,criado_por) "
                "VALUES(:tenant_id,:nome,:descricao,:user_id) RETURNING id"
            ),
            {"tenant_id": tenant_id, "user_id": user_id, **payload.model_dump()},
        )
        return await self.get_material(tenant_id, int(result.scalar_one()))  # type: ignore[return-value]

    async def update_material(
        self, tenant_id: int, material_id: int, payload: MaterialUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if values:
            assignments = ",".join(f"{field}=:{field}" for field in values)
            await self.session.execute(
                text(
                    f"UPDATE anuncio.material_comunicacao SET {assignments},atualizado_em=now() "
                    "WHERE tenant_id=:tenant_id AND id=:id"
                ),
                {"tenant_id": tenant_id, "id": material_id, **values},
            )
        return await self.get_material(tenant_id, material_id)

    async def material_is_used(self, tenant_id: int, material_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM anuncio.rota_comunicacao_ponto_material "
                    "WHERE tenant_id=:tenant_id AND material_id=:id)"
                ),
                {"tenant_id": tenant_id, "id": material_id},
            )
        )

    async def list_teams(
        self, tenant_id: int, params: ListParams, include_inactive: bool
    ) -> tuple[list[dict[str, Any]], int]:
        clauses = ["e.tenant_id=:tenant_id"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if not include_inactive:
            clauses.append("e.ativo")
        if params.query:
            clauses.append("e.nome ILIKE :query")
            values["query"] = f"%{params.query}%"
        where = " AND ".join(clauses)
        total = int(
            await self.session.scalar(
                text(f"SELECT count(*) FROM cadastro.equipe e WHERE {where}"), values
            )
            or 0
        )
        rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT e.id,e.uuid_publico,e.tenant_id,e.nome,e.descricao,e.lideranca_id,"
                        "e.territorio_id,e.ativo,e.criado_em,e.atualizado_em "
                        f"FROM cadastro.equipe e WHERE {where} ORDER BY e.nome "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    {**values, "limit": params.page_size, "offset": params.offset},
                )
            )
            .mappings()
            .all()
        )
        items = [dict(row) for row in rows]
        await self._attach_team_members(tenant_id, items)
        return items, total

    async def get_team(self, tenant_id: int, team_id: int) -> dict[str, Any] | None:
        row = (
            (
                await self.session.execute(
                    text(
                        "SELECT id,uuid_publico,tenant_id,nome,descricao,lideranca_id,territorio_id,"
                        "ativo,criado_em,atualizado_em FROM cadastro.equipe "
                        "WHERE tenant_id=:tenant_id AND id=:id"
                    ),
                    {"tenant_id": tenant_id, "id": team_id},
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        item = dict(row)
        await self._attach_team_members(tenant_id, [item])
        return item

    async def _attach_team_members(self, tenant_id: int, teams: list[dict[str, Any]]) -> None:
        if not teams:
            return
        ids = [item["id"] for item in teams]
        statement = text(
            "SELECT ep.equipe_id,u.id AS usuario_id,u.pessoa_id,u.nome,u.email "
            "FROM cadastro.equipe_pessoa ep "
            "JOIN auth.usuario u ON u.tenant_id=ep.tenant_id AND u.pessoa_id=ep.pessoa_id "
            "WHERE ep.tenant_id=:tenant_id AND ep.equipe_id IN :ids ORDER BY u.nome"
        ).bindparams(bindparam("ids", expanding=True))
        rows = (
            (await self.session.execute(statement, {"tenant_id": tenant_id, "ids": ids}))
            .mappings()
            .all()
        )
        grouped: dict[int, list[dict[str, Any]]] = {team_id: [] for team_id in ids}
        for row in rows:
            member = dict(row)
            grouped[int(member.pop("equipe_id"))].append(member)
        for team in teams:
            team["membros"] = grouped[team["id"]]

    async def users_for_team_assignment(
        self, tenant_id: int, user_ids: list[int]
    ) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        statement = text(
            "SELECT id,pessoa_id,nome,email FROM auth.usuario "
            "WHERE tenant_id=:tenant_id AND status='ativo' AND id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        rows = (
            (await self.session.execute(statement, {"tenant_id": tenant_id, "ids": user_ids}))
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    async def create_team(self, tenant_id: int, payload: TeamInput) -> dict[str, Any]:
        team_id = int(
            (
                await self.session.execute(
                    text(
                        "INSERT INTO cadastro.equipe"
                        "(tenant_id,nome,descricao,lideranca_id,territorio_id) "
                        "VALUES(:tenant_id,:nome,:descricao,:lideranca_id,:territorio_id) "
                        "RETURNING id"
                    ),
                    {"tenant_id": tenant_id, **payload.model_dump(exclude={"usuario_ids"})},
                )
            ).scalar_one()
        )
        await self.replace_team_members(tenant_id, team_id, payload.usuario_ids)
        return await self.get_team(tenant_id, team_id)  # type: ignore[return-value]

    async def update_team(
        self, tenant_id: int, team_id: int, payload: TeamUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True, exclude={"usuario_ids"})
        if values:
            assignments = ",".join(f"{field}=:{field}" for field in values)
            await self.session.execute(
                text(
                    f"UPDATE cadastro.equipe SET {assignments},atualizado_em=now() "
                    "WHERE tenant_id=:tenant_id AND id=:id"
                ),
                {"tenant_id": tenant_id, "id": team_id, **values},
            )
        if payload.usuario_ids is not None:
            await self.replace_team_members(tenant_id, team_id, payload.usuario_ids)
        return await self.get_team(tenant_id, team_id)

    async def replace_team_members(self, tenant_id: int, team_id: int, user_ids: list[int]) -> None:
        await self.session.execute(
            text(
                "DELETE FROM cadastro.equipe_pessoa "
                "WHERE tenant_id=:tenant_id AND equipe_id=:team_id"
            ),
            {"tenant_id": tenant_id, "team_id": team_id},
        )
        if user_ids:
            await self.session.execute(
                text(
                    "INSERT INTO cadastro.equipe_pessoa(tenant_id,equipe_id,pessoa_id) "
                    "SELECT :tenant_id,:team_id,pessoa_id FROM auth.usuario "
                    "WHERE tenant_id=:tenant_id AND id IN :ids"
                ).bindparams(bindparam("ids", expanding=True)),
                {"tenant_id": tenant_id, "team_id": team_id, "ids": user_ids},
            )

    async def reference_exists(self, table: str, tenant_id: int, item_id: int) -> bool:
        references = {
            "equipe": ("cadastro.equipe", "ativo"),
            "usuario": ("auth.usuario", "status='ativo'"),
            "lideranca": ("cadastro.lideranca", "ativo"),
            "territorio": ("territorio.territorio", "ativo"),
            "material": ("anuncio.material_comunicacao", "ativo"),
        }
        sql_table, predicate = references[table]
        return bool(
            await self.session.scalar(
                text(
                    f"SELECT EXISTS(SELECT 1 FROM {sql_table} "
                    f"WHERE tenant_id=:tenant_id AND id=:id AND {predicate})"
                ),
                {"tenant_id": tenant_id, "id": item_id},
            )
        )

    async def list_routes(
        self,
        tenant_id: int,
        params: ListParams,
        *,
        territory_id: int | None = None,
        material_id: int | None = None,
        include_inactive: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses = ["r.tenant_id=:tenant_id"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if not include_inactive:
            clauses.append("r.ativo")
        if params.query:
            clauses.append("(r.nome ILIKE :query OR r.descricao ILIKE :query)")
            values["query"] = f"%{params.query}%"
        if territory_id is not None:
            clauses.append("r.territorio_id=:territory_id")
            values["territory_id"] = territory_id
        if material_id is not None:
            clauses.append(
                "EXISTS(SELECT 1 FROM anuncio.rota_comunicacao_ponto p JOIN "
                "anuncio.rota_comunicacao_ponto_material pm ON pm.ponto_id=p.id "
                "WHERE p.rota_id=r.id AND pm.material_id=:material_id)"
            )
            values["material_id"] = material_id
        where = " AND ".join(clauses)
        total = int(
            await self.session.scalar(
                text(f"SELECT count(*) FROM anuncio.rota_comunicacao r WHERE {where}"), values
            )
            or 0
        )
        result = await self.session.execute(
            text(
                self._route_summary_select() + f" WHERE {where} GROUP BY r.id,t.nome "
                "ORDER BY r.nome LIMIT :limit OFFSET :offset"
            ),
            {**values, "limit": params.page_size, "offset": params.offset},
        )
        return [dict(row) for row in result.mappings()], total

    @staticmethod
    def _route_summary_select() -> str:
        return (
            "SELECT r.id,r.uuid_publico,r.tenant_id,r.nome,r.descricao,r.territorio_id,"
            "t.nome AS territorio_nome,r.ativo,count(p.id)::int AS total_pontos,"
            "r.criado_em,r.atualizado_em "
            "FROM anuncio.rota_comunicacao r "
            "LEFT JOIN territorio.territorio t ON t.id=r.territorio_id AND t.tenant_id=r.tenant_id "
            "LEFT JOIN anuncio.rota_comunicacao_ponto p ON p.rota_id=r.id AND p.tenant_id=r.tenant_id "
        )

    async def get_route(
        self, tenant_id: int, route_uuid: UUID, *, lock: bool = False
    ) -> dict[str, Any] | None:
        suffix = " FOR UPDATE OF r" if lock else ""
        row = (
            (
                await self.session.execute(
                    text(
                        self._route_summary_select()
                        + " WHERE r.tenant_id=:tenant_id AND r.uuid_publico=:uuid "
                        "GROUP BY r.id,t.nome" + suffix
                    ),
                    {"tenant_id": tenant_id, "uuid": route_uuid},
                )
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    async def get_route_by_id(self, tenant_id: int, route_id: int) -> dict[str, Any] | None:
        row = (
            (
                await self.session.execute(
                    text(
                        "SELECT id,uuid_publico,tenant_id,nome,descricao,territorio_id,ativo,"
                        "criado_em,atualizado_em FROM anuncio.rota_comunicacao "
                        "WHERE tenant_id=:tenant_id AND id=:id"
                    ),
                    {"tenant_id": tenant_id, "id": route_id},
                )
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    async def create_route(
        self, tenant_id: int, user_id: int, payload: RouteCreate
    ) -> dict[str, Any]:
        route_id = int(
            (
                await self.session.execute(
                    text(
                        "INSERT INTO anuncio.rota_comunicacao"
                        "(tenant_id,nome,descricao,territorio_id,ativo,criado_por) "
                        "VALUES(:tenant_id,:nome,:descricao,:territorio_id,:ativo,:user_id) "
                        "RETURNING id"
                    ),
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        **payload.model_dump(exclude={"pontos"}),
                    },
                )
            ).scalar_one()
        )
        await self.replace_route_points(tenant_id, route_id, payload.pontos)
        route_uuid = await self.session.scalar(
            text("SELECT uuid_publico FROM anuncio.rota_comunicacao WHERE id=:id"),
            {"id": route_id},
        )
        return await self.get_route_detail(tenant_id, route_uuid)  # type: ignore[return-value]

    async def update_route(
        self, tenant_id: int, route_id: int, user_id: int, payload: RouteUpdate
    ) -> None:
        await self.session.execute(
            text(
                "SELECT id FROM anuncio.rota_comunicacao "
                "WHERE tenant_id=:tenant_id AND id=:id FOR UPDATE"
            ),
            {"tenant_id": tenant_id, "id": route_id},
        )
        values = payload.model_dump(exclude_unset=True, exclude={"pontos"})
        if values:
            assignments = ",".join(f"{field}=:{field}" for field in values)
            await self.session.execute(
                text(
                    f"UPDATE anuncio.rota_comunicacao SET {assignments},"
                    "atualizado_por=:user_id,atualizado_em=now() "
                    "WHERE tenant_id=:tenant_id AND id=:id"
                ),
                {"tenant_id": tenant_id, "id": route_id, "user_id": user_id, **values},
            )
        if payload.pontos is not None:
            await self.replace_route_points(tenant_id, route_id, payload.pontos)
        synchronized_fields = {"nome", "descricao", "territorio_id", "pontos"}
        if payload.model_fields_set & synchronized_fields:
            await self.synchronize_unstarted_plannings(
                tenant_id,
                route_id,
                user_id,
                sync_points=payload.pontos is not None,
            )

    async def replace_route_points(
        self, tenant_id: int, route_id: int, points: list[RoutePointInput]
    ) -> None:
        await self.session.execute(
            text(
                "DELETE FROM anuncio.rota_comunicacao_ponto "
                "WHERE tenant_id=:tenant_id AND rota_id=:route_id"
            ),
            {"tenant_id": tenant_id, "route_id": route_id},
        )
        for point in sorted(points, key=lambda item: item.ordem):
            point_id = int(
                (
                    await self.session.execute(
                        text(
                            "INSERT INTO anuncio.rota_comunicacao_ponto"
                            "(tenant_id,rota_id,ordem,descricao_local,endereco,"
                            "latitude_planejada,longitude_planejada,observacao) "
                            "VALUES(:tenant_id,:route_id,:ordem,:descricao_local,:endereco,"
                            ":latitude_planejada,:longitude_planejada,:observacao) RETURNING id"
                        ),
                        {
                            "tenant_id": tenant_id,
                            "route_id": route_id,
                            **point.model_dump(exclude={"materiais", "uuid_publico"}),
                        },
                    )
                ).scalar_one()
            )
            for material in point.materiais:
                await self.session.execute(
                    text(
                        "INSERT INTO anuncio.rota_comunicacao_ponto_material"
                        "(tenant_id,ponto_id,material_id,quantidade_planejada) "
                        "VALUES(:tenant_id,:point_id,:material_id,:quantidade_planejada)"
                    ),
                    {"tenant_id": tenant_id, "point_id": point_id, **material.model_dump()},
                )

    async def synchronize_unstarted_plannings(
        self,
        tenant_id: int,
        route_id: int,
        user_id: int,
        *,
        sync_points: bool,
    ) -> None:
        """Atualiza snapshots que ainda nao possuem nenhuma execucao operacional."""
        planning_ids = list(
            (
                await self.session.execute(
                    text(
                        "SELECT pl.id FROM anuncio.rota_comunicacao_planejamento pl "
                        "WHERE pl.tenant_id=:tenant_id AND pl.rota_id=:route_id "
                        "AND pl.status IN ('PLANEJADA','LIBERADA') AND NOT EXISTS ("
                        "SELECT 1 FROM anuncio.rota_comunicacao_execucao ex "
                        "WHERE ex.tenant_id=pl.tenant_id AND ex.planejamento_id=pl.id)"
                    ),
                    {"tenant_id": tenant_id, "route_id": route_id},
                )
            )
            .scalars()
            .all()
        )
        if not planning_ids:
            return

        planning_ids_parameter: Any = bindparam("planning_ids", expanding=True)
        values = {
            "tenant_id": tenant_id,
            "route_id": route_id,
            "user_id": user_id,
            "planning_ids": planning_ids,
        }
        # Mantem a mesma ordem de bloqueio usada pela execucao mobile: primeiro o
        # ponto e depois o planejamento. A elegibilidade e revalidada apos o lock.
        await self.session.execute(
            text(
                "SELECT pp.id FROM anuncio.rota_comunicacao_planejamento_ponto pp "
                "WHERE pp.tenant_id=:tenant_id AND pp.planejamento_id IN :planning_ids "
                "FOR UPDATE OF pp"
            ).bindparams(planning_ids_parameter),
            values,
        )
        planning_ids = list(
            (
                await self.session.execute(
                    text(
                        "SELECT pl.id FROM anuncio.rota_comunicacao_planejamento pl "
                        "WHERE pl.tenant_id=:tenant_id AND pl.id IN :planning_ids "
                        "AND pl.status IN ('PLANEJADA','LIBERADA') AND NOT EXISTS ("
                        "SELECT 1 FROM anuncio.rota_comunicacao_execucao ex "
                        "WHERE ex.tenant_id=pl.tenant_id AND ex.planejamento_id=pl.id) "
                        "FOR UPDATE OF pl"
                    ).bindparams(planning_ids_parameter),
                    values,
                )
            )
            .scalars()
            .all()
        )
        if not planning_ids:
            return
        values["planning_ids"] = planning_ids
        await self.session.execute(
            text(
                "UPDATE anuncio.rota_comunicacao_planejamento pl SET "
                "rota_nome=r.nome,rota_descricao=r.descricao,territorio_id=r.territorio_id,"
                "territorio_nome=(SELECT t.nome FROM territorio.territorio t "
                "WHERE t.tenant_id=r.tenant_id AND t.id=r.territorio_id),"
                "atualizado_por=:user_id,atualizado_em=now() "
                "FROM anuncio.rota_comunicacao r "
                "WHERE pl.tenant_id=:tenant_id AND pl.id IN :planning_ids "
                "AND r.tenant_id=pl.tenant_id AND r.id=:route_id"
            ).bindparams(planning_ids_parameter),
            values,
        )
        if not sync_points:
            return

        await self.session.execute(
            text(
                "DELETE FROM anuncio.rota_comunicacao_planejamento_ponto pp "
                "WHERE pp.tenant_id=:tenant_id AND pp.planejamento_id IN :planning_ids "
                "AND NOT EXISTS (SELECT 1 FROM anuncio.rota_comunicacao_ponto rp "
                "WHERE rp.tenant_id=:tenant_id AND rp.rota_id=:route_id "
                "AND rp.ordem=pp.ordem)"
            ).bindparams(planning_ids_parameter),
            values,
        )
        await self.session.execute(
            text(
                "UPDATE anuncio.rota_comunicacao_planejamento_ponto pp SET "
                "rota_ponto_origem_id=rp.id,descricao_local=rp.descricao_local,"
                "endereco=rp.endereco,latitude_planejada=rp.latitude_planejada,"
                "longitude_planejada=rp.longitude_planejada,observacao=rp.observacao,"
                "atualizado_em=now() FROM anuncio.rota_comunicacao_ponto rp "
                "WHERE pp.tenant_id=:tenant_id AND pp.planejamento_id IN :planning_ids "
                "AND rp.tenant_id=pp.tenant_id AND rp.rota_id=:route_id "
                "AND rp.ordem=pp.ordem"
            ).bindparams(planning_ids_parameter),
            values,
        )
        await self.session.execute(
            text(
                "INSERT INTO anuncio.rota_comunicacao_planejamento_ponto"
                "(tenant_id,planejamento_id,rota_id,rota_ponto_origem_id,ordem,"
                "descricao_local,endereco,latitude_planejada,longitude_planejada,observacao) "
                "SELECT pl.tenant_id,pl.id,:route_id,rp.id,rp.ordem,rp.descricao_local,"
                "rp.endereco,rp.latitude_planejada,rp.longitude_planejada,rp.observacao "
                "FROM anuncio.rota_comunicacao_planejamento pl "
                "JOIN anuncio.rota_comunicacao_ponto rp "
                "ON rp.tenant_id=pl.tenant_id AND rp.rota_id=:route_id "
                "WHERE pl.tenant_id=:tenant_id AND pl.id IN :planning_ids "
                "AND NOT EXISTS (SELECT 1 FROM anuncio.rota_comunicacao_planejamento_ponto pp "
                "WHERE pp.tenant_id=pl.tenant_id AND pp.planejamento_id=pl.id "
                "AND pp.ordem=rp.ordem)"
            ).bindparams(planning_ids_parameter),
            values,
        )
        await self.session.execute(
            text(
                "DELETE FROM anuncio.rota_comunicacao_planejamento_ponto_material pm "
                "USING anuncio.rota_comunicacao_planejamento_ponto pp "
                "WHERE pm.tenant_id=:tenant_id AND pm.ponto_id=pp.id "
                "AND pp.tenant_id=pm.tenant_id AND pp.planejamento_id IN :planning_ids"
            ).bindparams(planning_ids_parameter),
            values,
        )
        await self.session.execute(
            text(
                "INSERT INTO anuncio.rota_comunicacao_planejamento_ponto_material"
                "(tenant_id,ponto_id,material_id,quantidade_planejada) "
                "SELECT pp.tenant_id,pp.id,rpm.material_id,rpm.quantidade_planejada "
                "FROM anuncio.rota_comunicacao_planejamento_ponto pp "
                "JOIN anuncio.rota_comunicacao_ponto_material rpm "
                "ON rpm.tenant_id=pp.tenant_id AND rpm.ponto_id=pp.rota_ponto_origem_id "
                "WHERE pp.tenant_id=:tenant_id AND pp.planejamento_id IN :planning_ids"
            ).bindparams(planning_ids_parameter),
            values,
        )

    async def get_route_detail(self, tenant_id: int, route_uuid: UUID) -> dict[str, Any] | None:
        route = await self.get_route(tenant_id, route_uuid)
        if route is None:
            return None
        route["pontos"] = await self.list_route_points(tenant_id, route["id"])
        return route

    async def list_route_points(self, tenant_id: int, route_id: int) -> list[dict[str, Any]]:
        rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT id,uuid_publico,ordem,descricao_local,endereco,latitude_planejada,"
                        "longitude_planejada,observacao FROM anuncio.rota_comunicacao_ponto "
                        "WHERE tenant_id=:tenant_id AND rota_id=:route_id ORDER BY ordem"
                    ),
                    {"tenant_id": tenant_id, "route_id": route_id},
                )
            )
            .mappings()
            .all()
        )
        points = [dict(row) for row in rows]
        for point in points:
            point["materiais"] = await self.route_point_materials(tenant_id, point["id"])
        return points

    async def route_point_materials(self, tenant_id: int, point_id: int) -> list[dict[str, Any]]:
        rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT pm.id,pm.material_id,m.nome AS material_nome,pm.quantidade_planejada "
                        "FROM anuncio.rota_comunicacao_ponto_material pm "
                        "JOIN anuncio.material_comunicacao m ON m.id=pm.material_id AND m.tenant_id=pm.tenant_id "
                        "WHERE pm.tenant_id=:tenant_id AND pm.ponto_id=:point_id ORDER BY m.nome"
                    ),
                    {"tenant_id": tenant_id, "point_id": point_id},
                )
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    async def list_plannings(
        self,
        tenant_id: int,
        params: ListParams,
        *,
        start: date | None = None,
        end: date | None = None,
        status: str | None = None,
        team_id: int | None = None,
        user_id: int | None = None,
        territory_id: int | None = None,
        material_id: int | None = None,
        route_id: int | None = None,
        accessible_user_id: int | None = None,
        accessible_person_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses = ["pl.tenant_id=:tenant_id"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if params.query:
            clauses.append(
                "(pl.rota_nome ILIKE :query OR pl.rota_descricao ILIKE :query "
                "OR pl.observacao ILIKE :query)"
            )
            values["query"] = f"%{params.query}%"
        for value, expression, name in (
            (start, "pl.data_execucao>=:start", "start"),
            (end, "pl.data_execucao<=:end", "end"),
            (status, "pl.status=:status", "status"),
            (team_id, "pl.equipe_id=:team_id", "team_id"),
            (user_id, "pl.usuario_responsavel_id=:user_id", "user_id"),
            (territory_id, "pl.territorio_id=:territory_id", "territory_id"),
            (route_id, "pl.rota_id=:route_id", "route_id"),
        ):
            if value is not None:
                clauses.append(expression)
                values[name] = value
        if material_id is not None:
            clauses.append(
                "EXISTS(SELECT 1 FROM anuncio.rota_comunicacao_planejamento_ponto pp "
                "JOIN anuncio.rota_comunicacao_planejamento_ponto_material pm ON pm.ponto_id=pp.id "
                "WHERE pp.planejamento_id=pl.id AND pm.material_id=:material_id)"
            )
            values["material_id"] = material_id
        if accessible_user_id is not None:
            clauses.extend(
                [
                    "pl.status <> 'CANCELADA'",
                    "(pl.usuario_responsavel_id=:accessible_user_id OR EXISTS(SELECT 1 FROM cadastro.equipe_pessoa ep "
                    "WHERE ep.tenant_id=pl.tenant_id AND ep.equipe_id=pl.equipe_id "
                    "AND ep.pessoa_id=:accessible_person_id))",
                ]
            )
            values.update(
                accessible_user_id=accessible_user_id,
                accessible_person_id=accessible_person_id or -1,
            )
        where = " AND ".join(clauses)
        join = (
            " FROM anuncio.rota_comunicacao_planejamento pl JOIN anuncio.rota_comunicacao r "
            "ON r.id=pl.rota_id AND r.tenant_id=pl.tenant_id "
        )
        total = int(
            await self.session.scalar(text(f"SELECT count(*){join} WHERE {where}"), values) or 0
        )
        rows = (
            (
                await self.session.execute(
                    text(
                        self._planning_summary_select() + f" WHERE {where} "
                        "GROUP BY pl.id,r.id,e.nome,u.nome "
                        "ORDER BY pl.data_execucao DESC,pl.rota_nome "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    {**values, "limit": params.page_size, "offset": params.offset},
                )
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows], total

    @staticmethod
    def _planning_summary_select() -> str:
        return (
            "SELECT pl.id,pl.uuid_publico,pl.tenant_id,pl.rota_id,r.uuid_publico AS rota_uuid,"
            "pl.rota_nome AS nome,pl.rota_descricao AS descricao,pl.data_execucao,"
            "pl.status,pl.observacao,pl.equipe_id,"
            "e.nome AS equipe_nome,pl.usuario_responsavel_id,u.nome AS usuario_responsavel_nome,"
            "pl.territorio_id,pl.territorio_nome,count(p.id)::int AS total_pontos,"
            "count(p.id) FILTER (WHERE p.status IN ('INSTALADO','RECOLHIDO','RECOLHIDO_PARCIALMENTE','COM_EXTRAVIO'))::int AS pontos_concluidos,"
            "count(p.id) FILTER (WHERE p.status IN ('PENDENTE','EM_EXECUCAO'))::int AS pontos_pendentes,"
            "pl.criado_em,pl.atualizado_em FROM anuncio.rota_comunicacao_planejamento pl "
            "JOIN anuncio.rota_comunicacao r ON r.id=pl.rota_id AND r.tenant_id=pl.tenant_id "
            "LEFT JOIN cadastro.equipe e ON e.id=pl.equipe_id AND e.tenant_id=pl.tenant_id "
            "LEFT JOIN auth.usuario u ON u.id=pl.usuario_responsavel_id AND u.tenant_id=pl.tenant_id "
            "LEFT JOIN anuncio.rota_comunicacao_planejamento_ponto p ON p.planejamento_id=pl.id AND p.tenant_id=pl.tenant_id"
        )

    async def get_planning(
        self, tenant_id: int, planning_uuid: UUID, *, lock: bool = False
    ) -> dict[str, Any] | None:
        suffix = " FOR UPDATE OF pl" if lock else ""
        row = (
            (
                await self.session.execute(
                    text(
                        self._planning_summary_select()
                        + " WHERE pl.tenant_id=:tenant_id AND pl.uuid_publico=:uuid "
                        "GROUP BY pl.id,r.id,e.nome,u.nome" + suffix
                    ),
                    {"tenant_id": tenant_id, "uuid": planning_uuid},
                )
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    async def planning_is_accessible(
        self, tenant_id: int, planning_id: int, user_id: int, person_id: int | None
    ) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM anuncio.rota_comunicacao_planejamento pl "
                    "WHERE pl.tenant_id=:tenant_id AND pl.id=:planning_id AND "
                    "(pl.usuario_responsavel_id=:user_id OR EXISTS(SELECT 1 FROM cadastro.equipe_pessoa ep "
                    "WHERE ep.tenant_id=pl.tenant_id AND ep.equipe_id=pl.equipe_id AND ep.pessoa_id=:person_id)))"
                ),
                {
                    "tenant_id": tenant_id,
                    "planning_id": planning_id,
                    "user_id": user_id,
                    "person_id": person_id or -1,
                },
            )
        )

    async def create_planning(
        self, tenant_id: int, user_id: int, payload: PlanningCreate
    ) -> dict[str, Any]:
        # Serializa a copia com edicoes do template para impedir snapshots hibridos.
        await self.session.execute(
            text(
                "SELECT id FROM anuncio.rota_comunicacao "
                "WHERE tenant_id=:tenant_id AND id=:id FOR SHARE"
            ),
            {"tenant_id": tenant_id, "id": payload.rota_id},
        )
        planning_id = int(
            (
                await self.session.execute(
                    text(
                        "INSERT INTO anuncio.rota_comunicacao_planejamento"
                        "(tenant_id,rota_id,rota_nome,rota_descricao,territorio_id,territorio_nome,"
                        "equipe_id,usuario_responsavel_id,data_execucao,observacao,criado_por) "
                        "SELECT :tenant_id,r.id,r.nome,r.descricao,r.territorio_id,t.nome,"
                        ":equipe_id,:usuario_responsavel_id,:data_execucao,:observacao,:user_id "
                        "FROM anuncio.rota_comunicacao r LEFT JOIN territorio.territorio t "
                        "ON t.id=r.territorio_id AND t.tenant_id=r.tenant_id "
                        "WHERE r.tenant_id=:tenant_id AND r.id=:rota_id RETURNING id"
                    ),
                    {"tenant_id": tenant_id, "user_id": user_id, **payload.model_dump()},
                )
            ).scalar_one()
        )
        await self.session.execute(
            text(
                "INSERT INTO anuncio.rota_comunicacao_planejamento_ponto"
                "(tenant_id,planejamento_id,rota_id,rota_ponto_origem_id,ordem,descricao_local,endereco,latitude_planejada,longitude_planejada,observacao) "
                "SELECT p.tenant_id,:planning_id,p.rota_id,p.id,p.ordem,p.descricao_local,p.endereco,p.latitude_planejada,p.longitude_planejada,p.observacao "
                "FROM anuncio.rota_comunicacao_ponto p WHERE p.tenant_id=:tenant_id AND p.rota_id=:route_id"
            ),
            {"tenant_id": tenant_id, "planning_id": planning_id, "route_id": payload.rota_id},
        )
        await self.session.execute(
            text(
                "INSERT INTO anuncio.rota_comunicacao_planejamento_ponto_material"
                "(tenant_id,ponto_id,material_id,quantidade_planejada) "
                "SELECT ppm.tenant_id,s.id,ppm.material_id,ppm.quantidade_planejada "
                "FROM anuncio.rota_comunicacao_planejamento_ponto s "
                "JOIN anuncio.rota_comunicacao_ponto_material ppm ON ppm.ponto_id=s.rota_ponto_origem_id AND ppm.tenant_id=s.tenant_id "
                "WHERE s.tenant_id=:tenant_id AND s.planejamento_id=:planning_id"
            ),
            {"tenant_id": tenant_id, "planning_id": planning_id},
        )
        planning_uuid = await self.session.scalar(
            text("SELECT uuid_publico FROM anuncio.rota_comunicacao_planejamento WHERE id=:id"),
            {"id": planning_id},
        )
        return await self.get_planning_detail(tenant_id, planning_uuid)  # type: ignore[return-value]

    async def update_planning(
        self, tenant_id: int, planning_id: int, user_id: int, payload: PlanningUpdate
    ) -> None:
        values = payload.model_dump(exclude_unset=True)
        if values:
            assignments = ",".join(f"{field}=:{field}" for field in values)
            await self.session.execute(
                text(
                    f"UPDATE anuncio.rota_comunicacao_planejamento SET {assignments},"
                    "atualizado_por=:user_id,atualizado_em=now() WHERE tenant_id=:tenant_id AND id=:id"
                ),
                {"tenant_id": tenant_id, "id": planning_id, "user_id": user_id, **values},
            )

    async def planning_has_executions(self, tenant_id: int, planning_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM anuncio.rota_comunicacao_execucao "
                    "WHERE tenant_id=:tenant_id AND planejamento_id=:planning_id)"
                ),
                {"tenant_id": tenant_id, "planning_id": planning_id},
            )
        )

    async def get_planning_detail(
        self, tenant_id: int, planning_uuid: UUID
    ) -> dict[str, Any] | None:
        planning = await self.get_planning(tenant_id, planning_uuid)
        if planning is not None:
            planning["pontos"] = await self.list_planning_points(
                tenant_id, planning["id"], include_history=True
            )
        return planning

    async def list_planning_points(
        self, tenant_id: int, planning_id: int, *, include_history: bool
    ) -> list[dict[str, Any]]:
        rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT id,uuid_publico,ordem,descricao_local,endereco,latitude_planejada,"
                        "longitude_planejada,observacao,status FROM anuncio.rota_comunicacao_planejamento_ponto "
                        "WHERE tenant_id=:tenant_id AND planejamento_id=:planning_id ORDER BY ordem"
                    ),
                    {"tenant_id": tenant_id, "planning_id": planning_id},
                )
            )
            .mappings()
            .all()
        )
        points = [dict(row) for row in rows]
        for point in points:
            point["materiais"] = await self.point_materials(tenant_id, point["id"])
            point["historico"] = (
                await self.point_history(tenant_id, point["id"]) if include_history else []
            )
        return points

    async def get_point(
        self, tenant_id: int, point_uuid: UUID, *, lock: bool = False
    ) -> dict[str, Any] | None:
        suffix = " FOR UPDATE" if lock else ""
        row = (
            (
                await self.session.execute(
                    text(
                        "SELECT p.id,p.uuid_publico,p.tenant_id,p.rota_id,p.ordem,p.descricao_local,"
                        "p.endereco,p.latitude_planejada,p.longitude_planejada,p.observacao,p.status,"
                        "p.planejamento_id,pl.uuid_publico AS planejamento_uuid,pl.status AS planejamento_status,"
                        "p.rota_id,r.uuid_publico AS rota_uuid FROM anuncio.rota_comunicacao_planejamento_ponto p "
                        "JOIN anuncio.rota_comunicacao_planejamento pl ON pl.id=p.planejamento_id AND pl.tenant_id=p.tenant_id "
                        "JOIN anuncio.rota_comunicacao r ON r.id=p.rota_id AND r.tenant_id=p.tenant_id "
                        "WHERE p.tenant_id=:tenant_id AND p.uuid_publico=:uuid" + suffix
                    ),
                    {"tenant_id": tenant_id, "uuid": point_uuid},
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        point = dict(row)
        point["materiais"] = await self.point_materials(tenant_id, point["id"], lock=lock)
        return point

    async def point_materials(
        self, tenant_id: int, point_id: int, *, lock: bool = False
    ) -> list[dict[str, Any]]:
        suffix = " FOR UPDATE OF pm" if lock else ""
        rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT pm.id,pm.material_id,m.nome AS material_nome,pm.quantidade_planejada,"
                        "pm.quantidade_instalada,pm.quantidade_recolhida,pm.quantidade_extraviada,"
                        "(pm.quantidade_planejada-pm.quantidade_instalada)::int "
                        "AS quantidade_pendente "
                        "FROM anuncio.rota_comunicacao_planejamento_ponto_material pm "
                        "JOIN anuncio.material_comunicacao m ON m.id=pm.material_id "
                        "WHERE pm.tenant_id=:tenant_id AND pm.ponto_id=:point_id "
                        "ORDER BY m.nome" + suffix
                    ),
                    {"tenant_id": tenant_id, "point_id": point_id},
                )
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    async def point_history(self, tenant_id: int, point_id: int) -> list[dict[str, Any]]:
        executions = [
            dict(row)
            for row in (
                await self.session.execute(
                    text(
                        "SELECT ex.id,ex.uuid_publico,ex.tipo_operacao,ex.usuario_id,"
                        "u.nome AS usuario_nome,ex.latitude,ex.longitude,ex.precisao,"
                        "ex.observacao,ex.executado_em FROM anuncio.rota_comunicacao_execucao ex "
                        "JOIN auth.usuario u ON u.id=ex.usuario_id "
                        "WHERE ex.tenant_id=:tenant_id AND ex.ponto_id=:point_id "
                        "ORDER BY ex.executado_em,ex.id"
                    ),
                    {"tenant_id": tenant_id, "point_id": point_id},
                )
            ).mappings()
        ]
        for execution in executions:
            execution["movimentacoes"] = await self.execution_movements(tenant_id, execution["id"])
            photo = (
                (
                    await self.session.execute(
                        text(
                            "SELECT an.id AS anexo_id,an.criado_em FROM arquivo.anexo an "
                            "JOIN arquivo.arquivo ar ON ar.id=an.arquivo_id "
                            "WHERE an.tenant_id=:tenant_id AND an.entidade_tipo='anuncio_execucao' "
                            "AND an.entidade_id=:execution_id AND an.excluido_em IS NULL "
                            "AND ar.excluido_em IS NULL ORDER BY an.criado_em DESC LIMIT 1"
                        ),
                        {"tenant_id": tenant_id, "execution_id": execution["id"]},
                    )
                )
                .mappings()
                .first()
            )
            execution["foto"] = (
                {
                    **dict(photo),
                    "preview_url": f"/api/v1/arquivos/anexos/{photo['anexo_id']}/preview",
                    "download_url": f"/api/v1/arquivos/anexos/{photo['anexo_id']}/download",
                }
                if photo
                else None
            )
        return executions

    async def execution_movements(self, tenant_id: int, execution_id: int) -> list[dict[str, Any]]:
        rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT mv.id,mv.uuid_publico,mv.material_id,m.nome AS material_nome,"
                        "mv.tipo_movimentacao,mv.quantidade,mv.usuario_id,u.nome AS usuario_nome,"
                        "mv.latitude,mv.longitude,mv.observacao,mv.registrado_em "
                        "FROM anuncio.rota_comunicacao_material_movimentacao mv "
                        "JOIN anuncio.material_comunicacao m ON m.id=mv.material_id "
                        "JOIN auth.usuario u ON u.id=mv.usuario_id "
                        "WHERE mv.tenant_id=:tenant_id AND mv.execucao_id=:execution_id "
                        "ORDER BY mv.id"
                    ),
                    {"tenant_id": tenant_id, "execution_id": execution_id},
                )
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    async def get_execution_by_key(
        self, tenant_id: int, user_id: int, key: str
    ) -> dict[str, Any] | None:
        row = (
            (
                await self.session.execute(
                    text(
                        "SELECT id,uuid_publico,tipo_operacao,usuario_id,latitude,longitude,precisao,"
                        "observacao,executado_em,ponto_id,rota_id,planejamento_id FROM "
                        "anuncio.rota_comunicacao_execucao WHERE tenant_id=:tenant_id "
                        "AND usuario_id=:user_id AND chave_idempotencia=:key"
                    ),
                    {"tenant_id": tenant_id, "user_id": user_id, "key": key},
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        item = dict(row)
        item["movimentacoes"] = await self.execution_movements(tenant_id, item["id"])
        return item

    async def create_execution(
        self,
        *,
        tenant_id: int,
        route_id: int,
        planning_id: int,
        point_id: int,
        user_id: int,
        operation_type: str,
        idempotency_key: str,
        latitude: Any,
        longitude: Any,
        accuracy: Any,
        note: str | None,
        captured_at: datetime,
    ) -> int:
        return int(
            (
                await self.session.execute(
                    text(
                        "INSERT INTO anuncio.rota_comunicacao_execucao"
                        "(tenant_id,planejamento_id,rota_id,ponto_id,usuario_id,tipo_operacao,"
                        "chave_idempotencia,latitude,longitude,precisao,observacao,executado_em) "
                        "VALUES(:tenant_id,:planning_id,:route_id,:point_id,:user_id,:operation_type,"
                        ":idempotency_key,:latitude,:longitude,:accuracy,:note,:captured_at) "
                        "RETURNING id"
                    ),
                    {
                        "tenant_id": tenant_id,
                        "route_id": route_id,
                        "planning_id": planning_id,
                        "point_id": point_id,
                        "user_id": user_id,
                        "operation_type": operation_type,
                        "idempotency_key": idempotency_key,
                        "latitude": latitude,
                        "longitude": longitude,
                        "accuracy": accuracy,
                        "note": note,
                        "captured_at": captured_at,
                    },
                )
            ).scalar_one()
        )

    async def add_movement(
        self,
        *,
        tenant_id: int,
        execution_id: int,
        route_id: int,
        planning_id: int,
        point_id: int,
        material_id: int,
        user_id: int,
        movement_type: str,
        quantity: int,
        latitude: Any,
        longitude: Any,
        note: str | None,
        registered_at: datetime,
    ) -> None:
        await self.session.execute(
            text(
                "INSERT INTO anuncio.rota_comunicacao_material_movimentacao"
                "(tenant_id,execucao_id,planejamento_id,rota_id,ponto_id,material_id,usuario_id,"
                "tipo_movimentacao,quantidade,latitude,longitude,observacao,registrado_em) "
                "VALUES(:tenant_id,:execution_id,:planning_id,:route_id,:point_id,:material_id,:user_id,"
                ":movement_type,:quantity,:latitude,:longitude,:note,:registered_at)"
            ),
            {
                "tenant_id": tenant_id,
                "execution_id": execution_id,
                "route_id": route_id,
                "planning_id": planning_id,
                "point_id": point_id,
                "material_id": material_id,
                "user_id": user_id,
                "movement_type": movement_type,
                "quantity": quantity,
                "latitude": latitude,
                "longitude": longitude,
                "note": note,
                "registered_at": registered_at,
            },
        )

    async def update_material_totals(
        self,
        tenant_id: int,
        point_material_id: int,
        *,
        installed: int = 0,
        collected: int = 0,
        lost: int = 0,
    ) -> None:
        await self.session.execute(
            text(
                "UPDATE anuncio.rota_comunicacao_planejamento_ponto_material SET "
                "quantidade_instalada=quantidade_instalada+:installed,"
                "quantidade_recolhida=quantidade_recolhida+:collected,"
                "quantidade_extraviada=quantidade_extraviada+:lost,atualizado_em=now() "
                "WHERE tenant_id=:tenant_id AND id=:id"
            ),
            {
                "tenant_id": tenant_id,
                "id": point_material_id,
                "installed": installed,
                "collected": collected,
                "lost": lost,
            },
        )

    async def update_operation_statuses(
        self, tenant_id: int, planning_id: int, point_id: int, point_status: str
    ) -> str:
        await self.session.execute(
            text(
                "UPDATE anuncio.rota_comunicacao_planejamento_ponto SET status=:status,atualizado_em=now() "
                "WHERE tenant_id=:tenant_id AND id=:point_id"
            ),
            {"tenant_id": tenant_id, "point_id": point_id, "status": point_status},
        )
        pending = int(
            await self.session.scalar(
                text(
                    "SELECT count(*) FROM anuncio.rota_comunicacao_planejamento_ponto p "
                    "WHERE p.tenant_id=:tenant_id AND p.planejamento_id=:planning_id AND ("
                    "p.status IN ('PENDENTE','EM_EXECUCAO','INSTALADO',"
                    "'RECOLHIDO_PARCIALMENTE') OR (p.status='COM_EXTRAVIO' AND EXISTS("
                    "SELECT 1 FROM anuncio.rota_comunicacao_planejamento_ponto_material pm "
                    "WHERE pm.tenant_id=p.tenant_id AND pm.ponto_id=p.id AND "
                    "pm.quantidade_instalada>pm.quantidade_recolhida+"
                    "pm.quantidade_extraviada)))"
                ),
                {"tenant_id": tenant_id, "planning_id": planning_id},
            )
            or 0
        )
        current = str(
            await self.session.scalar(
                text(
                    "SELECT status FROM anuncio.rota_comunicacao_planejamento "
                    "WHERE tenant_id=:tenant_id AND id=:planning_id"
                ),
                {"tenant_id": tenant_id, "planning_id": planning_id},
            )
        )
        route_status = "CONCLUIDA" if pending == 0 else "EM_EXECUCAO"
        if current == "CANCELADA":
            route_status = current
        await self.session.execute(
            text(
                "UPDATE anuncio.rota_comunicacao_planejamento SET status=:status,atualizado_em=now() "
                "WHERE tenant_id=:tenant_id AND id=:planning_id"
            ),
            {"tenant_id": tenant_id, "planning_id": planning_id, "status": route_status},
        )
        return route_status

    async def dashboard(
        self,
        tenant_id: int,
        *,
        start: date,
        end: date,
        team_id: int | None,
        user_id: int | None,
        material_id: int | None,
        route_id: int | None,
        territory_id: int | None,
        status: str | None,
    ) -> dict[str, Any]:
        clauses = ["pl.tenant_id=:tenant_id", "pl.data_execucao BETWEEN :start AND :end"]
        values: dict[str, Any] = {"tenant_id": tenant_id, "start": start, "end": end}
        filters = (
            (team_id, "pl.equipe_id=:team_id", "team_id"),
            (user_id, "pl.usuario_responsavel_id=:user_id", "user_id"),
            (route_id, "pl.rota_id=:route_id", "route_id"),
            (territory_id, "pl.territorio_id=:territory_id", "territory_id"),
            (status, "pl.status=:status", "status"),
        )
        for value, expression, name in filters:
            if value is not None:
                clauses.append(expression)
                values[name] = value
        if material_id is not None:
            clauses.append("pm.material_id=:material_id")
            values["material_id"] = material_id
        where = " AND ".join(clauses)
        totals = (
            (
                await self.session.execute(
                    text(
                        "SELECT count(DISTINCT pl.id) FILTER (WHERE pl.status IN "
                        "('PLANEJADA','LIBERADA'))::int AS rotas_programadas,"
                        "count(DISTINCT pl.id) FILTER (WHERE pl.status='EM_EXECUCAO')::int "
                        "AS rotas_iniciadas,count(DISTINCT pl.id) FILTER "
                        "(WHERE pl.status='CONCLUIDA')::int AS rotas_concluidas,"
                        "count(DISTINCT p.id)::int AS pontos_planejados,"
                        "count(DISTINCT p.id) FILTER (WHERE p.status NOT IN "
                        "('PENDENTE','EM_EXECUCAO','NAO_EXECUTADO'))::int AS pontos_executados,"
                        "count(DISTINCT p.id) FILTER (WHERE p.status IN "
                        "('PENDENTE','EM_EXECUCAO'))::int AS pontos_pendentes,"
                        "COALESCE(sum(pm.quantidade_instalada),0)::int AS materiais_instalados,"
                        "COALESCE(sum(pm.quantidade_recolhida),0)::int AS materiais_recolhidos,"
                        "COALESCE(sum(pm.quantidade_extraviada),0)::int AS materiais_extraviados "
                        "FROM anuncio.rota_comunicacao_planejamento pl "
                        "JOIN anuncio.rota_comunicacao r ON r.id=pl.rota_id AND r.tenant_id=pl.tenant_id "
                        "LEFT JOIN anuncio.rota_comunicacao_planejamento_ponto p ON p.planejamento_id=pl.id "
                        "LEFT JOIN anuncio.rota_comunicacao_planejamento_ponto_material pm ON pm.ponto_id=p.id "
                        f"WHERE {where}"
                    ),
                    values,
                )
            )
            .mappings()
            .one()
        )
        total_dict = dict(totals)
        installed = total_dict["materiais_instalados"]
        total_dict["taxa_extravio"] = (
            round(total_dict["materiais_extraviados"] * 100 / installed, 2) if installed else 0
        )
        material_rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT m.id::text AS chave,m.nome,"
                        "COALESCE(sum(pm.quantidade_instalada),0)::int AS instalado,"
                        "COALESCE(sum(pm.quantidade_recolhida),0)::int AS recolhido,"
                        "COALESCE(sum(pm.quantidade_extraviada),0)::int AS extraviado "
                        "FROM anuncio.rota_comunicacao_planejamento pl "
                        "JOIN anuncio.rota_comunicacao r ON r.id=pl.rota_id AND r.tenant_id=pl.tenant_id "
                        "JOIN anuncio.rota_comunicacao_planejamento_ponto p ON p.planejamento_id=pl.id "
                        "JOIN anuncio.rota_comunicacao_planejamento_ponto_material pm ON pm.ponto_id=p.id "
                        "JOIN anuncio.material_comunicacao m ON m.id=pm.material_id "
                        f"WHERE {where} GROUP BY m.id,m.nome ORDER BY m.nome"
                    ),
                    values,
                )
            )
            .mappings()
            .all()
        )
        point_rows = (
            (
                await self.session.execute(
                    text(
                        "SELECT p.uuid_publico::text AS uuid_publico,p.descricao_local,p.endereco,"
                        "p.latitude_planejada,p.longitude_planejada,p.status,pl.rota_nome,"
                        "e.nome AS equipe_nome,u.nome AS usuario_nome,"
                        "ex.usuario_nome AS executor_nome,ex.executado_em,"
                        "ex.latitude AS latitude_execucao,ex.longitude AS longitude_execucao,"
                        "foto.anexo_id,"
                        "COALESCE(sum(pm.quantidade_instalada),0)::int AS instalado,"
                        "COALESCE(sum(pm.quantidade_recolhida),0)::int AS recolhido,"
                        "COALESCE(sum(pm.quantidade_extraviada),0)::int AS extraviado,"
                        "string_agg(DISTINCT m.nome || ': ' || pm.quantidade_instalada::text "
                        "|| ' instalados, ' || pm.quantidade_recolhida::text || ' recolhidos, ' "
                        "|| pm.quantidade_extraviada::text || ' extraviados', '; ') AS materiais "
                        "FROM anuncio.rota_comunicacao_planejamento pl "
                        "JOIN anuncio.rota_comunicacao r ON r.id=pl.rota_id AND r.tenant_id=pl.tenant_id "
                        "JOIN anuncio.rota_comunicacao_planejamento_ponto p ON p.planejamento_id=pl.id "
                        "LEFT JOIN anuncio.rota_comunicacao_planejamento_ponto_material pm ON pm.ponto_id=p.id "
                        "LEFT JOIN anuncio.material_comunicacao m ON m.id=pm.material_id "
                        "LEFT JOIN cadastro.equipe e ON e.id=pl.equipe_id AND e.tenant_id=pl.tenant_id "
                        "LEFT JOIN auth.usuario u ON u.id=pl.usuario_responsavel_id AND u.tenant_id=pl.tenant_id "
                        "LEFT JOIN LATERAL (SELECT eu.nome AS usuario_nome,xe.executado_em,"
                        "xe.latitude,xe.longitude,xe.id FROM anuncio.rota_comunicacao_execucao xe "
                        "JOIN auth.usuario eu ON eu.id=xe.usuario_id WHERE xe.tenant_id=pl.tenant_id "
                        "AND xe.ponto_id=p.id ORDER BY xe.executado_em DESC,xe.id DESC LIMIT 1) "
                        "ex ON TRUE LEFT JOIN LATERAL (SELECT an.id AS anexo_id "
                        "FROM anuncio.rota_comunicacao_execucao fe "
                        "JOIN arquivo.anexo an ON an.tenant_id=fe.tenant_id "
                        "AND an.entidade_tipo='anuncio_execucao' AND an.entidade_id=fe.id "
                        "JOIN arquivo.arquivo ar ON ar.id=an.arquivo_id AND ar.excluido_em IS NULL "
                        "WHERE fe.tenant_id=pl.tenant_id AND fe.ponto_id=p.id "
                        "AND an.excluido_em IS NULL ORDER BY an.criado_em DESC LIMIT 1) foto ON TRUE "
                        f"WHERE {where} GROUP BY p.id,pl.rota_nome,e.nome,u.nome,ex.usuario_nome,"
                        "ex.executado_em,ex.latitude,ex.longitude,foto.anexo_id "
                        "ORDER BY pl.rota_nome,p.ordem"
                    ),
                    values,
                )
            )
            .mappings()
            .all()
        )
        return {
            "totais": total_dict,
            "por_material": [dict(row) for row in material_rows],
            "pontos": [dict(row) for row in point_rows],
        }

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
