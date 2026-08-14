import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError, BusinessRuleError
from app.core.pagination import ListParams
from app.mod_cadastro.repository import CadastroRepository
from app.mod_cadastro.router import router
from app.mod_cadastro.service import CadastroService
from app.schemas.cadastro import (
    EleitorCreate,
    PessoaContatoCreate,
    PessoaDocumentoCreate,
)
from app.schemas.cadastro_operacional import (
    HierarquiaInput,
    HierarquiaRoleInput,
    HierarquiaStatusInput,
    IndicacaoPessoaInput,
    PessoaCadastroCreate,
    PessoaFiltros,
    PessoaMergeRequest,
    TagInput,
)


def make_actor() -> RequestActor:
    return RequestActor(
        tenant_id=10,
        user_id=20,
        session_id=30,
        profiles=("gestor",),
        permissions=frozenset(
            {
                "cadastro.visualizar",
                "cadastro.criar",
                "cadastro.editar",
                "cadastro.excluir",
            }
        ),
        token="token",
    )


def test_mobile_leader_filter_is_applied_only_to_mobile_session() -> None:
    filters = PessoaFiltros()
    common = {
        "tenant_id": 10,
        "user_id": 20,
        "session_id": 30,
        "profiles": ("gestor", "lider"),
        "permissions": frozenset({"cadastro.visualizar"}),
        "token": "token",
        "habilitado_app_lider": True,
        "lideranca_id": 5,
    }
    web_actor = RequestActor(**common, login_origin="web")
    mobile_actor = RequestActor(**common, login_origin="app_lider")

    web_filters = CadastroService._scope_mobile_leader_filters(web_actor, filters)
    mobile_filters = CadastroService._scope_mobile_leader_filters(mobile_actor, filters)

    assert web_filters.cadastrado_por_lideranca_id is None
    assert mobile_filters.cadastrado_por_lideranca_id == 5


def make_mobile_leader_actor() -> RequestActor:
    return RequestActor(
        tenant_id=10,
        user_id=20,
        session_id=30,
        profiles=("lider",),
        permissions=frozenset({"cadastro.visualizar"}),
        token="token",
        habilitado_app_lider=True,
        lideranca_id=5,
        login_origin="app_lider",
    )


@pytest.mark.asyncio
async def test_list_people_skips_territorial_filter_for_mobile_leader() -> None:
    repository = AsyncMock()
    repository.list_people.return_value = ([], 0)
    service = CadastroService(repository)
    territorial_access = TerritorialAccess(unrestricted=False, scopes=frozenset())

    await service.list_people(
        make_mobile_leader_actor(),
        ListParams(),
        PessoaFiltros(),
        territorial_access,
    )

    assert repository.list_people.await_args.args[3] is None


@pytest.mark.asyncio
async def test_list_people_keeps_territorial_filter_for_web_session() -> None:
    repository = AsyncMock()
    repository.list_people.return_value = ([], 0)
    service = CadastroService(repository)
    territorial_access = TerritorialAccess(
        unrestricted=False,
        scopes=frozenset(("territorio", 99, False)),
    )

    with patch(
        "app.mod_cadastro.service.TerritorioRepository.accessible_ids",
        new=AsyncMock(return_value={99}),
    ) as accessible_ids:
        await service.list_people(
            make_actor(),
            ListParams(),
            PessoaFiltros(),
            territorial_access,
        )

    accessible_ids.assert_awaited_once()
    assert repository.list_people.await_args.args[3] == {99}


@pytest.mark.asyncio
async def test_mobile_leader_can_access_own_registration_without_territory() -> None:
    repository = AsyncMock()
    repository.get_person.return_value = SimpleNamespace(
        id=42,
        tenant_id=10,
        cadastrado_por_lideranca_id=5,
    )
    service = CadastroService(repository)
    territorial_access = TerritorialAccess(unrestricted=False, scopes=frozenset())

    await service.ensure_person_territorial_access(
        make_mobile_leader_actor(), 42, territorial_access
    )

    repository.person_in_territories.assert_not_awaited()


@pytest.mark.asyncio
async def test_mobile_leader_cannot_access_other_leader_registration() -> None:
    repository = AsyncMock()
    repository.get_person.return_value = SimpleNamespace(
        id=42,
        tenant_id=10,
        cadastrado_por_lideranca_id=99,
    )
    repository.person_in_territories.return_value = False
    service = CadastroService(repository)
    territorial_access = TerritorialAccess(unrestricted=False, scopes=frozenset())

    with pytest.raises(AuthorizationError):
        await service.ensure_person_territorial_access(
            make_mobile_leader_actor(), 42, territorial_access
        )


