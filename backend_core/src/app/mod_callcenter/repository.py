from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError
from app.core.repository import BaseRepository
from app.mod_callcenter.schemas import ContactCreate

CHANNEL_CODES = {
    "ligacao": "telefone",
    "whatsapp": "whatsapp",
    "presencial": "presencial",
    "outro": "outro",
}


class CallCenterRepository(BaseRepository[object]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_queue(
        self,
        tenant_id: int,
        campaign_id: int,
        *,
        leader_id: int | None,
        status: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT p.id AS pessoa_id, p.nome_completo,
                       h.lideranca_id,
                       lp.nome_completo AS lideranca_nome,
                       contacts.telefone, contacts.whatsapp,
                       COALESCE(s.status, 'nao_contatado') AS status,
                       history.ultima_tentativa_em, history.proximo_contato_em,
                       COALESCE(history.total_tentativas, 0)::int AS total_tentativas
                  FROM eleicao.campanha_liderado h
                  JOIN cadastro.pessoa p
                    ON p.id = h.pessoa_id
                   AND p.tenant_id = h.tenant_id
                   AND p.ativo AND p.excluido_em IS NULL
                  JOIN cadastro.lideranca l
                    ON l.id = h.lideranca_id AND l.tenant_id = h.tenant_id
                  JOIN cadastro.pessoa lp ON lp.id = l.pessoa_id
             LEFT JOIN eleicao.status_eleitor_eleicao s
                    ON s.tenant_id = h.tenant_id
                   AND s.campanha_eleicao_id = :campaign_id
                   AND s.pessoa_id = p.id
             LEFT JOIN LATERAL (
                       SELECT
                         max(CASE WHEN tipo_contato IN ('telefone','celular')
                                  THEN valor END) AS telefone,
                         max(CASE WHEN tipo_contato = 'whatsapp'
                                  THEN valor END) AS whatsapp
                         FROM cadastro.pessoa_contato pc
                        WHERE pc.tenant_id = p.tenant_id AND pc.pessoa_id = p.id
                    ) contacts ON true
             LEFT JOIN LATERAL (
                       SELECT max(a.finalizado_em) AS ultima_tentativa_em,
                              max(a.proximo_contato_em)
                                FILTER (WHERE a.proximo_contato_em > now()) AS proximo_contato_em,
                              count(*)::int AS total_tentativas
                         FROM comunicacao.atendimento_eleitor a
                        WHERE a.tenant_id = h.tenant_id
                          AND a.campanha_eleicao_id = :campaign_id
                          AND a.pessoa_id = p.id
                    ) history ON true
                 WHERE h.tenant_id = :tenant_id
                   AND h.campanha_eleicao_id = :campaign_id AND h.ativo
                   AND (:leader_id IS NULL OR h.lideranca_id = :leader_id)
                   AND (:status IS NULL OR COALESCE(s.status, 'nao_contatado') = :status)
              ORDER BY history.proximo_contato_em NULLS LAST,
                       history.ultima_tentativa_em NULLS FIRST, p.nome_completo
                 LIMIT :limit
                """
            ),
            {
                "tenant_id": tenant_id,
                "campaign_id": campaign_id,
                "leader_id": leader_id,
                "status": status,
                "limit": limit,
            },
        )
        return [dict(row) for row in result.mappings()]

    async def active_leader_for_person(
        self, tenant_id: int, campaign_id: int, person_id: int
    ) -> int | None:
        value = await self.session.scalar(
            text(
                "SELECT lideranca_id FROM eleicao.campanha_liderado "
                "WHERE tenant_id = :tenant_id "
                "AND campanha_eleicao_id = :campaign_id "
                "AND pessoa_id = :person_id AND ativo"
            ),
            {
                "tenant_id": tenant_id,
                "campaign_id": campaign_id,
                "person_id": person_id,
            },
        )
        return int(value) if value is not None else None

    async def resolve_channel_id(self, tenant_id: int, code: str) -> int:
        mapped = CHANNEL_CODES.get(code, code)
        channel_id = await self.session.scalar(
            text(
                """
                SELECT id
                  FROM comunicacao.canal_comunicacao
                 WHERE ativo
                   AND codigo = :code
                   AND (tenant_id IS NULL OR tenant_id = :tenant_id)
                 ORDER BY tenant_id NULLS FIRST, id
                 LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "code": mapped},
        )
        if channel_id is None:
            raise BusinessRuleError("Canal de comunicacao invalido.")
        return int(channel_id)

    async def create_contact(
        self,
        tenant_id: int,
        user_id: int,
        leader_id: int,
        payload: ContactCreate,
    ) -> dict[str, Any]:
        now = datetime.now().astimezone()
        situacao = {
            "tentativa_sem_resposta": "sem_resposta",
            "numero_invalido": "numero_invalido",
        }.get(payload.resultado, "concluido")
        values = {
            **payload.model_dump(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "leader_id": leader_id,
            "situacao": situacao,
            "canal": await self.resolve_channel_id(tenant_id, payload.canal),
            "iniciado_em": payload.iniciado_em or now,
            "finalizado_em": payload.finalizado_em or now,
        }
        result = await self.session.execute(
            text(
                """
                INSERT INTO comunicacao.atendimento_eleitor
                    (tenant_id, campanha_eleicao_id, pessoa_id, lideranca_id,
                     atendente_usuario_id, canal, situacao, resultado, observacao,
                     iniciado_em, finalizado_em, proximo_contato_em)
                VALUES
                    (:tenant_id, :campanha_eleicao_id, :pessoa_id, :leader_id,
                     :user_id, :canal, :situacao, :resultado, :observacao,
                     :iniciado_em, :finalizado_em, :proximo_contato_em)
                RETURNING id, tenant_id, campanha_eleicao_id, pessoa_id,
                          lideranca_id, atendente_usuario_id, canal, situacao, resultado,
                          observacao, iniciado_em, finalizado_em, proximo_contato_em
                """
            ),
            values,
        )
        contact = dict(result.mappings().one())
        contact["canal"] = payload.canal
        contact_id = contact["id"]
        await self.session.execute(
            text(
                """
                INSERT INTO eleicao.status_eleitor_eleicao
                    (tenant_id, campanha_eleicao_id, pessoa_id, lideranca_id,
                     status, atualizado_por)
                VALUES
                    (:tenant_id, :campanha_eleicao_id, :pessoa_id, :leader_id,
                     :resultado, :user_id)
                ON CONFLICT (campanha_eleicao_id, pessoa_id) DO UPDATE SET
                    lideranca_id = EXCLUDED.lideranca_id,
                    status = EXCLUDED.status,
                    atualizado_por = EXCLUDED.atualizado_por,
                    atualizado_em = now()
                """
            ),
            values,
        )
        if payload.resultado == "confirmado":
            await self.session.execute(
                text(
                    """
                INSERT INTO eleicao.confirmacao_operacional_voto
                    (tenant_id, campanha_eleicao_id, pessoa_id, lideranca_id,
                     atendimento_eleitor_id, informado_por_tipo,
                     informado_por_usuario_id, confirmado, observacao,
                     data_confirmacao, revogado_em, revogado_por_usuario_id)
                VALUES
                    (:tenant_id, :campanha_eleicao_id, :pessoa_id, :leader_id,
                     :contact_id, 'equipe', :user_id, TRUE, :observacao,
                     now(), NULL, NULL)
                ON CONFLICT (campanha_eleicao_id, pessoa_id) DO UPDATE SET
                    lideranca_id = EXCLUDED.lideranca_id,
                    atendimento_eleitor_id = EXCLUDED.atendimento_eleitor_id,
                    informado_por_tipo = EXCLUDED.informado_por_tipo,
                    informado_por_usuario_id = EXCLUDED.informado_por_usuario_id,
                    confirmado = EXCLUDED.confirmado,
                    observacao = EXCLUDED.observacao,
                    data_confirmacao = EXCLUDED.data_confirmacao,
                    revogado_em = EXCLUDED.revogado_em,
                    revogado_por_usuario_id = EXCLUDED.revogado_por_usuario_id,
                    atualizado_em = now()
                """
                ),
                {**values, "contact_id": contact_id},
            )
        elif payload.resultado in {"indeciso", "nao_apoia"}:
            await self.session.execute(
                text(
                    """
                    UPDATE eleicao.confirmacao_operacional_voto
                       SET confirmado = FALSE,
                           atendimento_eleitor_id = :contact_id,
                           informado_por_usuario_id = :user_id,
                           observacao = :observacao,
                           revogado_em = now(),
                           revogado_por_usuario_id = :user_id,
                           atualizado_em = now()
                     WHERE tenant_id = :tenant_id
                       AND campanha_eleicao_id = :campanha_eleicao_id
                       AND pessoa_id = :pessoa_id
                    """
                ),
                {**values, "contact_id": contact_id},
            )
        confirmed = bool(
            await self.session.scalar(
                text(
                    """
                    SELECT COALESCE(bool_or(confirmado AND revogado_em IS NULL), FALSE)
                      FROM eleicao.confirmacao_operacional_voto
                     WHERE tenant_id = :tenant_id
                       AND campanha_eleicao_id = :campanha_eleicao_id
                       AND pessoa_id = :pessoa_id
                    """
                ),
                values,
            )
        )
        contact["confirmado"] = confirmed
        return contact

    async def confirmed_report(
        self, tenant_id: int, campaign_id: int, leader_id: int | None
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT p.id AS pessoa_id, p.nome_completo, c.lideranca_id,
                       lp.nome_completo AS lideranca_nome,
                       contacts.telefone, contacts.whatsapp,
                       c.data_confirmacao, u.nome AS confirmado_por_nome,
                       c.observacao
                  FROM eleicao.confirmacao_operacional_voto c
                  JOIN cadastro.pessoa p ON p.id = c.pessoa_id
             LEFT JOIN cadastro.lideranca l ON l.id = c.lideranca_id
             LEFT JOIN cadastro.pessoa lp ON lp.id = l.pessoa_id
             LEFT JOIN auth.usuario u ON u.id = c.informado_por_usuario_id
             LEFT JOIN LATERAL (
                       SELECT
                         max(CASE WHEN tipo_contato IN ('telefone','celular')
                                  THEN valor END) AS telefone,
                         max(CASE WHEN tipo_contato = 'whatsapp'
                                  THEN valor END) AS whatsapp
                         FROM cadastro.pessoa_contato pc
                        WHERE pc.tenant_id = p.tenant_id AND pc.pessoa_id = p.id
                    ) contacts ON true
                 WHERE c.tenant_id = :tenant_id
                   AND c.campanha_eleicao_id = :campaign_id
                   AND c.confirmado AND c.revogado_em IS NULL
                   AND (:leader_id IS NULL OR c.lideranca_id = :leader_id)
              ORDER BY lp.nome_completo NULLS LAST, p.nome_completo
                """
            ),
            {
                "tenant_id": tenant_id,
                "campaign_id": campaign_id,
                "leader_id": leader_id,
            },
        )
        return [dict(row) for row in result.mappings()]

    async def campaign_exists(self, tenant_id: int, campaign_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM eleicao.campanha_eleicao "
                    "WHERE id = :id AND tenant_id = :tenant_id)"
                ),
                {"id": campaign_id, "tenant_id": tenant_id},
            )
        )

    async def commit(self) -> None:
        await self.session.commit()
