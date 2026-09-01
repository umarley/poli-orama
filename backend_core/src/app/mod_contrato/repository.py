"""Persistencia do modulo de contratos."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_contrato.schemas import ContractCreate, ContractUpdate, LegalEntityInput


class ContractRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _person_select() -> str:
        return (
            "SELECT p.id, p.nome_completo AS nome, p.data_nascimento, "
            "cpf.numero AS cpf, rg.numero AS rg, contato.valor AS telefone, "
            "e.cep, e.logradouro, e.numero, e.complemento, "
            "COALESCE(b.nome, e.bairro_texto) AS bairro, e.codigo_municipio_ibge, "
            "m.nome AS cidade, e.latitude, e.longitude FROM cadastro.pessoa p "
            "LEFT JOIN LATERAL (SELECT numero FROM cadastro.pessoa_documento d "
            "WHERE d.pessoa_id=p.id AND d.tenant_id=p.tenant_id "
            "AND d.tipo_documento='cpf' ORDER BY d.id LIMIT 1) cpf ON TRUE "
            "LEFT JOIN LATERAL (SELECT numero FROM cadastro.pessoa_documento d "
            "WHERE d.pessoa_id=p.id AND d.tenant_id=p.tenant_id "
            "AND d.tipo_documento='rg' ORDER BY d.id LIMIT 1) rg ON TRUE "
            "LEFT JOIN LATERAL (SELECT valor FROM cadastro.pessoa_contato c "
            "WHERE c.pessoa_id=p.id AND c.tenant_id=p.tenant_id "
            "AND c.tipo_contato IN ('celular','whatsapp','telefone') "
            "ORDER BY c.principal DESC,c.id LIMIT 1) contato ON TRUE "
            "LEFT JOIN LATERAL (SELECT pe.endereco_id FROM cadastro.pessoa_endereco pe "
            "WHERE pe.pessoa_id=p.id AND pe.tenant_id=p.tenant_id "
            "ORDER BY pe.principal DESC, pe.id LIMIT 1) endereco_principal ON TRUE "
            "LEFT JOIN cadastro.endereco e ON e.id=endereco_principal.endereco_id "
            "AND e.tenant_id=p.tenant_id "
            "LEFT JOIN global.bairro b ON b.id=e.bairro_id "
            "LEFT JOIN global.municipio m ON m.codigo_ibge=e.codigo_municipio_ibge "
        )

    async def search_people(
        self, tenant_id: int, query: str, limit: int = 30
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                self._person_select()
                + "WHERE p.tenant_id=:tenant_id AND p.ativo AND p.excluido_em IS NULL "
                "AND cpf.numero IS NOT NULL AND (p.nome_completo ILIKE :query "
                "OR cpf.numero ILIKE :query) ORDER BY p.nome_completo LIMIT :limit"
            ),
            {"tenant_id": tenant_id, "query": f"%{query}%", "limit": limit},
        )
        return [dict(row) for row in result.mappings()]

    async def person(self, tenant_id: int, person_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                self._person_select() + "WHERE p.tenant_id=:tenant_id AND p.id=:person_id "
                "AND p.ativo AND p.excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def active_campaign_id(self, tenant_id: int) -> int | None:
        value = await self.session.scalar(
            text(
                "SELECT id FROM eleicao.campanha_eleicao WHERE tenant_id=:tenant_id "
                "AND ativa ORDER BY data_ativacao DESC NULLS LAST,id DESC LIMIT 1"
            ),
            {"tenant_id": tenant_id},
        )
        return int(value) if value is not None else None

    async def campaign_exists(self, tenant_id: int, campaign_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM eleicao.campanha_eleicao "
                    "WHERE tenant_id=:tenant_id AND id=:campaign_id)"
                ),
                {"tenant_id": tenant_id, "campaign_id": campaign_id},
            )
        )

    async def upsert_legal_entity(
        self, tenant_id: int, user_id: int, payload: LegalEntityInput
    ) -> int:
        values = payload.model_dump()
        result = await self.session.execute(
            text(
                "INSERT INTO contrato.pessoa_juridica (tenant_id,razao_social,nome_fantasia,"
                "cnpj,telefone,cep,logradouro,numero,complemento,bairro_texto,"
                "codigo_municipio_ibge,latitude,longitude,criado_por) VALUES "
                "(:tenant_id,:razao_social,:nome_fantasia,:cnpj,:telefone,:cep,:logradouro,"
                ":numero,:complemento,:bairro_texto,:codigo_municipio_ibge,:latitude,"
                ":longitude,:user_id) ON CONFLICT (tenant_id,cnpj) "
                "WHERE excluido_em IS NULL DO UPDATE SET razao_social=EXCLUDED.razao_social,"
                "nome_fantasia=EXCLUDED.nome_fantasia,telefone=EXCLUDED.telefone,"
                "cep=EXCLUDED.cep,logradouro=EXCLUDED.logradouro,numero=EXCLUDED.numero,"
                "complemento=EXCLUDED.complemento,bairro_texto=EXCLUDED.bairro_texto,"
                "codigo_municipio_ibge=EXCLUDED.codigo_municipio_ibge,"
                "latitude=EXCLUDED.latitude,longitude=EXCLUDED.longitude RETURNING id"
            ),
            {"tenant_id": tenant_id, "user_id": user_id, **values},
        )
        return int(result.scalar_one())

    async def update_legal_entity(
        self, tenant_id: int, legal_entity_id: int, values: dict[str, Any]
    ) -> None:
        if not values:
            return
        assignments = ",".join(f"{field}=:{field}" for field in values)
        await self.session.execute(
            text(
                f"UPDATE contrato.pessoa_juridica SET {assignments} "
                "WHERE tenant_id=:tenant_id AND id=:id AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": legal_entity_id, **values},
        )

    async def create_contract(
        self,
        tenant_id: int,
        user_id: int,
        campaign_id: int,
        payload: ContractCreate,
        legal_entity_id: int | None,
    ) -> int:
        values = payload.model_dump(exclude={"pessoa_juridica", "campanha_eleicao_id"})
        result = await self.session.execute(
            text(
                "INSERT INTO contrato.contrato (tenant_id,campanha_eleicao_id,"
                "tipo_contratado,pessoa_id,pessoa_juridica_id,funcao_cargo,valor_parcela,"
                "quantidade_parcelas,data_inicio,data_termino,status,observacoes,criado_por) "
                "VALUES (:tenant_id,:campaign_id,:tipo_contratado,:pessoa_id,"
                ":legal_entity_id,:funcao_cargo,:valor_parcela,:quantidade_parcelas,"
                ":data_inicio,:data_termino,:status,:observacoes,:user_id) RETURNING id"
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "campaign_id": campaign_id,
                "legal_entity_id": legal_entity_id,
                **values,
            },
        )
        return int(result.scalar_one())

    async def list_contracts(
        self,
        tenant_id: int,
        *,
        query: str | None = None,
        contractor_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["c.tenant_id=:tenant_id", "c.excluido_em IS NULL"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if query:
            clauses.append(
                "(p.nome_completo ILIKE :query OR pj.razao_social ILIKE :query "
                "OR pj.nome_fantasia ILIKE :query OR cpf.numero ILIKE :query "
                "OR pj.cnpj ILIKE :query OR c.funcao_cargo ILIKE :query)"
            )
            values["query"] = f"%{query}%"
        if contractor_type:
            clauses.append("c.tipo_contratado=:contractor_type")
            values["contractor_type"] = contractor_type
        if status:
            clauses.append("c.status=:status")
            values["status"] = status
        result = await self.session.execute(
            text(
                self._contract_select()
                + " WHERE "
                + " AND ".join(clauses)
                + " ORDER BY c.data_inicio DESC,c.id DESC"
            ),
            values,
        )
        return [self._contract_dict(row) for row in result.mappings()]

    async def contract(self, tenant_id: int, contract_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                self._contract_select()
                + " WHERE c.tenant_id=:tenant_id AND c.id=:id AND c.excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": contract_id},
        )
        row = result.mappings().first()
        return self._contract_dict(row) if row else None

    async def update_contract(
        self, tenant_id: int, contract_id: int, payload: ContractUpdate
    ) -> bool:
        values = payload.model_dump(exclude_unset=True, exclude={"pessoa_juridica"})
        if not values:
            return True
        assignments = ",".join(f"{field}=:{field}" for field in values)
        result = await self.session.execute(
            text(
                f"UPDATE contrato.contrato SET {assignments} WHERE tenant_id=:tenant_id "
                "AND id=:id AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": contract_id, **values},
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def delete_contract(self, tenant_id: int, contract_id: int) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE contrato.contrato SET excluido_em=now(),status='cancelado' "
                "WHERE tenant_id=:tenant_id AND id=:id AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": contract_id},
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def commit(self) -> None:
        await self.session.commit()

    @staticmethod
    def _contract_select() -> str:
        return (
            "SELECT c.id,c.uuid_publico,c.tenant_id,c.campanha_eleicao_id,"
            "c.tipo_contratado,c.pessoa_id,c.pessoa_juridica_id,c.funcao_cargo,"
            "c.valor_parcela,c.quantidade_parcelas,c.valor_total,c.data_inicio,"
            "c.data_termino,c.dias_trabalho,c.valor_diaria,c.status,c.observacoes,"
            "c.criado_em,c.atualizado_em,COALESCE(p.id,pj.id) AS contratado_id,"
            "COALESCE(p.nome_completo,pj.razao_social) AS contratado_nome,"
            "COALESCE(cpf.numero,pj.cnpj) AS contratado_documento,rg.numero AS contratado_rg,"
            "p.data_nascimento AS contratado_nascimento,"
            "COALESCE(contato.valor,pj.telefone) AS contratado_telefone,"
            "COALESCE(e.cep,pj.cep) AS contratado_cep,"
            "COALESCE(e.logradouro,pj.logradouro) AS contratado_logradouro,"
            "COALESCE(e.numero,pj.numero) AS contratado_numero,"
            "COALESCE(e.complemento,pj.complemento) AS contratado_complemento,"
            "COALESCE(b.nome,e.bairro_texto,pj.bairro_texto) AS contratado_bairro,"
            "COALESCE(e.codigo_municipio_ibge,pj.codigo_municipio_ibge) "
            "AS contratado_municipio,COALESCE(m.nome,mpj.nome) AS contratado_cidade,"
            "COALESCE(e.latitude,pj.latitude) AS contratado_latitude,"
            "COALESCE(e.longitude,pj.longitude) AS contratado_longitude "
            "FROM contrato.contrato c LEFT JOIN cadastro.pessoa p ON p.id=c.pessoa_id "
            "AND p.tenant_id=c.tenant_id "
            "LEFT JOIN contrato.pessoa_juridica pj ON pj.id=c.pessoa_juridica_id "
            "AND pj.tenant_id=c.tenant_id AND pj.excluido_em IS NULL "
            "LEFT JOIN LATERAL (SELECT numero FROM cadastro.pessoa_documento d "
            "WHERE d.pessoa_id=p.id AND d.tenant_id=c.tenant_id "
            "AND d.tipo_documento='cpf' ORDER BY d.id LIMIT 1) cpf ON TRUE "
            "LEFT JOIN LATERAL (SELECT numero FROM cadastro.pessoa_documento d "
            "WHERE d.pessoa_id=p.id AND d.tenant_id=c.tenant_id "
            "AND d.tipo_documento='rg' ORDER BY d.id LIMIT 1) rg ON TRUE "
            "LEFT JOIN LATERAL (SELECT valor FROM cadastro.pessoa_contato pc "
            "WHERE pc.pessoa_id=p.id AND pc.tenant_id=c.tenant_id "
            "AND pc.tipo_contato IN ('celular','whatsapp','telefone') "
            "ORDER BY pc.principal DESC,pc.id LIMIT 1) contato ON TRUE "
            "LEFT JOIN LATERAL (SELECT pe.endereco_id FROM cadastro.pessoa_endereco pe "
            "WHERE pe.pessoa_id=p.id AND pe.tenant_id=c.tenant_id "
            "ORDER BY pe.principal DESC,pe.id LIMIT 1) ep ON TRUE "
            "LEFT JOIN cadastro.endereco e ON e.id=ep.endereco_id AND e.tenant_id=c.tenant_id "
            "LEFT JOIN global.bairro b ON b.id=e.bairro_id "
            "LEFT JOIN global.municipio m ON m.codigo_ibge=e.codigo_municipio_ibge "
            "LEFT JOIN global.municipio mpj ON mpj.codigo_ibge=pj.codigo_municipio_ibge"
        )

    @staticmethod
    def _contract_dict(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["contratado"] = {
            "tipo": item["tipo_contratado"],
            "id": item.pop("contratado_id"),
            "nome": item.pop("contratado_nome"),
            "documento": item.pop("contratado_documento"),
            "rg": item.pop("contratado_rg"),
            "data_nascimento": item.pop("contratado_nascimento"),
            "telefone": item.pop("contratado_telefone"),
            "cep": item.pop("contratado_cep"),
            "logradouro": item.pop("contratado_logradouro"),
            "numero": item.pop("contratado_numero"),
            "complemento": item.pop("contratado_complemento"),
            "bairro": item.pop("contratado_bairro"),
            "codigo_municipio_ibge": item.pop("contratado_municipio"),
            "cidade": item.pop("contratado_cidade"),
            "latitude": item.pop("contratado_latitude"),
            "longitude": item.pop("contratado_longitude"),
        }
        return item
