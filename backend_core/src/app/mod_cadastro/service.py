"""Regras de negocio do dominio de cadastro."""

from datetime import UTC, date, datetime
from typing import Any

from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.core.pagination import ListParams, Page
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
    ComunidadeResponse,
    EstadoCivilResponse,
    HierarquiaInput,
    HierarquiaResponse,
    HierarquiaResumo,
    IndicacaoGraphEdge,
    IndicacaoGraphNode,
    IndicacaoGraphResponse,
    IndicacaoInput,
    IndicacaoResponse,
    LiderancaOperacionalResponse,
    MergePessoaCampo,
    NucleoFamiliarInput,
    NucleoFamiliarResponse,
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
    SuspeitaDuplicidadeResolve,
    SuspeitaDuplicidadeResponse,
    TagInput,
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
        accessible_ids = None
        if territorial_access is not None:
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
                    HierarquiaResumo.model_validate(item) for item in extensions["hierarquia"]
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
        person = await self.repository.create_person(actor.tenant_id, actor.user_id, payload)
        await self.repository.create_duplicate_suspicions(actor.tenant_id, person, payload)
        if not self._has_assigned_leader(payload):
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

    async def list_leaderships(self, actor: RequestActor) -> list[LiderancaOperacionalResponse]:
        items = await self.repository.list_leaderships(actor.tenant_id)
        territories = await self.repository.leadership_territories(
            actor.tenant_id, [item.id for item in items]
        )
        return [
            LiderancaOperacionalResponse(
                **LiderancaResponse.model_validate(item).model_dump(),
                territorio_ids=territories.get(item.id, []),
            )
            for item in items
        ]

    async def list_hierarchy(self, actor: RequestActor) -> list[HierarquiaResponse]:
        return [
            HierarquiaResponse.model_validate(item)
            for item in await self.repository.list_hierarchy(actor.tenant_id)
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
        item = await self.repository.add_hierarchy(actor.tenant_id, payload)
        await self._audit_created(actor, "hierarquia_lideranca", item.id)
        return HierarquiaResponse.model_validate(item)

    async def add_indication(
        self, actor: RequestActor, person_id: int, payload: IndicacaoInput
    ) -> IndicacaoResponse:
        await self._person(actor.tenant_id, person_id)
        if payload.pessoa_indicante_id is not None:
            await self._person(actor.tenant_id, payload.pessoa_indicante_id)
            if payload.pessoa_indicante_id == person_id:
                raise BusinessRuleError(
                    "Uma pessoa nao pode indicar a si mesma.",
                    code="self_indication",
                )
        item = await self.repository.add_indication(actor.tenant_id, person_id, payload)
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

    async def add_community_member(
        self, actor: RequestActor, community_id: int, payload: VinculoComunidadeInput
    ) -> None:
        if await self.repository.community(actor.tenant_id, community_id) is None:
            raise ResourceNotFoundError("Comunidade", community_id)
        await self._person(actor.tenant_id, payload.pessoa_id)
        await self.repository.add_community_member(actor.tenant_id, community_id, payload)
        await self.repository.commit()

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
        return [
            ValidacaoResponse.model_validate(item)
            for item in await self.repository.list_validations(actor.tenant_id, status)
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
        self, actor: RequestActor, status: str | None
    ) -> list[SuspeitaDuplicidadeResponse]:
        return [
            SuspeitaDuplicidadeResponse.model_validate(item)
            for item in await self.repository.list_duplicates(actor.tenant_id, status)
        ]

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
    def _has_assigned_leader(payload: PessoaCadastroCreate) -> bool:
        if payload.lideranca_superior_id is not None:
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
