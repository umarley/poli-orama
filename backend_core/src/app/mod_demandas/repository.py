from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_demandas.schemas import (
    AttendanceIn,
    CatalogIn,
    CatalogPatch,
    DemandIn,
    DemandPatch,
    ResponsibleIn,
)

CAT = {
    "categorias": "categoria_demanda",
    "status": "status_demanda",
    "prioridades": "prioridade_demanda",
    "origens": "origem_demanda",
    "resultados": "resultado_atendimento",
}


class DemandRepository:
    def __init__(self, s: AsyncSession):
        self.session = s

    async def catalogs(self, key: str, tid: int, include_inactive: bool = False) -> list[dict]:
        t = CAT[key]
        extra = {"status": ", ordem, final", "prioridades": ", peso"}.get(key, "")
        active = "" if include_inactive else " AND ativo"
        r = await self.session.execute(
            text(
                f"SELECT id,tenant_id,codigo,nome,descricao,ativo{extra} FROM demanda.{t} "
                f"WHERE (tenant_id IS NULL OR tenant_id=:t){active} "
                "ORDER BY tenant_id NULLS FIRST,nome"
            ),
            {"t": tid},
        )
        return [dict(x) for x in r.mappings()]

    async def catalog(self, key: str, tid: int, i: int) -> dict | None:
        return next(
            (x for x in await self.catalogs(key, tid, include_inactive=True) if x["id"] == i),
            None,
        )

    async def create_catalog(self, key: str, tid: int, p: CatalogIn) -> dict:
        t = CAT[key]
        data = p.model_dump()
        fields = ["tenant_id", "codigo", "nome", "descricao"]
        if key == "status":
            fields += ["ordem", "final"]
        if key == "prioridades":
            fields += ["peso"]
        vals = {"tenant_id": tid, **data}
        cols = ",".join(fields)
        binds = ",".join(":" + x for x in fields)
        i = int(
            await self.session.scalar(
                text(f"INSERT INTO demanda.{t}({cols}) VALUES({binds}) RETURNING id"),
                vals,
            )
        )
        return (await self.catalog(key, tid, i)) or {}

    async def patch_catalog(
        self, key: str, tid: int, i: int, p: CatalogPatch
    ) -> dict | None:
        allowed = {"nome", "descricao", "ativo"}
        if key == "status":
            allowed |= {"ordem", "final"}
        elif key == "prioridades":
            allowed.add("peso")
        v = {k: value for k, value in p.model_dump(exclude_unset=True).items() if k in allowed}
        if v:
            await self.session.execute(
                text(
                    f"UPDATE demanda.{CAT[key]} SET "
                    + ",".join(f"{x}=:{x}" for x in v)
                    + " WHERE id=:id AND tenant_id=:t"
                ),
                {"id": i, "t": tid, **v},
            )
        return await self.catalog(key, tid, i)

    async def delete_catalog(self, key: str, tid: int, i: int) -> bool:
        result = await self.session.execute(
            text(
                f"UPDATE demanda.{CAT[key]} SET ativo=FALSE,atualizado_em=now() "
                "WHERE id=:id AND tenant_id=:t AND ativo"
            ),
            {"id": i, "t": tid},
        )
        return bool(result.rowcount)

    def select(self) -> str:
        return """SELECT d.id,d.origem_contexto,d.campanha_eleicao_id,d.protocolo,d.titulo,d.descricao,d.pessoa_solicitante_id,p.nome_completo solicitante_nome,
  d.lideranca_indicacao_id,d.evento_id,d.territorio_id,t.nome territorio_nome,d.categoria_demanda_id,c.nome categoria_nome,
  d.prioridade_demanda_id,pr.nome prioridade_nome,d.status_demanda_id,s.codigo status_codigo,s.nome status_nome,
  d.origem_demanda_id,o.nome origem_nome,d.responsavel_atendimento_id,r.nome responsavel_nome,
  d.resultado_atendimento_id,ra.nome resultado_nome,d.prazo,COALESCE(d.prazo<CURRENT_DATE AND NOT s.final,FALSE) vencida,
  d.classificacao_automatica,d.classificacao_detalhes,d.criado_em,d.atualizado_em FROM demanda.demanda d
  JOIN demanda.status_demanda s ON s.id=d.status_demanda_id LEFT JOIN cadastro.pessoa p ON p.id=d.pessoa_solicitante_id
  LEFT JOIN territorio.territorio t ON t.id=d.territorio_id LEFT JOIN demanda.categoria_demanda c ON c.id=d.categoria_demanda_id
  LEFT JOIN demanda.prioridade_demanda pr ON pr.id=d.prioridade_demanda_id LEFT JOIN demanda.origem_demanda o ON o.id=d.origem_demanda_id
  LEFT JOIN demanda.responsavel_atendimento r ON r.id=d.responsavel_atendimento_id LEFT JOIN demanda.resultado_atendimento ra ON ra.id=d.resultado_atendimento_id"""

    async def list(self, tid: int, filters: dict, ids: set[int] | None) -> list[dict]:
        w = ["d.tenant_id=:tid", "d.excluido_em IS NULL"]
        v = {"tid": tid}
        for k, col in {
            "status": "d.status_demanda_id",
            "categoria": "d.categoria_demanda_id",
            "responsavel": "d.responsavel_atendimento_id",
            "territorio": "d.territorio_id",
            "origem": "d.origem_demanda_id",
            "lider": "d.lideranca_indicacao_id",
        }.items():
            if filters.get(k):
                w.append(f"{col}=:{k}")
                v[k] = filters[k]
        if filters.get("inicio"):
            w.append("d.criado_em>=:inicio")
            v["inicio"] = filters["inicio"]
        if filters.get("fim"):
            w.append("d.criado_em<:fim")
            v["fim"] = filters["fim"]
        if ids is not None:
            if not ids:
                return []
            w.append("d.territorio_id=ANY(:ids)")
            v["ids"] = list(ids)
        r = await self.session.execute(
            text(
                self.select()
                + " WHERE "
                + " AND ".join(w)
                + " ORDER BY d.criado_em DESC"
            ),
            v,
        )
        return [dict(x) for x in r.mappings()]

    async def get(self, tid: int, i: int) -> dict | None:
        r = await self.session.execute(
            text(
                self.select()
                + " WHERE d.tenant_id=:t AND d.id=:i AND d.excluido_em IS NULL"
            ),
            {"t": tid, "i": i},
        )
        x = r.mappings().first()
        return dict(x) if x else None

    async def create(
        self,
        tid: int,
        uid: int,
        p: DemandIn,
        *,
        automatic: bool = False,
        classification_details: dict | None = None,
    ) -> int:
        v = p.model_dump()
        return int(
            await self.session.scalar(
                text(
                    """INSERT INTO demanda.demanda(tenant_id,origem_contexto,campanha_eleicao_id,protocolo,categoria_demanda_id,prioridade_demanda_id,status_demanda_id,origem_demanda_id,titulo,descricao,pessoa_solicitante_id,lideranca_indicacao_id,evento_id,territorio_id,prazo,criado_por,classificacao_automatica,classificacao_detalhes)
  VALUES(:tid,:origem_contexto,:campanha_eleicao_id,'DEM-'||to_char(now(),'YYYYMMDD')||'-'||nextval('demanda.demanda_id_seq'),:categoria_demanda_id,:prioridade_demanda_id,(SELECT id FROM demanda.status_demanda WHERE codigo='pendente' AND tenant_id IS NULL),COALESCE(CAST(:origem_demanda_id AS smallint),(SELECT id FROM demanda.origem_demanda WHERE codigo='evento' AND :evento_id IS NOT NULL)),:titulo,:descricao,:pessoa_solicitante_id,:lideranca_indicacao_id,:evento_id,:territorio_id,:prazo,:uid,:automatic,CAST(:details AS jsonb)) RETURNING id"""
                ),
                {
                    "tid": tid,
                    "uid": uid,
                    "automatic": automatic,
                    "details": json.dumps(classification_details or {}),
                    **v,
                },
            )
        )

    async def update(self, tid: int, i: int, p: DemandPatch) -> None:
        v = p.model_dump(exclude_unset=True)
        v.pop("observacao", None)
        if v:
            await self.session.execute(
                text(
                    "UPDATE demanda.demanda SET "
                    + ",".join(f"{x}=:{x}" for x in v)
                    + " WHERE tenant_id=:tid AND id=:id"
                ),
                {"tid": tid, "id": i, **v},
            )

    async def movement(
        self, tid: int, i: int, uid: int, b: dict, a: dict, obs: str | None
    ) -> None:
        await self.session.execute(
            text(
                """INSERT INTO demanda.movimentacao_demanda(tenant_id,demanda_id,status_anterior_id,status_novo_id,responsavel_anterior_id,responsavel_novo_id,prazo_anterior,prazo_novo,resultado_anterior_id,resultado_novo_id,observacao,usuario_id)
  VALUES(:t,:i,:sa,:sn,:ra,:rn,:pa,:pn,:resa,:resn,:o,:u)"""
            ),
            {
                "t": tid,
                "i": i,
                "u": uid,
                "o": obs,
                "sa": b.get("status_demanda_id"),
                "sn": a.get("status_demanda_id"),
                "ra": b.get("responsavel_atendimento_id"),
                "rn": a.get("responsavel_atendimento_id"),
                "pa": b.get("prazo"),
                "pn": a.get("prazo"),
                "resa": b.get("resultado_atendimento_id"),
                "resn": a.get("resultado_atendimento_id"),
            },
        )

    async def responsible(self, tid: int, p: ResponsibleIn) -> dict:
        r = await self.session.execute(
            text(
                "INSERT INTO demanda.responsavel_atendimento(tenant_id,nome,tipo,usuario_id,pessoa_id,area) VALUES(:t,:nome,:tipo,:usuario_id,:pessoa_id,:area) RETURNING *"
            ),
            {"t": tid, **p.model_dump()},
        )
        return dict(r.mappings().one())

    async def responsibles(self, tid: int) -> list[dict]:
        r = await self.session.execute(
            text(
                "SELECT * FROM demanda.responsavel_atendimento WHERE tenant_id=:t AND ativo ORDER BY nome"
            ),
            {"t": tid},
        )
        return [dict(x) for x in r.mappings()]

    async def reference_exists(self, kind: str, tid: int, i: int) -> bool:
        definitions = {
            "pessoa": ("cadastro.pessoa", "tenant_id=:t AND excluido_em IS NULL"),
            "lideranca": ("cadastro.lideranca", "tenant_id=:t AND ativo"),
            "evento": ("agenda.evento", "tenant_id=:t"),
            "territorio": ("territorio.territorio", "tenant_id=:t AND ativo"),
            "responsavel": ("demanda.responsavel_atendimento", "tenant_id=:t AND ativo"),
        }
        table, scope = definitions[kind]
        return bool(
            await self.session.scalar(
                text(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE id=:i AND {scope})"),
                {"t": tid, "i": i},
            )
        )

    async def attendance(self, tid: int, i: int, uid: int, p: AttendanceIn) -> dict:
        r = await self.session.execute(
            text(
                "INSERT INTO demanda.atendimento(tenant_id,demanda_id,responsavel_atendimento_id,resultado_atendimento_id,descricao,prazo,data_execucao,tempo_atendimento_horas,criado_por) VALUES(:t,:i,:responsavel_atendimento_id,:resultado_atendimento_id,:descricao,:prazo,:data_execucao,:tempo_atendimento_horas,:u) RETURNING *"
            ),
            {"t": tid, "i": i, "u": uid, **p.model_dump()},
        )
        return dict(r.mappings().one())

    async def detail_lists(self, tid: int, i: int) -> dict:
        async def q(sql):
            return [
                dict(x)
                for x in (
                    await self.session.execute(text(sql), {"t": tid, "i": i})
                ).mappings()
            ]

        return {
            "atendimentos": await q(
                "SELECT a.*,r.nome responsavel_nome,ra.nome resultado_nome FROM demanda.atendimento a LEFT JOIN demanda.responsavel_atendimento r ON r.id=a.responsavel_atendimento_id LEFT JOIN demanda.resultado_atendimento ra ON ra.id=a.resultado_atendimento_id WHERE a.tenant_id=:t AND demanda_id=:i ORDER BY criado_em DESC"
            ),
            "movimentacoes": await q(
                "SELECT * FROM demanda.movimentacao_demanda WHERE tenant_id=:t AND demanda_id=:i ORDER BY criado_em DESC"
            ),
            "anexos": await q(
                "SELECT an.id,an.descricao,ar.nome_original FROM arquivo.anexo an JOIN arquivo.arquivo ar ON ar.id=an.arquivo_id WHERE an.tenant_id=:t AND an.entidade_tipo='demanda' AND an.entidade_id=:i"
            ),
            "alertas": await q(
                "SELECT * FROM demanda.alerta_prazo WHERE tenant_id=:t AND demanda_id=:i ORDER BY criado_em DESC"
            ),
        }

    async def commit(self):
        await self.session.commit()
