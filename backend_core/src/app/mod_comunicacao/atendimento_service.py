from typing import Any

from app.audit.service import AuditService
from app.auth.access import RequestActor
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_comunicacao.atendimento_repository import AtendimentoRepository
from app.mod_comunicacao.atendimento_schemas import (
    AttendanceClose,
    AttendanceDocumentInput,
    AttendanceIndicators,
    AttendanceInteractionInput,
    AttendanceInvalidate,
    AttendancePersonUpdate,
    AttendanceQueue,
    AttendanceQueueItem,
    AttendanceResponse,
    AttendanceUpdate,
    CommunicationChannel,
    IndicatorFilters,
    RejectionReason,
)
from app.schemas.cadastro import PessoaContatoCreate, PessoaContatoUpdate

_INTENTION_LABELS = {
    "votara": "Votará no candidato",
    "nao_votara": "Não votará no candidato",
    "indeciso": "Ainda está indeciso",
    "nao_respondeu": "Preferiu não responder",
}
_STATUS_LABELS = {
    "concluido": "Concluído",
    "sem_resposta": "Sem resposta",
    "numero_invalido": "Número inválido",
    "interrompido": "Interrompido",
}


class AtendimentoService:
    def __init__(self, repository: AtendimentoRepository) -> None:
        self.repository = repository
        self.audit = AuditService(repository.session)

    def ensure_operator(self, actor: RequestActor) -> None:
        if "telefonista" not in actor.profiles:
            raise AuthorizationError("Somente o perfil telefonista pode operar o atendimento.")

    async def campaign_id(self, actor: RequestActor, campaign_header: str | None) -> int:
        campaign_id = await self.repository.resolve_campaign_id(actor.tenant_id, campaign_header)
        if campaign_id is None:
            raise BusinessRuleError("Nenhuma campanha ativa encontrada para o atendimento.")
        return int(campaign_id)

    async def list_rejection_reasons(self, actor: RequestActor) -> list[RejectionReason]:
        rows = await self.repository.list_rejection_reasons(actor.tenant_id)
        return [RejectionReason.model_validate(row) for row in rows]

    async def list_channels(self, actor: RequestActor) -> list[CommunicationChannel]:
        rows = await self.repository.list_channels(actor.tenant_id)
        return [CommunicationChannel.model_validate(row) for row in rows]

    async def _ensure_channel(
        self, tenant_id: int, channel_id: int, canal_outro: str | None
    ) -> dict[str, Any]:
        channel = await self.repository.get_channel(tenant_id, channel_id)
        if channel is None:
            raise BusinessRuleError("Canal de comunicacao invalido.")
        if channel["codigo"] == "outro" and not (canal_outro or "").strip():
            raise BusinessRuleError("Informe o canal utilizado.")
        return channel

    async def current(self, actor: RequestActor) -> AttendanceResponse | None:
        self.ensure_operator(actor)
        row = await self.repository.active_for_user(actor.tenant_id, actor.user_id)
        if row is None:
            return None
        return await self._hydrate(actor, row)

    async def open_queue(self, actor: RequestActor) -> AttendanceQueue:
        self.ensure_operator(actor)
        limite = await self.repository.simultaneous_limit(actor.tenant_id)
        itens = await self.repository.list_open_queue(actor.tenant_id, actor.user_id)
        return AttendanceQueue(
            itens=[AttendanceQueueItem.model_validate(item) for item in itens],
            total=len(itens),
            limite=limite,
        )

    async def start(
        self, actor: RequestActor, campaign_header: str | None
    ) -> AttendanceResponse:
        self.ensure_operator(actor)
        await self.repository.lock_operator_queue(actor.tenant_id, actor.user_id)
        limite = await self.repository.simultaneous_limit(actor.tenant_id)
        abertos = await self.repository.count_active_for_user(actor.tenant_id, actor.user_id)
        if abertos >= limite:
            raise BusinessRuleError(
                f"Limite de {limite} atendimentos simultaneos atingido. "
                "Encerre um atendimento aberto antes de assumir outro.",
                code="attendance_queue_limit_reached",
                details={"limite": limite, "abertos": abertos},
            )
        campaign_id = await self.campaign_id(actor, campaign_header)
        person_id = await self.repository.pick_eligible_person(actor.tenant_id)
        if person_id is None:
            raise BusinessRuleError("Nao ha pessoas disponiveis para atendimento no momento.")
        channel_id = await self.repository.default_channel_id(actor.tenant_id)
        if channel_id is None:
            raise BusinessRuleError("Nenhum canal de comunicacao cadastrado.")
        row = await self.repository.start_attendance(
            actor.tenant_id, campaign_id, actor.user_id, person_id, channel_id
        )
        await self.audit.record(
            action="criar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="comunicacao",
            table_name="atendimento_eleitor",
            record_id=int(row["id"]),
            after={"pessoa_id": person_id, "situacao": "em_atendimento"},
        )
        await self.repository.commit()
        return await self._hydrate(actor, row)

    async def get(self, actor: RequestActor, attendance_id: int) -> AttendanceResponse:
        row = await self._owned(actor, attendance_id, operator_only=False)
        if (
            "telefonista" in actor.profiles
            and int(row["atendente_usuario_id"]) == actor.user_id
            and row.get("situacao") == "em_atendimento"
            and row.get("finalizado_em") is None
        ):
            await self.repository.mark_viewed(actor.tenant_id, actor.user_id, attendance_id)
            await self.repository.commit()
        return await self._hydrate(actor, row)

    async def update(
        self, actor: RequestActor, attendance_id: int, payload: AttendanceUpdate
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        if payload.motivo_rejeicao_id and not await self.repository.rejection_reason_exists(
            actor.tenant_id, payload.motivo_rejeicao_id
        ):
            raise BusinessRuleError("Motivo de rejeicao invalido.")
        if payload.canal is not None:
            await self._ensure_channel(actor.tenant_id, payload.canal, payload.canal_outro)
        before = {"intencao_voto": row.get("intencao_voto")}
        updated = await self.repository.update_attendance(actor.tenant_id, attendance_id, payload)
        assert updated is not None
        if payload.intencao_voto and payload.intencao_voto != row.get("intencao_voto"):
            await self.repository.add_vote_history(
                actor.tenant_id,
                attendance_id,
                int(row["pessoa_id"]),
                actor.user_id,
                payload.intencao_voto,
                payload.motivo_rejeicao_id,
                payload.motivo_observacao,
            )
        if payload.intencao_voto:
            await self._sync_vote_confirmation(actor, updated, payload.intencao_voto)
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="comunicacao",
            table_name="atendimento_eleitor",
            record_id=attendance_id,
            before=before,
            after=payload.model_dump(exclude_unset=True),
        )
        await self.repository.commit()
        return await self._hydrate(actor, updated)

    async def update_person(
        self,
        actor: RequestActor,
        attendance_id: int,
        payload: AttendancePersonUpdate,
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        snapshot = await self.repository.update_person(
            actor.tenant_id, int(row["pessoa_id"]), actor.user_id, payload
        )
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="cadastro",
            table_name="pessoa",
            record_id=int(row["pessoa_id"]),
            before=snapshot.get("before"),
            after=snapshot.get("after"),
        )
        await self.repository.commit()
        refreshed = await self.repository.get_attendance(actor.tenant_id, attendance_id)
        assert refreshed is not None
        return await self._hydrate(actor, refreshed)

    async def add_document(
        self,
        actor: RequestActor,
        attendance_id: int,
        payload: AttendanceDocumentInput,
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        await self.repository.add_document(actor.tenant_id, int(row["pessoa_id"]), payload)
        await self.audit.record(
            action="criar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="cadastro",
            table_name="pessoa_documento",
            record_id=int(row["pessoa_id"]),
            after=payload.model_dump(),
        )
        await self.repository.commit()
        refreshed = await self.repository.get_attendance(actor.tenant_id, attendance_id)
        assert refreshed is not None
        return await self._hydrate(actor, refreshed)

    async def add_interaction(
        self,
        actor: RequestActor,
        attendance_id: int,
        payload: AttendanceInteractionInput,
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        await self.repository.add_interaction(
            actor.tenant_id,
            actor.user_id,
            int(row["pessoa_id"]),
            payload.assunto,
            payload.conteudo,
            payload.resultado,
        )
        await self.audit.record(
            action="criar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="comunicacao",
            table_name="interacao",
            record_id=int(row["pessoa_id"]),
            after=payload.model_dump(),
        )
        await self.repository.commit()
        refreshed = await self.repository.get_attendance(actor.tenant_id, attendance_id)
        assert refreshed is not None
        return await self._hydrate(actor, refreshed)

    async def add_contact(
        self,
        actor: RequestActor,
        attendance_id: int,
        payload: PessoaContatoCreate,
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        person_id = int(row["pessoa_id"])
        if await self.repository.contact_type_exists(
            actor.tenant_id, person_id, payload.tipo_contato
        ):
            raise BusinessRuleError("Ja existe um contato deste tipo.")
        item = await self.repository.add_contact(actor.tenant_id, person_id, payload)
        await self.audit.record(
            action="criar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="cadastro",
            table_name="pessoa_contato",
            record_id=int(item["id"]),
            after=payload.model_dump(),
        )
        await self.repository.commit()
        refreshed = await self.repository.get_attendance(actor.tenant_id, attendance_id)
        assert refreshed is not None
        return await self._hydrate(actor, refreshed)

    async def update_contact(
        self,
        actor: RequestActor,
        attendance_id: int,
        contact_id: int,
        payload: PessoaContatoUpdate,
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        person_id = int(row["pessoa_id"])
        current = await self.repository.contact(actor.tenant_id, person_id, contact_id)
        if current is None:
            raise ResourceNotFoundError("Contato", contact_id)
        if payload.valor is not None:
            normalized = PessoaContatoCreate(
                tipo_contato=current["tipo_contato"],
                valor=payload.valor,
                principal=(
                    payload.principal if payload.principal is not None else current["principal"]
                ),
                verificado=(
                    payload.verificado if payload.verificado is not None else current["verificado"]
                ),
                observacao=(
                    payload.observacao
                    if "observacao" in payload.model_fields_set
                    else current["observacao"]
                ),
            )
            payload.valor = normalized.valor
        item = await self.repository.update_contact(
            actor.tenant_id, person_id, contact_id, payload
        )
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="cadastro",
            table_name="pessoa_contato",
            record_id=contact_id,
            before=current,
            after=item,
        )
        await self.repository.commit()
        refreshed = await self.repository.get_attendance(actor.tenant_id, attendance_id)
        assert refreshed is not None
        return await self._hydrate(actor, refreshed)

    async def delete_contact(
        self,
        actor: RequestActor,
        attendance_id: int,
        contact_id: int,
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        person_id = int(row["pessoa_id"])
        current = await self.repository.contact(actor.tenant_id, person_id, contact_id)
        if current is None:
            raise ResourceNotFoundError("Contato", contact_id)
        await self.repository.delete_contact(actor.tenant_id, person_id, contact_id)
        await self.audit.record(
            action="excluir",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="cadastro",
            table_name="pessoa_contato",
            record_id=contact_id,
            before=current,
            after=None,
        )
        await self.repository.commit()
        refreshed = await self.repository.get_attendance(actor.tenant_id, attendance_id)
        assert refreshed is not None
        return await self._hydrate(actor, refreshed)

    async def close(
        self, actor: RequestActor, attendance_id: int, payload: AttendanceClose
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        if payload.motivo_rejeicao_id and not await self.repository.rejection_reason_exists(
            actor.tenant_id, payload.motivo_rejeicao_id
        ):
            raise BusinessRuleError("Motivo de rejeicao invalido.")
        channel = await self._ensure_channel(actor.tenant_id, payload.canal, payload.canal_outro)
        resultado = {
            "concluido": "confirmado" if payload.intencao_voto == "votara" else "concluido",
            "sem_resposta": "tentativa_sem_resposta",
            "numero_invalido": "numero_invalido",
            "interrompido": "interrompido",
        }[payload.situacao]
        if payload.intencao_voto == "nao_votara":
            resultado = "nao_apoia"
        elif payload.intencao_voto == "indeciso" and payload.situacao == "concluido":
            resultado = "indeciso"
        closed = await self.repository.close_attendance(
            actor.tenant_id, attendance_id, payload, resultado
        )
        assert closed is not None
        await self.repository.add_vote_history(
            actor.tenant_id,
            attendance_id,
            int(row["pessoa_id"]),
            actor.user_id,
            payload.intencao_voto,
            payload.motivo_rejeicao_id,
            payload.motivo_observacao,
        )
        await self._sync_vote_confirmation(actor, closed, payload.intencao_voto)
        await self.repository.add_interaction(
            actor.tenant_id,
            actor.user_id,
            int(row["pessoa_id"]),
            "Encerramento de atendimento",
            self._close_interaction_content(
                payload,
                resultado,
                channel,
                closed.get("motivo_rejeicao_nome"),
            ),
            resultado,
            payload.canal,
        )
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="comunicacao",
            table_name="atendimento_eleitor",
            record_id=attendance_id,
            before={"situacao": "em_atendimento"},
            after={"situacao": payload.situacao, "resultado": resultado},
        )
        await self.repository.commit()
        return await self._hydrate(actor, closed)

    async def invalidate(
        self, actor: RequestActor, attendance_id: int, payload: AttendanceInvalidate
    ) -> AttendanceResponse:
        row = await self._active_owned(actor, attendance_id)
        person_id = int(row["pessoa_id"])
        snapshot = await self.repository.deactivate_person(
            actor.tenant_id, person_id, actor.user_id
        )
        closed = await self.repository.invalidate_attendance(
            actor.tenant_id, attendance_id, payload
        )
        assert closed is not None
        canal_id = int(row["canal"]) if row.get("canal") else None
        await self.repository.add_interaction(
            actor.tenant_id,
            actor.user_id,
            person_id,
            "Contato inválido",
            "Cadastro marcado como contato inválido.\nMotivo: "
            + payload.motivo_inativacao.strip(),
            "contato_invalido",
            canal_id,
        )
        await self.audit.record(
            action="excluir",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="cadastro",
            table_name="pessoa",
            record_id=person_id,
            before=snapshot.get("before"),
            after=snapshot.get("after"),
        )
        await self.audit.record(
            action="editar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="comunicacao",
            table_name="atendimento_eleitor",
            record_id=attendance_id,
            after={"resultado": "contato_invalido", "motivo_inativacao": payload.motivo_inativacao},
        )
        await self.repository.commit()
        return await self._hydrate(actor, closed)

    async def indicators(
        self, actor: RequestActor, campaign_header: str | None, filters: IndicatorFilters
    ) -> AttendanceIndicators:
        if "gestor" not in actor.profiles:
            raise AuthorizationError("Somente o perfil gestor pode consultar os indicadores.")
        campaign_id = await self.campaign_id(actor, campaign_header)
        data = await self.repository.indicators(actor.tenant_id, campaign_id, filters)
        concluded = int(data.get("concluidos") or 0)
        confirmed = int(data.get("votos_confirmados") or 0)
        conversion = round((confirmed * 100 / concluded), 2) if concluded else 0.0
        return AttendanceIndicators(
            total_atendimentos=int(data.get("total_atendimentos") or 0),
            concluidos=concluded,
            sem_resposta=int(data.get("sem_resposta") or 0),
            votos_confirmados=confirmed,
            indecisos=int(data.get("indecisos") or 0),
            respostas_negativas=int(data.get("respostas_negativas") or 0),
            tempo_medio_minutos=round(float(data.get("tempo_medio_minutos") or 0), 2),
            percentual_conversao=conversion,
            por_periodo=data.get("por_periodo") or [],
            por_telefonista=data.get("por_telefonista") or [],
            por_canal=data.get("por_canal") or [],
            principais_motivos_rejeicao=data.get("principais_motivos_rejeicao") or [],
        )

    async def _sync_vote_confirmation(
        self,
        actor: RequestActor,
        row: dict[str, Any],
        intention: str,
    ) -> None:
        await self.repository.sync_vote_confirmation(
            actor.tenant_id,
            int(row["campanha_eleicao_id"]),
            int(row["pessoa_id"]),
            int(row["id"]),
            actor.user_id,
            intention,
        )

    def _close_interaction_content(
        self,
        payload: AttendanceClose,
        resultado: str,
        channel: dict[str, Any],
        reason_name: str | None,
    ) -> str:
        channel_name = str(channel.get("nome") or channel.get("codigo") or payload.canal)
        if channel.get("codigo") == "outro" and payload.canal_outro:
            channel_name = f"{channel_name} ({payload.canal_outro.strip()})"
        lines = [
            f"Canal: {channel_name}",
            f"Situação: {_STATUS_LABELS[payload.situacao]}",
            f"Intenção de voto: {_INTENTION_LABELS[payload.intencao_voto]}",
            f"Resultado: {resultado}",
        ]
        if reason_name:
            lines.append(f"Motivo: {reason_name}")
        if payload.motivo_observacao:
            lines.append(f"Complemento do motivo: {payload.motivo_observacao.strip()}")
        if payload.observacao:
            lines.append(f"Observações: {payload.observacao.strip()}")
        if payload.motivo_encerramento:
            lines.append(f"Motivo do encerramento: {payload.motivo_encerramento.strip()}")
        return "\n".join(lines)

    async def _hydrate(self, actor: RequestActor, row: dict[str, Any]) -> AttendanceResponse:
        person_id = int(row["pessoa_id"])
        person = await self.repository.person_snapshot(actor.tenant_id, person_id)
        interactions = await self.repository.list_interactions(actor.tenant_id, person_id)
        history = await self.repository.list_vote_history(actor.tenant_id, person_id)
        return AttendanceResponse.model_validate(
            {
                **row,
                "pessoa": person,
                "interacoes": interactions,
                "historico_intencao": history,
            }
        )

    async def _owned(
        self, actor: RequestActor, attendance_id: int, *, operator_only: bool
    ) -> dict[str, Any]:
        row = await self.repository.get_attendance(actor.tenant_id, attendance_id)
        if row is None:
            raise ResourceNotFoundError("Atendimento", attendance_id)
        if operator_only or "telefonista" in actor.profiles:
            if int(row["atendente_usuario_id"]) != actor.user_id and "gestor" not in actor.profiles:
                raise AuthorizationError("Este atendimento pertence a outro telefonista.")
        return row

    async def _active_owned(self, actor: RequestActor, attendance_id: int) -> dict[str, Any]:
        self.ensure_operator(actor)
        row = await self._owned(actor, attendance_id, operator_only=True)
        if row.get("situacao") != "em_atendimento" or row.get("finalizado_em") is not None:
            raise BusinessRuleError(
                "O atendimento ja foi encerrado. A edicao cadastral nao e mais permitida."
            )
        if int(row["atendente_usuario_id"]) != actor.user_id:
            raise AuthorizationError("Este atendimento pertence a outro telefonista.")
        return row
