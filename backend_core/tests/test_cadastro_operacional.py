import asyncio
from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.auth.access import RequestActor
from app.core.errors import BusinessRuleError
from app.mod_cadastro.router import router
from app.mod_cadastro.service import CadastroService
from app.schemas.cadastro import (
    EleitorCreate,
    PessoaContatoCreate,
    PessoaDocumentoCreate,
)
from app.schemas.cadastro_operacional import (
    HierarquiaInput,
    PessoaCadastroCreate,
    PessoaFiltros,
    PessoaMergeRequest,
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
