import logging
from datetime import date
from typing import Any

from celery import Celery
from sqlalchemy.exc import IntegrityError

from app.auth.access import RequestActor
from app.core.config import Settings
from app.core.errors import BusinessRuleError, ResourceNotFoundError
from app.mod_eleicoes.repository import ElectionRepository
from app.mod_eleicoes.schemas import (
    CampaignClosureCreate,
    CampaignClosureResponse,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    ContestedOfficeResponse,
    ElectionCreate,
    ElectionUpdate,
)

logger = logging.getLogger(__name__)


class ElectionService:
    def __init__(self, repository: ElectionRepository, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings

    async def create(self, actor: RequestActor, payload: ElectionCreate) -> dict[str, Any]:
        payload = payload.model_copy(
            update={"codigo_uf_ibge": None, "codigo_municipio_ibge": None}
        )
        item = await self.repository.create(actor.user_id, payload)
        await self.repository.commit()
        return item

    async def update(self, election_id: int, payload: ElectionUpdate) -> dict[str, Any]:
        current = await self.repository.get(election_id)
        if current is None:
            raise ResourceNotFoundError("Eleicao", election_id)
        payload = ElectionUpdate.model_validate(
            {
                **payload.model_dump(exclude_unset=True),
                "codigo_uf_ibge": None,
                "codigo_municipio_ibge": None,
            }
        )
        merged = {**current, **payload.model_dump(exclude_unset=True)}
        ElectionCreate.model_validate(
            {field: merged[field] for field in ElectionCreate.model_fields}
        )
        if payload.ativo is False and await self.repository.references_exist(election_id):
            raise BusinessRuleError(
                "Eleicao vinculada a campanhas nao pode ser inativada.",
                code="election_in_use",
            )
        updated = await self.repository.update(election_id, payload)
        assert updated is not None
        await self.repository.commit()
        return updated

    async def list_campaigns(self, actor: RequestActor) -> list[CampaignResponse]:
        return [
            CampaignResponse.model_validate(item)
            for item in await self.repository.campaign_list(actor.tenant_id)
        ]

    async def list_contested_offices(
        self, election_type: str
    ) -> list[ContestedOfficeResponse]:
        return [
            ContestedOfficeResponse.model_validate(item)
            for item in await self.repository.list_contested_offices(election_type)
        ]

    async def current_campaign(self, actor: RequestActor) -> CampaignResponse | None:
        item = await self.repository.active_campaign(actor.tenant_id)
        return CampaignResponse.model_validate(item) if item else None

    async def create_campaign(
        self, actor: RequestActor, payload: CampaignCreate
    ) -> CampaignResponse:
        election = await self.repository.get(payload.eleicao_id)
        if election is None or not election["ativo"]:
            raise BusinessRuleError(
                "A campanha deve estar vinculada a uma eleicao oficial ativa.",
                code="active_election_required",
            )
        await self._validate_contested_office(
            payload.cargo_pleiteado_id, election["tipo"]
        )
        if payload.ativa:
            current = await self.repository.active_campaign(actor.tenant_id)
            if current is not None:
                await self.repository.activate_campaign(actor.tenant_id, -1)
        try:
            item = await self.repository.create_campaign(
                actor.tenant_id, actor.user_id, payload
            )
            await self.repository.commit()
        except IntegrityError:
            await self.repository.session.rollback()
            raise BusinessRuleError(
                "Ja existe uma campanha deste tenant para a eleicao selecionada.",
                code="campaign_election_already_exists",
            ) from None
        return CampaignResponse.model_validate(item)

    async def update_campaign(
        self, actor: RequestActor, campaign_id: int, payload: CampaignUpdate
    ) -> CampaignResponse:
        current = await self.repository.get_campaign(actor.tenant_id, campaign_id)
        if current is None:
            raise ResourceNotFoundError("Campanha", campaign_id)
        if current["data_encerramento"] is not None:
            raise BusinessRuleError(
                "Campanhas encerradas nao podem ser alteradas.",
                code="closed_campaign_read_only",
            )
        if payload.cargo_pleiteado_id is not None:
            await self._validate_contested_office(
                payload.cargo_pleiteado_id, current["eleicao_tipo"]
            )
        item = await self.repository.update_campaign(
            actor.tenant_id, campaign_id, payload
        )
        assert item is not None
        await self.repository.commit()
        return CampaignResponse.model_validate(item)

    async def _validate_contested_office(
        self, office_id: int, election_type: str
    ) -> None:
        office = await self.repository.get_contested_office(office_id)
        normalized_type = "municipal" if election_type == "municipal" else "federal"
        if (
            office is None
            or not office["ativo"]
            or office["tipo_eleicao"] != normalized_type
        ):
            raise BusinessRuleError(
                "O cargo pleiteado nao pertence ao tipo da eleicao selecionada.",
                code="invalid_contested_office",
            )

    async def activate_campaign(
        self, actor: RequestActor, campaign_id: int
    ) -> CampaignResponse:
        current = await self.repository.get_campaign(actor.tenant_id, campaign_id)
        if current is None:
            raise ResourceNotFoundError("Campanha", campaign_id)
        if current["data_encerramento"] is not None:
            raise BusinessRuleError(
                "Uma campanha encerrada nao pode ser reativada.",
                code="closed_campaign_cannot_activate",
            )
        item = await self.repository.activate_campaign(actor.tenant_id, campaign_id)
        assert item is not None
        await self.repository.commit()
        return CampaignResponse.model_validate(item)

    async def active_closure(self, actor: RequestActor) -> CampaignClosureResponse | None:
        campaign = await self.repository.active_campaign(actor.tenant_id)
        if campaign is None:
            campaign = await self.repository.latest_campaign(actor.tenant_id)
        if campaign is None:
            return None
        closure = await self.repository.closure(actor.tenant_id, campaign["id"])
        return CampaignClosureResponse.model_validate(closure) if closure is not None else None

    async def request_closure(
        self, actor: RequestActor, payload: CampaignClosureCreate
    ) -> CampaignClosureResponse:
        campaign = await self.repository.active_campaign(actor.tenant_id)
        if campaign is None:
            raise BusinessRuleError(
                "Nao existe campanha ativa para encerrar.",
                code="active_campaign_required",
            )
        if campaign["eleicao_data"] > date.today():
            raise BusinessRuleError(
                "A campanha so pode ser encerrada a partir da data da eleicao.",
                code="campaign_election_not_finished",
            )
        await self.repository.lock_campaign(actor.tenant_id, campaign["id"])
        existing = await self.repository.closure(actor.tenant_id, campaign["id"])
        if existing is not None:
            raise BusinessRuleError(
                "O encerramento desta campanha ja foi solicitado.",
                code="campaign_closure_already_requested",
            )
        closure_id, job_id = await self.repository.create_closure_job(
            actor.tenant_id, actor.user_id, campaign["id"], payload
        )
        await self.repository.commit()
        self._dispatch(
            "jobs.campanhas.close",
            {
                "job_id": job_id,
                "tenant_id": actor.tenant_id,
                "campaign_id": campaign["id"],
                "closure_id": closure_id,
            },
        )
        closure = await self.repository.closure(actor.tenant_id, campaign["id"])
        assert closure is not None
        return CampaignClosureResponse.model_validate(closure)

    async def retry_closure(self, actor: RequestActor) -> CampaignClosureResponse:
        campaign = await self.repository.latest_campaign(actor.tenant_id)
        if campaign is None:
            raise BusinessRuleError("Nenhuma campanha foi encontrada.")
        closure = await self.repository.closure(actor.tenant_id, campaign["id"])
        if closure is None or closure["status"] != "falha":
            raise BusinessRuleError(
                "Somente encerramentos com falha podem ser reprocessados.",
                code="campaign_closure_not_retryable",
            )
        job_id = await self.repository.create_closure_retry_job(
            actor.tenant_id, campaign["id"], closure["id"]
        )
        await self.repository.commit()
        self._dispatch(
            "jobs.campanhas.close",
            {
                "job_id": job_id,
                "tenant_id": actor.tenant_id,
                "campaign_id": campaign["id"],
                "closure_id": closure["id"],
            },
        )
        updated = await self.repository.closure(actor.tenant_id, campaign["id"])
        assert updated is not None
        return CampaignClosureResponse.model_validate(updated)

    def _dispatch(self, task: str, kwargs: dict[str, Any]) -> None:
        if self.settings is None:
            raise RuntimeError("Configuracao do broker nao foi fornecida.")
        try:
            Celery(broker=self.settings.celery_broker_url).send_task(task, kwargs=kwargs)
        except Exception:
            logger.exception("Falha ao despachar %s; o job permanece enfileirado.", task)
