"""Regras de negocio do dominio de cadastro."""

from datetime import UTC, date, datetime
from typing import Any

from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.core.pagination import ListParams, Page
from app.mod_cadastro.mobile import MobileLeaderContext
from app.mod_cadastro.repository import CadastroRepository, person_snapshot
from app.mod_territorio.repository import TerritorioRepository
from app.schemas.cadastro import (
    EleitorCreate,
    EleitorResponse,
    LiderancaCreate,
    LiderancaResponse,
    PessoaContatoCreate,
    PessoaContatoResponse,
    PessoaContatoUpdate,
    PessoaDocumentoCreate,
    PessoaDocumentoResponse,
    PessoaDocumentoUpdate,
    PessoaEnderecoCreate,
    PessoaEnderecoResponse,
    PessoaEnderecoUpdate,
    PessoaResponse,
    PessoaUpdate,
)
from app.schemas.cadastro_operacional import (
    BuscaRapidaItem,
    ComplementoPoliticoInput,
    ComplementoPoliticoResponse,
    ComunidadeInput,
    ComunidadePessoaResponse,
    ComunidadeResponse,
    DuplicidadeResumoResponse,
    EstadoCivilResponse,
    HierarquiaInput,
    HierarquiaResponse,
    HierarquiaResumo,
    HierarquiaRoleInput,
    HierarquiaStatusInput,
    IndicacaoGraphEdge,
    IndicacaoGraphNode,
    IndicacaoGraphResponse,
    IndicacaoInput,
    IndicacaoPessoaInput,
    IndicacaoResponse,
    LiderancaOperacionalResponse,
    MergePessoaCampo,
    NucleoFamiliarInput,
    NucleoFamiliarResponse,
    NucleoPessoaResponse,
    PapelComunidadeResponse,
    ParentescoResponse,
    PessoaCadastroCreate,
    PessoaDetalheResponse,
    PessoaFiltros,
    PessoaListItem,
    PessoaMergeConflict,
    PessoaMergePreview,
    PessoaMergeRequest,
    PessoaMergeResponse,
    PessoaRedeSocialInput,
    PessoaRedeSocialResponse,
    PessoaTipoResponse,
    RelacionamentoInput,
    RelacionamentoResponse,
    ReligiaoResponse,
    SuspeitaDuplicidadeResolve,
    SuspeitaDuplicidadeResponse,
    TagInput,
    TagPessoaResponse,
    TagResponse,
    TagUpdate,
    ValidacaoInput,
    ValidacaoResolve,
    ValidacaoResponse,
    VinculoComunidadeInput,
    VinculoNucleoInput,
    VinculoNucleoResponse,
    VinculoResumo,
)


SITE_ORIGIN_TAG_NAME = "origem-site"
SITE_ORIGIN_NOTE = "Cadastro originado pelo site."


