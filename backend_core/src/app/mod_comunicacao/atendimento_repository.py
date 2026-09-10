from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_comunicacao.atendimento_schemas import (
    AttendanceClose,
    AttendanceDocumentInput,
    AttendanceInvalidate,
    AttendanceManualCreate,
    AttendancePersonUpdate,
    AttendanceReasonReportFilters,
    AttendanceReportFilters,
    AttendanceUpdate,
    IndicatorFilters,
)
from app.schemas.cadastro import PessoaContatoCreate, PessoaContatoUpdate
from app.tenants.preferences import maximo_atendimentos_simultaneos


class AtendimentoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _all(self, query: str, values: dict[str, Any]) -> list[dict[str, Any]]:
        rows = (await self.session.execute(text(query), values)).mappings()
        return [dict(row) for row in rows]

    async def _one(self, query: str, values: dict[str, Any]) -> dict[str, Any] | None:
        row = (await self.session.execute(text(query), values)).mappings().first()
        return dict(row) if row else None

    async def resolve_campaign_id(self, tenant_id: int, campaign_ref: str | None) -> int | None:
        if campaign_ref:
            row = await self.session.scalar(
                text(
                    """
                    SELECT id
                      FROM eleicao.campanha_eleicao
                     WHERE tenant_id = :tenant_id
                       AND (
                            id::text = :ref
                            OR uuid_publico::text = :ref
                       )
                     LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "ref": campaign_ref},
            )
            if row is not None:
                return int(row)
        return await self.session.scalar(
            text(
                """
                SELECT id
                  FROM eleicao.campanha_eleicao
                 WHERE tenant_id = :tenant_id
                   AND ativa
                   AND data_encerramento IS NULL
                 ORDER BY data_ativacao DESC NULLS LAST, id DESC
                 LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )

    async def list_rejection_reasons(self, tenant_id: int) -> list[dict[str, Any]]:
        return await self._all(
            """
            SELECT id, codigo, nome, descricao
              FROM comunicacao.motivo_rejeicao_voto
             WHERE ativo
               AND (tenant_id IS NULL OR tenant_id = :tenant_id)
             ORDER BY tenant_id NULLS FIRST, nome
            """,
            {"tenant_id": tenant_id},
        )

    async def list_channels(self, tenant_id: int) -> list[dict[str, Any]]:
        return await self._all(
            """
            SELECT id, codigo, nome, descricao
              FROM comunicacao.canal_comunicacao
             WHERE ativo
               AND (tenant_id IS NULL OR tenant_id = :tenant_id)
             ORDER BY tenant_id NULLS FIRST, nome
            """,
            {"tenant_id": tenant_id},
        )

    async def get_channel(self, tenant_id: int, channel_id: int) -> dict[str, Any] | None:
        return await self._one(
            """
            SELECT id, codigo, nome, descricao
              FROM comunicacao.canal_comunicacao
             WHERE id = :id
               AND ativo
               AND (tenant_id IS NULL OR tenant_id = :tenant_id)
            """,
            {"tenant_id": tenant_id, "id": channel_id},
        )

    async def default_channel_id(self, tenant_id: int) -> int | None:
        channel_id = await self.session.scalar(
            text(
                """
                SELECT id
                  FROM comunicacao.canal_comunicacao
                 WHERE ativo
                   AND (tenant_id IS NULL OR tenant_id = :tenant_id)
                 ORDER BY CASE codigo
                            WHEN 'telefone' THEN 0
                            WHEN 'whatsapp' THEN 1
                            ELSE 2
                          END,
                          nome
                 LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        return int(channel_id) if channel_id is not None else None

    async def rejection_reason_exists(self, tenant_id: int, reason_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    """
                    SELECT EXISTS(
                        SELECT 1
                          FROM comunicacao.motivo_rejeicao_voto
                         WHERE id = :id
                           AND ativo
                           AND (tenant_id IS NULL OR tenant_id = :tenant_id)
                    )
                    """
                ),
                {"id": reason_id, "tenant_id": tenant_id},
            )
        )

    async def simultaneous_limit(self, tenant_id: int) -> int:
        raw = await self.session.scalar(
            text(
                """
                SELECT preferencias
                  FROM public.tenant_configuracao
                 WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        if isinstance(raw, dict):
            preferencias = raw
        elif isinstance(raw, str):
            preferencias = json.loads(raw)
        else:
            preferencias = {}
        return maximo_atendimentos_simultaneos(preferencias)

    async def count_active_for_user(self, tenant_id: int, user_id: int) -> int:
        count = await self.session.scalar(
            text(
                """
                SELECT count(*)::int
                  FROM comunicacao.atendimento_eleitor
                 WHERE tenant_id = :tenant_id
                   AND atendente_usuario_id = :user_id
                   AND situacao = 'em_atendimento'
                   AND finalizado_em IS NULL
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return int(count or 0)

    async def lock_operator_queue(self, tenant_id: int, user_id: int) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"attendance-queue:{tenant_id}:{user_id}"},
        )

    async def active_for_user(self, tenant_id: int, user_id: int) -> dict[str, Any] | None:
        queue = await self.list_open_queue(tenant_id, user_id)
        if not queue:
            return None
        return await self.get_attendance(tenant_id, int(queue[0]["id"]))

    async def list_open_queue(self, tenant_id: int, user_id: int) -> list[dict[str, Any]]:
        return await self._all(
            """
            SELECT a.id,
                   a.situacao,
                   a.iniciado_em,
                   p.nome_completo,
                   COALESCE(whatsapp.valor, celular.valor, telefone.valor) AS whatsapp,
                   last_i.data_interacao AS ultima_interacao_em,
                   last_i.conteudo AS ultima_mensagem,
                   last_i.direcao AS ultima_direcao,
                   COALESCE(unread.quantidade, 0) AS mensagens_nao_lidas
              FROM comunicacao.atendimento_eleitor a
              JOIN cadastro.pessoa p
                ON p.id = a.pessoa_id AND p.tenant_id = a.tenant_id
              LEFT JOIN LATERAL (
                    SELECT pc.valor
                      FROM cadastro.pessoa_contato pc
                     WHERE pc.tenant_id = a.tenant_id
                       AND pc.pessoa_id = a.pessoa_id
                       AND pc.tipo_contato = 'whatsapp'
                     ORDER BY pc.principal DESC, pc.id
                     LIMIT 1
              ) whatsapp ON TRUE
              LEFT JOIN LATERAL (
                    SELECT pc.valor
                      FROM cadastro.pessoa_contato pc
                     WHERE pc.tenant_id = a.tenant_id
                       AND pc.pessoa_id = a.pessoa_id
                       AND pc.tipo_contato = 'celular'
                     ORDER BY pc.principal DESC, pc.id
                     LIMIT 1
              ) celular ON TRUE
              LEFT JOIN LATERAL (
                    SELECT pc.valor
                      FROM cadastro.pessoa_contato pc
                     WHERE pc.tenant_id = a.tenant_id
                       AND pc.pessoa_id = a.pessoa_id
                       AND pc.tipo_contato = 'telefone'
                     ORDER BY pc.principal DESC, pc.id
                     LIMIT 1
              ) telefone ON TRUE
              LEFT JOIN LATERAL (
                    SELECT i.data_interacao, i.conteudo, i.direcao
                      FROM comunicacao.interacao i
                     WHERE i.tenant_id = a.tenant_id
                       AND i.pessoa_id = a.pessoa_id
                     ORDER BY i.data_interacao DESC, i.id DESC
                     LIMIT 1
              ) last_i ON TRUE
              LEFT JOIN LATERAL (
                    SELECT count(*)::int AS quantidade
                      FROM comunicacao.interacao i
                     WHERE i.tenant_id = a.tenant_id
                       AND i.pessoa_id = a.pessoa_id
                       AND i.direcao = 'entrada'
                       AND i.data_interacao > COALESCE(a.ultima_visualizacao_em, a.iniciado_em)
              ) unread ON TRUE
             WHERE a.tenant_id = :tenant_id
               AND a.atendente_usuario_id = :user_id
               AND a.situacao = 'em_atendimento'
               AND a.finalizado_em IS NULL
             ORDER BY COALESCE(unread.quantidade, 0) > 0 DESC,
                      COALESCE(last_i.data_interacao, a.iniciado_em) DESC,
                      a.id DESC
            """,
            {"tenant_id": tenant_id, "user_id": user_id},
        )

    async def mark_viewed(self, tenant_id: int, user_id: int, attendance_id: int) -> None:
        await self.session.execute(
            text(
                """
                UPDATE comunicacao.atendimento_eleitor
                   SET ultima_visualizacao_em = now()
                 WHERE tenant_id = :tenant_id
                   AND id = :id
                   AND atendente_usuario_id = :user_id
                   AND situacao = 'em_atendimento'
                   AND finalizado_em IS NULL
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "id": attendance_id},
        )

    async def get_attendance(
        self, tenant_id: int, attendance_id: int
    ) -> dict[str, Any] | None:
        return await self._one(
            self._attendance_select()
            + " WHERE a.tenant_id = :tenant_id AND a.id = :id",
            {"tenant_id": tenant_id, "id": attendance_id},
        )

    async def pick_eligible_person(self, tenant_id: int) -> int | None:
        """Sorteia pessoa ativa sem atendimento aberto.

        Quem ja foi encerrado como concluido ou numero_invalido nao volta a
        fila. Interrompido e sem_resposta permanecem elegiveis.
        """
        person_id = await self.session.scalar(
            text(
                """
                SELECT p.id
                  FROM cadastro.pessoa p
                 WHERE p.tenant_id = :tenant_id
                   AND p.ativo
                   AND p.excluido_em IS NULL
                   AND NOT EXISTS (
                        SELECT 1
                          FROM comunicacao.atendimento_eleitor a
                         WHERE a.tenant_id = p.tenant_id
                           AND a.pessoa_id = p.id
                           AND (
                                (a.situacao = 'em_atendimento' AND a.finalizado_em IS NULL)
                                OR a.situacao IN ('concluido', 'numero_invalido')
                           )
                   )
                 ORDER BY random()
                 LIMIT 1
                 FOR UPDATE SKIP LOCKED
                """
            ),
            {"tenant_id": tenant_id},
        )
        return int(person_id) if person_id is not None else None

    @staticmethod
    def phone_digits(value: str) -> list[str]:
        digits = "".join(character for character in value if character.isdigit())
        local = digits[2:] if digits.startswith("55") and len(digits) in {12, 13} else digits
        variants = {digits, local, f"55{local}"}
        return [item for item in variants if item]

    async def find_person_by_phone(
        self, tenant_id: int, phone: str
    ) -> dict[str, Any] | None:
        variants = self.phone_digits(phone)
        if not variants:
            return None
        phone_1, phone_2, phone_3 = (variants + variants[:1] * 2)[:3]
        return await self._one(
            """
            SELECT p.id,
                   p.nome_completo,
                   a.id AS atendimento_id,
                   a.atendente_usuario_id,
                   COALESCE(u.nome, 'outro telefonista') AS atendente_nome
              FROM cadastro.pessoa_contato pc
              JOIN cadastro.pessoa p
                ON p.id = pc.pessoa_id AND p.tenant_id = pc.tenant_id
              LEFT JOIN comunicacao.atendimento_eleitor a
                ON a.tenant_id = p.tenant_id
               AND a.pessoa_id = p.id
               AND a.situacao = 'em_atendimento'
               AND a.finalizado_em IS NULL
              LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
             WHERE pc.tenant_id = :tenant_id
               AND pc.tipo_contato IN ('telefone', 'celular', 'whatsapp')
               AND p.excluido_em IS NULL
               AND regexp_replace(pc.valor, '\\D', '', 'g')
                   IN (:phone_1, :phone_2, :phone_3)
             ORDER BY a.id NULLS LAST, p.id
             LIMIT 1
            """,
            {
                "tenant_id": tenant_id,
                "phone_1": phone_1,
                "phone_2": phone_2,
                "phone_3": phone_3,
            },
        )

    async def create_manual_person(
        self,
        tenant_id: int,
        user_id: int,
        payload: AttendanceManualCreate,
    ) -> int:
        person_id = await self.session.scalar(
            text(
                """
                INSERT INTO cadastro.pessoa (
                    tenant_id, nome_completo, sexo, data_nascimento,
                    origem_cadastro, ativo, criado_por, atualizado_por,
                    criado_em, atualizado_em
                )
                VALUES (
                    :tenant_id, :nome_completo, :sexo, :data_nascimento,
                    'call_center', TRUE, :user_id, :user_id, now(), now()
                )
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "nome_completo": payload.nome_completo,
                "sexo": payload.sexo,
                "data_nascimento": payload.data_nascimento,
            },
        )
        created_id = int(person_id)
        phone_type = "celular" if len(payload.telefone) == 11 else "telefone"
        await self.add_contact(
            tenant_id,
            created_id,
            PessoaContatoCreate(
                tipo_contato=phone_type,
                valor=payload.telefone,
                principal=True,
            ),
        )
        if payload.email:
            await self.add_contact(
                tenant_id,
                created_id,
                PessoaContatoCreate(
                    tipo_contato="email",
                    valor=payload.email,
                    principal=True,
                ),
            )
        return created_id

    async def start_attendance(
        self,
        tenant_id: int,
        campaign_id: int,
        user_id: int,
        person_id: int,
        channel_id: int,
    ) -> dict[str, Any]:
        row = (
            await self.session.execute(
                text(
                    """
                    INSERT INTO comunicacao.atendimento_eleitor
                        (tenant_id, campanha_eleicao_id, pessoa_id, atendente_usuario_id,
                         canal, situacao, resultado, iniciado_em, finalizado_em,
                         ultima_visualizacao_em)
                    VALUES
                        (:tenant_id, :campaign_id, :person_id, :user_id,
                         :channel_id, 'em_atendimento', NULL, now(), NULL, now())
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "campaign_id": campaign_id,
                    "person_id": person_id,
                    "user_id": user_id,
                    "channel_id": channel_id,
                },
            )
        ).scalar_one()
        item = await self.get_attendance(tenant_id, int(row))
        assert item is not None
        return item

    async def search_attendances(
        self,
        tenant_id: int,
        campaign_id: int,
        nome: str | None,
        telefone: str | None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
        }
        clauses = [
            "a.tenant_id = :tenant_id",
            "a.campanha_eleicao_id = :campaign_id",
        ]
        if nome:
            clauses.append("p.nome_completo ILIKE :nome")
            params["nome"] = f"%{nome}%"
        if telefone:
            variants = self.phone_digits(telefone)
            phone_1, phone_2, phone_3 = (variants + variants[:1] * 2)[:3]
            params.update(
                {
                    "phone_1": phone_1,
                    "phone_2": phone_2,
                    "phone_3": phone_3,
                    "phone_local": telefone,
                }
            )
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                      FROM cadastro.pessoa_contato pc
                     WHERE pc.tenant_id = p.tenant_id
                       AND pc.pessoa_id = p.id
                       AND pc.tipo_contato IN ('telefone', 'celular', 'whatsapp')
                       AND (
                            regexp_replace(pc.valor, '\\D', '', 'g')
                                IN (:phone_1, :phone_2, :phone_3)
                            OR regexp_replace(pc.valor, '\\D', '', 'g')
                                LIKE '%' || :phone_local
                       )
                )
                """
            )
        return await self._all(
            f"""
            SELECT a.id,
                   a.pessoa_id,
                   p.nome_completo,
                   COALESCE(whatsapp.valor, celular.valor, telefone.valor) AS telefone,
                   a.situacao,
                   a.iniciado_em,
                   a.finalizado_em,
                   a.atendente_usuario_id,
                   COALESCE(u.nome, 'Telefonista') AS atendente_nome,
                   (p.ativo AND p.excluido_em IS NULL) AS pessoa_ativa,
                   EXISTS (
                        SELECT 1
                          FROM comunicacao.atendimento_eleitor terminal
                         WHERE terminal.tenant_id = a.tenant_id
                           AND terminal.pessoa_id = a.pessoa_id
                           AND terminal.situacao IN ('concluido', 'numero_invalido')
                   ) AS possui_encerramento_definitivo,
                   aberto.id AS atendimento_aberto_id,
                   aberto.atendente_usuario_id AS atendimento_aberto_atendente_id
              FROM comunicacao.atendimento_eleitor a
              JOIN cadastro.pessoa p
                ON p.id = a.pessoa_id AND p.tenant_id = a.tenant_id
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
         LEFT JOIN comunicacao.atendimento_eleitor aberto
                ON aberto.tenant_id = a.tenant_id
               AND aberto.pessoa_id = a.pessoa_id
               AND aberto.situacao = 'em_atendimento'
               AND aberto.finalizado_em IS NULL
              LEFT JOIN LATERAL (
                    SELECT pc.valor
                      FROM cadastro.pessoa_contato pc
                     WHERE pc.tenant_id = a.tenant_id
                       AND pc.pessoa_id = a.pessoa_id
                       AND pc.tipo_contato = 'whatsapp'
                     ORDER BY pc.principal DESC, pc.id
                     LIMIT 1
              ) whatsapp ON TRUE
              LEFT JOIN LATERAL (
                    SELECT pc.valor
                      FROM cadastro.pessoa_contato pc
                     WHERE pc.tenant_id = a.tenant_id
                       AND pc.pessoa_id = a.pessoa_id
                       AND pc.tipo_contato = 'celular'
                     ORDER BY pc.principal DESC, pc.id
                     LIMIT 1
              ) celular ON TRUE
              LEFT JOIN LATERAL (
                    SELECT pc.valor
                      FROM cadastro.pessoa_contato pc
                     WHERE pc.tenant_id = a.tenant_id
                       AND pc.pessoa_id = a.pessoa_id
                       AND pc.tipo_contato = 'telefone'
                     ORDER BY pc.principal DESC, pc.id
                     LIMIT 1
              ) telefone ON TRUE
             WHERE {" AND ".join(clauses)}
             ORDER BY CASE a.situacao
                        WHEN 'sem_resposta' THEN 0
                        WHEN 'interrompido' THEN 1
                        WHEN 'em_atendimento' THEN 2
                        ELSE 3
                      END,
                      a.iniciado_em DESC,
                      a.id DESC
             LIMIT 20
            """,
            params,
        )

    async def find_open_for_person(
        self, tenant_id: int, person_id: int
    ) -> dict[str, Any] | None:
        return await self._one(
            """
            SELECT a.id,
                   a.atendente_usuario_id,
                   COALESCE(u.nome, 'outro telefonista') AS atendente_nome
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
             WHERE a.tenant_id = :tenant_id
               AND a.pessoa_id = :person_id
               AND a.situacao = 'em_atendimento'
               AND a.finalizado_em IS NULL
             LIMIT 1
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )

    async def person_has_terminal_attendance(
        self, tenant_id: int, person_id: int
    ) -> bool:
        exists = await self.session.scalar(
            text(
                """
                SELECT 1
                  FROM comunicacao.atendimento_eleitor
                 WHERE tenant_id = :tenant_id
                   AND pessoa_id = :person_id
                   AND situacao IN ('concluido', 'numero_invalido')
                 LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        return exists is not None

    async def person_is_active(self, tenant_id: int, person_id: int) -> bool:
        active = await self.session.scalar(
            text(
                """
                SELECT p.ativo AND p.excluido_em IS NULL
                  FROM cadastro.pessoa p
                 WHERE p.tenant_id = :tenant_id AND p.id = :person_id
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        return bool(active)

    async def reopen_attendance(
        self,
        tenant_id: int,
        attendance_id: int,
        user_id: int,
    ) -> dict[str, Any] | None:
        await self.session.execute(
            text(
                """
                UPDATE comunicacao.atendimento_eleitor
                   SET situacao = 'em_atendimento',
                       finalizado_em = NULL,
                       resultado = NULL,
                       atendente_usuario_id = :user_id,
                       ultima_visualizacao_em = now()
                 WHERE tenant_id = :tenant_id
                   AND id = :id
                   AND situacao IN ('sem_resposta', 'interrompido')
                """
            ),
            {"tenant_id": tenant_id, "id": attendance_id, "user_id": user_id},
        )
        return await self.get_attendance(tenant_id, attendance_id)

    async def update_attendance(
        self, tenant_id: int, attendance_id: int, payload: AttendanceUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return await self.get_attendance(tenant_id, attendance_id)
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        await self.session.execute(
            text(
                f"""
                UPDATE comunicacao.atendimento_eleitor
                   SET {assignments}
                 WHERE tenant_id = :tenant_id
                   AND id = :id
                   AND situacao = 'em_atendimento'
                """
            ),
            {"tenant_id": tenant_id, "id": attendance_id, **values},
        )
        return await self.get_attendance(tenant_id, attendance_id)

    async def close_attendance(
        self,
        tenant_id: int,
        attendance_id: int,
        payload: AttendanceClose,
        resultado: str,
    ) -> dict[str, Any] | None:
        await self.session.execute(
            text(
                """
                UPDATE comunicacao.atendimento_eleitor
                   SET situacao = :situacao,
                       canal = :canal,
                       canal_outro = :canal_outro,
                       intencao_voto = :intencao_voto,
                       motivo_rejeicao_id = :motivo_rejeicao_id,
                       motivo_observacao = :motivo_observacao,
                       observacao = :observacao,
                       motivo_encerramento = :motivo_encerramento,
                       resultado = :resultado,
                       finalizado_em = now()
                 WHERE tenant_id = :tenant_id
                   AND id = :id
                   AND situacao = 'em_atendimento'
                """
            ),
            {
                "tenant_id": tenant_id,
                "id": attendance_id,
                "resultado": resultado,
                **payload.model_dump(),
            },
        )
        return await self.get_attendance(tenant_id, attendance_id)

    async def invalidate_attendance(
        self, tenant_id: int, attendance_id: int, payload: AttendanceInvalidate
    ) -> dict[str, Any] | None:
        await self.session.execute(
            text(
                """
                UPDATE comunicacao.atendimento_eleitor
                   SET situacao = 'numero_invalido',
                       resultado = 'contato_invalido',
                       motivo_inativacao = :motivo_inativacao,
                       motivo_encerramento = :motivo_inativacao,
                       finalizado_em = now()
                 WHERE tenant_id = :tenant_id
                   AND id = :id
                   AND situacao = 'em_atendimento'
                """
            ),
            {
                "tenant_id": tenant_id,
                "id": attendance_id,
                **payload.model_dump(),
            },
        )
        return await self.get_attendance(tenant_id, attendance_id)

    async def deactivate_person(
        self, tenant_id: int, person_id: int, user_id: int
    ) -> dict[str, Any]:
        before = await self._one(
            """
            SELECT id, nome_completo, ativo, excluido_em
              FROM cadastro.pessoa
             WHERE tenant_id = :tenant_id AND id = :person_id
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        await self.session.execute(
            text(
                """
                UPDATE cadastro.pessoa
                   SET ativo = FALSE,
                       excluido_em = now(),
                       atualizado_em = now(),
                       atualizado_por = :user_id
                 WHERE tenant_id = :tenant_id
                   AND id = :person_id
                   AND excluido_em IS NULL
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id, "user_id": user_id},
        )
        after = await self._one(
            """
            SELECT id, nome_completo, ativo, excluido_em
              FROM cadastro.pessoa
             WHERE tenant_id = :tenant_id AND id = :person_id
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        return {"before": before, "after": after}

    async def person_snapshot(self, tenant_id: int, person_id: int) -> dict[str, Any]:
        person = await self._one(
            """
            SELECT p.id, p.nome_completo, p.nome_social, p.apelido, p.sexo, p.data_nascimento,
                   p.observacoes, p.foto_arquivo_id,
                   contacts.telefone, contacts.email,
                   e.titulo_eleitor, e.codigo_municipio_ibge, e.zona_eleitoral_id,
                   e.secao_eleitoral_id, e.local_votacao_id,
                   ze.numero_zona::text AS zona_eleitoral,
                   se.numero_secao::text AS secao_eleitoral,
                   lv.nome AS local_votacao
              FROM cadastro.pessoa p
         LEFT JOIN cadastro.eleitor e
                ON e.pessoa_id = p.id AND e.tenant_id = p.tenant_id
         LEFT JOIN global.zona_eleitoral ze ON ze.id = e.zona_eleitoral_id
         LEFT JOIN global.secao_eleitoral se ON se.id = e.secao_eleitoral_id
         LEFT JOIN global.local_votacao lv ON lv.id = e.local_votacao_id
         LEFT JOIN LATERAL (
                   SELECT
                     max(pc.valor) FILTER (
                        WHERE pc.tipo_contato IN ('telefone', 'celular', 'whatsapp')
                     ) AS telefone,
                     max(pc.valor) FILTER (WHERE pc.tipo_contato = 'email') AS email
                     FROM cadastro.pessoa_contato pc
                    WHERE pc.tenant_id = p.tenant_id AND pc.pessoa_id = p.id
                ) contacts ON TRUE
             WHERE p.tenant_id = :tenant_id AND p.id = :person_id
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        if person is None:
            return {}
        tags = await self._all(
            """
            SELECT t.nome
              FROM cadastro.pessoa_tag pt
              JOIN cadastro.tag t ON t.id = pt.tag_id
             WHERE pt.tenant_id = :tenant_id AND pt.pessoa_id = :person_id
             ORDER BY t.nome
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        frentes = await self._all(
            """
            SELECT c.nome
              FROM cadastro.pessoa_comunidade pc
              JOIN cadastro.comunidade c ON c.id = pc.comunidade_id
             WHERE pc.tenant_id = :tenant_id AND pc.pessoa_id = :person_id
             ORDER BY c.nome
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        nucleos = await self._all(
            """
            SELECT nf.nome
              FROM cadastro.pessoa_nucleo_familiar pnf
              JOIN cadastro.nucleo_familiar nf ON nf.id = pnf.nucleo_familiar_id
             WHERE pnf.tenant_id = :tenant_id AND pnf.pessoa_id = :person_id
             ORDER BY nf.nome
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        contacts = await self.list_contacts(tenant_id, person_id)
        person["tags"] = [row["nome"] for row in tags if row.get("nome")]
        person["frentes"] = [row["nome"] for row in frentes if row.get("nome")]
        person["nucleos_familiares"] = [row["nome"] for row in nucleos if row.get("nome")]
        person["contatos"] = contacts
        return person

    async def list_contacts(self, tenant_id: int, person_id: int) -> list[dict[str, Any]]:
        return await self._all(
            """
            SELECT id, tenant_id, pessoa_id, tipo_contato, valor, principal,
                   verificado, observacao, criado_em
              FROM cadastro.pessoa_contato
             WHERE tenant_id = :tenant_id AND pessoa_id = :person_id
             ORDER BY principal DESC, id
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )

    async def contact(
        self, tenant_id: int, person_id: int, contact_id: int
    ) -> dict[str, Any] | None:
        return await self._one(
            """
            SELECT id, tenant_id, pessoa_id, tipo_contato, valor, principal,
                   verificado, observacao, criado_em
              FROM cadastro.pessoa_contato
             WHERE tenant_id = :tenant_id AND pessoa_id = :person_id AND id = :contact_id
            """,
            {
                "tenant_id": tenant_id,
                "person_id": person_id,
                "contact_id": contact_id,
            },
        )

    async def contact_type_exists(
        self, tenant_id: int, person_id: int, contact_type: str, exclude_id: int | None = None
    ) -> bool:
        value = await self.session.scalar(
            text(
                """
                SELECT 1
                  FROM cadastro.pessoa_contato
                 WHERE tenant_id = :tenant_id
                   AND pessoa_id = :person_id
                   AND tipo_contato = :contact_type
                   AND (CAST(:exclude_id AS BIGINT) IS NULL OR id <> CAST(:exclude_id AS BIGINT))
                 LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "person_id": person_id,
                "contact_type": contact_type,
                "exclude_id": exclude_id,
            },
        )
        return value is not None

    async def add_contact(
        self, tenant_id: int, person_id: int, payload: PessoaContatoCreate
    ) -> dict[str, Any]:
        if payload.principal:
            await self._clear_principal_contacts(tenant_id, person_id, payload.tipo_contato)
        row_id = await self.session.scalar(
            text(
                """
                INSERT INTO cadastro.pessoa_contato (
                    tenant_id, pessoa_id, tipo_contato, valor, principal,
                    verificado, observacao, criado_em
                )
                VALUES (
                    :tenant_id, :person_id, :tipo_contato, :valor, :principal,
                    :verificado, :observacao, now()
                )
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "person_id": person_id,
                **payload.model_dump(),
            },
        )
        item = await self.contact(tenant_id, person_id, int(row_id))
        assert item is not None
        return item

    async def update_contact(
        self,
        tenant_id: int,
        person_id: int,
        contact_id: int,
        payload: PessoaContatoUpdate,
    ) -> dict[str, Any]:
        data = payload.model_dump(exclude_unset=True)
        if data.get("principal"):
            current = await self.contact(tenant_id, person_id, contact_id)
            if current is not None:
                await self._clear_principal_contacts(
                    tenant_id, person_id, str(current["tipo_contato"]), contact_id
                )
        if data:
            assignments = ", ".join(f"{key} = :{key}" for key in data)
            await self.session.execute(
                text(
                    f"""
                    UPDATE cadastro.pessoa_contato
                       SET {assignments}
                     WHERE tenant_id = :tenant_id
                       AND pessoa_id = :person_id
                       AND id = :contact_id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "person_id": person_id,
                    "contact_id": contact_id,
                    **data,
                },
            )
        item = await self.contact(tenant_id, person_id, contact_id)
        assert item is not None
        return item

    async def delete_contact(self, tenant_id: int, person_id: int, contact_id: int) -> None:
        await self.session.execute(
            text(
                """
                DELETE FROM cadastro.pessoa_contato
                 WHERE tenant_id = :tenant_id
                   AND pessoa_id = :person_id
                   AND id = :contact_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "person_id": person_id,
                "contact_id": contact_id,
            },
        )

    async def active_hierarchy_leader(
        self, tenant_id: int, campaign_id: int, person_id: int
    ) -> int | None:
        value = await self.session.scalar(
            text(
                """
                SELECT lideranca_superior_id
                  FROM cadastro.hierarquia_lideranca
                 WHERE tenant_id = :tenant_id
                   AND campanha_eleicao_id = :campaign_id
                   AND pessoa_subordinada_id = :person_id
                   AND ativo
                   AND (data_fim IS NULL OR data_fim >= CURRENT_DATE)
                 ORDER BY data_inicio DESC, id DESC
                 LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "campaign_id": campaign_id,
                "person_id": person_id,
            },
        )
        return int(value) if value is not None else None

    async def sync_vote_confirmation(
        self,
        tenant_id: int,
        campaign_id: int,
        person_id: int,
        attendance_id: int,
        user_id: int,
        intention: str,
    ) -> None:
        leader_id = await self.active_hierarchy_leader(tenant_id, campaign_id, person_id)
        values = {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "person_id": person_id,
            "attendance_id": attendance_id,
            "user_id": user_id,
            "leader_id": leader_id,
        }
        if intention == "votara":
            if leader_id is None:
                return
            await self.session.execute(
                text(
                    """
                    INSERT INTO eleicao.confirmacao_operacional_voto
                        (tenant_id, campanha_eleicao_id, pessoa_id, lideranca_id,
                         atendimento_eleitor_id, informado_por_tipo,
                         informado_por_usuario_id, confirmado, observacao,
                         data_confirmacao, revogado_em, revogado_por_usuario_id)
                    VALUES
                        (:tenant_id, :campaign_id, :person_id, :leader_id,
                         :attendance_id, 'equipe', :user_id, TRUE,
                         'Confirmado no atendimento.',
                         now(), NULL, NULL)
                    ON CONFLICT (campanha_eleicao_id, pessoa_id) DO UPDATE SET
                        lideranca_id = EXCLUDED.lideranca_id,
                        atendimento_eleitor_id = EXCLUDED.atendimento_eleitor_id,
                        informado_por_tipo = EXCLUDED.informado_por_tipo,
                        informado_por_usuario_id = EXCLUDED.informado_por_usuario_id,
                        confirmado = TRUE,
                        observacao = EXCLUDED.observacao,
                        data_confirmacao = EXCLUDED.data_confirmacao,
                        revogado_em = NULL,
                        revogado_por_usuario_id = NULL,
                        atualizado_em = now()
                    """
                ),
                values,
            )
            return
        await self.session.execute(
            text(
                """
                UPDATE eleicao.confirmacao_operacional_voto
                   SET confirmado = FALSE,
                       atendimento_eleitor_id = :attendance_id,
                       informado_por_usuario_id = :user_id,
                       observacao = 'Intencao alterada no atendimento.',
                       revogado_em = now(),
                       revogado_por_usuario_id = :user_id,
                       atualizado_em = now()
                 WHERE tenant_id = :tenant_id
                   AND campanha_eleicao_id = :campaign_id
                   AND pessoa_id = :person_id
                   AND confirmado
                   AND revogado_em IS NULL
                """
            ),
            values,
        )

    async def update_person(
        self,
        tenant_id: int,
        person_id: int,
        user_id: int,
        payload: AttendancePersonUpdate,
    ) -> dict[str, Any]:
        before = await self.person_snapshot(tenant_id, person_id)
        data = payload.model_dump(exclude_unset=True)
        person_fields = {
            key: data[key]
            for key in ("nome_completo", "data_nascimento", "sexo")
            if key in data
        }
        if person_fields:
            assignments = ", ".join(f"{key} = :{key}" for key in person_fields)
            await self.session.execute(
                text(
                    f"""
                    UPDATE cadastro.pessoa
                       SET {assignments},
                           atualizado_em = now(),
                           atualizado_por = :user_id
                     WHERE tenant_id = :tenant_id AND id = :person_id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "person_id": person_id,
                    "user_id": user_id,
                    **person_fields,
                },
            )
        voter_fields = {
            key: data[key]
            for key in (
                "titulo_eleitor",
                "codigo_municipio_ibge",
                "zona_eleitoral_id",
                "secao_eleitoral_id",
                "local_votacao_id",
            )
            if key in data
        }
        if voter_fields:
            columns = ["tenant_id", "pessoa_id", *voter_fields]
            values_sql = ", ".join(f":{key}" for key in columns)
            updates = ", ".join(
                f"{key} = EXCLUDED.{key}" for key in voter_fields
            )
            await self.session.execute(
                text(
                    f"""
                    INSERT INTO cadastro.eleitor
                        ({", ".join(columns)}, criado_em, atualizado_em)
                    VALUES
                        ({values_sql}, now(), now())
                    ON CONFLICT (pessoa_id) DO UPDATE SET
                        {updates},
                        atualizado_em = now()
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "pessoa_id": person_id,
                    **voter_fields,
                },
            )
        after = await self.person_snapshot(tenant_id, person_id)
        return {"before": before, "after": after}

    async def add_document(
        self, tenant_id: int, person_id: int, payload: AttendanceDocumentInput
    ) -> None:
        await self.session.execute(
            text(
                """
                INSERT INTO cadastro.pessoa_documento (
                    tenant_id, pessoa_id, tipo_documento, numero,
                    orgao_emissor, uf_emissor, criado_em
                )
                VALUES (
                    :tenant_id, :person_id, :tipo_documento, :numero,
                    :orgao_emissor, :uf_emissor, now()
                )
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id, **payload.model_dump()},
        )

    async def add_interaction(
        self,
        tenant_id: int,
        user_id: int,
        person_id: int,
        assunto: str | None,
        conteudo: str,
        resultado: str | None,
        canal_id: int | None = None,
    ) -> dict[str, Any]:
        row_id = await self.session.scalar(
            text(
                """
                INSERT INTO comunicacao.interacao
                    (tenant_id, pessoa_id, canal_comunicacao_id, direcao, assunto,
                     conteudo, resultado, data_interacao, registrado_por)
                VALUES
                    (:tenant_id, :person_id, :canal_id, 'saida', :assunto,
                     :conteudo, :resultado, now(), :user_id)
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "person_id": person_id,
                "canal_id": canal_id,
                "assunto": assunto,
                "conteudo": conteudo,
                "resultado": resultado,
            },
        )
        item = await self._one(
            """
            SELECT i.id, i.assunto, i.conteudo, i.resultado, i.data_interacao,
                   u.nome AS registrado_por_nome
              FROM comunicacao.interacao i
         LEFT JOIN auth.usuario u ON u.id = i.registrado_por
             WHERE i.tenant_id = :tenant_id AND i.id = :id
            """,
            {"tenant_id": tenant_id, "id": int(row_id)},
        )
        assert item is not None
        return item

    async def list_interactions(self, tenant_id: int, person_id: int) -> list[dict[str, Any]]:
        return await self._all(
            """
            SELECT i.id, i.assunto, i.conteudo, i.resultado, i.data_interacao,
                   u.nome AS registrado_por_nome
              FROM comunicacao.interacao i
         LEFT JOIN auth.usuario u ON u.id = i.registrado_por
             WHERE i.tenant_id = :tenant_id AND i.pessoa_id = :person_id
             ORDER BY i.data_interacao DESC, i.id DESC
             LIMIT 30
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )

    async def add_vote_history(
        self,
        tenant_id: int,
        attendance_id: int,
        person_id: int,
        user_id: int,
        intention: str,
        reason_id: int | None,
        reason_note: str | None,
    ) -> None:
        await self.session.execute(
            text(
                """
                INSERT INTO comunicacao.intencao_voto_historico
                    (tenant_id, atendimento_id, pessoa_id, intencao_voto,
                     motivo_rejeicao_id, motivo_observacao, registrado_por)
                VALUES
                    (:tenant_id, :attendance_id, :person_id, :intention,
                     :reason_id, :reason_note, :user_id)
                """
            ),
            {
                "tenant_id": tenant_id,
                "attendance_id": attendance_id,
                "person_id": person_id,
                "user_id": user_id,
                "intention": intention,
                "reason_id": reason_id,
                "reason_note": reason_note,
            },
        )

    async def list_vote_history(self, tenant_id: int, person_id: int) -> list[dict[str, Any]]:
        return await self._all(
            """
            SELECT h.id, h.intencao_voto, m.nome AS motivo_rejeicao_nome,
                   h.motivo_observacao, h.criado_em, u.nome AS registrado_por_nome
              FROM comunicacao.intencao_voto_historico h
         LEFT JOIN comunicacao.motivo_rejeicao_voto m ON m.id = h.motivo_rejeicao_id
         LEFT JOIN auth.usuario u ON u.id = h.registrado_por
             WHERE h.tenant_id = :tenant_id AND h.pessoa_id = :person_id
             ORDER BY h.criado_em DESC, h.id DESC
             LIMIT 40
            """,
            {"tenant_id": tenant_id, "person_id": person_id},
        )

    async def indicators(
        self, tenant_id: int, campaign_id: int, filters: IndicatorFilters
    ) -> dict[str, Any]:
        where = [
            "a.tenant_id = :tenant_id",
            "a.campanha_eleicao_id = :campaign_id",
            "a.situacao <> 'em_atendimento'",
        ]
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "inicio": filters.inicio,
            "fim": filters.fim,
            "atendente_usuario_id": filters.atendente_usuario_id,
            "canal": filters.canal,
            "situacao": filters.situacao,
            "resultado": filters.resultado,
        }
        if filters.inicio is not None:
            where.append("a.iniciado_em >= :inicio")
        if filters.fim is not None:
            where.append("a.iniciado_em < :fim")
        if filters.atendente_usuario_id is not None:
            where.append("a.atendente_usuario_id = :atendente_usuario_id")
        if filters.canal is not None:
            where.append("a.canal = :canal")
        if filters.situacao is not None:
            where.append("a.situacao = :situacao")
        if filters.resultado is not None:
            where.append("a.resultado = :resultado")
        clause = " AND ".join(where)
        totals = await self._one(
            f"""
            SELECT
              count(*)::int AS total_atendimentos,
              count(*) FILTER (WHERE a.situacao = 'concluido')::int AS concluidos,
              count(*) FILTER (WHERE a.situacao = 'sem_resposta')::int AS sem_resposta,
              count(*) FILTER (
                WHERE a.situacao = 'concluido' AND a.intencao_voto = 'votara'
              )::int AS votos_confirmados,
              count(*) FILTER (
                WHERE a.situacao = 'concluido' AND a.intencao_voto = 'indeciso'
              )::int AS indecisos,
              count(*) FILTER (
                WHERE a.situacao = 'concluido' AND a.intencao_voto = 'nao_votara'
              )::int AS respostas_negativas,
              COALESCE(
                EXTRACT(EPOCH FROM avg(a.finalizado_em - a.iniciado_em)
                  FILTER (WHERE a.finalizado_em IS NOT NULL)
                ) / 60.0,
                0
              )::float AS tempo_medio_minutos
              FROM comunicacao.atendimento_eleitor a
             WHERE {clause}
            """,
            values,
        )
        period = await self._all(
            f"""
            SELECT a.iniciado_em::date AS periodo, count(*)::int AS quantidade
              FROM comunicacao.atendimento_eleitor a
             WHERE {clause}
             GROUP BY a.iniciado_em::date
             ORDER BY periodo
            """,
            values,
        )
        operators = await self._all(
            f"""
            SELECT a.atendente_usuario_id, COALESCE(u.nome, 'Atendente') AS atendente_nome,
                   count(*)::int AS quantidade
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
             WHERE {clause}
             GROUP BY a.atendente_usuario_id, u.nome
             ORDER BY quantidade DESC, atendente_nome
            """,
            values,
        )
        channels = await self._all(
            f"""
            SELECT a.canal AS canal_id, COALESCE(c.nome, 'Canal') AS canal,
                   count(*)::int AS quantidade
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN comunicacao.canal_comunicacao c ON c.id = a.canal
             WHERE {clause}
             GROUP BY a.canal, c.nome
             ORDER BY quantidade DESC, canal
            """,
            values,
        )
        reasons = await self._all(
            f"""
            SELECT m.id AS motivo_rejeicao_id,
                   COALESCE(m.nome, 'Sem motivo') AS motivo,
                   count(*)::int AS quantidade
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN comunicacao.motivo_rejeicao_voto m ON m.id = a.motivo_rejeicao_id
             WHERE {clause}
               AND a.intencao_voto = 'nao_votara'
             GROUP BY m.id, COALESCE(m.nome, 'Sem motivo')
             ORDER BY quantidade DESC
             LIMIT 8
            """,
            values,
        )
        assert totals is not None
        return {
            **totals,
            "por_periodo": period,
            "por_telefonista": operators,
            "por_canal": channels,
            "principais_motivos_rejeicao": reasons,
        }

    async def operator_report(
        self,
        tenant_id: int,
        campaign_id: int,
        filters: AttendanceReportFilters,
    ) -> dict[str, Any]:
        where = [
            "a.tenant_id = :tenant_id",
            "a.campanha_eleicao_id = :campaign_id",
            "a.situacao <> 'em_atendimento'",
            "a.atendente_usuario_id = :atendente_usuario_id",
        ]
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "atendente_usuario_id": filters.atendente_usuario_id,
            "inicio": filters.inicio,
            "fim": filters.fim,
            "limit": filters.tamanho,
            "offset": (filters.pagina - 1) * filters.tamanho,
        }
        if filters.inicio is not None:
            where.append("a.iniciado_em >= :inicio")
        if filters.fim is not None:
            where.append("a.iniciado_em < :fim")
        clause = " AND ".join(where)
        totals = await self._one(
            f"""
            SELECT count(*)::int AS total,
                   count(*) FILTER (WHERE a.situacao = 'concluido')::int AS concluido,
                   count(*) FILTER (WHERE a.situacao = 'sem_resposta')::int AS sem_resposta,
                   count(*) FILTER (WHERE a.situacao = 'numero_invalido')::int AS numero_invalido,
                   count(*) FILTER (WHERE a.situacao = 'interrompido')::int AS interrompido,
                   count(*) FILTER (WHERE a.intencao_voto = 'votara')::int AS votara,
                   count(*) FILTER (WHERE a.intencao_voto = 'nao_votara')::int AS nao_votara,
                   count(*) FILTER (WHERE a.intencao_voto = 'indeciso')::int AS indeciso,
                   count(*) FILTER (WHERE a.intencao_voto = 'nao_respondeu')::int AS nao_respondeu,
                   COALESCE(max(u.nome), 'Telefonista') AS atendente_nome
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
             WHERE {clause}
            """,
            values,
        )
        if totals is None or int(totals.get("total") or 0) == 0:
            operator_name = await self.session.scalar(
                text(
                    """
                    SELECT COALESCE(u.nome, 'Telefonista')
                      FROM auth.usuario u
                     WHERE u.id = :atendente_usuario_id
                     LIMIT 1
                    """
                ),
                {"atendente_usuario_id": filters.atendente_usuario_id},
            )
            totals = {
                "total": 0,
                "concluido": 0,
                "sem_resposta": 0,
                "numero_invalido": 0,
                "interrompido": 0,
                "votara": 0,
                "nao_votara": 0,
                "indeciso": 0,
                "nao_respondeu": 0,
                "atendente_nome": operator_name or "Telefonista",
            }
        itens = await self._all(
            f"""
            SELECT a.id,
                   a.pessoa_id,
                   p.nome_completo,
                   contacts.telefone,
                   contacts.email,
                   p.data_nascimento,
                   p.sexo,
                   a.iniciado_em,
                   a.finalizado_em,
                   a.situacao,
                   a.resultado,
                   a.intencao_voto,
                   COALESCE(cc.nome, 'Canal') AS canal_nome,
                   a.canal_outro,
                   a.observacao,
                   m.nome AS motivo_rejeicao_nome,
                   a.motivo_observacao,
                   a.motivo_encerramento,
                   a.motivo_inativacao,
                   a.atendente_usuario_id,
                   COALESCE(u.nome, 'Telefonista') AS atendente_nome
              FROM comunicacao.atendimento_eleitor a
              JOIN cadastro.pessoa p
                ON p.id = a.pessoa_id AND p.tenant_id = a.tenant_id
         LEFT JOIN comunicacao.canal_comunicacao cc ON cc.id = a.canal
         LEFT JOIN comunicacao.motivo_rejeicao_voto m ON m.id = a.motivo_rejeicao_id
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
         LEFT JOIN LATERAL (
                   SELECT
                     max(pc.valor) FILTER (
                        WHERE pc.tipo_contato IN ('telefone', 'celular', 'whatsapp')
                     ) AS telefone,
                     max(pc.valor) FILTER (WHERE pc.tipo_contato = 'email') AS email
                     FROM cadastro.pessoa_contato pc
                    WHERE pc.tenant_id = p.tenant_id AND pc.pessoa_id = p.id
                ) contacts ON TRUE
             WHERE {clause}
             ORDER BY a.iniciado_em DESC, a.id DESC
             LIMIT :limit OFFSET :offset
            """,
            values,
        )
        operators = await self._all(
            """
            SELECT a.atendente_usuario_id, COALESCE(u.nome, 'Atendente') AS atendente_nome,
                   count(*)::int AS quantidade
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
             WHERE a.tenant_id = :tenant_id
               AND a.campanha_eleicao_id = :campaign_id
               AND a.situacao <> 'em_atendimento'
             GROUP BY a.atendente_usuario_id, u.nome
             ORDER BY atendente_nome
            """,
            {"tenant_id": tenant_id, "campaign_id": campaign_id},
        )
        return {
            "total": int(totals.get("total") or 0),
            "atendente_nome": totals.get("atendente_nome") or "Telefonista",
            "resumo": {
                "total": int(totals.get("total") or 0),
                "concluido": int(totals.get("concluido") or 0),
                "sem_resposta": int(totals.get("sem_resposta") or 0),
                "numero_invalido": int(totals.get("numero_invalido") or 0),
                "interrompido": int(totals.get("interrompido") or 0),
                "votara": int(totals.get("votara") or 0),
                "nao_votara": int(totals.get("nao_votara") or 0),
                "indeciso": int(totals.get("indeciso") or 0),
                "nao_respondeu": int(totals.get("nao_respondeu") or 0),
            },
            "itens": itens,
            "telefonistas": operators,
        }

    async def reason_report(
        self,
        tenant_id: int,
        campaign_id: int,
        filters: AttendanceReasonReportFilters,
    ) -> dict[str, Any]:
        where = [
            "a.tenant_id = :tenant_id",
            "a.campanha_eleicao_id = :campaign_id",
            "a.situacao <> 'em_atendimento'",
            "a.intencao_voto = 'nao_votara'",
        ]
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "motivo_rejeicao_id": filters.motivo_rejeicao_id,
            "inicio": filters.inicio,
            "fim": filters.fim,
            "limit": filters.tamanho,
            "offset": (filters.pagina - 1) * filters.tamanho,
        }
        if filters.inicio is not None:
            where.append("a.iniciado_em >= :inicio")
        if filters.fim is not None:
            where.append("a.iniciado_em < :fim")
        if filters.motivo_rejeicao_id is None:
            where.append("a.motivo_rejeicao_id IS NULL")
        else:
            where.append("a.motivo_rejeicao_id = :motivo_rejeicao_id")
        clause = " AND ".join(where)
        totals = await self._one(
            f"""
            SELECT count(*)::int AS total,
                   count(*) FILTER (WHERE a.situacao = 'concluido')::int AS concluido,
                   count(*) FILTER (WHERE a.situacao = 'sem_resposta')::int AS sem_resposta,
                   count(*) FILTER (WHERE a.situacao = 'numero_invalido')::int AS numero_invalido,
                   count(*) FILTER (WHERE a.situacao = 'interrompido')::int AS interrompido,
                   count(*) FILTER (WHERE a.intencao_voto = 'votara')::int AS votara,
                   count(*) FILTER (WHERE a.intencao_voto = 'nao_votara')::int AS nao_votara,
                   count(*) FILTER (WHERE a.intencao_voto = 'indeciso')::int AS indeciso,
                   count(*) FILTER (WHERE a.intencao_voto = 'nao_respondeu')::int AS nao_respondeu,
                   COALESCE(max(m.nome), 'Sem motivo') AS motivo
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN comunicacao.motivo_rejeicao_voto m ON m.id = a.motivo_rejeicao_id
             WHERE {clause}
            """,
            values,
        )
        if totals is None or int(totals.get("total") or 0) == 0:
            reason_name = "Sem motivo"
            if filters.motivo_rejeicao_id is not None:
                reason_name = (
                    await self.session.scalar(
                        text(
                            """
                            SELECT COALESCE(nome, 'Sem motivo')
                              FROM comunicacao.motivo_rejeicao_voto
                             WHERE id = :motivo_rejeicao_id
                             LIMIT 1
                            """
                        ),
                        {"motivo_rejeicao_id": filters.motivo_rejeicao_id},
                    )
                    or "Sem motivo"
                )
            totals = {
                "total": 0,
                "concluido": 0,
                "sem_resposta": 0,
                "numero_invalido": 0,
                "interrompido": 0,
                "votara": 0,
                "nao_votara": 0,
                "indeciso": 0,
                "nao_respondeu": 0,
                "motivo": reason_name,
            }
        itens = await self._all(
            f"""
            SELECT a.id,
                   a.pessoa_id,
                   p.nome_completo,
                   contacts.telefone,
                   contacts.email,
                   p.data_nascimento,
                   p.sexo,
                   a.iniciado_em,
                   a.finalizado_em,
                   a.situacao,
                   a.resultado,
                   a.intencao_voto,
                   COALESCE(cc.nome, 'Canal') AS canal_nome,
                   a.canal_outro,
                   a.observacao,
                   m.nome AS motivo_rejeicao_nome,
                   a.motivo_observacao,
                   a.motivo_encerramento,
                   a.motivo_inativacao,
                   a.atendente_usuario_id,
                   COALESCE(u.nome, 'Telefonista') AS atendente_nome
              FROM comunicacao.atendimento_eleitor a
              JOIN cadastro.pessoa p
                ON p.id = a.pessoa_id AND p.tenant_id = a.tenant_id
         LEFT JOIN comunicacao.canal_comunicacao cc ON cc.id = a.canal
         LEFT JOIN comunicacao.motivo_rejeicao_voto m ON m.id = a.motivo_rejeicao_id
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
         LEFT JOIN LATERAL (
                   SELECT
                     max(pc.valor) FILTER (
                        WHERE pc.tipo_contato IN ('telefone', 'celular', 'whatsapp')
                     ) AS telefone,
                     max(pc.valor) FILTER (WHERE pc.tipo_contato = 'email') AS email
                     FROM cadastro.pessoa_contato pc
                    WHERE pc.tenant_id = p.tenant_id AND pc.pessoa_id = p.id
                ) contacts ON TRUE
             WHERE {clause}
             ORDER BY a.iniciado_em DESC, a.id DESC
             LIMIT :limit OFFSET :offset
            """,
            values,
        )
        reasons = await self._all(
            """
            SELECT m.id AS motivo_rejeicao_id,
                   COALESCE(m.nome, 'Sem motivo') AS motivo,
                   count(*)::int AS quantidade
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN comunicacao.motivo_rejeicao_voto m ON m.id = a.motivo_rejeicao_id
             WHERE a.tenant_id = :tenant_id
               AND a.campanha_eleicao_id = :campaign_id
               AND a.situacao <> 'em_atendimento'
               AND a.intencao_voto = 'nao_votara'
             GROUP BY m.id, COALESCE(m.nome, 'Sem motivo')
             ORDER BY motivo
            """,
            {"tenant_id": tenant_id, "campaign_id": campaign_id},
        )
        return {
            "total": int(totals.get("total") or 0),
            "motivo": totals.get("motivo") or "Sem motivo",
            "resumo": {
                "total": int(totals.get("total") or 0),
                "concluido": int(totals.get("concluido") or 0),
                "sem_resposta": int(totals.get("sem_resposta") or 0),
                "numero_invalido": int(totals.get("numero_invalido") or 0),
                "interrompido": int(totals.get("interrompido") or 0),
                "votara": int(totals.get("votara") or 0),
                "nao_votara": int(totals.get("nao_votara") or 0),
                "indeciso": int(totals.get("indeciso") or 0),
                "nao_respondeu": int(totals.get("nao_respondeu") or 0),
            },
            "itens": itens,
            "motivos": reasons,
        }

    async def commit(self) -> None:
        await self.session.commit()

    async def _clear_principal_contacts(
        self,
        tenant_id: int,
        person_id: int,
        contact_type: str,
        exclude_id: int | None = None,
    ) -> None:
        await self.session.execute(
            text(
                """
                UPDATE cadastro.pessoa_contato
                   SET principal = FALSE
                 WHERE tenant_id = :tenant_id
                   AND pessoa_id = :person_id
                   AND tipo_contato = :contact_type
                   AND principal
                   AND (
                        CAST(:exclude_id AS BIGINT) IS NULL
                        OR id <> CAST(:exclude_id AS BIGINT)
                   )
                """
            ),
            {
                "tenant_id": tenant_id,
                "person_id": person_id,
                "contact_type": contact_type,
                "exclude_id": exclude_id,
            },
        )

    @staticmethod
    def _attendance_select() -> str:
        return """
            SELECT a.id, a.tenant_id, a.campanha_eleicao_id, a.pessoa_id,
                   a.atendente_usuario_id, u.nome AS atendente_nome,
                   a.canal, cc.codigo AS canal_codigo, cc.nome AS canal_nome,
                   a.canal_outro, a.situacao, a.resultado,
                   a.intencao_voto, a.motivo_rejeicao_id, m.nome AS motivo_rejeicao_nome,
                   a.motivo_observacao, a.observacao, a.motivo_encerramento,
                   a.motivo_inativacao, a.iniciado_em, a.finalizado_em
              FROM comunicacao.atendimento_eleitor a
         LEFT JOIN auth.usuario u ON u.id = a.atendente_usuario_id
         LEFT JOIN comunicacao.canal_comunicacao cc ON cc.id = a.canal
         LEFT JOIN comunicacao.motivo_rejeicao_voto m ON m.id = a.motivo_rejeicao_id
        """