def test_create_tag_translates_duplicate_name_to_business_error() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.flush.side_effect = IntegrityError(
        "INSERT INTO cadastro.tag",
        {},
        Exception('duplicate key value violates unique constraint "uq_tag_nome"'),
    )
    repository = CadastroRepository(session)

    with pytest.raises(BusinessRuleError) as error:
        asyncio.run(repository.create_tag(10, TagInput(nome="Mobilizacao")))

    assert error.value.code == "tag_name_already_exists"
    session.rollback.assert_awaited_once()


def test_cadastro_audit_uses_shared_audit_service() -> None:
    session = AsyncMock(spec=AsyncSession)
    repository = CadastroRepository(session)

    asyncio.run(
        repository.audit(
            tenant_id=10,
            user_id=20,
            action="criar",
            table_name="tag",
            record_id=30,
            before=None,
            after={"id": 30},
        )
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()


def test_cpf_is_normalized_and_validated() -> None:
    document = PessoaDocumentoCreate(tipo_documento="cpf", numero="529.982.247-25")
    assert document.numero == "52998224725"

    with pytest.raises(ValidationError, match="CPF invalido"):
        PessoaDocumentoCreate(tipo_documento="cpf", numero="111.111.111-11")


@pytest.mark.parametrize(
    ("contact_type", "value", "expected"),
    [
        ("email", " PESSOA@EXAMPLE.COM ", "pessoa@example.com"),
        ("telefone", "(11) 3333-4444", "1133334444"),
        ("whatsapp", "+55 (11) 99999-8888", "5511999998888"),
    ],
)
def test_contacts_are_normalized(contact_type: str, value: str, expected: str) -> None:
    contact = PessoaContatoCreate(tipo_contato=contact_type, valor=value)  # type: ignore[arg-type]
    assert contact.valor == expected


@pytest.mark.parametrize(
    ("contact_type", "value"),
    [("email", "invalido"), ("telefone", "1234")],
)
def test_invalid_contacts_are_rejected(contact_type: str, value: str) -> None:
    with pytest.raises(ValidationError):
        PessoaContatoCreate(tipo_contato=contact_type, valor=value)  # type: ignore[arg-type]


def test_voter_title_and_list_filters_are_normalized() -> None:
    voter = EleitorCreate(titulo_eleitor="1234 5678 9012")
    filters = PessoaFiltros(cpf="529.982.247-25", telefone="(11) 99999-8888")

    assert voter.titulo_eleitor == "123456789012"
    assert filters.cpf == "52998224725"
    assert filters.telefone == "11999998888"


class StrongDuplicateRepository:
    async def strong_duplicate(self, *args: object, **kwargs: object) -> tuple[str, int]:
        return ("cpf", 99)


def test_create_blocks_strong_duplicate_before_writing() -> None:
    service = CadastroService(StrongDuplicateRepository())  # type: ignore[arg-type]
    payload = PessoaCadastroCreate(
        nome_completo="Maria da Silva",
        documentos=[PessoaDocumentoCreate(tipo_documento="cpf", numero="52998224725")],
    )

    with pytest.raises(BusinessRuleError) as error:
        asyncio.run(service.create_person(make_actor(), payload))

    assert error.value.code == "strong_duplicate"
    assert error.value.details == {"criterio": "cpf", "pessoa_id": 99}


class CycleRepository:
    async def get_person(self, tenant_id: int, person_id: int) -> SimpleNamespace:
        return SimpleNamespace(id=person_id, tenant_id=tenant_id)

    async def hierarchy_would_cycle(
        self, tenant_id: int, superior_id: int, subordinate_person_id: int
    ) -> bool:
        return True


def test_hierarchy_cycle_is_rejected() -> None:
    service = CadastroService(CycleRepository())  # type: ignore[arg-type]

    with pytest.raises(BusinessRuleError) as error:
        asyncio.run(
            service.add_hierarchy(
                make_actor(),
                HierarquiaInput(
                    lideranca_superior_id=1,
                    pessoa_subordinada_id=2,
                ),
            )
        )

    assert error.value.code == "leadership_cycle"


@pytest.mark.asyncio
async def test_person_cannot_receive_two_active_leaderships() -> None:
    repository = AsyncMock()
    repository.get_person.return_value = SimpleNamespace(id=2, tenant_id=10)
    repository.hierarchy_would_cycle.return_value = False
    repository.active_hierarchy_for_person.return_value = SimpleNamespace(id=99)
    service = CadastroService(repository)

    with pytest.raises(BusinessRuleError) as error:
        await service.add_hierarchy(
            make_actor(),
            HierarquiaInput(lideranca_superior_id=1, pessoa_subordinada_id=2),
        )

    assert error.value.code == "person_already_has_active_leadership"
    repository.add_hierarchy.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_hierarchy_uses_current_active_campaign() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=37)
    session.flush = AsyncMock()
    repository = CadastroRepository(session)

    item = await repository.add_hierarchy(
        10,
        HierarquiaInput(lideranca_superior_id=1, pessoa_subordinada_id=2),
    )

    assert item.tenant_id == 10
    assert item.campanha_eleicao_id == 37
    assert session.scalar.await_args.args[1] == {"tenant_id": 10}
    session.add.assert_called_once_with(item)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_inactive_link_cannot_be_reactivated_when_another_is_active() -> None:
    repository = AsyncMock()
    repository.hierarchy.return_value = SimpleNamespace(
        id=10, pessoa_subordinada_id=2, ativo=False, data_fim=date.today()
    )
    repository.active_hierarchy_for_person.return_value = SimpleNamespace(id=11)
    service = CadastroService(repository)

    with pytest.raises(BusinessRuleError) as error:
        await service.set_hierarchy_status(
            make_actor(), 10, HierarquiaStatusInput(ativo=True)
        )

    assert error.value.code == "person_already_has_active_leadership"
    repository.set_hierarchy_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_hierarchy_role_is_updated_and_audited() -> None:
    item = SimpleNamespace(
        id=10,
        tenant_id=10,
        campanha_eleicao_id=None,
        lideranca_superior_id=1,
        lideranca_superior_nome="Lider Superior",
        pessoa_subordinada_id=2,
        pessoa_subordinada_nome="Pessoa Vinculada",
        papel_subordinado="liderado",
        data_inicio=date.today(),
        data_fim=None,
        ativo=True,
        origem=None,
        criado_em=datetime.now(UTC),
    )
    repository = AsyncMock()
    repository.hierarchy.return_value = item

    async def update_role(current: SimpleNamespace, role: str) -> SimpleNamespace:
        current.papel_subordinado = role
        return current

    repository.set_hierarchy_role.side_effect = update_role
    service = CadastroService(repository)

    result = await service.set_hierarchy_role(
        make_actor(), 10, HierarquiaRoleInput(papel_subordinado="eleitor")
    )

    assert result.papel_subordinado == "eleitor"
    repository.set_hierarchy_role.assert_awaited_once_with(item, "eleitor")
    repository.audit.assert_awaited_once_with(
        tenant_id=10,
        user_id=20,
        action="editar",
        table_name="hierarquia_lideranca",
        record_id=10,
        before={"papel_subordinado": "liderado"},
        after={"papel_subordinado": "eleitor"},
    )
    repository.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_list_includes_both_person_names() -> None:
    repository = AsyncMock()
    repository.list_duplicates.return_value = [
        SimpleNamespace(
            id=7,
            tenant_id=10,
            pessoa_id=11,
            pessoa_duplicada_id=12,
            criterio="telefone",
            score_similaridade=None,
            status="pendente",
            resolvido_por=None,
            resolvido_em=None,
            criado_em=datetime.now(UTC),
        )
    ]
    repository.duplicate_person_names.return_value = {11: "Maria A", 12: "Maria B"}
    service = CadastroService(repository)

    result = await service.list_duplicates(make_actor(), "pendente", "Maria")

    assert result[0].pessoa_nome == "Maria A"
    assert result[0].pessoa_duplicada_nome == "Maria B"
    repository.list_duplicates.assert_awaited_once_with(10, "pendente", "Maria")
    repository.duplicate_person_names.assert_awaited_once_with(10, {11, 12})


