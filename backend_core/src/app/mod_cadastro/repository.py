"""Acesso a dados do dominio de cadastro."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, and_, delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.audit.service import AuditService
from app.core.errors import BusinessRuleError
from app.core.pagination import ListParams, SortDirection
from app.core.repository import BaseRepository
from app.mod_cadastro.mobile import MobileLeaderContext
from app.models import (
    Comunidade,
    Eleitor,
    Endereco,
    EstadoCivil,
    HierarquiaLideranca,
    Indicacao,
    Lideranca,
    LiderancaTerritorio,
    NucleoFamiliar,
    Pessoa,
    PessoaComplementoPolitico,
    PessoaComunidade,
    PessoaContato,
    PessoaDocumento,
    PessoaEndereco,
    PessoaMerge,
    PessoaNucleoFamiliar,
    PessoaPessoaTipo,
    PessoaRedeSocial,
    PessoaTag,
    PessoaTipo,
    RelacionamentoPessoa,
    SuspeitaDuplicidade,
    Tag,
    ValidacaoCadastro,
)
from app.schemas.cadastro import (
    EleitorCreate,
    LiderancaCreate,
    PessoaContatoCreate,
    PessoaContatoUpdate,
    PessoaDocumentoCreate,
    PessoaDocumentoUpdate,
    PessoaEnderecoCreate,
    PessoaEnderecoUpdate,
    PessoaUpdate,
)
from app.schemas.cadastro_operacional import (
    ComplementoPoliticoInput,
    ComunidadeInput,
    HierarquiaInput,
    IndicacaoInput,
    NucleoFamiliarInput,
    PapelSubordinado,
    PessoaCadastroCreate,
    PessoaFiltros,
    PessoaRedeSocialInput,
    RelacionamentoInput,
    TagInput,
    TagUpdate,
    ValidacaoInput,
    VinculoComunidadeInput,
    VinculoNucleoInput,
)


class CadastroRepository(BaseRepository[Pessoa]):
    sortable_columns = {
        "id": Pessoa.id,
        "nome_completo": Pessoa.nome_completo,
        "data_nascimento": Pessoa.data_nascimento,
        "criado_em": Pessoa.criado_em,
        "atualizado_em": Pessoa.atualizado_em,
    }

    def _person_filters(
        self,
        statement: Select[tuple[Pessoa]],
        tenant_id: int,
        params: ListParams,
        filters: PessoaFiltros,
        accessible_territory_ids: set[int] | None = None,
    ) -> Select[tuple[Pessoa]]:
        statement = statement.where(Pessoa.tenant_id == tenant_id)
        if not filters.incluir_inativos:
            statement = statement.where(Pessoa.ativo.is_(True), Pessoa.excluido_em.is_(None))
        if params.query or filters.nome:
            term = f"%{params.query or filters.nome}%"
            statement = statement.where(
                or_(
                    Pessoa.nome_completo.ilike(term),
                    Pessoa.nome_social.ilike(term),
                    Pessoa.apelido.ilike(term),
                )
            )
        if filters.cpf:
            statement = statement.where(
                Pessoa.documentos.any(
                    (PessoaDocumento.tipo_documento == "cpf")
                    & (PessoaDocumento.numero == filters.cpf)
                )
            )
        if filters.telefone:
            statement = statement.where(
                Pessoa.contatos.any(PessoaContato.valor == filters.telefone)
            )
        if filters.tipo_id:
            statement = statement.where(
                text(
                    "EXISTS (SELECT 1 FROM cadastro.pessoa_pessoa_tipo ppt "
                    "WHERE ppt.pessoa_id = cadastro.pessoa.id "
                    "AND ppt.tenant_id = :tenant_id AND ppt.pessoa_tipo_id = :tipo_id)"
                )
            )
        if filters.lideranca_id:
            statement = statement.where(
                text(
                    "EXISTS (SELECT 1 FROM cadastro.hierarquia_lideranca hl "
                    "WHERE hl.pessoa_subordinada_id = cadastro.pessoa.id "
                    "AND hl.tenant_id = :tenant_id AND hl.ativo "
                    "AND hl.lideranca_superior_id = :lideranca_id)"
                )
            )
        if filters.cadastrado_por_lideranca_id:
            statement = statement.where(
                Pessoa.cadastrado_por_lideranca_id == filters.cadastrado_por_lideranca_id
            )
        if filters.origem_cadastro:
            statement = statement.where(Pessoa.origem_cadastro == filters.origem_cadastro)
        if filters.territorio_id:
            statement = statement.where(
                text(
                    "EXISTS (SELECT 1 FROM territorio.pessoa_territorio pt "
                    "WHERE pt.pessoa_id = cadastro.pessoa.id "
                    "AND pt.tenant_id = :tenant_id AND pt.territorio_id = :territorio_id)"
                )
            )
        if accessible_territory_ids is not None:
            if not accessible_territory_ids:
                statement = statement.where(text("FALSE"))
            else:
                statement = statement.where(
                    text(
                        "EXISTS (SELECT 1 FROM territorio.pessoa_territorio access_pt "
                        "WHERE access_pt.pessoa_id = cadastro.pessoa.id "
                        "AND access_pt.tenant_id = :tenant_id "
                        "AND access_pt.territorio_id = ANY(:accessible_territory_ids))"
                    )
                )
        if filters.tag_id:
            statement = statement.where(
                text(
                    "EXISTS (SELECT 1 FROM cadastro.pessoa_tag ptag "
                    "WHERE ptag.pessoa_id = cadastro.pessoa.id "
                    "AND ptag.tenant_id = :tenant_id AND ptag.tag_id = :tag_id)"
                )
            )
        return statement

    async def list_people(
        self,
        tenant_id: int,
        params: ListParams,
        filters: PessoaFiltros,
        accessible_territory_ids: set[int] | None = None,
    ) -> tuple[list[Pessoa], int]:
        order_column = self.sortable_columns.get(params.order_by)
        if order_column is None:
            raise BusinessRuleError(
                "Campo de ordenacao nao permitido.",
                code="invalid_order_field",
                details={"allowed": sorted(self.sortable_columns)},
            )
        filtered = self._person_filters(
            select(Pessoa), tenant_id, params, filters, accessible_territory_ids
        )
        values = {
            "tenant_id": tenant_id,
            "tipo_id": filters.tipo_id,
            "lideranca_id": filters.lideranca_id,
            "territorio_id": filters.territorio_id,
            "tag_id": filters.tag_id,
            "accessible_territory_ids": (
                sorted(accessible_territory_ids)
                if accessible_territory_ids is not None
                else None
            ),
        }
        total = int(
            (
                await self.session.scalar(
                    select(func.count()).select_from(filtered.order_by(None).subquery()),
                    values,
                )
            )
            or 0
        )
        ordering = (
            order_column.desc() if params.direction == SortDirection.DESC else order_column.asc()
        )
        result = await self.session.scalars(
            filtered.order_by(ordering).offset(params.offset).limit(params.page_size),
            values,
        )
        return list(result.unique().all()), total

    async def person_in_territories(
        self, tenant_id: int, person_id: int, territory_ids: set[int]
    ) -> bool:
        if not territory_ids:
            return False
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM territorio.pessoa_territorio "
                    "WHERE tenant_id = :tenant_id AND pessoa_id = :person_id "
                    "AND territorio_id = ANY(:territory_ids))"
                ),
                {
                    "tenant_id": tenant_id,
                    "person_id": person_id,
                    "territory_ids": sorted(territory_ids),
                },
            )
        )

    async def get_person(self, tenant_id: int, person_id: int) -> Pessoa | None:
        result: Pessoa | None = await self.session.scalar(
            select(Pessoa).where(
                Pessoa.id == person_id,
                Pessoa.tenant_id == tenant_id,
                Pessoa.excluido_em.is_(None),
            )
        )
        if result is not None:
            await self.session.refresh(
                result,
                attribute_names=[
                    "documentos",
                    "contatos",
                    "enderecos",
                    "eleitor",
                    "lideranca",
                ],
            )
        return result

    async def person_exists(self, tenant_id: int, person_id: int) -> bool:
        return (
            await self.session.scalar(
                select(Pessoa.id).where(
                    Pessoa.id == person_id,
                    Pessoa.tenant_id == tenant_id,
                    Pessoa.excluido_em.is_(None),
                )
            )
            is not None
        )

    async def address_exists(self, tenant_id: int, address_id: int) -> bool:
        return (
            await self.session.scalar(
                select(Endereco.id).where(
                    Endereco.id == address_id, Endereco.tenant_id == tenant_id
                )
            )
            is not None
        )

    async def territory_exists(self, tenant_id: int, territory_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM territorio.territorio "
                    "WHERE id = :territory_id AND tenant_id = :tenant_id)"
                ),
                {"territory_id": territory_id, "tenant_id": tenant_id},
            )
        )

    async def strong_duplicate(
        self,
        tenant_id: int,
        *,
        cpf: str | None,
        titulo: str | None,
        exclude_person_id: int | None = None,
    ) -> tuple[str, int] | None:
        if cpf:
            statement = select(PessoaDocumento.pessoa_id).where(
                PessoaDocumento.tenant_id == tenant_id,
                PessoaDocumento.tipo_documento == "cpf",
                PessoaDocumento.numero == cpf,
            )
            if exclude_person_id:
                statement = statement.where(PessoaDocumento.pessoa_id != exclude_person_id)
            person_id = await self.session.scalar(statement)
            if person_id is not None:
                return "cpf", int(person_id)
        if titulo:
            statement = select(Eleitor.pessoa_id).where(
                Eleitor.tenant_id == tenant_id, Eleitor.titulo_eleitor == titulo
            )
            if exclude_person_id:
                statement = statement.where(Eleitor.pessoa_id != exclude_person_id)
            person_id = await self.session.scalar(statement)
            if person_id is not None:
                return "titulo_eleitor", int(person_id)
        return None

    async def resolve_global_fonte_dado_id(self, codigo: str) -> int | None:
        value = await self.session.scalar(
            text(
                "SELECT id FROM etl.fonte_dado "
                "WHERE codigo = :codigo AND tenant_id IS NULL AND ativo LIMIT 1"
            ),
            {"codigo": codigo},
        )
        return int(value) if value is not None else None

    async def create_person(
        self,
        tenant_id: int,
        user_id: int,
        payload: PessoaCadastroCreate,
        *,
        mobile: MobileLeaderContext | None = None,
        origem_cadastro: str | None = None,
        fonte_dado_id: int | None = None,
    ) -> Pessoa:
        now = datetime.now(UTC)
        mobile_fields: dict[str, Any] = {}
        if mobile is not None:
            mobile_fields = {
                "origem_cadastro": mobile.origem_cadastro,
                "cadastrado_por_lideranca_id": mobile.cadastrado_por_lideranca_id,
            }
            if mobile.fonte_dado_id is not None:
                mobile_fields["fonte_dado_id"] = mobile.fonte_dado_id
        elif origem_cadastro:
            mobile_fields["origem_cadastro"] = origem_cadastro
            if fonte_dado_id is not None:
                mobile_fields["fonte_dado_id"] = fonte_dado_id
        person = Pessoa(
            uuid_publico=uuid4(),
            tenant_id=tenant_id,
            **payload.model_dump(
                exclude={
                    "documentos",
                    "contatos",
                    "enderecos",
                    "redes_sociais",
                    "tipo_ids",
                    "eleitor",
                    "lideranca",
                    "lideranca_superior_id",
                    "papel_subordinado",
                    "indicacao",
                    "complemento_politico",
                }
            ),
            **mobile_fields,
            ativo=True,
            criado_por=user_id,
            atualizado_por=user_id,
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(person)
        await self.session.flush()
        for document in payload.documentos:
            await self.add_document(tenant_id, person.id, document)
        for contact in payload.contatos:
            await self.add_contact(tenant_id, person.id, contact)
        for address in payload.enderecos:
            await self.add_address(tenant_id, person.id, address)
        for social in payload.redes_sociais:
            await self.add_social(tenant_id, person.id, social)
        for type_id in payload.tipo_ids:
            self.session.add(
                PessoaPessoaTipo(
                    pessoa_id=person.id,
                    pessoa_tipo_id=type_id,
                    tenant_id=tenant_id,
                    criado_em=now,
                )
            )
        if payload.eleitor:
            await self.upsert_voter(tenant_id, person.id, payload.eleitor)
        if payload.lideranca:
            await self.upsert_leadership(tenant_id, person.id, payload.lideranca)
        if payload.lideranca_superior_id:
            hierarchy_payload = HierarquiaInput(
                lideranca_superior_id=payload.lideranca_superior_id,
                pessoa_subordinada_id=person.id,
                papel_subordinado=payload.papel_subordinado,
                origem=mobile.hierarquia_origem if mobile is not None else None,
            )
            await self.add_hierarchy(tenant_id, hierarchy_payload)
        if payload.indicacao:
            await self.add_indication(tenant_id, person.id, payload.indicacao)
        if payload.complemento_politico:
            await self.upsert_political(tenant_id, person.id, payload.complemento_politico)
        await self.session.flush()
        return person

    async def update_person(self, person: Pessoa, payload: PessoaUpdate, user_id: int) -> Pessoa:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(person, field, value)
        person.atualizado_por = user_id
        person.atualizado_em = datetime.now(UTC)
        await self.session.flush()
        return person

    async def calculate_registration_completeness(
        self, tenant_id: int, person_id: int, user_id: int
    ) -> Decimal:
        value = await self.session.scalar(
            text(
                """
                UPDATE cadastro.pessoa
                   SET completude_cadastral = cadastro.calcular_completude_cadastral(id),
                       atualizado_por = :user_id,
                       atualizado_em = now()
                 WHERE tenant_id = :tenant_id
                   AND id = :person_id
                   AND excluido_em IS NULL
                RETURNING completude_cadastral
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id, "user_id": user_id},
        )
        if value is None:
            raise BusinessRuleError(
                "Nao foi possivel calcular a completude cadastral.",
                code="registration_completeness_not_calculated",
            )
        self.session.expire_all()
        return Decimal(value)

    async def deactivate_person(self, person: Pessoa, user_id: int) -> None:
        now = datetime.now(UTC)
        person.ativo = False
        person.excluido_em = now
        person.atualizado_em = now
        person.atualizado_por = user_id
        await self.session.flush()

    async def add_document(
        self, tenant_id: int, person_id: int, payload: PessoaDocumentoCreate
    ) -> PessoaDocumento:
        item = PessoaDocumento(
            tenant_id=tenant_id,
            pessoa_id=person_id,
            **payload.model_dump(),
            criado_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def document(
        self, tenant_id: int, person_id: int, document_id: int
    ) -> PessoaDocumento | None:
        result: PessoaDocumento | None = await self.session.scalar(
            select(PessoaDocumento).where(
                PessoaDocumento.id == document_id,
                PessoaDocumento.tenant_id == tenant_id,
                PessoaDocumento.pessoa_id == person_id,
            )
        )
        return result

    async def update_document(
        self, item: PessoaDocumento, payload: PessoaDocumentoUpdate
    ) -> PessoaDocumento:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def add_contact(
        self, tenant_id: int, person_id: int, payload: PessoaContatoCreate
    ) -> PessoaContato:
        if payload.principal:
            current = await self.session.scalars(
                select(PessoaContato).where(
                    PessoaContato.tenant_id == tenant_id,
                    PessoaContato.pessoa_id == person_id,
                    PessoaContato.tipo_contato == payload.tipo_contato,
                    PessoaContato.principal.is_(True),
                )
            )
            for item in current:
                item.principal = False
        item = PessoaContato(
            tenant_id=tenant_id,
            pessoa_id=person_id,
            **payload.model_dump(),
            criado_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def contact(
        self, tenant_id: int, person_id: int, contact_id: int
    ) -> PessoaContato | None:
        result: PessoaContato | None = await self.session.scalar(
            select(PessoaContato).where(
                PessoaContato.id == contact_id,
                PessoaContato.tenant_id == tenant_id,
                PessoaContato.pessoa_id == person_id,
            )
        )
        return result

    async def delete_contact(self, item: PessoaContato) -> None:
        await self.session.delete(item)
        await self.session.flush()

    async def person_linked_to_leadership(
        self, tenant_id: int, person_id: int, leadership_id: int
    ) -> bool:
        registered_or_own = await self.session.scalar(
            select(Pessoa.id)
            .outerjoin(
                Lideranca,
                (Lideranca.pessoa_id == Pessoa.id) & (Lideranca.tenant_id == Pessoa.tenant_id),
            )
            .where(
                Pessoa.tenant_id == tenant_id,
                Pessoa.id == person_id,
                or_(
                    Pessoa.cadastrado_por_lideranca_id == leadership_id,
                    Lideranca.id == leadership_id,
                    Lideranca.coordenador_id == leadership_id,
                ),
            )
            .limit(1)
        )
        if registered_or_own is not None:
            return True
        hierarchy = await self.session.scalar(
            select(HierarquiaLideranca.id)
            .where(
                HierarquiaLideranca.tenant_id == tenant_id,
                HierarquiaLideranca.pessoa_subordinada_id == person_id,
                HierarquiaLideranca.lideranca_superior_id == leadership_id,
                HierarquiaLideranca.ativo.is_(True),
            )
            .limit(1)
        )
        return hierarchy is not None

    async def update_contact(
        self, tenant_id: int, item: PessoaContato, payload: PessoaContatoUpdate
    ) -> PessoaContato:
        if payload.principal:
            current = await self.session.scalars(
                select(PessoaContato).where(
                    PessoaContato.tenant_id == tenant_id,
                    PessoaContato.pessoa_id == item.pessoa_id,
                    PessoaContato.tipo_contato == item.tipo_contato,
                    PessoaContato.id != item.id,
                    PessoaContato.principal.is_(True),
                )
            )
            for current_item in current:
                current_item.principal = False
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def add_address(
        self, tenant_id: int, person_id: int, payload: PessoaEnderecoCreate
    ) -> PessoaEndereco:
        now = datetime.now(UTC)
        address = Endereco(
            tenant_id=tenant_id,
            **payload.endereco.model_dump(),
            geocodificado=False,
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(address)
        await self.session.flush()
        if payload.principal:
            current = await self.session.scalars(
                select(PessoaEndereco).where(
                    PessoaEndereco.tenant_id == tenant_id,
                    PessoaEndereco.pessoa_id == person_id,
                    PessoaEndereco.tipo == payload.tipo,
                    PessoaEndereco.principal.is_(True),
                )
            )
            for item in current:
                item.principal = False
        link = PessoaEndereco(
            tenant_id=tenant_id,
            pessoa_id=person_id,
            endereco_id=address.id,
            tipo=payload.tipo,
            principal=payload.principal,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def address_link(
        self, tenant_id: int, person_id: int, link_id: int
    ) -> PessoaEndereco | None:
        result: PessoaEndereco | None = await self.session.scalar(
            select(PessoaEndereco).where(
                PessoaEndereco.id == link_id,
                PessoaEndereco.tenant_id == tenant_id,
                PessoaEndereco.pessoa_id == person_id,
            )
        )
        if result is not None:
            await self.session.refresh(result, attribute_names=["endereco"])
        return result

    async def update_address(
        self,
        tenant_id: int,
        item: PessoaEndereco,
        payload: PessoaEnderecoUpdate,
    ) -> PessoaEndereco:
        if payload.principal:
            current = await self.session.scalars(
                select(PessoaEndereco).where(
                    PessoaEndereco.tenant_id == tenant_id,
                    PessoaEndereco.pessoa_id == item.pessoa_id,
                    PessoaEndereco.tipo == (payload.tipo or item.tipo),
                    PessoaEndereco.id != item.id,
                    PessoaEndereco.principal.is_(True),
                )
            )
            for current_item in current:
                current_item.principal = False
        for field, value in payload.model_dump(exclude_unset=True, exclude={"endereco"}).items():
            setattr(item, field, value)
        if payload.endereco is not None:
            address_values = payload.endereco.model_dump(exclude_unset=True)
            for field, value in address_values.items():
                setattr(item.endereco, field, value)
            if "latitude" in address_values or "longitude" in address_values:
                item.endereco.geocodificado = (
                    item.endereco.latitude is not None and item.endereco.longitude is not None
                )
            item.endereco.atualizado_em = datetime.now(UTC)
        await self.session.flush()
        return item

    async def add_social(
        self, tenant_id: int, person_id: int, payload: PessoaRedeSocialInput
    ) -> PessoaRedeSocial:
        item = PessoaRedeSocial(
            tenant_id=tenant_id,
            pessoa_id=person_id,
            **payload.model_dump(),
            criado_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def social(
        self, tenant_id: int, person_id: int, social_id: int
    ) -> PessoaRedeSocial | None:
        return await self.session.scalar(
            select(PessoaRedeSocial).where(
                PessoaRedeSocial.id == social_id,
                PessoaRedeSocial.tenant_id == tenant_id,
                PessoaRedeSocial.pessoa_id == person_id,
            )
        )

    async def update_social(
        self, item: PessoaRedeSocial, payload: PessoaRedeSocialInput
    ) -> PessoaRedeSocial:
        for field, value in payload.model_dump().items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def upsert_voter(self, tenant_id: int, person_id: int, payload: EleitorCreate) -> Eleitor:
        item = await self.session.scalar(
            select(Eleitor).where(Eleitor.tenant_id == tenant_id, Eleitor.pessoa_id == person_id)
        )
        now = datetime.now(UTC)
        if item is None:
            item = Eleitor(
                tenant_id=tenant_id,
                pessoa_id=person_id,
                **payload.model_dump(),
                criado_em=now,
                atualizado_em=now,
            )
            self.session.add(item)
        else:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(item, field, value)
            item.atualizado_em = now
        await self.session.flush()
        return item

    async def upsert_leadership(
        self, tenant_id: int, person_id: int, payload: LiderancaCreate
    ) -> Lideranca:
        item = await self.session.scalar(
            select(Lideranca).where(
                Lideranca.tenant_id == tenant_id, Lideranca.pessoa_id == person_id
            )
        )
        now = datetime.now(UTC)
        if item is None:
            item = Lideranca(
                tenant_id=tenant_id,
                pessoa_id=person_id,
                **payload.model_dump(),
                criado_em=now,
                atualizado_em=now,
            )
            self.session.add(item)
        else:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(item, field, value)
            item.atualizado_em = now
        await self.session.flush()
        return item

    async def add_indication(
        self, tenant_id: int, person_id: int, payload: IndicacaoInput
    ) -> Indicacao:
        item = Indicacao(
            tenant_id=tenant_id,
            pessoa_indicada_id=person_id,
            **payload.model_dump(),
            criado_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def person_has_indication(self, tenant_id: int, person_id: int) -> bool:
        return bool(
            await self.session.scalar(
                select(Indicacao.id).where(
                    Indicacao.tenant_id == tenant_id,
                    Indicacao.pessoa_indicada_id == person_id,
                )
            )
        )

    async def upsert_political(
        self, tenant_id: int, person_id: int, payload: ComplementoPoliticoInput
    ) -> PessoaComplementoPolitico:
        item = await self.session.scalar(
            select(PessoaComplementoPolitico).where(
                PessoaComplementoPolitico.tenant_id == tenant_id,
                PessoaComplementoPolitico.pessoa_id == person_id,
            )
        )
        if item is None:
            item = PessoaComplementoPolitico(
                tenant_id=tenant_id, pessoa_id=person_id, **payload.model_dump()
            )
            self.session.add(item)
        else:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(item, field, value)
        item.atualizado_em = datetime.now(UTC)
        await self.session.flush()
        return item

    async def get_person_extensions(self, tenant_id: int, person_id: int) -> dict[str, Any]:
        async def many(model: Any, criterion: Any) -> list[Any]:
            result = await self.session.scalars(
                select(model).where(model.tenant_id == tenant_id, criterion)
            )
            return list(result.all())

        type_result = await self.session.scalars(
            select(PessoaTipo)
            .join(PessoaPessoaTipo, PessoaPessoaTipo.pessoa_tipo_id == PessoaTipo.id)
            .where(
                PessoaPessoaTipo.tenant_id == tenant_id,
                PessoaPessoaTipo.pessoa_id == person_id,
            )
        )
        political = await self.session.scalar(
            select(PessoaComplementoPolitico).where(
                PessoaComplementoPolitico.tenant_id == tenant_id,
                PessoaComplementoPolitico.pessoa_id == person_id,
            )
        )
        tags = await self.session.scalars(
            select(Tag)
            .join(PessoaTag, PessoaTag.tag_id == Tag.id)
            .where(
                PessoaTag.tenant_id == tenant_id,
                PessoaTag.pessoa_id == person_id,
            )
            .order_by(Tag.nome)
        )
        communities = await self.session.scalars(
            select(Comunidade)
            .join(
                PessoaComunidade,
                PessoaComunidade.comunidade_id == Comunidade.id,
            )
            .where(
                PessoaComunidade.tenant_id == tenant_id,
                PessoaComunidade.pessoa_id == person_id,
            )
            .order_by(Comunidade.nome)
        )
        nuclei = await self.session.scalars(
            select(NucleoFamiliar)
            .join(
                PessoaNucleoFamiliar,
                PessoaNucleoFamiliar.nucleo_familiar_id == NucleoFamiliar.id,
            )
            .where(
                PessoaNucleoFamiliar.tenant_id == tenant_id,
                PessoaNucleoFamiliar.pessoa_id == person_id,
            )
            .order_by(NucleoFamiliar.nome, NucleoFamiliar.id)
        )
        hierarchy = await self.session.scalars(
            select(HierarquiaLideranca).where(
                HierarquiaLideranca.tenant_id == tenant_id,
                HierarquiaLideranca.pessoa_subordinada_id == person_id,
            )
        )
        indication_rows = await self.session.execute(
            select(Indicacao, Pessoa.nome_completo)
            .outerjoin(
                Pessoa,
                (Pessoa.id == Indicacao.pessoa_indicada_id)
                & (Pessoa.tenant_id == Indicacao.tenant_id),
            )
            .where(
                Indicacao.tenant_id == tenant_id,
                Indicacao.pessoa_indicante_id == person_id,
            )
            .order_by(Indicacao.data_indicacao.desc(), Indicacao.id.desc())
        )
        indications: list[Indicacao] = []
        for indication, indicated_name in indication_rows.all():
            indication.pessoa_indicada_nome = indicated_name
            indications.append(indication)
        return {
            "redes_sociais": await many(PessoaRedeSocial, PessoaRedeSocial.pessoa_id == person_id),
            "tipos": list(type_result.all()),
            "indicacoes": indications,
            "complemento_politico": political,
            "tags": list(tags.all()),
            "comunidades": list(communities.all()),
            "nucleos_familiares": list(nuclei.all()),
            "hierarquia": list(hierarchy.all()),
        }

    async def list_person_types(self) -> list[PessoaTipo]:
        result = await self.session.scalars(select(PessoaTipo).order_by(PessoaTipo.nome))
        return list(result.all())

    async def list_marital_statuses(self) -> list[EstadoCivil]:
        result = await self.session.scalars(
            select(EstadoCivil).order_by(EstadoCivil.ordem, EstadoCivil.nome)
        )
        return list(result.all())

    async def list_religions(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT id, nome FROM cadastro.religiao ORDER BY nome")
        )
        return [{"id": int(row.id), "nome": str(row.nome)} for row in result]

    async def marital_status_exists(self, marital_status_id: int) -> bool:
        return bool(
            await self.session.scalar(
                select(func.count())
                .select_from(EstadoCivil)
                .where(EstadoCivil.id == marital_status_id)
            )
        )

    async def list_leaderships(
        self,
        tenant_id: int,
        query: str | None = None,
        coordinator_id: int | None = None,
        territory_id: int | None = None,
        leadership_type: str | None = None,
    ) -> list[Lideranca]:
        statement = (
            select(Lideranca)
            .join(Pessoa, Pessoa.id == Lideranca.pessoa_id)
            .options(
                selectinload(Lideranca.pessoa),
                selectinload(Lideranca.coordenador).selectinload(Lideranca.pessoa),
            )
            .where(
                Lideranca.tenant_id == tenant_id,
                Pessoa.tenant_id == tenant_id,
                Lideranca.ativo.is_(True),
            )
        )
        if query:
            term = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    func.unaccent(Pessoa.nome_completo).ilike(func.unaccent(term)),
                    func.unaccent(Lideranca.apelido_campanha).ilike(func.unaccent(term)),
                )
            )
        if coordinator_id is not None:
            statement = statement.where(Lideranca.coordenador_id == coordinator_id)
        if leadership_type is not None:
            statement = statement.where(Lideranca.tipo_lideranca == leadership_type)
        if territory_id is not None:
            statement = statement.where(
                Lideranca.id.in_(
                    select(LiderancaTerritorio.lideranca_id).where(
                        LiderancaTerritorio.tenant_id == tenant_id,
                        LiderancaTerritorio.territorio_id == territory_id,
                    )
                )
            )
        result = await self.session.scalars(
            statement.order_by(Lideranca.tipo_lideranca, Lideranca.id)
        )
        return list(result.all())

    async def leadership_territories(
        self, tenant_id: int, leadership_ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        if not leadership_ids:
            return {}
        rows = await self.session.execute(
            text(
                "SELECT lt.lideranca_id, t.id AS territorio_id, t.nome "
                "FROM territorio.lideranca_territorio lt "
                "JOIN territorio.territorio t "
                "  ON t.id = lt.territorio_id AND t.tenant_id = lt.tenant_id "
                "WHERE lt.tenant_id = :tenant_id "
                "  AND lt.lideranca_id = ANY(:leadership_ids) "
                "ORDER BY t.nome, t.id"
            ),
            {"tenant_id": tenant_id, "leadership_ids": leadership_ids},
        )
        result: dict[int, list[dict[str, Any]]] = {}
        for leadership_id, territory_id, territory_name in rows:
            result.setdefault(int(leadership_id), []).append(
                {"id": int(territory_id), "nome": str(territory_name)}
            )
        return result

    async def leadership_person_tags(
        self, tenant_id: int, leadership_ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        if not leadership_ids:
            return {}
        rows = await self.session.execute(
            text(
                "SELECT l.id AS lideranca_id, t.id AS tag_id, t.nome, t.cor "
                "FROM cadastro.lideranca l "
                "JOIN cadastro.pessoa_tag pt "
                "  ON pt.pessoa_id = l.pessoa_id AND pt.tenant_id = l.tenant_id "
                "JOIN cadastro.tag t "
                "  ON t.id = pt.tag_id AND t.tenant_id = pt.tenant_id "
                "WHERE l.tenant_id = :tenant_id "
                "  AND l.id = ANY(:leadership_ids) "
                "  AND t.ativo = TRUE "
                "ORDER BY t.nome, t.id"
            ),
            {"tenant_id": tenant_id, "leadership_ids": leadership_ids},
        )
        result: dict[int, list[dict[str, Any]]] = {}
        for leadership_id, tag_id, tag_name, tag_color in rows:
            result.setdefault(int(leadership_id), []).append(
                {
                    "id": int(tag_id),
                    "nome": str(tag_name),
                    "cor": str(tag_color) if tag_color else None,
                }
            )
        return result

    async def list_hierarchy(
        self,
        tenant_id: int,
        person_query: str | None = None,
        superior_id: int | None = None,
        role: str | None = None,
    ) -> list[HierarquiaLideranca]:
        statement = (
            select(HierarquiaLideranca)
            .join(Pessoa, Pessoa.id == HierarquiaLideranca.pessoa_subordinada_id)
            .where(
                HierarquiaLideranca.tenant_id == tenant_id,
                Pessoa.tenant_id == tenant_id,
            )
        )
        if person_query:
            term = f"%{person_query.strip()}%"
            statement = statement.where(
                func.unaccent(Pessoa.nome_completo).ilike(func.unaccent(term))
            )
        if superior_id is not None:
            statement = statement.where(
                HierarquiaLideranca.lideranca_superior_id == superior_id
            )
        if role is not None:
            statement = statement.where(HierarquiaLideranca.papel_subordinado == role)
        result = await self.session.scalars(
            statement.order_by(
                HierarquiaLideranca.lideranca_superior_id,
                HierarquiaLideranca.pessoa_subordinada_id,
            )
        )
        return list(result.all())

    async def hierarchy(self, tenant_id: int, hierarchy_id: int) -> HierarquiaLideranca | None:
        return await self.session.scalar(
            select(HierarquiaLideranca).where(
                HierarquiaLideranca.tenant_id == tenant_id,
                HierarquiaLideranca.id == hierarchy_id,
            )
        )

    async def active_hierarchy_for_person(
        self, tenant_id: int, person_id: int, *, exclude_id: int | None = None
    ) -> HierarquiaLideranca | None:
        statement = select(HierarquiaLideranca).where(
            HierarquiaLideranca.tenant_id == tenant_id,
            HierarquiaLideranca.pessoa_subordinada_id == person_id,
            HierarquiaLideranca.ativo.is_(True),
        )
        if exclude_id is not None:
            statement = statement.where(HierarquiaLideranca.id != exclude_id)
        return await self.session.scalar(statement.limit(1))

    async def set_hierarchy_status(
        self, item: HierarquiaLideranca, active: bool
    ) -> HierarquiaLideranca:
        item.ativo = active
        item.data_fim = None if active else date.today()
        if active:
            item.campanha_eleicao_id = await self._active_campaign_id(item.tenant_id)
        await self.session.flush()
        return item

    async def set_hierarchy_role(
        self, item: HierarquiaLideranca, role: PapelSubordinado
    ) -> HierarquiaLideranca:
        item.papel_subordinado = role
        await self.session.flush()
        return item

    async def delete_hierarchy(self, item: HierarquiaLideranca) -> None:
        await self.session.delete(item)

    async def delete_leadership(self, item: Lideranca) -> None:
        await self.session.delete(item)

    async def hierarchy_names(
        self, tenant_id: int, hierarchy_ids: list[int]
    ) -> dict[int, dict[str, str]]:
        if not hierarchy_ids:
            return {}
        rows = await self.session.execute(
            text(
                "SELECT h.id, superior.nome_completo AS superior_nome, "
                "       subordinada.nome_completo AS subordinada_nome "
                "FROM cadastro.hierarquia_lideranca h "
                "JOIN cadastro.lideranca l "
                "  ON l.id = h.lideranca_superior_id AND l.tenant_id = h.tenant_id "
                "JOIN cadastro.pessoa superior "
                "  ON superior.id = l.pessoa_id AND superior.tenant_id = h.tenant_id "
                "JOIN cadastro.pessoa subordinada "
                "  ON subordinada.id = h.pessoa_subordinada_id "
                " AND subordinada.tenant_id = h.tenant_id "
                "WHERE h.tenant_id = :tenant_id AND h.id = ANY(:hierarchy_ids)"
            ),
            {"tenant_id": tenant_id, "hierarchy_ids": hierarchy_ids},
        )
        return {
            int(row.id): {
                "lideranca_superior_nome": str(row.superior_nome),
                "pessoa_subordinada_nome": str(row.subordinada_nome),
            }
            for row in rows
        }

    async def replace_person_types(
        self, tenant_id: int, person_id: int, type_ids: list[int]
    ) -> None:
        await self.session.execute(
            delete(PessoaPessoaTipo).where(
                PessoaPessoaTipo.tenant_id == tenant_id,
                PessoaPessoaTipo.pessoa_id == person_id,
            )
        )
        now = datetime.now(UTC)
        self.session.add_all(
            [
                PessoaPessoaTipo(
                    pessoa_id=person_id,
                    pessoa_tipo_id=type_id,
                    tenant_id=tenant_id,
                    criado_em=now,
                )
                for type_id in type_ids
            ]
        )
        await self.session.flush()

    async def leadership(self, tenant_id: int, leadership_id: int) -> Lideranca | None:
        result: Lideranca | None = await self.session.scalar(
            select(Lideranca).where(Lideranca.id == leadership_id, Lideranca.tenant_id == tenant_id)
        )
        return result

    async def hierarchy_would_cycle(
        self, tenant_id: int, superior_id: int, subordinate_person_id: int
    ) -> bool:
        superior_person_id = await self.session.scalar(
            select(Lideranca.pessoa_id).where(
                Lideranca.id == superior_id, Lideranca.tenant_id == tenant_id
            )
        )
        if superior_person_id is None:
            return True
        if int(superior_person_id) == subordinate_person_id:
            return True
        subordinate_leadership_id = await self.session.scalar(
            select(Lideranca.id).where(
                Lideranca.tenant_id == tenant_id,
                Lideranca.pessoa_id == subordinate_person_id,
            )
        )
        if subordinate_leadership_id is None:
            return False
        return bool(
            await self.session.scalar(
                text(
                    """
                    WITH RECURSIVE descendants(pessoa_id) AS (
                        SELECT pessoa_subordinada_id
                        FROM cadastro.hierarquia_lideranca
                        WHERE tenant_id = :tenant_id
                          AND lideranca_superior_id = :subordinate_leadership_id
                          AND ativo
                        UNION
                        SELECT child.pessoa_subordinada_id
                        FROM descendants parent
                        JOIN cadastro.lideranca leader
                          ON leader.pessoa_id = parent.pessoa_id
                         AND leader.tenant_id = :tenant_id
                        JOIN cadastro.hierarquia_lideranca child
                          ON child.lideranca_superior_id = leader.id
                         AND child.tenant_id = :tenant_id
                         AND child.ativo
                    )
                    SELECT EXISTS (
                        SELECT 1 FROM descendants WHERE pessoa_id = :superior_person_id
                    )
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "subordinate_leadership_id": subordinate_leadership_id,
                    "superior_person_id": superior_person_id,
                },
            )
        )

    async def add_hierarchy(self, tenant_id: int, payload: HierarquiaInput) -> HierarquiaLideranca:
        data = payload.model_dump()
        if data.get("origem") is None:
            data.pop("origem", None)
        item = HierarquiaLideranca(
            tenant_id=tenant_id,
            campanha_eleicao_id=await self._active_campaign_id(tenant_id),
            **data,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def _active_campaign_id(self, tenant_id: int) -> int | None:
        campaign_id = await self.session.scalar(
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
        return int(campaign_id) if campaign_id is not None else None

    async def add_relationship(
        self, tenant_id: int, origin_id: int, payload: RelacionamentoInput
    ) -> RelacionamentoPessoa:
        item = RelacionamentoPessoa(
            tenant_id=tenant_id,
            pessoa_origem_id=origin_id,
            **payload.model_dump(),
            criado_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def create_nucleus(self, tenant_id: int, payload: NucleoFamiliarInput) -> NucleoFamiliar:
        now = datetime.now(UTC)
        item = NucleoFamiliar(
            tenant_id=tenant_id,
            **payload.model_dump(),
            quantidade_membros=0,
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def nucleus(self, tenant_id: int, nucleus_id: int) -> NucleoFamiliar | None:
        result: NucleoFamiliar | None = await self.session.scalar(
            select(NucleoFamiliar).where(
                NucleoFamiliar.id == nucleus_id, NucleoFamiliar.tenant_id == tenant_id
            )
        )
        return result

    async def list_nuclei(self, tenant_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT n.id, n.tenant_id, n.nome, n.pessoa_referencia_id,
                       p.nome_completo AS pessoa_referencia_nome,
                       n.endereco_id, n.quantidade_membros,
                       n.criado_em, n.atualizado_em
                  FROM cadastro.nucleo_familiar n
             LEFT JOIN cadastro.pessoa p
                    ON p.id = n.pessoa_referencia_id
                   AND p.tenant_id = n.tenant_id
                 WHERE n.tenant_id = :tenant_id
              ORDER BY n.nome, n.id
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def add_nucleus_member(
        self, tenant_id: int, nucleus: NucleoFamiliar, payload: VinculoNucleoInput
    ) -> PessoaNucleoFamiliar:
        item = PessoaNucleoFamiliar(
            tenant_id=tenant_id,
            nucleo_familiar_id=nucleus.id,
            **payload.model_dump(),
        )
        self.session.add(item)
        await self.session.flush()
        nucleus.quantidade_membros = int(
            (
                await self.session.scalar(
                    select(func.count()).where(
                        PessoaNucleoFamiliar.tenant_id == tenant_id,
                        PessoaNucleoFamiliar.nucleo_familiar_id == nucleus.id,
                    )
                )
            )
            or 0
        )
        nucleus.atualizado_em = datetime.now(UTC)
        return item

    async def nucleus_people(self, tenant_id: int, nucleus_id: int) -> list[dict[str, Any]]:
        rows = await self.session.execute(
            select(
                Pessoa.id,
                Pessoa.nome_completo,
                Pessoa.data_nascimento,
                PessoaNucleoFamiliar.parentesco,
                PessoaNucleoFamiliar.observacao,
            )
            .join(
                PessoaNucleoFamiliar,
                (PessoaNucleoFamiliar.pessoa_id == Pessoa.id)
                & (PessoaNucleoFamiliar.tenant_id == Pessoa.tenant_id),
            )
            .where(
                Pessoa.tenant_id == tenant_id,
                PessoaNucleoFamiliar.nucleo_familiar_id == nucleus_id,
            )
            .order_by(Pessoa.nome_completo, Pessoa.id)
        )
        return [dict(row) for row in rows.mappings().all()]

    async def remove_nucleus_member(
        self, tenant_id: int, nucleus: NucleoFamiliar, person_id: int
    ) -> bool:
        result = await self.session.execute(
            delete(PessoaNucleoFamiliar).where(
                PessoaNucleoFamiliar.tenant_id == tenant_id,
                PessoaNucleoFamiliar.nucleo_familiar_id == nucleus.id,
                PessoaNucleoFamiliar.pessoa_id == person_id,
            )
        )
        if result.rowcount:
            nucleus.quantidade_membros = int(
                (
                    await self.session.scalar(
                        select(func.count()).where(
                            PessoaNucleoFamiliar.tenant_id == tenant_id,
                            PessoaNucleoFamiliar.nucleo_familiar_id == nucleus.id,
                        )
                    )
                )
                or 0
            )
            nucleus.atualizado_em = datetime.now(UTC)
        return bool(result.rowcount)

    async def create_community(self, tenant_id: int, payload: ComunidadeInput) -> Comunidade:
        now = datetime.now(UTC)
        item = Comunidade(
            tenant_id=tenant_id, **payload.model_dump(), criado_em=now, atualizado_em=now
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_community(self, item: Comunidade, payload: ComunidadeInput) -> Comunidade:
        for field, value in payload.model_dump().items():
            setattr(item, field, value)
        item.atualizado_em = datetime.now(UTC)
        await self.session.flush()
        return item

    async def community(self, tenant_id: int, community_id: int) -> Comunidade | None:
        result: Comunidade | None = await self.session.scalar(
            select(Comunidade).where(
                Comunidade.id == community_id, Comunidade.tenant_id == tenant_id
            )
        )
        return result

    async def list_communities(self, tenant_id: int) -> list[Comunidade]:
        result = await self.session.scalars(
            select(Comunidade).where(Comunidade.tenant_id == tenant_id).order_by(Comunidade.nome)
        )
        return list(result.all())

    async def add_community_member(
        self, tenant_id: int, community_id: int, payload: VinculoComunidadeInput
    ) -> PessoaComunidade:
        item = PessoaComunidade(
            tenant_id=tenant_id, comunidade_id=community_id, **payload.model_dump()
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def community_people(
        self, tenant_id: int, community_id: int
    ) -> list[dict[str, Any]]:
        rows = await self.session.execute(
            select(
                Pessoa.id,
                Pessoa.nome_completo,
                Pessoa.data_nascimento,
                PessoaComunidade.papel,
            )
            .join(
                PessoaComunidade,
                (PessoaComunidade.pessoa_id == Pessoa.id)
                & (PessoaComunidade.tenant_id == Pessoa.tenant_id),
            )
            .where(
                Pessoa.tenant_id == tenant_id,
                PessoaComunidade.comunidade_id == community_id,
            )
            .order_by(Pessoa.nome_completo, Pessoa.id)
        )
        return [dict(row) for row in rows.mappings().all()]

    async def remove_community_member(
        self, tenant_id: int, community_id: int, person_id: int
    ) -> bool:
        result = await self.session.execute(
            delete(PessoaComunidade).where(
                PessoaComunidade.tenant_id == tenant_id,
                PessoaComunidade.comunidade_id == community_id,
                PessoaComunidade.pessoa_id == person_id,
            )
        )
        return bool(result.rowcount)

    async def get_tag_by_name(self, tenant_id: int, nome: str) -> Tag | None:
        result: Tag | None = await self.session.scalar(
            select(Tag).where(
                Tag.tenant_id == tenant_id,
                func.lower(Tag.nome) == nome.strip().lower(),
            )
        )
        return result

    async def get_or_create_tag_by_name(
        self,
        tenant_id: int,
        nome: str,
        *,
        categoria: str | None = None,
        descricao: str | None = None,
    ) -> Tag:
        existing = await self.get_tag_by_name(tenant_id, nome)
        if existing is not None:
            return existing
        item = Tag(
            tenant_id=tenant_id,
            nome=nome.strip(),
            categoria=categoria,
            descricao=descricao,
            ativo=True,
            criado_em=datetime.now(UTC),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(item)
                await self.session.flush()
            return item
        except IntegrityError:
            existing = await self.get_tag_by_name(tenant_id, nome)
            if existing is None:
                raise
            return existing

    async def create_tag(self, tenant_id: int, payload: TagInput) -> Tag:
        item = Tag(
            tenant_id=tenant_id,
            **payload.model_dump(),
            ativo=True,
            criado_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self._flush_tag()
        return item

    async def tag(self, tenant_id: int, tag_id: int) -> Tag | None:
        result: Tag | None = await self.session.scalar(
            select(Tag).where(Tag.id == tag_id, Tag.tenant_id == tenant_id)
        )
        return result

    async def list_tags(self, tenant_id: int) -> list[Tag]:
        result = await self.session.scalars(
            select(Tag).where(Tag.tenant_id == tenant_id).order_by(Tag.nome)
        )
        return list(result.all())

    async def update_tag(self, item: Tag, payload: TagUpdate) -> Tag:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self._flush_tag()
        return item

    async def _flush_tag(self) -> None:
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            if "uq_tag_nome" in str(exc.orig).lower():
                raise BusinessRuleError(
                    "Ja existe uma tag com este nome neste tenant.",
                    code="tag_name_already_exists",
                ) from exc
            raise

    async def add_person_tag(self, tenant_id: int, tag_id: int, person_id: int) -> PessoaTag:
        item = PessoaTag(
            tenant_id=tenant_id,
            tag_id=tag_id,
            pessoa_id=person_id,
            atribuido_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def tag_people(self, tenant_id: int, tag_id: int) -> list[Pessoa]:
        result = await self.session.scalars(
            select(Pessoa)
            .join(
                PessoaTag,
                (PessoaTag.pessoa_id == Pessoa.id) & (PessoaTag.tenant_id == Pessoa.tenant_id),
            )
            .where(
                Pessoa.tenant_id == tenant_id,
                PessoaTag.tag_id == tag_id,
            )
            .order_by(Pessoa.nome_completo, Pessoa.id)
        )
        return list(result.all())

    async def remove_person_tag(self, tenant_id: int, tag_id: int, person_id: int) -> bool:
        result = await self.session.execute(
            delete(PessoaTag).where(
                PessoaTag.tenant_id == tenant_id,
                PessoaTag.tag_id == tag_id,
                PessoaTag.pessoa_id == person_id,
            )
        )
        return bool(result.rowcount)

    async def create_validation(
        self, tenant_id: int, person_id: int, payload: ValidacaoInput
    ) -> ValidacaoCadastro:
        item = ValidacaoCadastro(
            tenant_id=tenant_id,
            pessoa_id=person_id,
            **payload.model_dump(),
            status="pendente",
            criado_em=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def validation(self, tenant_id: int, validation_id: int) -> ValidacaoCadastro | None:
        result: ValidacaoCadastro | None = await self.session.scalar(
            select(ValidacaoCadastro).where(
                ValidacaoCadastro.id == validation_id,
                ValidacaoCadastro.tenant_id == tenant_id,
            )
        )
        return result

    async def list_validations(self, tenant_id: int, status: str | None) -> list[ValidacaoCadastro]:
        statement = select(ValidacaoCadastro).where(ValidacaoCadastro.tenant_id == tenant_id)
        if status:
            statement = statement.where(ValidacaoCadastro.status == status)
        result = await self.session.scalars(statement.order_by(ValidacaoCadastro.criado_em.desc()))
        return list(result.all())

    async def validation_person_names(
        self, tenant_id: int, person_ids: set[int]
    ) -> dict[int, str]:
        if not person_ids:
            return {}
        result = await self.session.execute(
            select(Pessoa.id, Pessoa.nome_completo).where(
                Pessoa.tenant_id == tenant_id,
                Pessoa.id.in_(person_ids),
            )
        )
        return {int(person_id): str(name) for person_id, name in result.all()}

    async def list_duplicates(
        self, tenant_id: int, status: str | None, nome: str | None = None
    ) -> list[SuspeitaDuplicidade]:
        active_person = (
            select(Pessoa.id)
            .where(
                Pessoa.id == SuspeitaDuplicidade.pessoa_id,
                Pessoa.tenant_id == tenant_id,
                Pessoa.ativo.is_(True),
                Pessoa.excluido_em.is_(None),
            )
            .exists()
        )
        active_duplicate = (
            select(Pessoa.id)
            .where(
                Pessoa.id == SuspeitaDuplicidade.pessoa_duplicada_id,
                Pessoa.tenant_id == tenant_id,
                Pessoa.ativo.is_(True),
                Pessoa.excluido_em.is_(None),
            )
            .exists()
        )
        statement = select(SuspeitaDuplicidade).where(
            SuspeitaDuplicidade.tenant_id == tenant_id,
            active_person,
            active_duplicate,
        )
        if status:
            statement = statement.where(SuspeitaDuplicidade.status == status)
        name_term = nome.strip() if nome else ""
        if name_term:
            pattern = f"%{name_term}%"
            name_match = or_(
                Pessoa.nome_completo.ilike(pattern),
                Pessoa.nome_social.ilike(pattern),
                Pessoa.apelido.ilike(pattern),
            )
            principal_name = (
                select(Pessoa.id)
                .where(
                    Pessoa.id == SuspeitaDuplicidade.pessoa_id,
                    Pessoa.tenant_id == tenant_id,
                    name_match,
                )
                .exists()
            )
            compared_name = (
                select(Pessoa.id)
                .where(
                    Pessoa.id == SuspeitaDuplicidade.pessoa_duplicada_id,
                    Pessoa.tenant_id == tenant_id,
                    name_match,
                )
                .exists()
            )
            statement = statement.where(or_(principal_name, compared_name))
        result = await self.session.scalars(
            statement.order_by(SuspeitaDuplicidade.criado_em.desc())
        )
        return list(result.all())

    async def duplicate_person_names(
        self, tenant_id: int, person_ids: set[int]
    ) -> dict[int, str]:
        if not person_ids:
            return {}
        result = await self.session.execute(
            select(Pessoa.id, Pessoa.nome_completo).where(
                Pessoa.tenant_id == tenant_id,
                Pessoa.id.in_(person_ids),
            )
        )
        return {int(person_id): str(name) for person_id, name in result.all()}

    async def duplicate_summary(self, tenant_id: int) -> dict[str, int]:
        active_person = (
            select(Pessoa.id)
            .where(
                Pessoa.id == SuspeitaDuplicidade.pessoa_id,
                Pessoa.tenant_id == tenant_id,
                Pessoa.ativo.is_(True),
                Pessoa.excluido_em.is_(None),
            )
            .exists()
        )
        active_duplicate = (
            select(Pessoa.id)
            .where(
                Pessoa.id == SuspeitaDuplicidade.pessoa_duplicada_id,
                Pessoa.tenant_id == tenant_id,
                Pessoa.ativo.is_(True),
                Pessoa.excluido_em.is_(None),
            )
            .exists()
        )
        visible_occurrence = or_(
            SuspeitaDuplicidade.status.in_(("descartada", "mesclada")),
            and_(
                SuspeitaDuplicidade.status.in_(("pendente", "confirmada")),
                active_person,
                active_duplicate,
            ),
        )
        result = await self.session.execute(
            select(SuspeitaDuplicidade.status, func.count(SuspeitaDuplicidade.id))
            .where(
                SuspeitaDuplicidade.tenant_id == tenant_id,
                visible_occurrence,
            )
            .group_by(SuspeitaDuplicidade.status)
        )
        counts = {str(item_status): int(total) for item_status, total in result.all()}
        return {
            "pendentes": counts.get("pendente", 0),
            "confirmadas": counts.get("confirmada", 0),
            "descartadas": counts.get("descartada", 0),
            "mescladas": counts.get("mesclada", 0),
        }

    async def duplicate(self, tenant_id: int, duplicate_id: int) -> SuspeitaDuplicidade | None:
        result: SuspeitaDuplicidade | None = await self.session.scalar(
            select(SuspeitaDuplicidade).where(
                SuspeitaDuplicidade.id == duplicate_id,
                SuspeitaDuplicidade.tenant_id == tenant_id,
            )
        )
        return result

    async def existing_merge_for_source(self, tenant_id: int, person_id: int) -> PessoaMerge | None:
        result: PessoaMerge | None = await self.session.scalar(
            select(PessoaMerge).where(
                PessoaMerge.tenant_id == tenant_id,
                PessoaMerge.pessoa_origem_id == person_id,
            )
        )
        return result

    async def merge_people(
        self,
        *,
        tenant_id: int,
        user_id: int,
        suspicion_id: int,
        principal: Pessoa,
        source: Pessoa,
        source_fields: list[str],
        principal_snapshot: dict[str, Any],
        source_snapshot: dict[str, Any],
    ) -> PessoaMerge:
        now = datetime.now(UTC)
        for field in source_fields:
            setattr(principal, field, getattr(source, field))
        principal.atualizado_por = user_id
        principal.atualizado_em = now
        params = {
            "tenant_id": tenant_id,
            "principal_id": principal.id,
            "source_id": source.id,
        }
        counts: dict[str, int] = {}

        async def execute_count(name: str, sql: str) -> None:
            result = await self.session.execute(text(sql), params)
            counts[name] = int(getattr(result, "rowcount", 0) or 0)

        move_statements = {
            "documentos": """
                UPDATE cadastro.pessoa_documento source
                SET pessoa_id = :principal_id
                WHERE source.tenant_id = :tenant_id
                  AND source.pessoa_id = :source_id
                  AND NOT EXISTS (
                      SELECT 1 FROM cadastro.pessoa_documento target
                      WHERE target.tenant_id = :tenant_id
                        AND target.pessoa_id = :principal_id
                        AND target.tipo_documento = source.tipo_documento
                        AND target.numero = source.numero)
            """,
            "contatos": """
                UPDATE cadastro.pessoa_contato source
                SET pessoa_id = :principal_id
                WHERE source.tenant_id = :tenant_id
                  AND source.pessoa_id = :source_id
                  AND NOT EXISTS (
                      SELECT 1 FROM cadastro.pessoa_contato target
                      WHERE target.tenant_id = :tenant_id
                        AND target.pessoa_id = :principal_id
                        AND target.tipo_contato = source.tipo_contato
                        AND target.valor = source.valor)
            """,
            "redes_sociais": """
                UPDATE cadastro.pessoa_rede_social source
                SET pessoa_id = :principal_id
                WHERE source.tenant_id = :tenant_id
                  AND source.pessoa_id = :source_id
                  AND NOT EXISTS (
                      SELECT 1 FROM cadastro.pessoa_rede_social target
                      WHERE target.tenant_id = :tenant_id
                        AND target.pessoa_id = :principal_id
                        AND target.rede = source.rede
                        AND target.usuario_perfil IS NOT DISTINCT
                            FROM source.usuario_perfil
                        AND target.url IS NOT DISTINCT FROM source.url)
            """,
            "enderecos": """
                UPDATE cadastro.pessoa_endereco source
                SET pessoa_id = :principal_id
                WHERE source.tenant_id = :tenant_id
                  AND source.pessoa_id = :source_id
                  AND NOT EXISTS (
                      SELECT 1 FROM cadastro.pessoa_endereco target
                      WHERE target.pessoa_id = :principal_id
                        AND target.endereco_id = source.endereco_id
                        AND target.tipo = source.tipo)
            """,
        }
        for name, statement in move_statements.items():
            await execute_count(name, statement)

        copy_statements = {
            "tipos": """
                INSERT INTO cadastro.pessoa_pessoa_tipo
                    (pessoa_id, pessoa_tipo_id, tenant_id, criado_em)
                SELECT :principal_id, pessoa_tipo_id, :tenant_id, criado_em
                FROM cadastro.pessoa_pessoa_tipo
                WHERE tenant_id = :tenant_id AND pessoa_id = :source_id
                ON CONFLICT (pessoa_id, pessoa_tipo_id) DO NOTHING
            """,
            "tags": """
                INSERT INTO cadastro.pessoa_tag
                    (pessoa_id, tag_id, tenant_id, atribuido_em)
                SELECT :principal_id, tag_id, :tenant_id, atribuido_em
                FROM cadastro.pessoa_tag
                WHERE tenant_id = :tenant_id AND pessoa_id = :source_id
                ON CONFLICT (pessoa_id, tag_id) DO NOTHING
            """,
            "comunidades": """
                INSERT INTO cadastro.pessoa_comunidade
                    (pessoa_id, comunidade_id, tenant_id, papel, desde)
                SELECT :principal_id, comunidade_id, :tenant_id, papel, desde
                FROM cadastro.pessoa_comunidade
                WHERE tenant_id = :tenant_id AND pessoa_id = :source_id
                ON CONFLICT (pessoa_id, comunidade_id) DO NOTHING
            """,
            "nucleos_familiares": """
                INSERT INTO cadastro.pessoa_nucleo_familiar
                    (tenant_id, pessoa_id, nucleo_familiar_id,
                     parentesco, responsavel, observacao)
                SELECT :tenant_id, :principal_id, nucleo_familiar_id,
                       parentesco, responsavel, observacao
                FROM cadastro.pessoa_nucleo_familiar
                WHERE tenant_id = :tenant_id AND pessoa_id = :source_id
                ON CONFLICT (pessoa_id, nucleo_familiar_id) DO NOTHING
            """,
            "territorios": """
                INSERT INTO territorio.pessoa_territorio
                    (tenant_id, pessoa_id, territorio_id, vinculo)
                SELECT :tenant_id, :principal_id, territorio_id, vinculo
                FROM territorio.pessoa_territorio
                WHERE tenant_id = :tenant_id AND pessoa_id = :source_id
                ON CONFLICT (pessoa_id, territorio_id, vinculo) DO NOTHING
            """,
        }
        for name, statement in copy_statements.items():
            await execute_count(name, statement)

        principal_voter = await self.session.scalar(
            select(Eleitor).where(Eleitor.tenant_id == tenant_id, Eleitor.pessoa_id == principal.id)
        )
        source_voter = await self.session.scalar(
            select(Eleitor).where(Eleitor.tenant_id == tenant_id, Eleitor.pessoa_id == source.id)
        )
        if source_voter is not None:
            if principal_voter is None:
                source_voter.pessoa_id = principal.id
                counts["eleitor"] = 1
            else:
                source_title_transferred = (
                    principal_voter.titulo_eleitor is None
                    and source_voter.titulo_eleitor is not None
                )
                for field in (
                    "titulo_eleitor",
                    "zona_eleitoral_id",
                    "secao_eleitoral_id",
                    "local_votacao_id",
                    "codigo_municipio_ibge",
                ):
                    if getattr(principal_voter, field) is None:
                        setattr(principal_voter, field, getattr(source_voter, field))
                if source_title_transferred:
                    # O titulo e unico no tenant; o valor original permanece no snapshot.
                    source_voter.titulo_eleitor = None
                principal_voter.atualizado_em = now
                counts["eleitor"] = 0

        principal_leadership = await self.session.scalar(
            select(Lideranca).where(
                Lideranca.tenant_id == tenant_id, Lideranca.pessoa_id == principal.id
            )
        )
        source_leadership = await self.session.scalar(
            select(Lideranca).where(
                Lideranca.tenant_id == tenant_id, Lideranca.pessoa_id == source.id
            )
        )
        if source_leadership is not None:
            if principal_leadership is None:
                source_leadership.pessoa_id = principal.id
                counts["lideranca"] = 1
            else:
                source_leadership.ativo = False
                counts["lideranca"] = 0

        principal_political = await self.session.scalar(
            select(PessoaComplementoPolitico).where(
                PessoaComplementoPolitico.tenant_id == tenant_id,
                PessoaComplementoPolitico.pessoa_id == principal.id,
            )
        )
        source_political = await self.session.scalar(
            select(PessoaComplementoPolitico).where(
                PessoaComplementoPolitico.tenant_id == tenant_id,
                PessoaComplementoPolitico.pessoa_id == source.id,
            )
        )
        if source_political is not None:
            if principal_political is None:
                source_political.pessoa_id = principal.id
                counts["complemento_politico"] = 1
            else:
                for field in (
                    "vinculo_politico",
                    "partido_id",
                    "cargo_funcao",
                    "nivel_engajamento",
                    "observacoes",
                ):
                    if getattr(principal_political, field) is None:
                        setattr(principal_political, field, getattr(source_political, field))
                principal_political.temas_interesse = list(
                    dict.fromkeys(
                        principal_political.temas_interesse + source_political.temas_interesse
                    )
                )
                principal_political.atualizado_em = now
                counts["complemento_politico"] = 0

        reference_statements = {
            "hierarquia": """
                UPDATE cadastro.hierarquia_lideranca source
                SET pessoa_subordinada_id = :principal_id
                WHERE source.tenant_id = :tenant_id
                  AND source.pessoa_subordinada_id = :source_id
                  AND NOT EXISTS (
                      SELECT 1 FROM cadastro.hierarquia_lideranca target
                      WHERE target.lideranca_superior_id =
                            source.lideranca_superior_id
                        AND target.pessoa_subordinada_id = :principal_id
                        AND target.data_inicio = source.data_inicio)
            """,
            "indicacoes_recebidas": """
                UPDATE cadastro.indicacao SET pessoa_indicada_id = :principal_id
                WHERE tenant_id = :tenant_id AND pessoa_indicada_id = :source_id
            """,
            "indicacoes_realizadas": """
                UPDATE cadastro.indicacao
                SET pessoa_indicante_id = CASE
                    WHEN pessoa_indicada_id = :principal_id THEN NULL
                    ELSE :principal_id END
                WHERE tenant_id = :tenant_id AND pessoa_indicante_id = :source_id
            """,
            "relacionamentos_origem": """
                UPDATE cadastro.relacionamento_pessoa
                SET pessoa_origem_id = :principal_id
                WHERE tenant_id = :tenant_id
                  AND pessoa_origem_id = :source_id
                  AND pessoa_destino_id <> :principal_id
            """,
            "relacionamentos_destino": """
                UPDATE cadastro.relacionamento_pessoa
                SET pessoa_destino_id = :principal_id
                WHERE tenant_id = :tenant_id
                  AND pessoa_destino_id = :source_id
                  AND pessoa_origem_id <> :principal_id
            """,
            "nucleos_referencia": """
                UPDATE cadastro.nucleo_familiar
                SET pessoa_referencia_id = :principal_id
                WHERE tenant_id = :tenant_id
                  AND pessoa_referencia_id = :source_id
            """,
        }
        for name, statement in reference_statements.items():
            await execute_count(name, statement)

        await self.session.execute(
            text(
                """
                UPDATE cadastro.suspeita_duplicidade
                SET status = 'mesclada',
                    resolvido_por = :user_id,
                    resolvido_em = :now
                WHERE tenant_id = :tenant_id
                  AND status IN ('pendente', 'confirmada')
                  AND (
                      pessoa_id IN (:principal_id, :source_id)
                      OR pessoa_duplicada_id IN (:principal_id, :source_id)
                  )
                """
            ),
            {**params, "user_id": user_id, "now": now},
        )

        source.ativo = False
        source.excluido_em = now
        source.atualizado_por = user_id
        source.atualizado_em = now
        marker = f"Cadastro mesclado na pessoa #{principal.id} em {now.isoformat()}."
        source.observacoes = f"{source.observacoes}\n{marker}" if source.observacoes else marker
        merge = PessoaMerge(
            tenant_id=tenant_id,
            pessoa_principal_id=principal.id,
            pessoa_origem_id=source.id,
            suspeita_duplicidade_id=suspicion_id,
            campos_origem=source_fields,
            snapshot_principal=principal_snapshot,
            snapshot_origem=source_snapshot,
            resumo_operacao=counts,
            executado_por=user_id,
            executado_em=now,
        )
        self.session.add(merge)
        await self.session.flush()
        return merge

    async def create_duplicate_suspicions(
        self, tenant_id: int, person: Pessoa, payload: PessoaCadastroCreate
    ) -> list[SuspeitaDuplicidade]:
        candidates: dict[tuple[int, str], Decimal] = {}
        for contact in payload.contatos:
            if contact.tipo_contato not in {"telefone", "celular", "whatsapp", "email"}:
                continue
            result = await self.session.scalars(
                select(PessoaContato.pessoa_id).where(
                    PessoaContato.tenant_id == tenant_id,
                    PessoaContato.valor == contact.valor,
                    PessoaContato.pessoa_id != person.id,
                )
            )
            criterion = "email" if contact.tipo_contato == "email" else "telefone"
            for candidate_id in result:
                candidates[(int(candidate_id), criterion)] = Decimal("100")
        if person.data_nascimento is not None:
            result = await self.session.scalars(
                select(Pessoa.id).where(
                    Pessoa.tenant_id == tenant_id,
                    Pessoa.id != person.id,
                    func.lower(Pessoa.nome_completo) == person.nome_completo.lower(),
                    Pessoa.data_nascimento == person.data_nascimento,
                    Pessoa.excluido_em.is_(None),
                )
            )
            for candidate_id in result:
                candidates[(int(candidate_id), "nome_data_nascimento")] = Decimal("100")
        now = datetime.now(UTC)
        items: list[SuspeitaDuplicidade] = []
        for (candidate_id, criterion), score in candidates.items():
            existing = await self.session.scalar(
                select(SuspeitaDuplicidade.id).where(
                    SuspeitaDuplicidade.tenant_id == tenant_id,
                    SuspeitaDuplicidade.criterio == criterion,
                    SuspeitaDuplicidade.status == "pendente",
                    or_(
                        (SuspeitaDuplicidade.pessoa_id == person.id)
                        & (SuspeitaDuplicidade.pessoa_duplicada_id == candidate_id),
                        (SuspeitaDuplicidade.pessoa_id == candidate_id)
                        & (SuspeitaDuplicidade.pessoa_duplicada_id == person.id),
                    ),
                )
            )
            if existing is None:
                items.append(
                    SuspeitaDuplicidade(
                        tenant_id=tenant_id,
                        pessoa_id=person.id,
                        pessoa_duplicada_id=candidate_id,
                        criterio=criterion,
                        score_similaridade=score,
                        status="pendente",
                        criado_em=now,
                    )
                )
        self.session.add_all(items)
        await self.session.flush()
        return items

    async def quick_search(
        self,
        tenant_id: int,
        query: str,
        limit: int,
        accessible_territory_ids: set[int] | None = None,
    ) -> list[Pessoa]:
        term = f"%{query}%"
        statement = select(Pessoa).where(
            Pessoa.tenant_id == tenant_id,
            Pessoa.ativo.is_(True),
            Pessoa.excluido_em.is_(None),
            or_(
                Pessoa.nome_completo.ilike(term),
                Pessoa.documentos.any(PessoaDocumento.numero.ilike(term)),
                Pessoa.contatos.any(PessoaContato.valor.ilike(term)),
            ),
        )
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if accessible_territory_ids is not None:
            if not accessible_territory_ids:
                return []
            statement = statement.where(
                text(
                    "EXISTS (SELECT 1 FROM territorio.pessoa_territorio access_pt "
                    "WHERE access_pt.pessoa_id = cadastro.pessoa.id "
                    "AND access_pt.tenant_id = :tenant_id "
                    "AND access_pt.territorio_id = ANY(:accessible_territory_ids))"
                )
            )
            values["accessible_territory_ids"] = sorted(accessible_territory_ids)
        result = await self.session.scalars(
            statement.order_by(Pessoa.nome_completo).limit(limit),
            values,
        )
        return list(result.unique().all())

    async def indication_graph(
        self,
        tenant_id: int,
        *,
        person_id: int | None,
        origin: str | None,
        date_from: date | None,
        date_to: date | None,
        depth: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], list[Pessoa], bool]:
        filters = [
            "i.tenant_id = :tenant_id",
            "(CAST(:origin AS varchar) IS NULL OR i.origem = CAST(:origin AS varchar))",
            "(CAST(:date_from AS date) IS NULL OR i.data_indicacao >= CAST(:date_from AS date))",
            "(CAST(:date_to AS date) IS NULL OR i.data_indicacao <= CAST(:date_to AS date))",
        ]
        filter_sql = " AND ".join(filters)
        params = {
            "tenant_id": tenant_id,
            "person_id": person_id,
            "origin": origin,
            "date_from": date_from,
            "date_to": date_to,
            "depth": depth,
            "limit": limit + 1,
        }
        if person_id is None:
            statement = text(
                f"""
                SELECT i.id, i.pessoa_indicante_id, i.pessoa_indicada_id,
                       i.origem, i.contexto, i.data_indicacao
                FROM cadastro.indicacao i
                WHERE {filter_sql}
                  AND i.pessoa_indicante_id IS NOT NULL
                ORDER BY i.data_indicacao DESC, i.id DESC
                LIMIT :limit
                """
            )
        else:
            recursive_filters = filter_sql.replace("i.", "child.")
            statement = text(
                f"""
                WITH RECURSIVE rede AS (
                    SELECT i.id, i.pessoa_indicante_id, i.pessoa_indicada_id,
                           i.origem, i.contexto, i.data_indicacao, 1 AS nivel
                    FROM cadastro.indicacao i
                    WHERE {filter_sql}
                      AND i.pessoa_indicante_id IS NOT NULL
                      AND (:person_id IN (
                          i.pessoa_indicante_id, i.pessoa_indicada_id
                      ))
                    UNION
                    SELECT child.id, child.pessoa_indicante_id,
                           child.pessoa_indicada_id, child.origem,
                           child.contexto, child.data_indicacao, rede.nivel + 1
                    FROM cadastro.indicacao child
                    JOIN rede
                      ON child.pessoa_indicante_id = rede.pessoa_indicada_id
                    WHERE {recursive_filters}
                      AND child.pessoa_indicante_id IS NOT NULL
                      AND rede.nivel < :depth
                )
                SELECT DISTINCT id, pessoa_indicante_id, pessoa_indicada_id,
                       origem, contexto, data_indicacao
                FROM rede
                ORDER BY data_indicacao DESC, id DESC
                LIMIT :limit
                """
            )
        rows = (await self.session.execute(statement, params)).mappings().all()
        truncated = len(rows) > limit
        selected = rows[:limit]
        edges = [dict(row) for row in selected]
        person_ids = {
            int(value)
            for row in selected
            for value in (row["pessoa_indicante_id"], row["pessoa_indicada_id"])
            if value is not None
        }
        people_result = await self.session.scalars(
            select(Pessoa).where(
                Pessoa.tenant_id == tenant_id,
                Pessoa.id.in_(person_ids),
            )
        )
        return edges, list(people_result.all()), truncated

    async def audit(
        self,
        *,
        tenant_id: int,
        user_id: int,
        action: str,
        table_name: str,
        record_id: int,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await AuditService(self.session).record(
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            schema_name="cadastro",
            table_name=table_name,
            record_id=record_id,
            before=before,
            after=after,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            message = str(exc.orig).lower()
            if "uq_pessoa_documento" in message:
                raise BusinessRuleError(
                    "Documento ja cadastrado neste tenant.",
                    code="document_already_exists",
                ) from exc
            if "uq_eleitor_titulo_tenant" in message:
                raise BusinessRuleError(
                    "Titulo eleitoral ja cadastrado neste tenant.",
                    code="voter_title_already_exists",
                ) from exc
            if "uq_indicacao_pessoa_indicada_tenant" in message:
                raise BusinessRuleError(
                    "Esta pessoa ja foi indicada.",
                    code="person_already_indicated",
                ) from exc
            if "uq_hierarquia_pessoa_ativa_tenant" in message:
                raise BusinessRuleError(
                    "Esta pessoa ja possui uma lideranca ativa.",
                    code="person_already_has_active_leadership",
                ) from exc
            if "uq_tag_nome" in message:
                raise BusinessRuleError(
                    "Ja existe uma tag com este nome neste tenant.",
                    code="tag_name_already_exists",
                ) from exc
            raise BusinessRuleError(
                "Registro duplicado ou referencia invalida.",
                code="cadastro_integrity_error",
            ) from exc

    async def rollback(self) -> None:
        await self.session.rollback()


def person_snapshot(person: Pessoa) -> dict[str, Any]:
    return {
        "id": person.id,
        "nome_completo": person.nome_completo,
        "nome_social": person.nome_social,
        "data_nascimento": person.data_nascimento.isoformat() if person.data_nascimento else None,
        "ativo": person.ativo,
    }
