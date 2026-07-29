from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.mod_eleicoes.schemas import (
    CampaignClosureCreate,
    CampaignCreate,
    CampaignUpdate,
    ElectionCreate,
    ElectionUpdate,
)


class ElectionRepository(BaseRepository[object]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @staticmethod
    def select_sql() -> str:
        return """
            SELECT e.id, e.uuid_publico, e.ano, e.tipo, e.turno,
                   e.data_eleicao, e.codigo_uf_ibge,
                   uf.nome AS estado_nome, uf.uf AS estado_uf,
                   e.codigo_municipio_ibge, municipio.nome AS municipio_nome,
                   e.descricao, e.ativo, e.criado_por,
                   e.criado_em, e.atualizado_em
              FROM eleicao.eleicao e
         LEFT JOIN global.estado uf
                ON uf.codigo_ibge = e.codigo_uf_ibge
         LEFT JOIN global.municipio municipio
                ON municipio.codigo_ibge = e.codigo_municipio_ibge
        """

    async def list(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        active = "" if include_inactive else "WHERE e.ativo"
        result = await self.session.execute(
            text(self.select_sql() + active + " ORDER BY e.data_eleicao DESC, e.turno, e.tipo")
        )
        return [dict(row) for row in result.mappings()]

    async def get(self, election_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(self.select_sql() + " WHERE e.id = :id"),
            {"id": election_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def references_exist(self, election_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM eleicao.campanha_eleicao WHERE eleicao_id = :id)"
                ),
                {"id": election_id},
            )
        )

    async def list_contested_offices(
        self, election_type: str
    ) -> Sequence[dict[str, Any]]:
        normalized_type = "municipal" if election_type == "municipal" else "federal"
        result = await self.session.execute(
            text(
                "SELECT id,codigo,nome,tipo_eleicao,ordem "
                "FROM eleicao.cargo_pleiteado "
                "WHERE tipo_eleicao=:tipo AND ativo "
                "ORDER BY ordem,nome"
            ),
            {"tipo": normalized_type},
        )
        return [dict(row) for row in result.mappings()]

    async def get_contested_office(self, office_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id,codigo,nome,tipo_eleicao,ordem,ativo "
                "FROM eleicao.cargo_pleiteado WHERE id=:id"
            ),
            {"id": office_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create(self, user_id: int, payload: ElectionCreate) -> dict[str, Any]:
        values = payload.model_dump()
        election_id = int(
            await self.session.scalar(
                text(
                    """
                    INSERT INTO eleicao.eleicao
                        (ano, tipo, turno, data_eleicao, codigo_uf_ibge,
                         codigo_municipio_ibge, descricao, criado_por)
                    VALUES
                        (:ano, :tipo, :turno, :data_eleicao, :codigo_uf_ibge,
                         :codigo_municipio_ibge, :descricao, :user_id)
                    RETURNING id
                    """
                ),
                {**values, "user_id": user_id},
            )
        )
        created = await self.get(election_id)
        assert created is not None
        return created

    async def update(self, election_id: int, payload: ElectionUpdate) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if values:
            assignments = ", ".join(f"{field} = :{field}" for field in values)
            await self.session.execute(
                text(f"UPDATE eleicao.eleicao SET {assignments} WHERE id = :id"),
                {"id": election_id, **values},
            )
        return await self.get(election_id)

    async def commit(self) -> None:
        await self.session.commit()

    async def active_campaign(self, tenant_id: int) -> dict[str, Any] | None:
        return await self.get_campaign(tenant_id, active_only=True)

    async def campaign_list(self, tenant_id: int) -> Sequence[dict[str, Any]]:
        result = await self.session.execute(
            text(self.campaign_select_sql() + """
                 WHERE ce.tenant_id = :tenant_id
                 ORDER BY ce.ativa DESC, e.data_eleicao DESC, ce.id DESC
            """),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    @staticmethod
    def campaign_select_sql() -> str:
        return """
            SELECT ce.id, ce.uuid_publico, ce.tenant_id, ce.eleicao_id,
                   ce.nome, ce.cargo_pleiteado_id,
                   COALESCE(cargo.nome, ce.cargo_pleiteado) AS cargo_pleiteado,
                   ce.ativa,
                   ce.data_ativacao, ce.data_encerramento, ce.criado_por,
                   ce.criado_em, ce.atualizado_em,
                   e.ano AS eleicao_ano, e.tipo AS eleicao_tipo,
                   e.turno AS eleicao_turno, e.data_eleicao AS eleicao_data,
                   e.descricao AS eleicao_descricao
              FROM eleicao.campanha_eleicao ce
              JOIN eleicao.eleicao e ON e.id = ce.eleicao_id
         LEFT JOIN eleicao.cargo_pleiteado cargo
                ON cargo.id = ce.cargo_pleiteado_id
        """

    async def get_campaign(
        self,
        tenant_id: int,
        campaign_id: int | None = None,
        *,
        active_only: bool = False,
    ) -> dict[str, Any] | None:
        filters = ["ce.tenant_id = :tenant_id"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if campaign_id is not None:
            filters.append("ce.id = :campaign_id")
            values["campaign_id"] = campaign_id
        if active_only:
            filters.append("ce.ativa")
        result = await self.session.execute(
            text(
                self.campaign_select_sql()
                + f" WHERE {' AND '.join(filters)}"
                + " ORDER BY ce.data_ativacao DESC NULLS LAST, ce.id DESC LIMIT 1"
            ),
            values,
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_campaign(
        self, tenant_id: int, user_id: int, payload: CampaignCreate
    ) -> dict[str, Any]:
        campaign_id = int(
            await self.session.scalar(
                text(
                    """
                    INSERT INTO eleicao.campanha_eleicao
                        (tenant_id, eleicao_id, nome, cargo_pleiteado_id,
                         cargo_pleiteado, ativa, criado_por, data_ativacao)
                    VALUES
                        (:tenant_id, :eleicao_id, :nome, :cargo_pleiteado_id,
                         (SELECT nome FROM eleicao.cargo_pleiteado
                           WHERE id=:cargo_pleiteado_id),
                         :ativa, :user_id,
                         CASE WHEN :ativa THEN now() ELSE NULL END)
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id, **payload.model_dump()},
            )
        )
        created = await self.get_campaign(tenant_id, campaign_id)
        assert created is not None
        return created

    async def update_campaign(
        self, tenant_id: int, campaign_id: int, payload: CampaignUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if values:
            assignments = [f"{field} = :{field}" for field in values]
            if "cargo_pleiteado_id" in values:
                assignments.append(
                    "cargo_pleiteado = (SELECT nome FROM eleicao.cargo_pleiteado "
                    "WHERE id=:cargo_pleiteado_id)"
                )
            await self.session.execute(
                text(
                    f"UPDATE eleicao.campanha_eleicao SET {', '.join(assignments)} "
                    "WHERE id = :campaign_id AND tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_id, "campaign_id": campaign_id, **values},
            )
        return await self.get_campaign(tenant_id, campaign_id)

    async def activate_campaign(self, tenant_id: int, campaign_id: int) -> dict[str, Any] | None:
        await self.session.execute(
            text(
                """
                UPDATE eleicao.campanha_eleicao
                   SET ativa = false
                 WHERE tenant_id = :tenant_id AND ativa AND id <> :campaign_id
                """
            ),
            {"tenant_id": tenant_id, "campaign_id": campaign_id},
        )
        await self.session.execute(
            text(
                """
                UPDATE eleicao.campanha_eleicao
                   SET ativa = true, data_ativacao = COALESCE(data_ativacao, now())
                 WHERE tenant_id = :tenant_id AND id = :campaign_id
                   AND data_encerramento IS NULL
                """
            ),
            {"tenant_id": tenant_id, "campaign_id": campaign_id},
        )
        return await self.get_campaign(tenant_id, campaign_id)

    async def latest_campaign(self, tenant_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                SELECT ce.id, ce.nome, ce.cargo_pleiteado, ce.ativa,
                       ce.data_encerramento, e.data_eleicao,
                       e.descricao AS eleicao_descricao
                  FROM eleicao.campanha_eleicao ce
                  JOIN eleicao.eleicao e ON e.id = ce.eleicao_id
                 WHERE ce.tenant_id = :tenant_id
                 ORDER BY ce.ativa DESC, ce.data_encerramento DESC NULLS LAST,
                          ce.data_ativacao DESC NULLS LAST, ce.id DESC
                 LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def closure(self, tenant_id: int, campaign_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                """
                SELECT ec.id, ec.tenant_id, ec.campanha_eleicao_id,
                       ce.nome AS campanha_nome, ce.cargo_pleiteado,
                       e.descricao AS eleicao_descricao,
                       ec.job_processamento_id, ec.votos_obtidos,
                       ec.total_votos_validos, ec.eleito, ec.colocacao,
                       ec.resultado_oficial_em, ec.fonte_resultado,
                       ec.observacao, ec.status, ec.erro,
                       ec.solicitado_por, ec.solicitado_em,
                       ec.iniciado_em, ec.concluido_em, ec.atualizado_em
                  FROM eleicao.encerramento_campanha ec
                  JOIN eleicao.campanha_eleicao ce
                    ON ce.id = ec.campanha_eleicao_id
                  JOIN eleicao.eleicao e ON e.id = ce.eleicao_id
                 WHERE ec.tenant_id = :tenant_id
                   AND ec.campanha_eleicao_id = :campaign_id
                """
            ),
            {"tenant_id": tenant_id, "campaign_id": campaign_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def lock_campaign(self, tenant_id: int, campaign_id: int) -> None:
        await self.session.execute(
            text(
                "SELECT id FROM eleicao.campanha_eleicao "
                "WHERE id = :campaign_id AND tenant_id = :tenant_id FOR UPDATE"
            ),
            {"tenant_id": tenant_id, "campaign_id": campaign_id},
        )

    async def create_closure_job(
        self,
        tenant_id: int,
        user_id: int,
        campaign_id: int,
        payload: CampaignClosureCreate,
    ) -> tuple[int, int]:
        closure_id = int(
            await self.session.scalar(
                text(
                    """
                    INSERT INTO eleicao.encerramento_campanha
                        (tenant_id, campanha_eleicao_id, votos_obtidos,
                         total_votos_validos, eleito, colocacao,
                         resultado_oficial_em, fonte_resultado, observacao,
                         solicitado_por)
                    VALUES
                        (:tenant_id, :campaign_id, :votos_obtidos,
                         :total_votos_validos, :eleito, :colocacao,
                         :resultado_oficial_em, :fonte_resultado, :observacao,
                         :user_id)
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "campaign_id": campaign_id,
                    "user_id": user_id,
                    **payload.model_dump(),
                },
            )
        )
        job_id = int(
            await self.session.scalar(
                text(
                    """
                    INSERT INTO etl.job_processamento
                        (tenant_id, tipo, referencia, parametros)
                    VALUES
                        (:tenant_id, 'indicador', :reference,
                         CAST(:parameters AS jsonb))
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "reference": f"encerramento_campanha:{campaign_id}",
                    "parameters": json.dumps(
                        {
                            "encerramento_campanha_id": closure_id,
                            "campanha_eleicao_id": campaign_id,
                        }
                    ),
                },
            )
        )
        await self.session.execute(
            text(
                """
                UPDATE eleicao.encerramento_campanha
                   SET job_processamento_id = :job_id
                 WHERE id = :closure_id AND tenant_id = :tenant_id
                """
            ),
            {
                "job_id": job_id,
                "closure_id": closure_id,
                "tenant_id": tenant_id,
            },
        )
        return closure_id, job_id

    async def create_closure_retry_job(
        self, tenant_id: int, campaign_id: int, closure_id: int
    ) -> int:
        job_id = int(
            await self.session.scalar(
                text(
                    """
                    INSERT INTO etl.job_processamento
                        (tenant_id, tipo, referencia, parametros)
                    VALUES
                        (:tenant_id, 'indicador', :reference,
                         CAST(:parameters AS jsonb))
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "reference": f"encerramento_campanha:{campaign_id}:reprocessar",
                    "parameters": json.dumps(
                        {
                            "encerramento_campanha_id": closure_id,
                            "campanha_eleicao_id": campaign_id,
                            "reprocessamento": True,
                        }
                    ),
                },
            )
        )
        await self.session.execute(
            text(
                """
                UPDATE eleicao.encerramento_campanha
                   SET job_processamento_id = :job_id,
                       status = 'enfileirado', erro = NULL,
                       iniciado_em = NULL, concluido_em = NULL
                 WHERE id = :closure_id AND tenant_id = :tenant_id
                   AND campanha_eleicao_id = :campaign_id
                   AND status = 'falha'
                """
            ),
            {
                "job_id": job_id,
                "closure_id": closure_id,
                "tenant_id": tenant_id,
                "campaign_id": campaign_id,
            },
        )
        return job_id