@pytest.mark.asyncio
async def test_validation_list_includes_person_name() -> None:
    repository = AsyncMock()
    repository.list_validations.return_value = [
        SimpleNamespace(
            id=7,
            tenant_id=10,
            pessoa_id=11,
            motivo="sem_lider",
            status="pendente",
            observacao=None,
            revisado_por=None,
            revisado_em=None,
            criado_em=datetime.now(UTC),
        )
    ]
    repository.validation_person_names.return_value = {11: "Maria da Silva"}
    service = CadastroService(repository)

    result = await service.list_validations(make_actor(), "pendente")

    assert result[0].pessoa_nome == "Maria da Silva"
    repository.validation_person_names.assert_awaited_once_with(10, {11})


@pytest.mark.asyncio
async def test_duplicate_repository_requires_both_people_to_be_active() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = []
    session.scalars.return_value = result
    repository = CadastroRepository(session)

    assert await repository.list_duplicates(10, "pendente") == []

    statement = str(session.scalars.await_args.args[0])
    assert statement.count("EXISTS") == 2
    assert statement.count("cadastro.pessoa.ativo IS true") == 2
    assert statement.count("cadastro.pessoa.excluido_em IS NULL") == 2
    assert "like lower" not in statement.lower()


@pytest.mark.asyncio
async def test_duplicate_repository_filters_by_either_person_name() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = []
    session.scalars.return_value = result
    repository = CadastroRepository(session)

    assert await repository.list_duplicates(10, "pendente", " Maria ") == []

    statement = str(session.scalars.await_args.args[0]).lower()
    assert statement.count("exists") == 4
    assert statement.count("like lower") == 6
    assert "pessoa_id" in statement
    assert "pessoa_duplicada_id" in statement
    assert "nome_completo" in statement
    assert "nome_social" in statement
    assert "apelido" in statement


