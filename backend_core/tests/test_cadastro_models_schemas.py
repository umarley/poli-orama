from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app.models import (
    Eleitor,
    Endereco,
    Lideranca,
    Pessoa,
    PessoaContato,
    PessoaDocumento,
    PessoaEndereco,
    PessoaMerge,
)
from app.schemas.cadastro import PessoaCreate, PessoaResponse
from app.tenants.models import Base


@pytest.mark.parametrize(
    ("model", "table_name"),
    [
        (Pessoa, "pessoa"),
        (PessoaDocumento, "pessoa_documento"),
        (PessoaContato, "pessoa_contato"),
        (Endereco, "endereco"),
        (PessoaEndereco, "pessoa_endereco"),
        (Eleitor, "eleitor"),
        (Lideranca, "lideranca"),
        (PessoaMerge, "pessoa_merge"),
    ],
)
def test_cadastro_models_use_expected_schema(model: type, table_name: str) -> None:
    assert model.__table__.schema == "cadastro"
    assert model.__table__.name == table_name


def test_cadastro_mappers_and_central_relationships_are_configured() -> None:
    configure_mappers()

    assert set(Pessoa.__mapper__.relationships.keys()) == {
        "documentos",
        "contatos",
        "enderecos",
        "eleitor",
        "lideranca",
    }
    assert Pessoa.__mapper__.relationships["eleitor"].uselist is False
    assert Pessoa.__mapper__.relationships["lideranca"].uselist is False


def test_all_cadastro_foreign_keys_resolve_in_shared_metadata() -> None:
    cadastro_tables = [
        table for table in Base.metadata.tables.values() if table.schema == "cadastro"
    ]

    for table in cadastro_tables:
        for foreign_key in table.foreign_keys:
            assert foreign_key.column.table is not None


def test_database_constraints_cover_identity_and_domain_rules() -> None:
    document_constraints = PessoaDocumento.__table__.constraints
    document_unique = next(
        constraint
        for constraint in document_constraints
        if isinstance(constraint, UniqueConstraint) and constraint.name == "uq_pessoa_documento"
    )
    assert [column.name for column in document_unique.columns] == [
        "tenant_id",
        "tipo_documento",
        "numero",
    ]
    assert any(
        isinstance(constraint, CheckConstraint) and constraint.name == "ck_lideranca_meta_votos"
        for constraint in Lideranca.__table__.constraints
    )


def test_pessoa_create_accepts_complete_central_registration() -> None:
    payload = PessoaCreate.model_validate(
        {
            "nome_completo": "  Maria da Silva  ",
            "sexo": "F",
            "data_nascimento": "1985-04-12",
            "documentos": [{"tipo_documento": "cpf", "numero": "52998224725"}],
            "contatos": [
                {
                    "tipo_contato": "whatsapp",
                    "valor": "11999999999",
                    "principal": True,
                }
            ],
            "enderecos": [
                {
                    "tipo": "residencial",
                    "principal": True,
                    "endereco": {
                        "logradouro": "Rua Um",
                        "numero": "10",
                        "cep": "01001-000",
                        "latitude": "-23.5505200",
                        "longitude": "-46.6333080",
                    },
                }
            ],
            "eleitor": {"titulo_eleitor": "123456789012", "situacao_titulo": "regular"},
            "lideranca": {"tipo_lideranca": "lider", "meta_votos": 100},
        }
    )

    assert payload.nome_completo == "Maria da Silva"
    assert payload.data_nascimento == date(1985, 4, 12)
    assert payload.enderecos[0].endereco.latitude == Decimal("-23.5505200")
    assert payload.lideranca is not None
    assert payload.lideranca.meta_votos == 100


@pytest.mark.parametrize(
    "payload",
    [
        {"nome_completo": "Pessoa", "sexo": "X"},
        {
            "nome_completo": "Pessoa",
            "documentos": [{"tipo_documento": "certidao", "numero": "1"}],
        },
        {"nome_completo": "Pessoa", "lideranca": {"meta_votos": -1}},
        {
            "nome_completo": "Pessoa",
            "enderecos": [{"endereco": {"latitude": -91}}],
        },
    ],
)
def test_pessoa_create_rejects_values_outside_database_domains(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PessoaCreate.model_validate(payload)


def test_pessoa_response_can_be_built_from_attributes() -> None:
    now = datetime.now(UTC)
    pessoa = Pessoa(
        id=1,
        uuid_publico=uuid4(),
        tenant_id=2,
        nome_completo="Maria da Silva",
        nivel_engajamento=None,
        score_confiabilidade=None,
        completude_cadastral=None,
        ativo=True,
        criado_por=None,
        atualizado_por=None,
        criado_em=now,
        atualizado_em=now,
        excluido_em=None,
    )

    response = PessoaResponse.model_validate(pessoa)

    assert response.id == 1
    assert response.tenant_id == 2
    assert response.documentos == []
