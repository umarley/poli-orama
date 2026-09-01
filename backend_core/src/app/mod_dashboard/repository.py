from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_agenda.access import calendar_view_clause
from app.mod_dashboard.schemas import DashboardConfigurationUpdate, DashboardFilters


class DashboardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _values(tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None):
        return {
            "tenant_id": tenant_id,
            "inicio": filters.data_inicio,
            "fim": filters.data_fim,
            "lideranca_id": filters.lideranca_id,
            "territory_ids": sorted(territory_ids) if territory_ids is not None else None,
        }

    @staticmethod
    def _territory(column: str) -> str:
        return (
            f"(CAST(:territory_ids AS BIGINT[]) IS NULL "
            f"OR {column} = ANY(CAST(:territory_ids AS BIGINT[])))"
        )

    @staticmethod
    def _leader_id() -> str:
        return "CAST(:lideranca_id AS BIGINT)"

    async def _one(self, query: str, values: dict[str, Any]) -> dict[str, Any]:
        row = (await self.session.execute(text(query), values)).mappings().one()
        return dict(row)

    async def _all(self, query: str, values: dict[str, Any]) -> list[dict[str, Any]]:
        rows = (await self.session.execute(text(query), values)).mappings()
        return [dict(row) for row in rows]

    async def cadastros(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> dict[str, Any]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("pt.territorio_id")
        leader_id = self._leader_id()
        leader = (
            f"({leader_id} IS NULL OR EXISTS (SELECT 1 FROM cadastro.hierarquia_lideranca h "
            "WHERE h.tenant_id=p.tenant_id AND h.pessoa_subordinada_id=p.id "
            f"AND h.lideranca_superior_id={leader_id} AND h.ativo "
            "AND (h.data_fim IS NULL OR h.data_fim >= CURRENT_DATE)))"
        )
        return await self._one(
            f"""
            WITH pessoas AS (
              SELECT DISTINCT p.id,p.criado_em,p.completude_cadastral
              FROM cadastro.pessoa p
              LEFT JOIN territorio.pessoa_territorio pt
                ON pt.tenant_id=p.tenant_id AND pt.pessoa_id=p.id
              WHERE p.tenant_id=:tenant_id AND p.ativo AND p.excluido_em IS NULL
                AND {territory} AND {leader}
            )
            SELECT
              COUNT(*)::int AS total,
              COUNT(*) FILTER (
                WHERE criado_em::date BETWEEN :inicio AND :fim
              )::int AS novos_periodo,
              COUNT(*) FILTER (
                WHERE COALESCE(completude_cadastral, 0) < 70
              )::int AS incompletos_pendentes,
              COALESCE(ROUND(AVG(completude_cadastral), 2), 0)::float
                AS completude_media,
              (SELECT COUNT(*)::int FROM cadastro.suspeita_duplicidade sd
               WHERE sd.tenant_id=:tenant_id AND sd.status='pendente') AS duplicidades_abertas
            FROM pessoas
            """,
            values,
        )

    async def liderancas(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> dict[str, Any]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("lt.territorio_id")
        leader_id = self._leader_id()
        return await self._one(
            f"""
            WITH lideres AS (
              SELECT DISTINCT l.id
              FROM cadastro.lideranca l
              LEFT JOIN territorio.lideranca_territorio lt
                ON lt.tenant_id=l.tenant_id AND lt.lideranca_id=l.id
              WHERE l.tenant_id=:tenant_id AND l.ativo
                AND {territory}
                AND ({leader_id} IS NULL OR l.id={leader_id} OR l.coordenador_id={leader_id})
            ), totais AS (
              SELECT COUNT(DISTINCT h.pessoa_subordinada_id)::int total_liderados
              FROM cadastro.hierarquia_lideranca h JOIN lideres l ON l.id=h.lideranca_superior_id
              WHERE h.tenant_id=:tenant_id AND h.ativo
                AND h.data_inicio <= :fim
                AND (h.data_fim IS NULL OR h.data_fim >= :inicio)
            )
            SELECT COUNT(*)::int total_lideres, COALESCE(MAX(t.total_liderados),0)::int
              total_liderados,
              CASE WHEN COUNT(*)=0 THEN 0
                ELSE ROUND(COALESCE(MAX(t.total_liderados),0)::numeric/COUNT(*),2)::float END
              media_liderados
            FROM lideres CROSS JOIN totais t
            """,
            values,
        )

    async def metas(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> dict[str, Any]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("m.territorio_id")
        leader_id = self._leader_id()
        return await self._one(
            f"""
            WITH dados AS (
              SELECT m.id, m.status, COALESCE(a.percentual_atingido,0)::numeric percentual,
                     COALESCE(a.situacao_risco,
                       CASE WHEN m.status='em_risco' THEN 'risco' ELSE 'normal' END) risco
              FROM meta.meta_voto m
              LEFT JOIN LATERAL (
                SELECT percentual_atingido,situacao_risco
                FROM meta.acompanhamento_meta a
                WHERE a.tenant_id=m.tenant_id AND a.meta_voto_id=m.id
                  AND a.data_referencia <= :fim
                ORDER BY a.data_referencia DESC LIMIT 1
              ) a ON true
              WHERE m.tenant_id=:tenant_id AND m.status IN ('ativa','concluida','em_risco')
                AND {territory}
                AND ({leader_id} IS NULL OR m.lideranca_id={leader_id}
                     OR m.coordenador_id={leader_id})
            )
            SELECT COUNT(*) FILTER (WHERE status IN ('ativa','em_risco'))::int metas_ativas,
                   COUNT(*) FILTER (WHERE status='concluida' OR percentual>=100)::int atingidas,
                   COUNT(*) FILTER (WHERE status='em_risco' OR risco IN ('risco','critico')
                                      OR (percentual<70 AND status<>'concluida'))::int em_risco,
                   COALESCE(ROUND(AVG(percentual),2),0)::float percentual_medio
            FROM dados
            """,
            values,
        )

    async def demandas(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> dict[str, Any]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("d.territorio_id")
        leader_id = self._leader_id()
        return await self._one(
            f"""
            SELECT COUNT(*)::int total,
              COUNT(*) FILTER (WHERE s.codigo='pendente')::int pendentes,
              COUNT(*) FILTER (WHERE s.codigo='em_andamento')::int em_andamento,
              COUNT(*) FILTER (WHERE s.codigo IN ('concluida','concluido'))::int concluidas,
              COUNT(*) FILTER (WHERE d.prazo<CURRENT_DATE AND NOT COALESCE(s.final,false))::int
                vencidas
            FROM demanda.demanda d
            JOIN demanda.status_demanda s ON s.id=d.status_demanda_id
            WHERE d.tenant_id=:tenant_id AND d.excluido_em IS NULL
              AND d.data_solicitacao BETWEEN :inicio AND :fim
              AND {territory}
              AND ({leader_id} IS NULL OR d.lideranca_indicacao_id={leader_id})
            """,
            values,
        )

    async def eventos(
        self,
        tenant_id: int,
        filters: DashboardFilters,
        territory_ids: set[int] | None,
        user_id: int,
        calendar_administrator: bool,
    ) -> dict[str, Any]:
        values = self._values(tenant_id, filters, territory_ids)
        values["user_id"] = user_id
        territory = self._territory("e.territorio_id")
        leader_id = self._leader_id()
        calendar_access = (
            "TRUE"
            if calendar_administrator
            else calendar_view_clause()
        )
        return await self._one(
            f"""
            SELECT COUNT(DISTINCT e.id)::int total_periodo,
              COUNT(DISTINCT e.id) FILTER (WHERE s.codigo='realizado')::int realizados,
              COUNT(DISTINCT e.id) FILTER (WHERE s.codigo='cancelado')::int cancelados,
              COUNT(DISTINCT e.id) FILTER (
                WHERE e.numero_presentes IS NOT NULL OR pe.evento_id IS NOT NULL
              )::int presencas_registradas
            FROM agenda.evento e
            JOIN agenda.agenda a ON a.id=e.agenda_id
            LEFT JOIN agenda.status_evento s ON s.id=e.status_evento_id
            LEFT JOIN agenda.presenca_evento pe ON pe.evento_id=e.id
            WHERE e.tenant_id=:tenant_id AND e.excluido_em IS NULL
              AND e.data_inicio::date BETWEEN :inicio AND :fim
              AND {calendar_access}
              AND {territory}
              AND ({leader_id} IS NULL OR EXISTS (
                SELECT 1 FROM agenda.evento_lideranca el
                WHERE el.tenant_id=e.tenant_id AND el.evento_id=e.id
                  AND el.lideranca_id={leader_id}))
            """,
            values,
        )

    async def birthdays(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> list[dict[str, Any]]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("pt.territorio_id")
        leader_id = self._leader_id()
        return await self._all(
            f"""
            SELECT DISTINCT ON (p.id) p.id pessoa_id, p.nome_completo nome, p.data_nascimento,
              EXTRACT(YEAR FROM age(CURRENT_DATE,p.data_nascimento))::int idade,
              t.nome territorio
            FROM cadastro.pessoa p
            LEFT JOIN territorio.pessoa_territorio pt ON pt.pessoa_id=p.id
              AND pt.tenant_id=p.tenant_id
            LEFT JOIN territorio.territorio t ON t.id=pt.territorio_id
            WHERE p.tenant_id=:tenant_id AND p.ativo AND p.excluido_em IS NULL
              AND p.data_nascimento IS NOT NULL AND {territory}
              AND ({leader_id} IS NULL OR EXISTS (
                SELECT 1 FROM cadastro.hierarquia_lideranca h
                WHERE h.tenant_id=p.tenant_id AND h.pessoa_subordinada_id=p.id
                  AND h.lideranca_superior_id={leader_id} AND h.ativo))
            ORDER BY p.id, t.nome NULLS LAST
            """,
            values,
        )

    async def commemorative_dates(
        self, filters: DashboardFilters, territory_ids: set[int] | None, today: date
    ) -> list[dict[str, Any]]:
        values: dict[str, Any] = {
            "today": today,
            "end": today.fromordinal(today.toordinal() + 30),
            "territory_ids": sorted(territory_ids) if territory_ids is not None else None,
            "territorio_id": filters.territorio_id,
        }
        return await self._all(
            """
            WITH datas AS (
              SELECT d.id,d.nome,c.nome categoria,d.ambito,
                make_date(
                  EXTRACT(YEAR FROM CAST(:today AS DATE))::int,
                  d.mes,
                  d.dia
                ) data_base,
                d.codigo_uf_ibge,d.codigo_municipio_ibge
              FROM global.data_comemorativa d
              LEFT JOIN global.categoria_data_comemorativa c ON c.id=d.categoria_id
              WHERE d.ativo AND NOT d.data_movel AND d.dia IS NOT NULL AND d.mes IS NOT NULL
            ), normalizadas AS (
              SELECT *, CASE WHEN data_base<CAST(:today AS DATE)
                             THEN data_base+INTERVAL '1 year'
                             ELSE data_base END::date data
              FROM datas
            )
            SELECT DISTINCT n.id,n.nome,n.categoria,n.data,n.ambito
            FROM normalizadas n
            WHERE n.data BETWEEN CAST(:today AS DATE) AND CAST(:end AS DATE) AND (
              n.ambito='nacional' OR EXISTS (
                SELECT 1 FROM territorio.territorio t
                WHERE (CAST(:territory_ids AS BIGINT[]) IS NULL
                       OR t.id=ANY(CAST(:territory_ids AS BIGINT[])))
                  AND (CAST(:territorio_id AS BIGINT) IS NULL
                       OR t.id=CAST(:territorio_id AS BIGINT))
                  AND (n.codigo_uf_ibge IS NULL OR n.codigo_uf_ibge=t.codigo_uf_ibge)
                  AND (n.codigo_municipio_ibge IS NULL
                       OR n.codigo_municipio_ibge=t.codigo_municipio_ibge)
              ))
            ORDER BY n.data,n.nome
            """,
            values,
        )

    async def goals_by_leader(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> list[dict[str, Any]]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("m.territorio_id")
        leader_id = self._leader_id()
        return await self._all(
            f"""
            SELECT l.id lideranca_id,p.nome_completo lider,
              SUM(m.quantidade_meta)::int meta,
              SUM(COALESCE(a.quantidade_confirmada,0))::int atual,
              CASE WHEN SUM(m.quantidade_meta)=0 THEN 0 ELSE
                ROUND(100.0*SUM(COALESCE(a.quantidade_confirmada,0))
                  /SUM(m.quantidade_meta),2)::float END percentual,
              CASE WHEN BOOL_OR(COALESCE(a.situacao_risco,'normal') IN ('risco','critico'))
                    THEN 'risco'
                   WHEN BOOL_OR(COALESCE(a.situacao_risco,'normal')='atencao')
                    THEN 'atencao' ELSE 'normal' END risco
            FROM meta.meta_voto m
            JOIN cadastro.lideranca l ON l.id=m.lideranca_id
            JOIN cadastro.pessoa p ON p.id=l.pessoa_id
            LEFT JOIN LATERAL (
              SELECT quantidade_confirmada,situacao_risco
              FROM meta.acompanhamento_meta a WHERE a.meta_voto_id=m.id
                AND a.tenant_id=m.tenant_id AND a.data_referencia<=:fim
              ORDER BY a.data_referencia DESC LIMIT 1
            ) a ON true
            WHERE m.tenant_id=:tenant_id AND m.status<>'cancelada'
              AND {territory} AND ({leader_id} IS NULL OR l.id={leader_id}
                                   OR l.coordenador_id={leader_id})
            GROUP BY l.id,p.nome_completo ORDER BY percentual DESC,p.nome_completo
            """,
            values,
        )

    async def demands_report(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> list[dict[str, Any]]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("d.territorio_id")
        leader_id = self._leader_id()
        return await self._all(
            f"""
            SELECT s.nome status,COALESCE(c.nome,'Sem categoria') categoria,
              COALESCE(r.nome,'Sem responsavel') responsavel,d.prazo,
              COUNT(*)::int total,
              COUNT(*) FILTER (WHERE d.prazo<CURRENT_DATE AND NOT COALESCE(s.final,false))::int
                vencidas
            FROM demanda.demanda d
            JOIN demanda.status_demanda s ON s.id=d.status_demanda_id
            LEFT JOIN demanda.categoria_demanda c ON c.id=d.categoria_demanda_id
            LEFT JOIN demanda.responsavel_atendimento r ON r.id=d.responsavel_atendimento_id
            WHERE d.tenant_id=:tenant_id AND d.excluido_em IS NULL
              AND d.data_solicitacao BETWEEN :inicio AND :fim AND {territory}
              AND ({leader_id} IS NULL OR d.lideranca_indicacao_id={leader_id})
            GROUP BY s.nome,c.nome,r.nome,d.prazo
            ORDER BY s.nome,c.nome,r.nome,d.prazo NULLS LAST
            """,
            values,
        )

    async def agenda_report(
        self,
        tenant_id: int,
        filters: DashboardFilters,
        territory_ids: set[int] | None,
        user_id: int,
        calendar_administrator: bool,
    ) -> list[dict[str, Any]]:
        values = self._values(tenant_id, filters, territory_ids)
        values["user_id"] = user_id
        territory = self._territory("e.territorio_id")
        leader_id = self._leader_id()
        calendar_access = (
            "TRUE"
            if calendar_administrator
            else calendar_view_clause()
        )
        return await self._all(
            f"""
            SELECT e.id evento_id,e.titulo,e.data_inicio,e.data_fim,
              COALESCE(s.nome,'Sem status') status,t.nome territorio,
              p.nome_completo responsavel,
              (SELECT COUNT(*) FROM agenda.convite c WHERE c.evento_id=e.id)::int convites,
              (SELECT COUNT(*) FROM agenda.pauta_evento pa WHERE pa.evento_id=e.id)::int pautas
            FROM agenda.evento e
            JOIN agenda.agenda a ON a.id=e.agenda_id
            LEFT JOIN agenda.status_evento s ON s.id=e.status_evento_id
            LEFT JOIN territorio.territorio t ON t.id=e.territorio_id
            LEFT JOIN cadastro.pessoa p ON p.id=e.responsavel_pessoa_id
            WHERE e.tenant_id=:tenant_id AND e.excluido_em IS NULL
              AND e.data_inicio::date BETWEEN :inicio AND :fim AND {territory}
              AND {calendar_access}
              AND ({leader_id} IS NULL OR EXISTS (
                SELECT 1 FROM agenda.evento_lideranca el WHERE el.evento_id=e.id
                  AND el.tenant_id=e.tenant_id AND el.lideranca_id={leader_id}))
            ORDER BY e.data_inicio,e.titulo
            """,
            values,
        )

    async def registrations_evolution(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> list[dict[str, Any]]:
        values = self._values(tenant_id, filters, territory_ids)
        territory = self._territory("pt.territorio_id")
        leader_id = self._leader_id()
        return await self._all(
            f"""
            SELECT p.criado_em::date data,COALESCE(fd.nome,'Cadastro direto') origem,
              COUNT(DISTINCT p.id)::int total
            FROM cadastro.pessoa p
            LEFT JOIN etl.fonte_dado fd ON fd.id=p.fonte_dado_id
            LEFT JOIN territorio.pessoa_territorio pt ON pt.pessoa_id=p.id
              AND pt.tenant_id=p.tenant_id
            WHERE p.tenant_id=:tenant_id AND p.excluido_em IS NULL
              AND p.criado_em::date BETWEEN :inicio AND :fim AND {territory}
              AND ({leader_id} IS NULL OR EXISTS (
                SELECT 1 FROM cadastro.hierarquia_lideranca h
                WHERE h.pessoa_subordinada_id=p.id AND h.tenant_id=p.tenant_id
                  AND h.lideranca_superior_id={leader_id} AND h.ativo))
            GROUP BY p.criado_em::date,fd.nome ORDER BY data,origem
            """,
            values,
        )

    async def leader_ranking(
        self, tenant_id: int, filters: DashboardFilters, territory_ids: set[int] | None
    ) -> list[dict[str, Any]]:
        rows = await self.goals_by_leader(tenant_id, filters, territory_ids)
        leaders = await self._all(
            """
            SELECT h.lideranca_superior_id lideranca_id,
              COUNT(DISTINCT h.pessoa_subordinada_id)::int liderados
            FROM cadastro.hierarquia_lideranca h
            WHERE h.tenant_id=:tenant_id AND h.ativo
              AND h.data_inicio<=:fim AND (h.data_fim IS NULL OR h.data_fim>=:inicio)
            GROUP BY h.lideranca_superior_id
            """,
            {"tenant_id": tenant_id, "inicio": filters.data_inicio, "fim": filters.data_fim},
        )
        counts = {row["lideranca_id"]: row["liderados"] for row in leaders}
        return [
            {"posicao": index, "liderados": counts.get(row["lideranca_id"], 0), **row}
            for index, row in enumerate(rows, 1)
        ]

    async def add_export_log(
        self,
        tenant_id: int,
        user_id: int,
        report: str,
        filters: dict[str, Any],
        count: int,
        output_format: str,
        purpose: str,
    ) -> None:
        await self.session.execute(
            text(
                "INSERT INTO auditoria.log_exportacao "
                "(tenant_id,usuario_id,entidade,filtros,volume_registros,formato,finalidade) "
                "VALUES (:tenant_id,:user_id,:report,CAST(:filters AS jsonb),"
                ":count,:format,:purpose)"
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "report": f"dashboard.{report}",
                "filters": __import__("json").dumps(filters, default=str),
                "count": count,
                "format": output_format,
                "purpose": purpose,
            },
        )

    async def configuration(self, tenant_id: int, profiles: tuple[str, ...]) -> dict | None:
        row = (
            await self.session.execute(
                text(
                    "SELECT dc.id,dc.nome,COALESCE(pa.codigo,'padrao') perfil,"
                    "dc.filtros_padrao,dc.widgets "
                    "FROM dw.dashboard_configuracao dc "
                    "LEFT JOIN auth.perfil_acesso pa ON pa.id=dc.perfil_acesso_id "
                    "WHERE dc.tenant_id=:tenant_id AND (pa.codigo=ANY(:profiles) "
                    "OR dc.perfil_acesso_id IS NULL) "
                    "ORDER BY dc.perfil_acesso_id IS NULL,pa.nivel DESC LIMIT 1"
                ),
                {"tenant_id": tenant_id, "profiles": list(profiles)},
            )
        ).mappings().first()
        return dict(row) if row else None

    async def save_configuration(
        self, tenant_id: int, user_id: int, payload: DashboardConfigurationUpdate
    ) -> dict:
        row = (
            await self.session.execute(
                text(
                    "WITH perfil AS (SELECT id FROM auth.perfil_acesso "
                    "WHERE codigo=:perfil AND (tenant_id=:tenant_id OR tenant_id IS NULL) "
                    "ORDER BY tenant_id NULLS LAST LIMIT 1), atualizado AS ("
                    "UPDATE dw.dashboard_configuracao dc SET nome=:nome,"
                    "filtros_padrao=CAST(:filters AS jsonb),widgets=CAST(:widgets AS jsonb) "
                    "FROM perfil p WHERE dc.tenant_id=:tenant_id "
                    "AND dc.perfil_acesso_id=p.id RETURNING dc.*), inserido AS ("
                    "INSERT INTO dw.dashboard_configuracao "
                    "(tenant_id,nome,perfil_acesso_id,filtros_padrao,widgets,criado_por) "
                    "SELECT :tenant_id,:nome,p.id,CAST(:filters AS jsonb),"
                    "CAST(:widgets AS jsonb),:user_id FROM perfil p "
                    "WHERE NOT EXISTS(SELECT 1 FROM atualizado) RETURNING *) "
                    "SELECT x.id,x.nome,:perfil perfil,x.filtros_padrao,x.widgets "
                    "FROM (SELECT * FROM atualizado UNION ALL SELECT * FROM inserido) x"
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "perfil": payload.perfil,
                    "nome": payload.nome,
                    "filters": __import__("json").dumps(payload.filtros_padrao),
                    "widgets": __import__("json").dumps(payload.widgets),
                },
            )
        ).mappings().one()
        return dict(row)

    async def report_definitions(self, tenant_id: int) -> list[dict[str, Any]]:
        return await self._all(
            "SELECT id,codigo,nome,descricao,tipo,automatico,agendamento_cron "
            "FROM dw.relatorio WHERE tenant_id IS NULL OR tenant_id=:tenant_id "
            "ORDER BY nome",
            {"tenant_id": tenant_id},
        )

    async def report_executions(self, tenant_id: int) -> list[dict[str, Any]]:
        return await self._all(
            "SELECT e.id,e.relatorio_id,r.nome relatorio,e.parametros,e.status,"
            "e.iniciado_em,e.concluido_em FROM dw.relatorio_execucao e "
            "JOIN dw.relatorio r ON r.id=e.relatorio_id "
            "WHERE e.tenant_id=:tenant_id ORDER BY e.iniciado_em DESC LIMIT 100",
            {"tenant_id": tenant_id},
        )

    async def commit(self) -> None:
        await self.session.commit()