@pytest.mark.asyncio
async def test_duplicate_summary_counts_all_statuses() -> None:
    repository = AsyncMock()
    repository.duplicate_summary.return_value = {
        "pendentes": 1200,
        "confirmadas": 30,
        "descartadas": 8,
        "mescladas": 4,
    }
    service = CadastroService(repository)

    result = await service.duplicate_summary(make_actor())

    assert result.pendentes == 1200
    assert result.confirmadas == 30
    assert result.descartadas == 8
    assert result.mescladas == 4
    repository.duplicate_summary.assert_awaited_once_with(10)


@pytest.mark.asyncio
async def test_duplicate_summary_preserves_terminal_history() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = [("pendente", 2), ("mesclada", 5)]
    session.execute.return_value = result
    repository = CadastroRepository(session)

    summary = await repository.duplicate_summary(10)

    assert summary == {
        "pendentes": 2,
        "confirmadas": 0,
        "descartadas": 0,
        "mescladas": 5,
    }
    statement = str(session.execute.await_args.args[0])
    assert statement.count(" IN ") == 2
    assert statement.count("EXISTS") == 2


def test_cadastro_router_exposes_required_operational_routes() -> None:
    paths = {route.path for route in router.routes}
    assert {
        "/cadastro/pessoas",
        "/cadastro/pessoas/busca-rapida",
        "/cadastro/pessoas/{person_id}",
        "/cadastro/hierarquia",
        "/cadastro/nucleos-familiares",
        "/cadastro/comunidades",
        "/cadastro/tags",
        "/cadastro/duplicidades",
        "/cadastro/duplicidades/resumo",
        "/cadastro/duplicidades/{duplicate_id}",
        "/cadastro/duplicidades/{duplicate_id}/merge-preview",
        "/cadastro/duplicidades/{duplicate_id}/merge",
        "/cadastro/indicacoes/grafo",
    } <= paths


def test_duplicate_merge_requires_explicit_confirmation() -> None:
    with pytest.raises(ValidationError):
        PessoaMergeRequest(
            pessoa_principal_id=1,
            campos_origem=[],
            confirmar=False,  # type: ignore[arg-type]
        )


class GraphRepository:
    async def get_person(self, tenant_id: int, person_id: int) -> SimpleNamespace:
        return SimpleNamespace(id=person_id, tenant_id=tenant_id)

    async def indication_graph(
        self, tenant_id: int, **filters: object
    ) -> tuple[list[dict[str, object]], list[SimpleNamespace], bool]:
        return (
            [
                {
                    "id": 1,
                    "pessoa_indicante_id": 10,
                    "pessoa_indicada_id": 11,
                    "origem": "evento",
                    "contexto": None,
                    "data_indicacao": date(2026, 6, 30),
                }
            ],
            [
                SimpleNamespace(id=10, nome_social=None, nome_completo="Origem", ativo=True),
                SimpleNamespace(id=11, nome_social="Destino", nome_completo="Destino", ativo=True),
            ],
            False,
        )


def test_indication_graph_maps_nodes_and_direction() -> None:
    service = CadastroService(GraphRepository())  # type: ignore[arg-type]

    graph = asyncio.run(
        service.indication_graph(
            make_actor(),
            person_id=10,
            origin=None,
            date_from=None,
            date_to=None,
            depth=3,
            limit=100,
        )
    )

    assert {node.nome for node in graph.nodes} == {"Origem", "Destino"}
    assert graph.edges[0].origem_id == 10
    assert graph.edges[0].destino_id == 11