class CadastroService:
    def __init__(self, repository: CadastroRepository) -> None:
        self.repository = repository

    async def list_people(
        self,
        actor: RequestActor,
        params: ListParams,
        filters: PessoaFiltros,
        territorial_access: TerritorialAccess | None = None,
    ) -> Page[PessoaListItem]:
        filters = self._scope_mobile_leader_filters(actor, filters)
        accessible_ids = None
        if territorial_access is not None and not self._is_scoped_mobile_leader(actor):
            accessible_ids = await TerritorioRepository(
                self.repository.session
            ).accessible_ids(actor.tenant_id, territorial_access)
        people, total = await self.repository.list_people(
            actor.tenant_id, params, filters, accessible_ids
        )
        items: list[PessoaListItem] = []
        for person in people:
            extensions = await self.repository.get_person_extensions(actor.tenant_id, person.id)
            cpf = next(
                (item.numero for item in person.documentos if item.tipo_documento == "cpf"),
                None,
            )
            phone = next(
                (
                    item.valor
                    for item in person.contatos
                    if item.principal and item.tipo_contato in {"telefone", "celular", "whatsapp"}
                ),
                None,
            )
            items.append(
                PessoaListItem(
                    id=person.id,
                    nome_completo=person.nome_completo,
                    nome_social=person.nome_social,
                    apelido=person.apelido,
                    data_nascimento=person.data_nascimento,
                    ativo=person.ativo,
                    cpf=cpf,
                    telefone=phone,
                    tipos=[item.codigo for item in extensions["tipos"]],
                    lideranca_id=(
                        extensions["hierarquia"][0].lideranca_superior_id
                        if extensions["hierarquia"]
                        else (person.lideranca.id if person.lideranca else None)
                    ),
                )
            )
        return Page[PessoaListItem].create(items, total, params)

    async def ensure_person_territorial_access(
        self,
        actor: RequestActor,
        person_id: int,
        territorial_access: TerritorialAccess,
    ) -> None:
        if self._is_scoped_mobile_leader(actor):
            person = await self.repository.get_person(actor.tenant_id, person_id)
            if person is None:
                raise ResourceNotFoundError("Pessoa", person_id)
            if person.cadastrado_por_lideranca_id == actor.lideranca_id:
                return
        ids = await TerritorioRepository(self.repository.session).accessible_ids(
            actor.tenant_id, territorial_access
        )
        if ids is not None and not await self.repository.person_in_territories(
            actor.tenant_id, person_id, ids
        ):
            raise AuthorizationError("Pessoa fora do escopo territorial permitido.")

    async def get_person(self, actor: RequestActor, person_id: int) -> PessoaDetalheResponse:
        person = await self.repository.get_person(actor.tenant_id, person_id)
        if person is None:
            raise ResourceNotFoundError("Pessoa", person_id)
        extensions = await self.repository.get_person_extensions(actor.tenant_id, person_id)
        hierarchy_names = await self.repository.hierarchy_names(
            actor.tenant_id,
            [item.id for item in extensions["hierarquia"]],
        )
        data = PessoaResponse.model_validate(person).model_dump()
        data.update(
            {
                "redes_sociais": [
                    PessoaRedeSocialResponse.model_validate(item)
                    for item in extensions["redes_sociais"]
                ],
                "tipos": [PessoaTipoResponse.model_validate(item) for item in extensions["tipos"]],
                "indicacoes": [
                    IndicacaoResponse.model_validate(item) for item in extensions["indicacoes"]
                ],
                "complemento_politico": (
                    ComplementoPoliticoResponse.model_validate(extensions["complemento_politico"])
                    if extensions["complemento_politico"]
                    else None
                ),
                "tags": [VinculoResumo(id=item.id, nome=item.nome) for item in extensions["tags"]],
                "comunidades": [
                    VinculoResumo(id=item.id, nome=item.nome) for item in extensions["comunidades"]
                ],
                "nucleos_familiares": [
                    VinculoResumo(
                        id=item.id,
                        nome=item.nome or f"Nucleo {item.id}",
                    )
                    for item in extensions["nucleos_familiares"]
                ],
                "hierarquia": [
                    HierarquiaResumo.model_validate(item).model_copy(
                        update=hierarchy_names.get(item.id, {})
                    )
                    for item in extensions["hierarquia"]
                ],
            }
        )
        return PessoaDetalheResponse.model_validate(data)

    async def create_person(
        self,
        actor: RequestActor,
        payload: PessoaCadastroCreate,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PessoaDetalheResponse:
        cpf = next(
            (item.numero for item in payload.documentos if item.tipo_documento == "cpf"),
            None,
        )
        title = payload.eleitor.titulo_eleitor if payload.eleitor else None
        duplicate = await self.repository.strong_duplicate(actor.tenant_id, cpf=cpf, titulo=title)
        if duplicate:
            criterion, person_id = duplicate
            raise BusinessRuleError(
                "Duplicidade forte detectada; cadastro bloqueado.",
                code="strong_duplicate",
                details={"criterio": criterion, "pessoa_id": person_id},
            )
        await self._validate_references(actor.tenant_id, payload)
        payload, mobile = await self._prepare_mobile_create(actor, payload)
        payload, origem_cadastro, fonte_dado_id = await self._prepare_integration_create(
            actor, payload
        )
        site_tag = None
        if actor.is_integration_session:
            site_tag = await self.repository.get_or_create_tag_by_name(
                actor.tenant_id,
                SITE_ORIGIN_TAG_NAME,
                categoria="origem",
                descricao="Cadastros recebidos pelo site de integracao.",
            )
        person = await self.repository.create_person(
            actor.tenant_id,
            actor.user_id,
            payload,
            mobile=mobile,
            origem_cadastro=origem_cadastro,
            fonte_dado_id=fonte_dado_id,
        )
        if site_tag is not None:
            await self.repository.add_person_tag(actor.tenant_id, site_tag.id, person.id)
        await self.repository.create_duplicate_suspicions(actor.tenant_id, person, payload)
        if not self._has_assigned_leader(payload, actor):
            await self.repository.create_validation(
                actor.tenant_id,
                person.id,
                ValidacaoInput(
                    motivo="sem_lider",
                    observacao="Cadastro criado sem lider responsavel.",
                ),
            )
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="criar",
            table_name="pessoa",
            record_id=person.id,
            before=None,
            after=person_snapshot(person),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return await self.get_person(actor, person.id)

    async def update_person(
        self,
        actor: RequestActor,
        person_id: int,
        payload: PessoaUpdate,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PessoaDetalheResponse:
        person = await self._person(actor.tenant_id, person_id)
        if payload.estado_civil is not None and not await self.repository.marital_status_exists(
            payload.estado_civil
        ):
            raise ResourceNotFoundError("Estado civil", payload.estado_civil)
        before = person_snapshot(person)
        await self.repository.update_person(person, payload, actor.user_id)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="editar",
            table_name="pessoa",
            record_id=person.id,
            before=before,
            after=person_snapshot(person),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return await self.get_person(actor, person.id)

    async def calculate_registration_completeness(
        self, actor: RequestActor, person_id: int
    ) -> PessoaDetalheResponse:
        person = await self._person(actor.tenant_id, person_id)
        before = person_snapshot(person)
        completeness = await self.repository.calculate_registration_completeness(
            actor.tenant_id, person_id, actor.user_id
        )
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="editar",
            table_name="pessoa",
            record_id=person_id,
            before=before,
            after={"completude_cadastral": str(completeness)},
        )
        await self.repository.commit()
        return await self.get_person(actor, person_id)

    async def deactivate_person(
        self,
        actor: RequestActor,
        person_id: int,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        person = await self._person(actor.tenant_id, person_id)
        before = person_snapshot(person)
        await self.repository.deactivate_person(person, actor.user_id)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="excluir",
            table_name="pessoa",
            record_id=person.id,
            before=before,
            after=person_snapshot(person),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()

    async def add_document(
        self, actor: RequestActor, person_id: int, payload: PessoaDocumentoCreate
    ) -> PessoaDocumentoResponse:
        await self._person(actor.tenant_id, person_id)
        if payload.tipo_documento == "cpf":
            duplicate = await self.repository.strong_duplicate(
                actor.tenant_id, cpf=payload.numero, titulo=None
            )
            if duplicate:
                raise BusinessRuleError(
                    "CPF ja cadastrado neste tenant.", code="cpf_already_exists"
                )
        item = await self.repository.add_document(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "pessoa_documento", item.id)
        return PessoaDocumentoResponse.model_validate(item)

    async def update_document(
        self,
        actor: RequestActor,
        person_id: int,
        document_id: int,
        payload: PessoaDocumentoUpdate,
    ) -> PessoaDocumentoResponse:
        item = await self.repository.document(actor.tenant_id, person_id, document_id)
        if item is None:
            raise ResourceNotFoundError("Documento", document_id)
        merged = PessoaDocumentoCreate(
            tipo_documento=item.tipo_documento,
            numero=payload.numero if payload.numero is not None else item.numero,
            orgao_emissor=(
                payload.orgao_emissor
                if "orgao_emissor" in payload.model_fields_set
                else item.orgao_emissor
            ),
            uf_emissor=(
                payload.uf_emissor if "uf_emissor" in payload.model_fields_set else item.uf_emissor
            ),
            data_emissao=(
                payload.data_emissao
                if "data_emissao" in payload.model_fields_set
                else item.data_emissao
            ),
        )
        item = await self.repository.update_document(
            item,
            PessoaDocumentoUpdate(**merged.model_dump(exclude={"tipo_documento"})),
        )
        await self._audit_updated(actor, "pessoa_documento", item.id)
        return PessoaDocumentoResponse.model_validate(item)

    async def add_contact(
        self, actor: RequestActor, person_id: int, payload: PessoaContatoCreate
    ) -> PessoaContatoResponse:
        person = await self._person(actor.tenant_id, person_id)
        item = await self.repository.add_contact(actor.tenant_id, person_id, payload)
        await self.repository.create_duplicate_suspicions(
            actor.tenant_id,
            person,
            PessoaCadastroCreate(
                nome_completo=person.nome_completo,
                data_nascimento=person.data_nascimento,
                contatos=[payload],
            ),
        )
        await self._audit_created(actor, "pessoa_contato", item.id)
        return PessoaContatoResponse.model_validate(item)

    async def update_contact(
        self,
        actor: RequestActor,
        person_id: int,
        contact_id: int,
        payload: PessoaContatoUpdate,
    ) -> PessoaContatoResponse:
        item = await self.repository.contact(actor.tenant_id, person_id, contact_id)
        if item is None:
            raise ResourceNotFoundError("Contato", contact_id)
        if payload.valor is not None:
            normalized = PessoaContatoCreate(
                tipo_contato=item.tipo_contato,
                valor=payload.valor,
                principal=payload.principal if payload.principal is not None else item.principal,
                verificado=payload.verificado
                if payload.verificado is not None
                else item.verificado,
                observacao=payload.observacao
                if "observacao" in payload.model_fields_set
                else item.observacao,
            )
            payload.valor = normalized.valor
        item = await self.repository.update_contact(actor.tenant_id, item, payload)
        await self._audit_updated(actor, "pessoa_contato", item.id)
        return PessoaContatoResponse.model_validate(item)

    async def delete_contact(
        self,
        actor: RequestActor,
        person_id: int,
        contact_id: int,
    ) -> None:
        await self._ensure_can_remove_contact(actor, person_id)
        item = await self.repository.contact(actor.tenant_id, person_id, contact_id)
        if item is None:
            raise ResourceNotFoundError("Contato", contact_id)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="excluir",
            table_name="pessoa_contato",
            record_id=item.id,
            before={
                "id": item.id,
                "pessoa_id": item.pessoa_id,
                "tipo_contato": item.tipo_contato,
                "valor": item.valor,
                "principal": item.principal,
            },
            after=None,
        )
        await self.repository.delete_contact(item)
        await self.repository.commit()

    async def _ensure_can_remove_contact(self, actor: RequestActor, person_id: int) -> None:
        profiles = set(actor.profiles)
        if {"gestor", "gestor_saas"} & profiles:
            return
        if "coordenador_territorial" in profiles:
            if actor.lideranca_id is None or not await self.repository.person_linked_to_leadership(
                actor.tenant_id, person_id, actor.lideranca_id
            ):
                raise AuthorizationError(
                    "Apenas contatos de pessoas vinculadas ao coordenador podem ser removidos."
                )
            return
        raise AuthorizationError(
            "Apenas gestores e coordenadores territoriais vinculados podem remover contatos."
        )

    async def add_address(
        self, actor: RequestActor, person_id: int, payload: PessoaEnderecoCreate
    ) -> PessoaEnderecoResponse:
        await self._person(actor.tenant_id, person_id)
        item = await self.repository.add_address(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "pessoa_endereco", item.id)
        return PessoaEnderecoResponse.model_validate(item)

    async def update_address(
        self,
        actor: RequestActor,
        person_id: int,
        address_id: int,
        payload: PessoaEnderecoUpdate,
    ) -> PessoaEnderecoResponse:
        item = await self.repository.address_link(actor.tenant_id, person_id, address_id)
        if item is None:
            raise ResourceNotFoundError("Endereco da pessoa", address_id)
        item = await self.repository.update_address(actor.tenant_id, item, payload)
        await self._audit_updated(actor, "pessoa_endereco", item.id)
        return PessoaEnderecoResponse.model_validate(item)

    async def add_social(
        self, actor: RequestActor, person_id: int, payload: PessoaRedeSocialInput
    ) -> PessoaRedeSocialResponse:
        await self._person(actor.tenant_id, person_id)
        item = await self.repository.add_social(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "pessoa_rede_social", item.id)
        return PessoaRedeSocialResponse.model_validate(item)

    async def update_social(
        self,
        actor: RequestActor,
        person_id: int,
        social_id: int,
        payload: PessoaRedeSocialInput,
    ) -> PessoaRedeSocialResponse:
        item = await self.repository.social(actor.tenant_id, person_id, social_id)
        if item is None:
            raise ResourceNotFoundError("Rede social", social_id)
        item = await self.repository.update_social(item, payload)
        await self._audit_updated(actor, "pessoa_rede_social", item.id)
        return PessoaRedeSocialResponse.model_validate(item)

    async def set_voter(
        self, actor: RequestActor, person_id: int, payload: EleitorCreate
    ) -> EleitorResponse:
        await self._person(actor.tenant_id, person_id)
        duplicate = await self.repository.strong_duplicate(
            actor.tenant_id,
            cpf=None,
            titulo=payload.titulo_eleitor,
            exclude_person_id=person_id,
        )
        if duplicate:
            raise BusinessRuleError(
                "Titulo eleitoral ja cadastrado neste tenant.",
                code="voter_title_already_exists",
            )
        item = await self.repository.upsert_voter(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "eleitor", item.id)
        return EleitorResponse.model_validate(item)

    async def list_types(self) -> list[PessoaTipoResponse]:
        return [
            PessoaTipoResponse.model_validate(item)
            for item in await self.repository.list_person_types()
        ]

    async def list_marital_statuses(self) -> list[EstadoCivilResponse]:
        return [
            EstadoCivilResponse.model_validate(item)
            for item in await self.repository.list_marital_statuses()
        ]

    async def list_religions(self) -> list[ReligiaoResponse]:
        return [
            ReligiaoResponse(**item)
            for item in await self.repository.list_religions()
        ]

    async def list_leaderships(
        self,
        actor: RequestActor,
        query: str | None = None,
        coordinator_id: int | None = None,
        territory_id: int | None = None,
        leadership_type: str | None = None,
    ) -> list[LiderancaOperacionalResponse]:
        items = await self.repository.list_leaderships(
            actor.tenant_id, query, coordinator_id, territory_id, leadership_type
        )
        territories = await self.repository.leadership_territories(
            actor.tenant_id, [item.id for item in items]
        )
        tags = await self.repository.leadership_person_tags(
            actor.tenant_id, [item.id for item in items]
        )
        return [
            LiderancaOperacionalResponse(
                **LiderancaResponse.model_validate(item).model_dump(),
                pessoa_nome_completo=item.pessoa.nome_completo,
                coordenador_nome_completo=(
                    item.coordenador.pessoa.nome_completo if item.coordenador else None
                ),
                territorio_ids=[territory["id"] for territory in territories.get(item.id, [])],
                territorios=territories.get(item.id, []),
                tags=tags.get(item.id, []),
            )
            for item in items
        ]

    async def list_hierarchy(
        self,
        actor: RequestActor,
        person_query: str | None = None,
        superior_id: int | None = None,
        role: str | None = None,
    ) -> list[HierarquiaResponse]:
        items = await self.repository.list_hierarchy(
            actor.tenant_id, person_query, superior_id, role
        )
        names = await self.repository.hierarchy_names(
            actor.tenant_id, [item.id for item in items]
        )
        return [
            HierarquiaResponse.model_validate(item).model_copy(
                update=names.get(item.id, {})
            )
            for item in items
        ]

    async def replace_types(
        self, actor: RequestActor, person_id: int, type_ids: list[int]
    ) -> list[PessoaTipoResponse]:
        await self._person(actor.tenant_id, person_id)
        await self.repository.replace_person_types(actor.tenant_id, person_id, type_ids)
        await self.repository.commit()
        extensions = await self.repository.get_person_extensions(actor.tenant_id, person_id)
        return [PessoaTipoResponse.model_validate(item) for item in extensions["tipos"]]

    async def set_leadership(
        self, actor: RequestActor, person_id: int, payload: LiderancaCreate
    ) -> LiderancaResponse:
        await self._person(actor.tenant_id, person_id)
        if payload.coordenador_id is not None:
            coordinator = await self.repository.leadership(actor.tenant_id, payload.coordenador_id)
            if coordinator is None or coordinator.pessoa_id == person_id:
                raise BusinessRuleError("Coordenador invalido.", code="invalid_coordinator")
        item = await self.repository.upsert_leadership(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "lideranca", item.id)
        return LiderancaResponse.model_validate(item)

    async def add_hierarchy(
        self, actor: RequestActor, payload: HierarquiaInput
    ) -> HierarquiaResponse:
        await self._person(actor.tenant_id, payload.pessoa_subordinada_id)
        if await self.repository.hierarchy_would_cycle(
            actor.tenant_id,
            payload.lideranca_superior_id,
            payload.pessoa_subordinada_id,
        ):
            raise BusinessRuleError(
                "A relacao criaria um ciclo na hierarquia.",
                code="leadership_cycle",
            )
        if payload.ativo and await self.repository.active_hierarchy_for_person(
            actor.tenant_id, payload.pessoa_subordinada_id
        ):
            raise BusinessRuleError(
                "Esta pessoa ja possui uma lideranca ativa.",
                code="person_already_has_active_leadership",
            )
        item = await self.repository.add_hierarchy(actor.tenant_id, payload)
        await self._audit_created(actor, "hierarquia_lideranca", item.id)
        return HierarquiaResponse.model_validate(item)

    async def set_hierarchy_status(
        self, actor: RequestActor, hierarchy_id: int, payload: HierarquiaStatusInput
    ) -> HierarquiaResponse:
        item = await self.repository.hierarchy(actor.tenant_id, hierarchy_id)
        if item is None:
            raise ResourceNotFoundError("Vinculo de lideranca", hierarchy_id)
        if payload.ativo and await self.repository.active_hierarchy_for_person(
            actor.tenant_id, item.pessoa_subordinada_id, exclude_id=item.id
        ):
            raise BusinessRuleError(
                "Esta pessoa ja possui uma lideranca ativa.",
                code="person_already_has_active_leadership",
            )
        before = {
            "ativo": item.ativo,
            "data_fim": item.data_fim.isoformat() if item.data_fim else None,
        }
        item = await self.repository.set_hierarchy_status(item, payload.ativo)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="editar",
            table_name="hierarquia_lideranca",
            record_id=item.id,
            before=before,
            after={
                "ativo": item.ativo,
                "data_fim": item.data_fim.isoformat() if item.data_fim else None,
            },
        )
        await self.repository.commit()
        return HierarquiaResponse.model_validate(item)

    async def set_hierarchy_role(
        self, actor: RequestActor, hierarchy_id: int, payload: HierarquiaRoleInput
    ) -> HierarquiaResponse:
        item = await self.repository.hierarchy(actor.tenant_id, hierarchy_id)
        if item is None:
            raise ResourceNotFoundError("Vinculo de lideranca", hierarchy_id)
        previous_role = item.papel_subordinado
        item = await self.repository.set_hierarchy_role(item, payload.papel_subordinado)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="editar",
            table_name="hierarquia_lideranca",
            record_id=item.id,
            before={"papel_subordinado": previous_role},
            after={"papel_subordinado": item.papel_subordinado},
        )
        await self.repository.commit()
        return HierarquiaResponse.model_validate(item)

    async def delete_hierarchy(self, actor: RequestActor, hierarchy_id: int) -> None:
        self._require_manager_profile(actor)
        item = await self.repository.hierarchy(actor.tenant_id, hierarchy_id)
        if item is None:
            raise ResourceNotFoundError("Vinculo de lideranca", hierarchy_id)
        before = {
            "id": item.id,
            "lideranca_superior_id": item.lideranca_superior_id,
            "pessoa_subordinada_id": item.pessoa_subordinada_id,
            "papel_subordinado": item.papel_subordinado,
            "ativo": item.ativo,
        }
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="excluir",
            table_name="hierarquia_lideranca",
            record_id=item.id,
            before=before,
            after=None,
        )
        await self.repository.delete_hierarchy(item)
        await self.repository.commit()

    async def delete_leadership(self, actor: RequestActor, leadership_id: int) -> None:
        self._require_manager_profile(actor)
        item = await self.repository.leadership(actor.tenant_id, leadership_id)
        if item is None:
            raise ResourceNotFoundError("Lideranca", leadership_id)
        before = {
            "id": item.id,
            "pessoa_id": item.pessoa_id,
            "tipo_lideranca": item.tipo_lideranca,
            "coordenador_id": item.coordenador_id,
            "apelido_campanha": item.apelido_campanha,
            "ativo": item.ativo,
        }
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="excluir",
            table_name="lideranca",
            record_id=item.id,
            before=before,
            after=None,
        )
        await self.repository.delete_leadership(item)
        await self.repository.commit()

    @staticmethod
    def _require_manager_profile(actor: RequestActor) -> None:
        if not {"gestor", "gestor_saas"} & set(actor.profiles):
            raise AuthorizationError("Perfil Gestor ou Gestor SaaS obrigatorio.")

    async def add_indication(
        self, actor: RequestActor, person_id: int, payload: IndicacaoPessoaInput
    ) -> IndicacaoResponse:
        await self._person(actor.tenant_id, person_id)
        await self._person(actor.tenant_id, payload.pessoa_indicada_id)
        if payload.pessoa_indicada_id == person_id:
            raise BusinessRuleError(
                "Uma pessoa nao pode indicar a si mesma.",
                code="self_indication",
            )
        if await self.repository.person_has_indication(
            actor.tenant_id, payload.pessoa_indicada_id
        ):
            raise BusinessRuleError(
                "Esta pessoa ja foi indicada.",
                code="person_already_indicated",
            )
        indication = IndicacaoInput(
            pessoa_indicante_id=person_id,
            origem=payload.origem,
            contexto=payload.contexto,
            data_indicacao=payload.data_indicacao,
        )
        item = await self.repository.add_indication(
            actor.tenant_id, payload.pessoa_indicada_id, indication
        )
        await self._audit_created(actor, "indicacao", item.id)
        return IndicacaoResponse.model_validate(item)

    async def add_relationship(
        self, actor: RequestActor, person_id: int, payload: RelacionamentoInput
    ) -> RelacionamentoResponse:
        await self._person(actor.tenant_id, person_id)
        await self._person(actor.tenant_id, payload.pessoa_destino_id)
        if person_id == payload.pessoa_destino_id:
            raise BusinessRuleError(
                "Uma pessoa nao pode se relacionar consigo mesma.",
                code="self_relationship",
            )
        item = await self.repository.add_relationship(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "relacionamento_pessoa", item.id)
        return RelacionamentoResponse.model_validate(item)

    async def create_nucleus(
        self, actor: RequestActor, payload: NucleoFamiliarInput
    ) -> NucleoFamiliarResponse:
        if payload.pessoa_referencia_id:
            await self._person(actor.tenant_id, payload.pessoa_referencia_id)
        if payload.endereco_id and not await self.repository.address_exists(
            actor.tenant_id, payload.endereco_id
        ):
            raise ResourceNotFoundError("Endereco", payload.endereco_id)
        item = await self.repository.create_nucleus(actor.tenant_id, payload)
        await self._audit_created(actor, "nucleo_familiar", item.id)
        return NucleoFamiliarResponse.model_validate(item)

    async def list_nuclei(self, actor: RequestActor) -> list[NucleoFamiliarResponse]:
        return [
            NucleoFamiliarResponse.model_validate(item)
            for item in await self.repository.list_nuclei(actor.tenant_id)
        ]

    async def add_nucleus_member(
        self, actor: RequestActor, nucleus_id: int, payload: VinculoNucleoInput
    ) -> VinculoNucleoResponse:
        nucleus = await self.repository.nucleus(actor.tenant_id, nucleus_id)
        if nucleus is None:
            raise ResourceNotFoundError("Nucleo familiar", nucleus_id)
        await self._person(actor.tenant_id, payload.pessoa_id)
        item = await self.repository.add_nucleus_member(actor.tenant_id, nucleus, payload)
        await self._audit_created(actor, "pessoa_nucleo_familiar", item.id)
        return VinculoNucleoResponse.model_validate(item)

    async def list_nucleus_people(
        self, actor: RequestActor, nucleus_id: int
    ) -> list[NucleoPessoaResponse]:
        if await self.repository.nucleus(actor.tenant_id, nucleus_id) is None:
            raise ResourceNotFoundError("Nucleo familiar", nucleus_id)
        return [
            NucleoPessoaResponse.model_validate(item)
            for item in await self.repository.nucleus_people(actor.tenant_id, nucleus_id)
        ]

    async def remove_nucleus_member(
        self, actor: RequestActor, nucleus_id: int, person_id: int
    ) -> None:
        nucleus = await self.repository.nucleus(actor.tenant_id, nucleus_id)
        if nucleus is None:
            raise ResourceNotFoundError("Nucleo familiar", nucleus_id)
        if not await self.repository.remove_nucleus_member(
            actor.tenant_id, nucleus, person_id
        ):
            raise ResourceNotFoundError("Vinculo entre pessoa e nucleo familiar", person_id)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="excluir",
            table_name="pessoa_nucleo_familiar",
            record_id=person_id,
            before={"nucleo_familiar_id": nucleus_id, "pessoa_id": person_id},
            after=None,
        )
        await self.repository.commit()

    @staticmethod
    def kinship_options() -> list[ParentescoResponse]:
        return [
            ParentescoResponse(codigo="responsavel", nome="Responsável"),
            ParentescoResponse(codigo="conjuge", nome="Cônjuge"),
            ParentescoResponse(codigo="pai", nome="Pai"),
            ParentescoResponse(codigo="mae", nome="Mãe"),
            ParentescoResponse(codigo="filho", nome="Filho(a)"),
            ParentescoResponse(codigo="irmao", nome="Irmão(ã)"),
            ParentescoResponse(codigo="avo", nome="Avô/ó"),
            ParentescoResponse(codigo="neto", nome="Neto(a)"),
            ParentescoResponse(codigo="tio", nome="Tio(a)"),
            ParentescoResponse(codigo="sobrinho", nome="Sobrinho(a)"),
            ParentescoResponse(codigo="primo", nome="Primo(a)"),
            ParentescoResponse(codigo="familiar", nome="Familiar"),
            ParentescoResponse(codigo="outro", nome="Outro"),
        ]

    async def create_community(
        self, actor: RequestActor, payload: ComunidadeInput
    ) -> ComunidadeResponse:
        if payload.lider_responsavel_id and (
            await self.repository.leadership(actor.tenant_id, payload.lider_responsavel_id) is None
        ):
            raise ResourceNotFoundError("Lideranca", payload.lider_responsavel_id)
        if payload.territorio_id and not await self.repository.territory_exists(
            actor.tenant_id, payload.territorio_id
        ):
            raise ResourceNotFoundError("Territorio", payload.territorio_id)
        item = await self.repository.create_community(actor.tenant_id, payload)
        await self._audit_created(actor, "comunidade", item.id)
        return ComunidadeResponse.model_validate(item)

    async def list_communities(self, actor: RequestActor) -> list[ComunidadeResponse]:
        return [
            ComunidadeResponse.model_validate(item)
            for item in await self.repository.list_communities(actor.tenant_id)
        ]

    async def update_community(
        self, actor: RequestActor, community_id: int, payload: ComunidadeInput
    ) -> ComunidadeResponse:
        item = await self.repository.community(actor.tenant_id, community_id)
        if item is None:
            raise ResourceNotFoundError("Comunidade", community_id)
        if payload.lider_responsavel_id and (
            await self.repository.leadership(actor.tenant_id, payload.lider_responsavel_id) is None
        ):
            raise ResourceNotFoundError("Lideranca", payload.lider_responsavel_id)
        if payload.territorio_id and not await self.repository.territory_exists(
            actor.tenant_id, payload.territorio_id
        ):
            raise ResourceNotFoundError("Territorio", payload.territorio_id)
        item = await self.repository.update_community(item, payload)
        await self._audit_updated(actor, "comunidade", item.id)
        return ComunidadeResponse.model_validate(item)

    async def add_community_member(
        self, actor: RequestActor, community_id: int, payload: VinculoComunidadeInput
    ) -> None:
        if await self.repository.community(actor.tenant_id, community_id) is None:
            raise ResourceNotFoundError("Comunidade", community_id)
        await self._person(actor.tenant_id, payload.pessoa_id)
        await self.repository.add_community_member(actor.tenant_id, community_id, payload)
        await self.repository.commit()

    async def list_community_people(
        self, actor: RequestActor, community_id: int
    ) -> list[ComunidadePessoaResponse]:
        if await self.repository.community(actor.tenant_id, community_id) is None:
            raise ResourceNotFoundError("Comunidade", community_id)
        return [
            ComunidadePessoaResponse.model_validate(item)
            for item in await self.repository.community_people(actor.tenant_id, community_id)
        ]

    async def remove_community_member(
        self, actor: RequestActor, community_id: int, person_id: int
    ) -> None:
        if await self.repository.community(actor.tenant_id, community_id) is None:
            raise ResourceNotFoundError("Comunidade", community_id)
        if not await self.repository.remove_community_member(
            actor.tenant_id, community_id, person_id
        ):
            raise ResourceNotFoundError("Vinculo entre pessoa e comunidade", person_id)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="excluir",
            table_name="pessoa_comunidade",
            record_id=person_id,
            before={"comunidade_id": community_id, "pessoa_id": person_id},
            after=None,
        )
        await self.repository.commit()

    @staticmethod
    def community_roles() -> list[PapelComunidadeResponse]:
        return [
            PapelComunidadeResponse(codigo="membro", nome="Membro"),
            PapelComunidadeResponse(codigo="lider", nome="Líder"),
            PapelComunidadeResponse(codigo="coordenador", nome="Coordenador"),
            PapelComunidadeResponse(codigo="mobilizador", nome="Mobilizador"),
            PapelComunidadeResponse(codigo="voluntario", nome="Voluntário"),
        ]

    async def create_tag(self, actor: RequestActor, payload: TagInput) -> TagResponse:
        item = await self.repository.create_tag(actor.tenant_id, payload)
        await self._audit_created(actor, "tag", item.id)
        return TagResponse.model_validate(item)

    async def list_tags(self, actor: RequestActor) -> list[TagResponse]:
        return [
            TagResponse.model_validate(item)
            for item in await self.repository.list_tags(actor.tenant_id)
        ]

    async def update_tag(self, actor: RequestActor, tag_id: int, payload: TagUpdate) -> TagResponse:
        item = await self.repository.tag(actor.tenant_id, tag_id)
        if item is None:
            raise ResourceNotFoundError("Tag", tag_id)
        item = await self.repository.update_tag(item, payload)
        await self._audit_updated(actor, "tag", item.id)
        return TagResponse.model_validate(item)

    async def add_person_tag(self, actor: RequestActor, tag_id: int, person_id: int) -> None:
        if await self.repository.tag(actor.tenant_id, tag_id) is None:
            raise ResourceNotFoundError("Tag", tag_id)
        await self._person(actor.tenant_id, person_id)
        await self.repository.add_person_tag(actor.tenant_id, tag_id, person_id)
        await self.repository.commit()

    async def list_tag_people(
        self, actor: RequestActor, tag_id: int
    ) -> list[TagPessoaResponse]:
        if await self.repository.tag(actor.tenant_id, tag_id) is None:
            raise ResourceNotFoundError("Tag", tag_id)
        return [
            TagPessoaResponse(
                id=person.id,
                nome_completo=person.nome_completo,
                data_nascimento=person.data_nascimento,
            )
            for person in await self.repository.tag_people(actor.tenant_id, tag_id)
        ]

    async def remove_person_tag(
        self, actor: RequestActor, tag_id: int, person_id: int
    ) -> None:
        if await self.repository.tag(actor.tenant_id, tag_id) is None:
            raise ResourceNotFoundError("Tag", tag_id)
        if not await self.repository.remove_person_tag(actor.tenant_id, tag_id, person_id):
            raise ResourceNotFoundError("Vinculo entre pessoa e tag", person_id)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="excluir",
            table_name="pessoa_tag",
            record_id=person_id,
            before={"tag_id": tag_id, "pessoa_id": person_id},
            after=None,
        )
        await self.repository.commit()

    async def set_political(
        self, actor: RequestActor, person_id: int, payload: ComplementoPoliticoInput
    ) -> ComplementoPoliticoResponse:
        await self._person(actor.tenant_id, person_id)
        item = await self.repository.upsert_political(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "pessoa_complemento_politico", item.id)
        return ComplementoPoliticoResponse.model_validate(item)

    async def create_validation(
        self, actor: RequestActor, person_id: int, payload: ValidacaoInput
    ) -> ValidacaoResponse:
        await self._person(actor.tenant_id, person_id)
        item = await self.repository.create_validation(actor.tenant_id, person_id, payload)
        await self._audit_created(actor, "validacao_cadastro", item.id)
        return ValidacaoResponse.model_validate(item)

    async def list_validations(
        self, actor: RequestActor, status: str | None
    ) -> list[ValidacaoResponse]:
        items = await self.repository.list_validations(actor.tenant_id, status)
        names = await self.repository.validation_person_names(
            actor.tenant_id, {item.pessoa_id for item in items}
        )
        return [
            ValidacaoResponse.model_validate(item).model_copy(
                update={"pessoa_nome": names.get(item.pessoa_id)}
            )
            for item in items
        ]

    async def resolve_validation(
        self, actor: RequestActor, validation_id: int, payload: ValidacaoResolve
    ) -> ValidacaoResponse:
        item = await self.repository.validation(actor.tenant_id, validation_id)
        if item is None:
            raise ResourceNotFoundError("Validacao cadastral", validation_id)
        item.status = payload.status
        if payload.observacao is not None:
            item.observacao = payload.observacao
        item.revisado_por = actor.user_id
        item.revisado_em = datetime.now(UTC)
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="editar",
            table_name="validacao_cadastro",
            record_id=item.id,
            before=None,
            after={"status": item.status},
        )
        await self.repository.commit()
        return ValidacaoResponse.model_validate(item)

    async def list_duplicates(
        self,
        actor: RequestActor,
        status: str | None,
        nome: str | None = None,
    ) -> list[SuspeitaDuplicidadeResponse]:
        items = await self.repository.list_duplicates(actor.tenant_id, status, nome)
        names = await self.repository.duplicate_person_names(
            actor.tenant_id,
            {
                person_id
                for item in items
                for person_id in (item.pessoa_id, item.pessoa_duplicada_id)
            },
        )
        return [
            SuspeitaDuplicidadeResponse.model_validate(item).model_copy(
                update={
                    "pessoa_nome": names.get(item.pessoa_id),
                    "pessoa_duplicada_nome": names.get(item.pessoa_duplicada_id),
                }
            )
            for item in items
        ]

    async def duplicate_summary(self, actor: RequestActor) -> DuplicidadeResumoResponse:
        return DuplicidadeResumoResponse.model_validate(
            await self.repository.duplicate_summary(actor.tenant_id)
        )

    async def merge_preview(self, actor: RequestActor, duplicate_id: int) -> PessoaMergePreview:
        self._require_merge_manager(actor)
        suspicion = await self.repository.duplicate(actor.tenant_id, duplicate_id)
        if suspicion is None:
            raise ResourceNotFoundError("Suspeita de duplicidade", duplicate_id)
        if suspicion.status == "mesclada":
            raise BusinessRuleError(
                "Esta suspeita ja foi mesclada.", code="duplicate_already_merged"
            )
        person_a = await self.get_person(actor, suspicion.pessoa_id)
        person_b = await self.get_person(actor, suspicion.pessoa_duplicada_id)
        merge_fields: tuple[MergePessoaCampo, ...] = (
            "nome_completo",
            "nome_social",
            "apelido",
            "sexo",
            "data_nascimento",
            "estado_civil",
            "escolaridade_id",
            "profissao_id",
            "religiao_id",
            "observacoes",
        )
        conflicts = [
            PessoaMergeConflict(
                campo=field,
                valor_principal=getattr(person_a, field),
                valor_origem=getattr(person_b, field),
            )
            for field in merge_fields
            if getattr(person_a, field) != getattr(person_b, field)
        ]
        return PessoaMergePreview(
            suspeita_id=suspicion.id,
            pessoa_a=person_a,
            pessoa_b=person_b,
            conflitos=conflicts,
        )

    async def merge_duplicate(
        self,
        actor: RequestActor,
        duplicate_id: int,
        payload: PessoaMergeRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PessoaMergeResponse:
        self._require_merge_manager(actor)
        suspicion = await self.repository.duplicate(actor.tenant_id, duplicate_id)
        if suspicion is None:
            raise ResourceNotFoundError("Suspeita de duplicidade", duplicate_id)
        if suspicion.status == "mesclada":
            raise BusinessRuleError(
                "Esta suspeita ja foi mesclada.", code="duplicate_already_merged"
            )
        pair = {suspicion.pessoa_id, suspicion.pessoa_duplicada_id}
        if payload.pessoa_principal_id not in pair:
            raise BusinessRuleError(
                "A pessoa principal deve pertencer a suspeita informada.",
                code="invalid_merge_principal",
            )
        source_id = next(
            person_id for person_id in pair if person_id != payload.pessoa_principal_id
        )
        if await self.repository.existing_merge_for_source(actor.tenant_id, source_id):
            raise BusinessRuleError(
                "A pessoa de origem ja foi mesclada.",
                code="source_already_merged",
            )
        principal_detail = await self.get_person(actor, payload.pessoa_principal_id)
        source_detail = await self.get_person(actor, source_id)
        principal = await self._person(actor.tenant_id, payload.pessoa_principal_id)
        source = await self._person(actor.tenant_id, source_id)
        principal_snapshot = principal_detail.model_dump(mode="json")
        source_snapshot = source_detail.model_dump(mode="json")
        merge = await self.repository.merge_people(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            suspicion_id=suspicion.id,
            principal=principal,
            source=source,
            source_fields=list(payload.campos_origem),
            principal_snapshot=principal_snapshot,
            source_snapshot=source_snapshot,
        )
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="mesclar",
            table_name="pessoa_merge",
            record_id=merge.id,
            before={"principal": principal_snapshot, "origem": source_snapshot},
            after={
                "pessoa_principal_id": principal.id,
                "pessoa_origem_id": source.id,
                "campos_origem": list(payload.campos_origem),
                "resumo_operacao": merge.resumo_operacao,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        return PessoaMergeResponse(
            merge_id=merge.id,
            pessoa_principal=await self.get_person(actor, principal.id),
            pessoa_origem_id=source.id,
            resumo_operacao={key: int(value) for key, value in merge.resumo_operacao.items()},
        )

    async def resolve_duplicate(
        self,
        actor: RequestActor,
        duplicate_id: int,
        payload: SuspeitaDuplicidadeResolve,
    ) -> SuspeitaDuplicidadeResponse:
        item = await self.repository.duplicate(actor.tenant_id, duplicate_id)
        if item is None:
            raise ResourceNotFoundError("Suspeita de duplicidade", duplicate_id)
        status_by_decision = {
            "duplicado": "confirmada",
            "falso_positivo": "descartada",
            "pendente": "pendente",
        }
        item.status = status_by_decision[payload.decisao]
        item.resolvido_por = actor.user_id if payload.decisao != "pendente" else None
        item.resolvido_em = datetime.now(UTC) if payload.decisao != "pendente" else None
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="editar",
            table_name="suspeita_duplicidade",
            record_id=item.id,
            before=None,
            after={"status": item.status, "decisao": payload.decisao},
        )
        await self.repository.commit()
        return SuspeitaDuplicidadeResponse.model_validate(item)

    async def quick_search(
        self,
        actor: RequestActor,
        query: str,
        limit: int,
        territorial_access: TerritorialAccess | None = None,
    ) -> list[BuscaRapidaItem]:
        accessible_ids = None
        if territorial_access is not None:
            accessible_ids = await TerritorioRepository(
                self.repository.session
            ).accessible_ids(actor.tenant_id, territorial_access)
        people = await self.repository.quick_search(
            actor.tenant_id, query, limit, accessible_ids
        )
        return [
            BuscaRapidaItem(
                id=person.id,
                nome_completo=person.nome_completo,
                data_nascimento=person.data_nascimento,
                documento=person.documentos[0].numero if person.documentos else None,
                telefone=person.contatos[0].valor if person.contatos else None,
            )
            for person in people
        ]

    async def indication_graph(
        self,
        actor: RequestActor,
        *,
        person_id: int | None,
        origin: str | None,
        date_from: date | None,
        date_to: date | None,
        depth: int,
        limit: int,
    ) -> IndicacaoGraphResponse:
        if date_from and date_to and date_from > date_to:
            raise BusinessRuleError(
                "A data inicial nao pode ser posterior a data final.",
                code="invalid_date_range",
            )
        if person_id is not None:
            await self._person(actor.tenant_id, person_id)
        edges, people, truncated = await self.repository.indication_graph(
            actor.tenant_id,
            person_id=person_id,
            origin=origin,
            date_from=date_from,
            date_to=date_to,
            depth=depth,
            limit=limit,
        )
        nodes = [
            IndicacaoGraphNode(
                id=person.id,
                nome=person.nome_social or person.nome_completo,
                ativo=person.ativo,
            )
            for person in people
        ]
        graph_edges = [
            IndicacaoGraphEdge(
                id=int(item["id"]),
                origem_id=int(item["pessoa_indicante_id"]),
                destino_id=int(item["pessoa_indicada_id"]),
                origem=item["origem"],
                contexto=item["contexto"],
                data_indicacao=item["data_indicacao"],
            )
            for item in edges
        ]
        return IndicacaoGraphResponse(
            nodes=nodes,
            edges=graph_edges,
            total_edges=len(graph_edges),
            truncated=truncated,
        )

    async def _person(self, tenant_id: int, person_id: int) -> Any:
        person = await self.repository.get_person(tenant_id, person_id)
        if person is None:
            raise ResourceNotFoundError("Pessoa", person_id)
        return person

    async def _audit_created(self, actor: RequestActor, table_name: str, record_id: int) -> None:
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="criar",
            table_name=table_name,
            record_id=record_id,
            before=None,
            after={"id": record_id},
        )
        await self.repository.commit()

    async def _audit_updated(self, actor: RequestActor, table_name: str, record_id: int) -> None:
        await self.repository.audit(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            action="editar",
            table_name=table_name,
            record_id=record_id,
            before=None,
            after={"id": record_id},
        )
        await self.repository.commit()

    async def _validate_references(self, tenant_id: int, payload: PessoaCadastroCreate) -> None:
        if payload.estado_civil is not None and not await self.repository.marital_status_exists(
            payload.estado_civil
        ):
            raise ResourceNotFoundError("Estado civil", payload.estado_civil)
        if payload.indicacao and payload.indicacao.pessoa_indicante_id:
            if not await self.repository.person_exists(
                tenant_id, payload.indicacao.pessoa_indicante_id
            ):
                raise ResourceNotFoundError(
                    "Pessoa indicante", payload.indicacao.pessoa_indicante_id
                )
        if payload.lideranca and payload.lideranca.coordenador_id:
            if (
                await self.repository.leadership(tenant_id, payload.lideranca.coordenador_id)
                is None
            ):
                raise ResourceNotFoundError("Coordenador", payload.lideranca.coordenador_id)
        if payload.lideranca_superior_id and (
            await self.repository.leadership(tenant_id, payload.lideranca_superior_id) is None
        ):
            raise ResourceNotFoundError("Lideranca responsavel", payload.lideranca_superior_id)

    @staticmethod
    def _is_scoped_mobile_leader(actor: RequestActor) -> bool:
        return (
            actor.is_mobile_leader_session
            and actor.habilitado_app_lider
            and actor.lideranca_id is not None
        )

    @staticmethod
    def _scope_mobile_leader_filters(
        actor: RequestActor, filters: PessoaFiltros
    ) -> PessoaFiltros:
        if (
            not actor.is_mobile_leader_session
            or not actor.habilitado_app_lider
            or actor.lideranca_id is None
        ):
            return filters
        if (
            filters.cadastrado_por_lideranca_id is None
            and filters.lideranca_id is None
            and filters.origem_cadastro is None
        ):
            return filters.model_copy(
                update={"cadastrado_por_lideranca_id": actor.lideranca_id}
            )
        return filters

    async def _prepare_mobile_create(
        self, actor: RequestActor, payload: PessoaCadastroCreate
    ) -> tuple[PessoaCadastroCreate, MobileLeaderContext | None]:
        if (
            not actor.is_mobile_leader_session
            or not actor.habilitado_app_lider
            or actor.lideranca_id is None
        ):
            return payload, None

        data = payload.model_copy(deep=True)
        if data.lideranca_superior_id is None:
            data.lideranca_superior_id = actor.lideranca_id

        if data.indicacao is None:
            data.indicacao = IndicacaoInput(
                pessoa_indicante_id=actor.pessoa_id,
                origem="lider_mobile",
            )
        else:
            indicacao_updates: dict[str, Any] = {}
            if data.indicacao.pessoa_indicante_id is None and actor.pessoa_id is not None:
                indicacao_updates["pessoa_indicante_id"] = actor.pessoa_id
            if not data.indicacao.origem:
                indicacao_updates["origem"] = "lider_mobile"
            if indicacao_updates:
                data.indicacao = data.indicacao.model_copy(update=indicacao_updates)

        fonte_dado_id = await self.repository.resolve_global_fonte_dado_id("app_lider_mobile")
        mobile = MobileLeaderContext(
            cadastrado_por_lideranca_id=actor.lideranca_id,
            fonte_dado_id=fonte_dado_id,
        )
        return data, mobile

    async def _prepare_integration_create(
        self, actor: RequestActor, payload: PessoaCadastroCreate
    ) -> tuple[PessoaCadastroCreate, str | None, int | None]:
        if not actor.is_integration_session:
            return payload, None, None
        fonte_dado_id = await self.repository.resolve_global_fonte_dado_id("site_integracao")
        observacoes = _with_site_origin_note(payload.observacoes)
        if observacoes != payload.observacoes:
            payload = payload.model_copy(update={"observacoes": observacoes})
        return payload, "integracao", fonte_dado_id

    @staticmethod
    def _has_assigned_leader(
        payload: PessoaCadastroCreate, actor: RequestActor | None = None
    ) -> bool:
        if payload.lideranca_superior_id is not None:
            return True
        if (
            actor is not None
            and actor.is_mobile_leader_session
            and actor.habilitado_app_lider
            and actor.lideranca_id is not None
        ):
            return True
        leadership = payload.lideranca
        return bool(
            leadership
            and (
                leadership.tipo_lideranca == "coordenador_geral"
                or leadership.coordenador_id is not None
            )
        )

    @staticmethod
    def _require_merge_manager(actor: RequestActor) -> None:
        if not {"gestor", "gestor_saas"} & set(actor.profiles):
            raise AuthorizationError("Apenas gestores podem executar merge de cadastros.")


def _with_site_origin_note(observacoes: str | None) -> str:
    current = (observacoes or "").strip()
    if current and SITE_ORIGIN_NOTE.lower() in current.lower():
        return current
    if not current:
        return SITE_ORIGIN_NOTE
    return f"{current}\n{SITE_ORIGIN_NOTE}"
