import csv
import io
import unicodedata

from fastapi.encoders import jsonable_encoder

from app.audit.service import AuditService
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_demandas.repository import DemandRepository
from app.mod_demandas.schemas import DemandPatch
from app.mod_territorio.repository import TerritorioRepository


class DemandService:
    def __init__(self, r: DemandRepository):
        self.r = r
        self.tr = TerritorioRepository(r.session)

    async def ids(self, a, x):
        return await self.tr.accessible_ids(a.tenant_id, x)

    async def ensure(self, a, x, i):
        d = await self.r.get(a.tenant_id, i)
        if not d:
            raise ResourceNotFoundError("Demanda", i)
        ids = await self.ids(a, x)
        if ids is not None and d["territorio_id"] not in ids:
            raise AuthorizationError("Demanda fora do escopo territorial.")
        return d

    async def create(self, a, x, p):
        await self.validate_references(a, p)
        if p.territorio_id:
            ids = await self.ids(a, x)
            if ids is not None and p.territorio_id not in ids:
                raise AuthorizationError()
        classification = await self.classify(a.tenant_id, p.descricao)
        updates = {}
        if not p.categoria_demanda_id and classification["categoria_demanda_id"]:
            updates["categoria_demanda_id"] = classification["categoria_demanda_id"]
        if not p.prioridade_demanda_id and classification["prioridade_demanda_id"]:
            updates["prioridade_demanda_id"] = classification["prioridade_demanda_id"]
        automatic = bool(updates)
        if updates:
            p = p.model_copy(update=updates)
        i = await self.r.create(
            a.tenant_id,
            a.user_id,
            p,
            automatic=automatic,
            classification_details=classification["detalhes"] if automatic else {},
        )
        d = await self.r.get(a.tenant_id, i)
        await self.audit(a, "criar", i, None, d)
        await self.r.commit()
        return d

    async def update(self, a, x, i, p):
        b = await self.ensure(a, x, i)
        await self.validate_references(a, p)
        if "territorio_id" in p.model_fields_set:
            ids = await self.ids(a, x)
            if ids is not None and (
                p.territorio_id is None or p.territorio_id not in ids
            ):
                raise AuthorizationError("Territorio fora do escopo permitido.")
        await self.r.update(a.tenant_id, i, p)
        n = await self.r.get(a.tenant_id, i)
        assert n
        changed = any(
            b.get(k) != n.get(k)
            for k in (
                "status_demanda_id",
                "responsavel_atendimento_id",
                "prazo",
                "resultado_atendimento_id",
            )
        )
        if changed:
            if (
                b.get("status_demanda_id") != n.get("status_demanda_id")
                and not p.observacao
            ):
                raise BusinessRuleError("Mudanca de status exige observacao.")
            status = await self.r.catalog("status", a.tenant_id, n["status_demanda_id"])
            if status and status.get("final") and not n.get("resultado_atendimento_id"):
                raise BusinessRuleError("Encerramento exige resultado.")
            await self.r.movement(a.tenant_id, i, a.user_id, b, n, p.observacao)
        await self.audit(a, "editar", i, b, n)
        await self.r.commit()
        return n

    async def detail(self, a, x, i):
        d = await self.ensure(a, x, i)
        return {**d, **await self.r.detail_lists(a.tenant_id, i)}

    async def attendance(self, a, x, i, p):
        b = await self.ensure(a, x, i)
        await self.validate_references(a, p)
        z = await self.r.attendance(a.tenant_id, i, a.user_id, p)
        if p.resultado_atendimento_id:
            patch = DemandPatch(
                resultado_atendimento_id=p.resultado_atendimento_id,
                observacao=p.descricao,
            )
            await self.r.update(a.tenant_id, i, patch)
            n = await self.r.get(a.tenant_id, i)
            await self.r.movement(a.tenant_id, i, a.user_id, b, n or b, p.descricao)
        await self.audit(a, "atender", i, b, await self.r.get(a.tenant_id, i))
        await self.r.commit()
        return z

    async def validate_references(self, a, p):
        mapping = {
            "pessoa_solicitante_id": "pessoa",
            "lideranca_indicacao_id": "lideranca",
            "evento_id": "evento",
            "territorio_id": "territorio",
            "responsavel_atendimento_id": "responsavel",
        }
        values = p.model_dump(exclude_unset=True)
        for field, kind in mapping.items():
            value = values.get(field)
            if value is not None and not await self.r.reference_exists(
                kind, a.tenant_id, value
            ):
                raise BusinessRuleError(f"Referencia invalida para {field}.")
        catalogs = {
            "categoria_demanda_id": "categorias",
            "prioridade_demanda_id": "prioridades",
            "status_demanda_id": "status",
            "origem_demanda_id": "origens",
            "resultado_atendimento_id": "resultados",
        }
        for field, key in catalogs.items():
            value = values.get(field)
            item = await self.r.catalog(key, a.tenant_id, value) if value else None
            if value is not None and (not item or not item["ativo"]):
                raise BusinessRuleError(f"Catalogo invalido para {field}.")

    async def classify(self, tid: int, description: str):
        normalized = "".join(
            char
            for char in unicodedata.normalize("NFKD", description.casefold())
            if not unicodedata.combining(char)
        )
        category_terms = {
            "saude": ("saude", "hospital", "medico", "remedio", "posto"),
            "educacao": ("escola", "educacao", "professor", "creche"),
            "infraestrutura": ("asfalto", "buraco", "iluminacao", "obra", "paviment"),
            "emprego": ("emprego", "trabalho", "vaga"),
            "seguranca": ("seguranca", "policia", "violencia"),
            "assistencia_social": ("assistencia", "cesta", "vulnerab"),
            "transporte": ("onibus", "transporte", "estrada"),
            "habitacao": ("moradia", "habitacao", "casa"),
        }
        category_code = next(
            (
                code
                for code, terms in category_terms.items()
                if any(term in normalized for term in terms)
            ),
            None,
        )
        urgent_terms = ("urgente", "emergencia", "risco de vida", "imediato")
        high_terms = ("grave", "risco", "prioridade", "sem atendimento")
        priority_code = (
            "urgente"
            if any(term in normalized for term in urgent_terms)
            else "alta"
            if any(term in normalized for term in high_terms)
            else None
        )
        categories = await self.r.catalogs("categorias", tid)
        priorities = await self.r.catalogs("prioridades", tid)
        category = next((c for c in categories if c["codigo"] == category_code), None)
        priority = next((p for p in priorities if p["codigo"] == priority_code), None)
        return {
            "categoria_demanda_id": category["id"] if category else None,
            "categoria_codigo": category_code if category else None,
            "prioridade_demanda_id": priority["id"] if priority else None,
            "prioridade_codigo": priority_code if priority else None,
            "detalhes": {
                "metodo": "regras_palavras_chave",
                "categoria_sugerida": category_code,
                "prioridade_sugerida": priority_code,
            },
        }

    async def summary(self, a, x, filters):
        ds = await self.r.list(a.tenant_id, filters, await self.ids(a, x))

        def g(k):
            out = {}
            for d in ds:
                out[str(d.get(k) or "Sem classificacao")] = (
                    out.get(str(d.get(k) or "Sem classificacao"), 0) + 1
                )
            return [{"chave": k, "total": v} for k, v in out.items()]

        return {
            "total": len(ds),
            "vencidas": sum(bool(d["vencida"]) for d in ds),
            "por_status": g("status_nome"),
            "por_categoria": g("categoria_nome"),
            "por_territorio": g("territorio_nome"),
            "por_responsavel": g("responsavel_nome"),
        }

    async def export(self, a, x, filters, purpose: str):
        ds = await self.r.list(a.tenant_id, filters, await self.ids(a, x))
        o = io.StringIO()
        w = csv.writer(o)
        w.writerow(
            [
                "protocolo",
                "titulo",
                "status",
                "categoria",
                "prioridade",
                "responsavel",
                "territorio",
                "prazo",
                "vencida",
            ]
        )
        for d in ds:
            w.writerow(
                [
                    d["protocolo"],
                    d["titulo"],
                    d["status_nome"],
                    d["categoria_nome"],
                    d["prioridade_nome"],
                    d["responsavel_nome"],
                    d["territorio_nome"],
                    d["prazo"],
                    d["vencida"],
                ]
            )
        await self.audit(
            a,
            "exportar",
            0,
            None,
            {"quantidade": len(ds), "filtros": filters, "finalidade": purpose},
        )
        await self.r.commit()
        return o.getvalue().encode("utf-8-sig")

    async def audit(self, a, act, i, b, n):
        await AuditService(self.r.session).record(
            action=act,
            tenant_id=a.tenant_id,
            user_id=a.user_id,
            schema_name="demanda",
            table_name="demanda",
            record_id=i,
            before=jsonable_encoder(b) if b else None,
            after=jsonable_encoder(n) if n else None,
        )