@pytest.mark.asyncio
async def test_indication_uses_url_person_as_indicator() -> None:
    repository = AsyncMock()
    repository.get_person.side_effect = lambda tenant_id, person_id: SimpleNamespace(
        id=person_id, tenant_id=tenant_id
    )
    repository.person_has_indication.return_value = False
    repository.add_indication.return_value = SimpleNamespace(
        id=50,
        tenant_id=10,
        pessoa_indicante_id=100,
        pessoa_indicada_id=200,
        pessoa_indicada_nome=None,
        origem="visita",
        contexto="Apresentacao no comite",
        data_indicacao=date(2026, 7, 21),
        criado_em=datetime.now(UTC),
    )
    service = CadastroService(repository)

    await service.add_indication(
        make_actor(),
        100,
        IndicacaoPessoaInput(
            pessoa_indicada_id=200,
            origem="visita",
            contexto="Apresentacao no comite",
            data_indicacao=date(2026, 7, 21),
        ),
    )

    args = repository.add_indication.await_args.args
    assert args[0:2] == (10, 200)
    assert args[2].pessoa_indicante_id == 100


@pytest.mark.asyncio
async def test_person_can_only_be_indicated_once() -> None:
    repository = AsyncMock()
    repository.get_person.side_effect = lambda tenant_id, person_id: SimpleNamespace(
        id=person_id, tenant_id=tenant_id
    )
    repository.person_has_indication.return_value = True
    service = CadastroService(repository)

    with pytest.raises(BusinessRuleError) as error:
        await service.add_indication(
            make_actor(), 100, IndicacaoPessoaInput(pessoa_indicada_id=200)
        )

    assert error.value.code == "person_already_indicated"
    repository.add_indication.assert_not_awaited()


def make_profile_actor(*profiles: str, lideranca_id: int | None = None) -> RequestActor:
    return RequestActor(
        tenant_id=10,
        user_id=20,
        session_id=30,
        profiles=profiles,
        permissions=frozenset({"cadastro.visualizar", "cadastro.editar"}),
        token="token",
        lideranca_id=lideranca_id,
    )


def _contact() -> SimpleNamespace:
    return SimpleNamespace(
        id=20,
        pessoa_id=10,
        tipo_contato="whatsapp",
        valor="11999999999",
        principal=True,
    )


@pytest.mark.asyncio
async def test_gestor_can_delete_person_contact() -> None:
    repository = AsyncMock()
    repository.contact.return_value = _contact()
    service = CadastroService(repository)

    await service.delete_contact(make_actor(), 10, 20)

    repository.delete_contact.assert_awaited_once()
    repository.commit.assert_awaited_once()
    repository.person_linked_to_leadership.assert_not_awaited()


@pytest.mark.asyncio
async def test_gestor_saas_can_delete_person_contact() -> None:
    repository = AsyncMock()
    repository.contact.return_value = _contact()
    service = CadastroService(repository)

    await service.delete_contact(make_profile_actor("gestor_saas"), 10, 20)

    repository.delete_contact.assert_awaited_once()


@pytest.mark.asyncio
async def test_leader_cannot_delete_person_contact() -> None:
    repository = AsyncMock()
    service = CadastroService(repository)

    with pytest.raises(AuthorizationError):
        await service.delete_contact(make_profile_actor("lider", lideranca_id=5), 10, 20)

    repository.person_linked_to_leadership.assert_not_awaited()
    repository.delete_contact.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_can_delete_contact_when_person_is_linked() -> None:
    repository = AsyncMock()
    repository.contact.return_value = _contact()
    repository.person_linked_to_leadership.return_value = True
    service = CadastroService(repository)

    await service.delete_contact(
        make_profile_actor("coordenador_territorial", lideranca_id=5), 10, 20
    )

    repository.person_linked_to_leadership.assert_awaited_once_with(10, 10, 5)
    repository.delete_contact.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_cannot_delete_contact_when_person_is_not_linked() -> None:
    repository = AsyncMock()
    repository.person_linked_to_leadership.return_value = False
    service = CadastroService(repository)

    with pytest.raises(AuthorizationError):
        await service.delete_contact(
            make_profile_actor("coordenador_territorial", lideranca_id=5), 10, 20
        )

    repository.delete_contact.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_without_leadership_cannot_delete_contact() -> None:
    repository = AsyncMock()
    service = CadastroService(repository)

    with pytest.raises(AuthorizationError):
        await service.delete_contact(make_profile_actor("coordenador_territorial"), 10, 20)

    repository.person_linked_to_leadership.assert_not_awaited()
    repository.delete_contact.assert_not_awaited()
