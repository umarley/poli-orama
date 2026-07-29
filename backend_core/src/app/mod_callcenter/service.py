from app.auth.access import RequestActor
from app.core.errors import BusinessRuleError, ResourceNotFoundError
from app.mod_callcenter.repository import CallCenterRepository
from app.mod_callcenter.schemas import ContactCreate, ContactResponse


class CallCenterService:
    def __init__(self, repository: CallCenterRepository) -> None:
        self.repository = repository

    async def ensure_campaign(self, actor: RequestActor, campaign_id: int) -> None:
        if not await self.repository.campaign_exists(actor.tenant_id, campaign_id):
            raise ResourceNotFoundError("Campanha eleitoral", campaign_id)

    async def create_contact(self, actor: RequestActor, payload: ContactCreate) -> ContactResponse:
        await self.ensure_campaign(actor, payload.campanha_eleicao_id)
        leader_id = await self.repository.active_leader_for_person(
            actor.tenant_id, payload.campanha_eleicao_id, payload.pessoa_id
        )
        if leader_id is None:
            raise BusinessRuleError(
                "A pessoa precisa possuir uma lideranca ativa antes do atendimento."
            )
        contact = await self.repository.create_contact(
            actor.tenant_id, actor.user_id, leader_id, payload
        )
        await self.repository.commit()
        return ContactResponse.model_validate(contact)
